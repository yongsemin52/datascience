import html
import re
import tempfile
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from wordcloud import WordCloud

try:
    from kiwipiepy import Kiwi
except ImportError:
    Kiwi = None


st.set_page_config(
    page_title="유튜브 댓글 분석기",
    page_icon="💬",
    layout="wide",
)

API_BASE = "https://www.googleapis.com/youtube/v3"

DEFAULT_STOPWORDS = {
    "영상", "댓글", "진짜", "정말", "너무", "그냥", "이거", "저거",
    "여기", "오늘", "지금", "사람", "생각", "부분", "느낌", "때문",
    "정도", "계속", "ㅋㅋ", "ㅋㅋㅋ", "ㅎㅎ", "ㅎㅎㅎ", "ㅠㅠ", "ㅜㅜ",
    "the", "and", "this", "that", "with", "you", "your", "for", "are",
    "was", "but", "not",
}


def extract_video_id(value: str):
    value = value.strip()

    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value

    try:
        parsed = urlparse(value)
    except ValueError:
        return None

    host = parsed.netloc.lower().split(":")[0]
    parts = [part for part in parsed.path.split("/") if part]
    candidate = None

    if host in {"youtu.be", "www.youtu.be"} and parts:
        candidate = parts[0]
    elif host.endswith("youtube.com"):
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [None])[0]
        elif len(parts) >= 2 and parts[0] in {"shorts", "embed", "live"}:
            candidate = parts[1]

    if candidate and re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
        return candidate

    return None


def youtube_get(endpoint: str, params: dict):
    try:
        response = requests.get(
            f"{API_BASE}/{endpoint}",
            params=params,
            timeout=20,
        )
    except requests.Timeout as exc:
        raise RuntimeError("YouTube API 응답 시간이 초과되었습니다.") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"네트워크 오류가 발생했습니다: {exc}") from exc

    if response.ok:
        return response.json()

    try:
        payload = response.json()
        message = payload.get("error", {}).get("message", "API 요청 실패")
        reasons = [
            item.get("reason", "")
            for item in payload.get("error", {}).get("errors", [])
        ]
    except ValueError:
        message = response.text or "API 요청 실패"
        reasons = []

    if "commentsDisabled" in reasons:
        raise RuntimeError("이 영상은 댓글이 비활성화되어 있습니다.")
    if response.status_code == 403:
        raise RuntimeError(
            "API 키 권한, 할당량 또는 YouTube Data API v3 활성화 상태를 확인하세요. "
            f"상세: {message}"
        )
    if response.status_code == 404:
        raise RuntimeError("영상을 찾을 수 없거나 공개 영상이 아닙니다.")

    raise RuntimeError(f"YouTube API 오류({response.status_code}): {message}")


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_video_info(api_key: str, video_id: str):
    data = youtube_get(
        "videos",
        {
            "part": "snippet,statistics",
            "id": video_id,
            "key": api_key,
        },
    )

    if not data.get("items"):
        raise RuntimeError("영상을 찾을 수 없거나 비공개 영상입니다.")

    item = data["items"][0]
    snippet = item["snippet"]
    stats = item.get("statistics", {})
    thumbnails = snippet.get("thumbnails", {})
    thumbnail = (
        thumbnails.get("high")
        or thumbnails.get("medium")
        or thumbnails.get("default")
        or {}
    ).get("url")

    return {
        "title": snippet.get("title", ""),
        "channel": snippet.get("channelTitle", ""),
        "thumbnail": thumbnail,
        "view_count": int(stats.get("viewCount", 0)),
        "like_count": int(stats.get("likeCount", 0)),
        "comment_count": int(stats.get("commentCount", 0)),
    }


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_comments(api_key: str, video_id: str, limit: int, order: str):
    comments = []
    page_token = None

    while len(comments) < limit:
        params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(100, limit - len(comments)),
            "order": order,
            "textFormat": "plainText",
            "key": api_key,
        }

        if page_token:
            params["pageToken"] = page_token

        data = youtube_get("commentThreads", params)

        for item in data.get("items", []):
            thread = item.get("snippet", {})
            top = thread.get("topLevelComment", {})
            snippet = top.get("snippet", {})

            comments.append(
                {
                    "작성자": snippet.get("authorDisplayName", "알 수 없음"),
                    "댓글": html.unescape(snippet.get("textDisplay", "")).strip(),
                    "좋아요": int(snippet.get("likeCount", 0)),
                    "답글": int(thread.get("totalReplyCount", 0)),
                    "작성시각": snippet.get("publishedAt"),
                }
            )

            if len(comments) >= limit:
                break

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return comments


def prepare_dataframe(comments):
    df = pd.DataFrame(comments)

    if df.empty:
        return df

    df["작성시각"] = pd.to_datetime(df["작성시각"], utc=True, errors="coerce")
    df["작성시각_KST"] = df["작성시각"].dt.tz_convert("Asia/Seoul")
    df["날짜"] = df["작성시각_KST"].dt.date
    df["시간"] = df["작성시각_KST"].dt.hour
    df["반응도"] = df["좋아요"] + df["답글"] * 2
    df["댓글길이"] = df["댓글"].str.len()

    return df


@st.cache_resource(show_spinner=False)
def get_kiwi():
    if Kiwi is None:
        return None
    return Kiwi()


def extract_words(texts, stopwords):
    joined = "\n".join(texts)
    words = []
    kiwi = get_kiwi()

    if kiwi is not None:
        allowed_tags = {"NNG", "NNP", "SL", "SN", "XR"}
        for token in kiwi.tokenize(joined):
            word = token.form.strip().lower()
            if token.tag in allowed_tags and len(word) >= 2:
                words.append(word)
    else:
        words = re.findall(r"[가-힣A-Za-z0-9]{2,}", joined.lower())

    cleaned = [
        word
        for word in words
        if word not in stopwords
        and not re.fullmatch(r"[ㅋㅎㅠㅜ]+", word)
        and not word.startswith("http")
    ]

    return Counter(cleaned)


def get_font_path(uploaded_font):
    if uploaded_font is not None:
        suffix = Path(uploaded_font.name).suffix.lower()
        if suffix not in {".ttf", ".otf", ".ttc"}:
            raise RuntimeError("TTF, OTF, TTC 글꼴만 업로드할 수 있습니다.")

        font_path = Path(tempfile.gettempdir()) / f"youtube_wc_font{suffix}"
        font_path.write_bytes(uploaded_font.getvalue())
        return str(font_path)

    candidates = [
        Path("assets/NanumGothic.ttf"),
        Path("assets/NotoSansKR-Regular.ttf"),
        Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("C:/Windows/Fonts/malgun.ttf"),
        Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return None


def create_wordcloud(frequencies, font_path):
    if not frequencies:
        return None

    cloud = WordCloud(
        width=1400,
        height=700,
        background_color="white",
        font_path=font_path,
        max_words=150,
        collocations=False,
        prefer_horizontal=0.9,
    )
    return cloud.generate_from_frequencies(dict(frequencies))


def fmt_number(value):
    return f"{int(value):,}"


st.title("💬 유튜브 댓글 분석기")
st.caption(
    "YouTube Data API v3를 이용해 댓글 작성 추이, 반응도, 워드클라우드를 분석합니다."
)

with st.sidebar:
    st.header("분석 설정")

    api_key = st.text_input(
        "YouTube Data API 키",
        type="password",
        help="입력한 API 키는 앱 코드에 저장되지 않습니다.",
    )

    video_input = st.text_input(
        "유튜브 영상 링크 또는 영상 ID",
        placeholder="https://www.youtube.com/watch?v=...",
    )

    comment_limit = st.number_input(
        "수집할 댓글 개수",
        min_value=10,
        max_value=5000,
        value=300,
        step=50,
    )

    order_label = st.radio(
        "댓글 정렬 기준",
        ["관련도순", "최신순"],
        horizontal=True,
    )
    order = "relevance" if order_label == "관련도순" else "time"

    custom_stopwords_text = st.text_area(
        "추가 불용어",
        placeholder="쉼표로 구분: 구독, 좋아요, 채널",
        height=90,
    )

    uploaded_font = st.file_uploader(
        "한글 글꼴 업로드(선택)",
        type=["ttf", "otf", "ttc"],
    )

    analyze = st.button(
        "댓글 분석 시작",
        type="primary",
        use_container_width=True,
    )


if not analyze:
    st.info("왼쪽에서 API 키와 영상 링크를 입력한 뒤 분석을 시작하세요.")
    st.markdown(
        """
        ### 제공 기능
        - 날짜별 댓글 작성 추이
        - 한국 시간 기준 시간대별 댓글 분포
        - 좋아요와 답글 기반 반응도 분석
        - 빈출 단어 및 워드클라우드
        - 댓글 데이터 CSV 다운로드
        """
    )
    st.stop()


if not api_key.strip():
    st.error("YouTube Data API 키를 입력하세요.")
    st.stop()


video_id = extract_video_id(video_input)

if not video_id:
    st.error("올바른 유튜브 영상 링크 또는 11자리 영상 ID를 입력하세요.")
    st.stop()


progress = st.progress(0, text="영상 정보를 불러오는 중입니다.")

try:
    video_info = fetch_video_info(api_key.strip(), video_id)

    progress.progress(25, text="댓글을 수집하는 중입니다.")
    comments = fetch_comments(
        api_key.strip(),
        video_id,
        int(comment_limit),
        order,
    )

    progress.progress(65, text="댓글 데이터를 분석하는 중입니다.")
    df = prepare_dataframe(comments)

    if df.empty:
        progress.empty()
        st.warning("수집 가능한 공개 댓글이 없습니다.")
        st.stop()

    custom_stopwords = {
        word.strip().lower()
        for word in custom_stopwords_text.split(",")
        if word.strip()
    }

    frequencies = extract_words(
        df["댓글"].dropna().tolist(),
        DEFAULT_STOPWORDS | custom_stopwords,
    )

    font_path = get_font_path(uploaded_font)

    progress.progress(85, text="워드클라우드를 만드는 중입니다.")

    wordcloud = None
    wordcloud_error = None

    try:
        wordcloud = create_wordcloud(frequencies, font_path)
    except Exception as exc:
        wordcloud_error = str(exc)

    progress.progress(100, text="분석이 완료되었습니다.")
    progress.empty()

except RuntimeError as exc:
    progress.empty()
    st.error(str(exc))
    st.stop()
except Exception as exc:
    progress.empty()
    st.error(f"예상하지 못한 오류가 발생했습니다: {exc}")
    st.stop()


left, right = st.columns([1, 3])

with left:
    if video_info["thumbnail"]:
        st.image(video_info["thumbnail"], use_container_width=True)

with right:
    st.subheader(video_info["title"])
    st.write(f"채널: **{video_info['channel']}**")

    metric_cols = st.columns(4)
    metric_cols[0].metric("조회수", fmt_number(video_info["view_count"]))
    metric_cols[1].metric("영상 좋아요", fmt_number(video_info["like_count"]))
    metric_cols[2].metric("영상 댓글 수", fmt_number(video_info["comment_count"]))
    metric_cols[3].metric("실제 수집", fmt_number(len(df)))


st.divider()
st.subheader("분석 요약")

summary_cols = st.columns(5)
summary_cols[0].metric("수집 댓글", fmt_number(len(df)))
summary_cols[1].metric("좋아요 합계", fmt_number(df["좋아요"].sum()))
summary_cols[2].metric("답글 합계", fmt_number(df["답글"].sum()))
summary_cols[3].metric("평균 좋아요", f"{df['좋아요'].mean():.1f}")
summary_cols[4].metric("평균 댓글 길이", f"{df['댓글길이'].mean():.1f}자")


tab1, tab2, tab3, tab4 = st.tabs(
    ["⏱ 작성 추이", "🔥 댓글 반응도", "☁️ 워드클라우드", "📄 원본 데이터"]
)


with tab1:
    st.markdown("#### 날짜별 댓글 작성 추이")

    daily = (
        df.groupby("날짜", as_index=False)
        .size()
        .rename(columns={"size": "댓글 수"})
    )
    daily["날짜"] = pd.to_datetime(daily["날짜"])

    daily_fig = px.line(
        daily,
        x="날짜",
        y="댓글 수",
        markers=True,
    )
    daily_fig.update_layout(
        hovermode="x unified",
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(daily_fig, use_container_width=True)

    st.markdown("#### 시간대별 댓글 작성 분포")

    hourly = (
        df.groupby("시간")
        .size()
        .reindex(range(24), fill_value=0)
        .rename("댓글 수")
        .reset_index()
    )
    hourly["시간대"] = hourly["시간"].map(lambda hour: f"{hour:02d}시")

    hourly_fig = px.bar(
        hourly,
        x="시간대",
        y="댓글 수",
        text_auto=True,
    )
    hourly_fig.update_layout(
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(hourly_fig, use_container_width=True)

    st.caption("시간대는 한국 표준시(KST, UTC+9)를 기준으로 표시합니다.")


with tab2:
    st.caption(
        "반응도 = 좋아요 수 + 답글 수 × 2로 계산합니다."
    )

    scatter = px.scatter(
        df,
        x="좋아요",
        y="답글",
        size="반응도",
        hover_name="작성자",
        hover_data={"댓글": True, "반응도": True},
    )
    scatter.update_layout(
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(scatter, use_container_width=True)

    st.markdown("#### 반응도 상위 댓글")

    max_top = min(30, len(df))
    default_top = min(10, len(df))

    top_n = st.slider(
        "표시할 댓글 수",
        min_value=1,
        max_value=max_top,
        value=default_top,
    )

    top_df = (
        df.nlargest(top_n, "반응도")[
            ["작성자", "댓글", "좋아요", "답글", "반응도", "작성시각_KST"]
        ]
        .copy()
    )
    top_df["작성시각_KST"] = top_df["작성시각_KST"].dt.strftime(
        "%Y-%m-%d %H:%M"
    )

    st.dataframe(
        top_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "댓글": st.column_config.TextColumn(width="large"),
        },
    )


with tab3:
    word_col, rank_col = st.columns([2, 1])

    with word_col:
        st.markdown("#### 댓글 워드클라우드")

        if not frequencies:
            st.warning("워드클라우드에 사용할 단어가 없습니다.")
        elif wordcloud_error:
            st.warning(f"워드클라우드 생성 실패: {wordcloud_error}")
        elif wordcloud is not None:
            st.image(wordcloud.to_array(), use_container_width=True)

            if font_path is None:
                st.warning(
                    "한글 글꼴을 찾지 못했습니다. 글자가 네모로 보이면 "
                    "사이드바에서 TTF 또는 OTF 글꼴을 업로드하세요."
                )

    with rank_col:
        st.markdown("#### 빈출 단어")

        word_df = pd.DataFrame(
            frequencies.most_common(30),
            columns=["단어", "빈도"],
        )

        st.dataframe(
            word_df,
            use_container_width=True,
            hide_index=True,
        )


with tab4:
    export_df = df[
        ["작성자", "댓글", "좋아요", "답글", "반응도", "작성시각_KST"]
    ].copy()

    export_df["작성시각_KST"] = export_df["작성시각_KST"].dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    st.dataframe(
        export_df,
        use_container_width=True,
        hide_index=True,
        height=500,
    )

    csv_data = export_df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "CSV 파일 다운로드",
        data=csv_data,
        file_name=f"youtube_comments_{video_id}.csv",
        mime="text/csv",
    )


st.caption(
    "※ 공개된 상위 댓글만 분석하며, 삭제·차단된 댓글과 답글 본문은 포함하지 않습니다."
)

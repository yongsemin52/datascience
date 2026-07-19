from pathlib import Path
import textwrap, zipfile, os, json

base = Path("/mnt/data/youtube_comment_analyzer")
base.mkdir(exist_ok=True)

app_py = r'''
import html
import re
import tempfile
from collections import Counter
from datetime import timezone
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

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
REQUEST_TIMEOUT = 20

DEFAULT_STOPWORDS = {
    "영상", "댓글", "진짜", "정말", "너무", "그냥", "이거", "저거", "여기",
    "오늘", "지금", "사람", "생각", "부분", "느낌", "때문", "정도", "계속",
    "ㅋㅋ", "ㅋㅋㅋ", "ㅎㅎ", "ㅎㅎㅎ", "ㅠㅠ", "ㅜㅜ", "the", "and", "this",
    "that", "with", "you", "your", "for", "are", "was", "but", "not",
}


def extract_video_id(value: str) -> str | None:
    """유튜브 URL 또는 11자리 영상 ID에서 videoId를 추출한다."""
    value = value.strip()

    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value

    try:
        parsed = urlparse(value)
    except ValueError:
        return None

    host = parsed.netloc.lower().split(":")[0]
    path_parts = [part for part in parsed.path.split("/") if part]

    if host in {"youtu.be", "www.youtu.be"} and path_parts:
        candidate = path_parts[0]
    elif host.endswith("youtube.com"):
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [None])[0]
        elif len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live"}:
            candidate = path_parts[1]
        else:
            candidate = None
    else:
        candidate = None

    if candidate and re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
        return candidate
    return None


def youtube_get(endpoint: str, params: dict) -> dict:
    response = requests.get(
        f"{YOUTUBE_API_BASE}/{endpoint}",
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    if response.ok:
        return response.json()

    try:
        error_data = response.json()
        message = (
            error_data.get("error", {})
            .get("message", "YouTube API 요청에 실패했습니다.")
        )
        reasons = [
            item.get("reason", "")
            for item in error_data.get("error", {}).get("errors", [])
        ]
    except ValueError:
        message = response.text or "YouTube API 요청에 실패했습니다."
        reasons = []

    if "commentsDisabled" in reasons:
        raise RuntimeError("이 영상은 댓글이 비활성화되어 있습니다.")
    if response.status_code == 403:
        raise RuntimeError(
            "API 키 권한·할당량 또는 YouTube Data API v3 활성화 상태를 확인하세요. "
            f"상세 메시지: {message}"
        )
    if response.status_code == 400:
        raise RuntimeError(f"영상 링크 또는 요청값을 확인하세요. 상세 메시지: {message}")
    if response.status_code == 404:
        raise RuntimeError("영상을 찾을 수 없거나 공개적으로 접근할 수 없습니다.")

    raise RuntimeError(f"YouTube API 오류({response.status_code}): {message}")


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_video_info(api_key: str, video_id: str) -> dict:
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
    statistics = item.get("statistics", {})

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
        "published_at": snippet.get("publishedAt"),
        "thumbnail": thumbnail,
        "view_count": int(statistics.get("viewCount", 0)),
        "like_count": int(statistics.get("likeCount", 0)),
        "comment_count": int(statistics.get("commentCount", 0)),
    }


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_comments(
    api_key: str,
    video_id: str,
    limit: int,
    order: str,
) -> list[dict]:
    """YouTube Data API로 상위 댓글을 페이지네이션하여 수집한다."""
    comments: list[dict] = []
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
            thread_snippet = item.get("snippet", {})
            top_comment = thread_snippet.get("topLevelComment", {})
            snippet = top_comment.get("snippet", {})

            text = html.unescape(snippet.get("textDisplay", "")).strip()
            comments.append(
                {
                    "comment_id": top_comment.get("id", ""),
                    "author": snippet.get("authorDisplayName", "알 수 없음"),
                    "text": text,
                    "like_count": int(snippet.get("likeCount", 0)),
                    "reply_count": int(thread_snippet.get("totalReplyCount", 0)),
                    "published_at": snippet.get("publishedAt"),
                    "updated_at": snippet.get("updatedAt"),
                }
            )

            if len(comments) >= limit:
                break

        page_token = data.get("nextPageToken")
        if not page_token or not data.get("items"):
            break

    return comments


def prepare_dataframe(comments: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(comments)
    if df.empty:
        return df

    df["published_at"] = pd.to_datetime(
        df["published_at"], utc=True, errors="coerce"
    )
    df["updated_at"] = pd.to_datetime(
        df["updated_at"], utc=True, errors="coerce"
    )

    # 한국 표준시로 변환
    df["published_kst"] = df["published_at"].dt.tz_convert("Asia/Seoul")
    df["date"] = df["published_kst"].dt.date
    df["hour"] = df["published_kst"].dt.hour

    # 댓글 반응도: 좋아요와 답글을 함께 반영한 단순 지표
    df["reaction_score"] = df["like_count"] + (df["reply_count"] * 2)
    df["text_length"] = df["text"].str.len()
    return df


@st.cache_resource(show_spinner=False)
def get_kiwi():
    if Kiwi is None:
        return None
    return Kiwi()


def extract_words(texts: list[str], stopwords: set[str]) -> Counter:
    joined = "\n".join(texts)
    kiwi = get_kiwi()
    words: list[str] = []

    if kiwi is not None:
        allowed_tags = {"NNG", "NNP", "SL", "SN", "XR"}
        for token in kiwi.tokenize(joined):
            word = token.form.strip().lower()
            if token.tag in allowed_tags and len(word) >= 2:
                words.append(word)
    else:
        # Kiwi를 불러오지 못했을 때의 가벼운 대체 처리
        words = re.findall(r"[가-힣A-Za-z0-9]{2,}", joined.lower())

    cleaned = [
        word
        for word in words
        if word not in stopwords
        and not re.fullmatch(r"[ㅋㅎㅠㅜ]+", word)
        and not word.startswith("http")
    ]
    return Counter(cleaned)


def save_uploaded_font(uploaded_font) -> str | None:
    if uploaded_font is None:
        return None

    suffix = Path(uploaded_font.name).suffix.lower()
    if suffix not in {".ttf", ".otf", ".ttc"}:
        raise ValueError("TTF, OTF 또는 TTC 글꼴 파일만 사용할 수 있습니다.")

    temp_dir = Path(tempfile.gettempdir()) / "youtube_comment_analyzer"
    temp_dir.mkdir(parents=True, exist_ok=True)
    font_path = temp_dir / f"wordcloud_font{suffix}"
    font_path.write_bytes(uploaded_font.getvalue())
    return str(font_path)


def find_local_korean_font() -> str | None:
    candidates = [
        Path("assets/NanumGothic.ttf"),
        Path("assets/NotoSansKR-Regular.ttf"),
        Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("C:/Windows/Fonts/malgun.ttf"),
        Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


def make_wordcloud(frequencies: Counter, font_path: str | None):
    if not frequencies:
        return None

    wc = WordCloud(
        width=1400,
        height=700,
        background_color="white",
        font_path=font_path,
        collocations=False,
        max_words=150,
        prefer_horizontal=0.9,
    )
    return wc.generate_from_frequencies(dict(frequencies))


def format_number(value: int) -> str:
    return f"{int(value):,}"


st.title("💬 유튜브 댓글 분석기")
st.caption(
    "YouTube Data API v3를 이용해 상위 댓글의 작성 추이, 반응도, 주요 단어를 분석합니다."
)

with st.sidebar:
    st.header("분석 설정")

    api_key = st.text_input(
        "YouTube Data API 키",
        type="password",
        help="입력한 키는 브라우저 세션에서만 사용하며 코드에 저장하지 않습니다.",
    )
    video_url = st.text_input(
        "유튜브 영상 링크 또는 영상 ID",
        placeholder="https://www.youtube.com/watch?v=...",
    )
    comment_limit = st.number_input(
        "수집할 댓글 개수",
        min_value=10,
        max_value=5000,
        value=300,
        step=50,
        help="API가 반환할 수 있는 공개 상위 댓글 범위 안에서 수집합니다.",
    )
    order_label = st.radio(
        "댓글 정렬 기준",
        ["관련도순", "최신순"],
        horizontal=True,
    )
    order = "relevance" if order_label == "관련도순" else "time"

    custom_stopwords_text = st.text_area(
        "추가 불용어",
        placeholder="단어를 쉼표로 구분하세요. 예: 채널, 구독, 좋아요",
        height=90,
    )
    uploaded_font = st.file_uploader(
        "워드클라우드용 한글 글꼴(선택)",
        type=["ttf", "otf", "ttc"],
        help="저장소의 assets/NanumGothic.ttf를 사용해도 됩니다.",
    )

    analyze_button = st.button(
        "댓글 분석 시작",
        type="primary",
        use_container_width=True,
    )

if not analyze_button:
    st.info("왼쪽에서 API 키와 영상 링크를 입력한 뒤 **댓글 분석 시작**을 누르세요.")
    st.markdown(
        """
        **제공 기능**
        - 댓글 작성 날짜 추이와 0~23시 시간대 분포
        - 좋아요·답글 수 및 반응도 상위 댓글
        - 한국어 형태소 기반 빈출 단어와 워드클라우드
        - 분석 결과 CSV 다운로드
        """
    )
    st.stop()

if not api_key.strip():
    st.error("YouTube Data API 키를 입력하세요.")
    st.stop()

video_id = extract_video_id(video_url)
if not video_id:
    st.error("올바른 유튜브 영상 링크 또는 11자리 영상 ID를 입력하세요.")
    st.stop()

progress = st.progress(0, text="영상 정보를 불러오는 중입니다.")

try:
    video_info = fetch_video_info(api_key.strip(), video_id)
    progress.progress(20, text="댓글을 수집하는 중입니다.")

    comments = fetch_comments(
        api_key.strip(),
        video_id,
        int(comment_limit),
        order,
    )
    progress.progress(70, text="댓글 데이터를 정리하는 중입니다.")

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
    stopwords = DEFAULT_STOPWORDS | custom_stopwords
    frequencies = extract_words(df["text"].dropna().tolist(), stopwords)

    try:
        font_path = save_uploaded_font(uploaded_font)
    except ValueError as error:
        st.error(str(error))
        st.stop()

    font_path = font_path or find_local_korean_font()
    progress.progress(90, text="차트와 워드클라우드를 만드는 중입니다.")

    wordcloud = None
    wordcloud_error = None
    try:
        wordcloud = make_wordcloud(frequencies, font_path)
    except Exception as error:
        wordcloud_error = str(error)

    progress.progress(100, text="분석이 완료되었습니다.")
    progress.empty()

except requests.Timeout:
    progress.empty()
    st.error("YouTube API 응답 시간이 초과되었습니다. 잠시 후 다시 시도하세요.")
    st.stop()
except requests.RequestException as error:
    progress.empty()
    st.error(f"네트워크 요청 중 오류가 발생했습니다: {error}")
    st.stop()
except RuntimeError as error:
    progress.empty()
    st.error(str(error))
    st.stop()
except Exception as error:
    progress.empty()
    st.error(f"예상하지 못한 오류가 발생했습니다: {error}")
    st.stop()


# 영상 정보
header_left, header_right = st.columns([1, 3])
with header_left:
    if video_info["thumbnail"]:
        st.image(video_info["thumbnail"], use_container_width=True)
with header_right:
    st.subheader(video_info["title"])
    st.write(f"채널: **{video_info['channel']}**")
    st.caption(f"영상 ID: {video_id}")

    metric_cols = st.columns(4)
    metric_cols[0].metric("영상 조회수", format_number(video_info["view_count"]))
    metric_cols[1].metric("영상 좋아요", format_number(video_info["like_count"]))
    metric_cols[2].metric(
        "공개 댓글 수",
        format_number(video_info["comment_count"]),
    )
    metric_cols[3].metric("실제 수집", format_number(len(df)))

st.divider()

# 전체 댓글 지표
st.subheader("분석 요약")
summary_cols = st.columns(5)
summary_cols[0].metric("수집 댓글", format_number(len(df)))
summary_cols[1].metric("좋아요 합계", format_number(df["like_count"].sum()))
summary_cols[2].metric("답글 합계", format_number(df["reply_count"].sum()))
summary_cols[3].metric(
    "평균 좋아요",
    f"{df['like_count'].mean():.1f}",
)
summary_cols[4].metric(
    "평균 댓글 길이",
    f"{df['text_length'].mean():.1f}자",
)

tab_time, tab_reaction, tab_words, tab_data = st.tabs(
    ["⏱ 작성 추이", "🔥 댓글 반응도", "☁️ 워드클라우드", "📄 원본 데이터"]
)

with tab_time:
    st.markdown("#### 날짜별 댓글 작성 추이")
    daily = (
        df.groupby("date", as_index=False)
        .size()
        .rename(columns={"size": "댓글 수"})
    )
    daily["date"] = pd.to_datetime(daily["date"])

    daily_fig = px.line(
        daily,
        x="date",
        y="댓글 수",
        markers=True,
        labels={"date": "작성일"},
    )
    daily_fig.update_layout(
        hovermode="x unified",
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(daily_fig, use_container_width=True)

    st.markdown("#### 시간대별 댓글 작성 분포")
    hourly = (
        df.groupby("hour")
        .size()
        .reindex(range(24), fill_value=0)
        .rename("댓글 수")
        .reset_index()
        .rename(columns={"hour": "시간"})
    )
    hourly["시간대"] = hourly["시간"].map(lambda hour: f"{hour:02d}시")

    hourly_fig = px.bar(
        hourly,
        x="시간대",
        y="댓글 수",
        text_auto=True,
    )
    hourly_fig.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(hourly_fig, use_container_width=True)
    st.caption("시간대는 한국 표준시(KST, UTC+9)를 기준으로 표시합니다.")

with tab_reaction:
    st.caption(
        "반응도 점수 = 좋아요 수 + (답글 수 × 2). "
        "답글이 달린 댓글을 조금 더 강한 반응으로 간주한 자체 지표입니다."
    )

    reaction_fig = px.scatter(
        df,
        x="like_count",
        y="reply_count",
        size="reaction_score",
        hover_name="author",
        hover_data={"text": True, "reaction_score": True},
        labels={
            "like_count": "좋아요 수",
            "reply_count": "답글 수",
            "reaction_score": "반응도",
        },
    )
    reaction_fig.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(reaction_fig, use_container_width=True)

    st.markdown("#### 반응도 상위 댓글")
    top_n = st.slider(
        "표시할 댓글 수",
        min_value=5,
        max_value=min(30, len(df)),
        value=min(10, len(df)),
        key="top_n",
    )
    top_comments = (
        df.nlargest(top_n, "reaction_score")[
            [
                "author",
                "text",
                "like_count",
                "reply_count",
                "reaction_score",
                "published_kst",
            ]
        ]
        .copy()
    )
    top_comments.columns = [
        "작성자",
        "댓글",
        "좋아요",
        "답글",
        "반응도",
        "작성 시각(KST)",
    ]
    top_comments["작성 시각(KST)"] = top_comments["작성 시각(KST)"].dt.strftime(
        "%Y-%m-%d %H:%M"
    )
    st.dataframe(
        top_comments,
        use_container_width=True,
        hide_index=True,
        column_config={
            "댓글": st.column_config.TextColumn(width="large"),
            "좋아요": st.column_config.NumberColumn(format="%d"),
            "답글": st.column_config.NumberColumn(format="%d"),
            "반응도": st.column_config.NumberColumn(format="%d"),
        },
    )

with tab_words:
    word_col, rank_col = st.columns([2, 1])

    with word_col:
        st.markdown("#### 댓글 워드클라우드")
        if not frequencies:
            st.warning("불용어를 제외한 뒤 워드클라우드에 사용할 단어가 없습니다.")
        elif wordcloud_error:
            st.warning(f"워드클라우드를 만들지 못했습니다: {wordcloud_error}")
        elif wordcloud is not None:
            st.image(wordcloud.to_array(), use_container_width=True)
            if font_path is None:
                st.warning(
                    "한글 글꼴을 찾지 못했습니다. 글자가 네모로 보이면 "
                    "사이드바에서 TTF/OTF 글꼴을 업로드하거나 "
                    "저장소의 assets 폴더에 NanumGothic.ttf를 추가하세요."
                )

    with rank_col:
        st.markdown("#### 빈출 단어")
        top_words = pd.DataFrame(
            frequencies.most_common(30),
            columns=["단어", "빈도"],
        )
        st.dataframe(top_words, use_container_width=True, hide_index=True)

with tab_data:
    display_df = df[
        [
            "author",
            "text",
            "like_count",
            "reply_count",
            "reaction_score",
            "published_kst",
        ]
    ].copy()
    display_df.columns = [
        "작성자",
        "댓글",
        "좋아요",
        "답글",
        "반응도",
        "작성 시각(KST)",
    ]
    display_df["작성 시각(KST)"] = display_df["작성 시각(KST)"].dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=500,
    )

    csv_data = display_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "CSV 파일 다운로드",
        data=csv_data,
        file_name=f"youtube_comments_{video_id}.csv",
        mime="text/csv",
    )

st.caption(
    "※ 이 앱은 공개된 상위 댓글만 분석합니다. 삭제·차단·보류된 댓글 및 모든 답글 본문은 포함하지 않습니다."
)
'''

requirements = '''
streamlit>=1.40,<2
pandas>=2.2,<3
plotly>=5.24,<7
requests>=2.32,<3
wordcloud>=1.9.4,<2
kiwipiepy>=0.20,<1
'''

readme = r'''
# 유튜브 댓글 분석기

YouTube Data API v3를 이용해 유튜브 영상의 공개 상위 댓글을 수집하고 다음 항목을 분석하는 Streamlit 앱입니다.

- 날짜별 댓글 작성 추이
- 0~23시 시간대별 댓글 분포(KST)
- 좋아요·답글 기반 댓글 반응도
- 한국어 형태소 기반 빈출 단어와 워드클라우드
- CSV 다운로드

## 파일 구조

```text
youtube_comment_analyzer/
├─ app.py
├─ requirements.txt
└─ assets/
   └─ NanumGothic.ttf   # 선택 사항

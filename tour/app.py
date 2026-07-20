from pathlib import Path
import shutil
import zipfile
import py_compile

project = Path("/mnt/data/tour_app_clean")
if project.exists():
    shutil.rmtree(project)
project.mkdir()

app_code = '''import html
import random
import re
from urllib.parse import quote

import requests
import streamlit as st


st.set_page_config(
    page_title="랜덤 국내여행 뽑기",
    page_icon="🎲",
    layout="wide",
)

API_BASE = "https://apis.data.go.kr/B551011/KorService2"

AREA_CODES = {
    "전국": "",
    "서울": "1",
    "인천": "2",
    "대전": "3",
    "대구": "4",
    "광주": "5",
    "부산": "6",
    "울산": "7",
    "세종": "8",
    "경기": "31",
    "강원": "32",
    "충북": "33",
    "충남": "34",
    "경북": "35",
    "경남": "36",
    "전북": "37",
    "전남": "38",
    "제주": "39",
}

CONTENT_TYPES = {
    "관광지": "12",
    "문화시설": "14",
    "축제·행사": "15",
    "여행코스": "25",
    "레포츠": "28",
    "숙박": "32",
    "쇼핑": "38",
    "음식점": "39",
}


def init_state():
    defaults = {
        "destination": None,
        "candidate_pool": [],
        "favorites": [],
        "error": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_api_key():
    try:
        return str(st.secrets["TOUR_API_KEY"]).strip()
    except (KeyError, FileNotFoundError):
        return ""


def clean_text(value):
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(value))
    text = html.unescape(text)
    return re.sub(r"\\s+", " ", text).strip()


def normalize_items(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


@st.cache_data(ttl=3600, show_spinner=False)
def call_api(operation, api_key, frozen_params):
    params = dict(frozen_params)
    params.update(
        {
            "serviceKey": api_key,
            "MobileOS": "ETC",
            "MobileApp": "RandomKoreaTrip",
            "_type": "json",
        }
    )

    response = requests.get(
        f"{API_BASE}/{operation}",
        params=params,
        timeout=20,
    )
    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError as exc:
        preview = response.text[:150]
        raise RuntimeError(
            "TourAPI가 JSON이 아닌 응답을 반환했어요. "
            f"인증키와 활용 신청 상태를 확인하세요. 응답: {preview}"
        ) from exc

    api_response = payload.get("response", {})
    header = api_response.get("header", {})
    result_code = str(header.get("resultCode", ""))

    if result_code not in {"0000", "0"}:
        result_message = header.get("resultMsg", "알 수 없는 오류")
        raise RuntimeError(f"TourAPI 오류 {result_code}: {result_message}")

    body = api_response.get("body", {})
    items = body.get("items", {})
    if not isinstance(items, dict):
        return []

    return normalize_items(items.get("item"))


def get_candidates(api_key, area_code, content_types, rows):
    combined = []

    for content_type in content_types:
        params = {
            "numOfRows": str(rows),
            "pageNo": "1",
            "arrange": "R",
            "areaCode": area_code,
            "sigunguCode": "",
            "contentTypeId": content_type,
        }
        combined.extend(
            call_api(
                "areaBasedList2",
                api_key,
                tuple(sorted(params.items())),
            )
        )

    unique = {}
    for item in combined:
        content_id = str(item.get("contentid", "")).strip()
        title = clean_text(item.get("title"))
        if content_id and title:
            unique[content_id] = item

    return list(unique.values())


def get_detail(api_key, content_id):
    params = {
        "contentId": str(content_id),
        "defaultYN": "Y",
        "firstImageYN": "Y",
        "areacodeYN": "Y",
        "catcodeYN": "Y",
        "addrinfoYN": "Y",
        "mapinfoYN": "Y",
        "overviewYN": "Y",
    }
    items = call_api(
        "detailCommon2",
        api_key,
        tuple(sorted(params.items())),
    )
    return items[0] if items else {}


def make_destination(item, detail):
    data = {**item, **detail}
    address = " ".join(
        part
        for part in [
            clean_text(data.get("addr1")),
            clean_text(data.get("addr2")),
        ]
        if part
    )

    return {
        "contentid": str(data.get("contentid", "")),
        "title": clean_text(data.get("title")) or "이름 없는 여행지",
        "address": address or "주소 정보 없음",
        "overview": clean_text(data.get("overview"))
        or "상세 소개가 제공되지 않은 장소예요.",
        "image": data.get("firstimage") or data.get("firstimage2") or "",
        "tel": clean_text(data.get("tel")) or "문의 정보 없음",
    }


def choose_destination(api_key, pool, previous_id=""):
    choices = [
        item
        for item in pool
        if str(item.get("contentid", "")) != previous_id
    ] or pool

    if not choices:
        return None

    item = random.choice(choices)
    detail = get_detail(api_key, item["contentid"])
    return make_destination(item, detail)


def save_favorite(destination):
    saved_ids = {item["contentid"] for item in st.session_state.favorites}

    if destination["contentid"] in saved_ids:
        st.info("이미 찜한 여행지예요.")
        return

    st.session_state.favorites.append(destination)
    st.success("찜 목록에 추가했어요.")


def show_destination(destination):
    st.markdown(
        f"""
        <div class="result-card">
            <div class="pin">📍</div>
            <h2>{html.escape(destination["title"])}</h2>
            <p>{html.escape(destination["address"])}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if destination["image"]:
        st.image(
            destination["image"],
            caption="사진 제공: 한국관광공사 TourAPI",
            use_container_width=True,
        )
    else:
        st.info("등록된 대표 이미지가 없는 여행지예요.")

    st.subheader("여행지 소개")
    st.write(destination["overview"])

    info1, info2 = st.columns(2)
    with info1:
        st.markdown("**주소**")
        st.write(destination["address"])
    with info2:
        st.markdown("**문의**")
        st.write(destination["tel"])

    map_query = quote(destination["title"])
    search_query = quote(f'{destination["title"]} 여행')

    link1, link2 = st.columns(2)
    with link1:
        st.link_button(
            "🗺️ 네이버 지도 검색",
            f"https://map.naver.com/p/search/{map_query}",
            use_container_width=True,
        )
    with link2:
        st.link_button(
            "🔎 여행 정보 검색",
            f"https://search.naver.com/search.naver?query={search_query}",
            use_container_width=True,
        )


def main():
    init_state()
    api_key = get_api_key()

    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(180deg, #fff9f2 0%, #f2faff 100%);
        }
        .hero {
            text-align: center;
            padding: 1rem 0 1.5rem;
        }
        .hero h1 {
            font-size: 2.55rem;
            margin-bottom: 0.35rem;
        }
        .hero p {
            color: #5f6770;
        }
        .result-card {
            text-align: center;
            padding: 1.6rem;
            margin: 1.2rem 0;
            border-radius: 24px;
            background: rgba(255, 255, 255, 0.95);
            border: 1px solid rgba(0, 0, 0, 0.08);
            box-shadow: 0 12px 28px rgba(0, 0, 0, 0.07);
        }
        .result-card h2 {
            margin: 0.2rem 0;
            font-size: 2.15rem;
        }
        .pin {
            font-size: 2.7rem;
        }
        </style>
        <div class="hero">
            <h1>🎲 랜덤 국내여행 뽑기</h1>
            <p>한국관광공사 TourAPI의 실제 관광정보에서 여행지를 추천해요.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not api_key:
        st.error("TourAPI 인증키가 설정되지 않았어요.")
        st.markdown("Streamlit Cloud의 **App settings → Secrets**에 입력하세요.")
        st.code(
            'TOUR_API_KEY = "공공데이터포털에서 발급받은 일반 인증키"',
            language="toml",
        )
        st.stop()

    draw_tab, favorites_tab = st.tabs(["🎲 여행지 뽑기", "❤️ 찜 목록"])

    with draw_tab:
        with st.container(border=True):
            col1, col2 = st.columns(2)

            with col1:
                selected_area = st.selectbox(
                    "지역",
                    list(AREA_CODES.keys()),
                    key="area_select",
                )

            with col2:
                selected_types = st.multiselect(
                    "관광 유형",
                    list(CONTENT_TYPES.keys()),
                    default=["관광지"],
                    key="type_select",
                )

            rows = st.slider(
                "유형별 후보 개수",
                min_value=20,
                max_value=100,
                value=60,
                step=20,
                key="rows_slider",
            )

            if st.button(
                "🎲 여행지 뽑기",
                type="primary",
                use_container_width=True,
                key="draw_button",
            ):
                if not selected_types:
                    st.warning("관광 유형을 한 개 이상 선택해 주세요.")
                else:
                    try:
                        with st.spinner("여행지를 찾고 있어요..."):
                            pool = get_candidates(
                                api_key,
                                AREA_CODES[selected_area],
                                [CONTENT_TYPES[name] for name in selected_types],
                                rows,
                            )
                            destination = choose_destination(api_key, pool)

                        st.session_state.candidate_pool = pool
                        st.session_state.destination = destination
                        st.session_state.error = ""

                        if destination is None:
                            st.warning("조건에 맞는 관광정보를 찾지 못했어요.")
                    except (requests.RequestException, RuntimeError) as exc:
                        st.session_state.destination = None
                        st.session_state.error = str(exc)

        if st.session_state.error:
            st.error(st.session_state.error)
            st.info(
                "인증키, API 활용 승인 상태와 일일 호출량을 확인해 주세요."
            )

        destination = st.session_state.destination
        if destination:
            show_destination(destination)

            action1, action2 = st.columns(2)

            with action1:
                if st.button(
                    "🔄 같은 조건으로 다시 뽑기",
                    use_container_width=True,
                    key="reroll_button",
                ):
                    try:
                        new_destination = choose_destination(
                            api_key,
                            st.session_state.candidate_pool,
                            destination["contentid"],
                        )
                        if new_destination:
                            st.session_state.destination = new_destination
                            st.rerun()
                    except (requests.RequestException, RuntimeError) as exc:
                        st.error(str(exc))

            with action2:
                if st.button(
                    "❤️ 찜하기",
                    use_container_width=True,
                    key="favorite_button",
                ):
                    save_favorite(destination)

    with favorites_tab:
        st.subheader("찜한 여행지")

        if not st.session_state.favorites:
            st.info("아직 찜한 여행지가 없어요.")
        else:
            if st.button("🗑️ 찜 목록 초기화", key="clear_button"):
                st.session_state.favorites = []
                st.rerun()

            for favorite in st.session_state.favorites:
                with st.container(border=True):
                    st.markdown(f'### 📍 {favorite["title"]}')
                    st.caption(favorite["address"])
                    if favorite["image"]:
                        st.image(favorite["image"], width=300)
                    summary = favorite["overview"]
                    st.write(summary[:250] + ("…" if len(summary) > 250 else ""))

    st.divider()
    st.caption("관광정보와 이미지는 한국관광공사 TourAPI에서 제공합니다.")


if __name__ == "__main__":
    main()
'''

requirements = '''streamlit>=1.36,<2.0
requests>=2.31,<3.0
'''

readme = '''# 랜덤 국내여행 뽑기

## Streamlit Cloud 배포

1. `app.py`, `requirements.txt`를 GitHub 저장소에 올립니다.
2. Streamlit Cloud에서 메인 파일을 `app.py`로 설정합니다.
3. App settings → Secrets에 아래 내용을 입력합니다.

```toml
TOUR_API_KEY = "공공데이터포털에서 발급받은 일반 인증키"

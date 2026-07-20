from pathlib import Path
import shutil
import textwrap
import zipfile
import py_compile

root = Path("/mnt/data/tour_random_trip_fixed")
if root.exists():
    shutil.rmtree(root)
root.mkdir(parents=True)
(root / ".streamlit").mkdir()

app_py = r'''
import html
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
    "축제·공연·행사": "15",
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
        "error_message": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_service_key():
    try:
        key = str(st.secrets["TOUR_API_KEY"]).strip()
    except (KeyError, FileNotFoundError):
        return ""
    return key


def clean_text(value):
    if not value:
        return ""
    value = re.sub(r"<[^>]*>", " ", str(value))
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_items(value):
    if not value:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


@st.cache_data(ttl=3600, show_spinner=False)
def request_tour_api(operation, service_key, frozen_params):
    params = dict(frozen_params)
    params.update(
        {
            "serviceKey": service_key,
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
        raise RuntimeError(
            "API가 JSON 형식으로 응답하지 않았어요. "
            "Streamlit Secrets의 인증키를 확인해 주세요."
        ) from exc

    response_data = payload.get("response", {})
    header = response_data.get("header", {})
    result_code = str(header.get("resultCode", ""))

    if result_code not in {"0000", "0"}:
        result_message = header.get("resultMsg", "알 수 없는 오류")
        raise RuntimeError(f"TourAPI 오류 {result_code}: {result_message}")

    body = response_data.get("body", {})
    items = body.get("items", {})
    if not isinstance(items, dict):
        return []

    return normalize_items(items.get("item"))


def get_area_items(service_key, area_code, content_type, rows):
    params = {
        "numOfRows": str(rows),
        "pageNo": "1",
        "arrange": "R",
        "areaCode": area_code,
        "sigunguCode": "",
        "contentTypeId": content_type,
    }
    return request_tour_api(
        "areaBasedList2",
        service_key,
        tuple(sorted(params.items())),
    )


def get_detail(service_key, content_id):
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

    items = request_tour_api(
        "detailCommon2",
        service_key,
        tuple(sorted(params.items())),
    )
    return items[0] if items else {}


def build_candidate_pool(service_key, area_code, content_types, rows):
    combined = []

    for content_type in content_types:
        combined.extend(
            get_area_items(
                service_key=service_key,
                area_code=area_code,
                content_type=content_type,
                rows=rows,
            )
        )

    deduplicated = {}
    for item in combined:
        content_id = str(item.get("contentid", "")).strip()
        title = clean_text(item.get("title"))
        if content_id and title:
            deduplicated[content_id] = item

    return list(deduplicated.values())


def format_destination(item, detail):
    merged = {**item, **detail}
    address = " ".join(
        part
        for part in [
            clean_text(merged.get("addr1")),
            clean_text(merged.get("addr2")),
        ]
        if part
    )

    return {
        "contentid": str(merged.get("contentid", "")),
        "title": clean_text(merged.get("title")) or "이름 없는 여행지",
        "address": address or "주소 정보 없음",
        "overview": clean_text(merged.get("overview"))
        or "한국관광공사에서 상세 소개를 제공하지 않은 장소예요.",
        "image": merged.get("firstimage") or merged.get("firstimage2") or "",
        "tel": clean_text(merged.get("tel")) or "문의 전화 정보 없음",
        "mapx": str(merged.get("mapx", "")),
        "mapy": str(merged.get("mapy", "")),
    }


def pick_from_pool(service_key, pool, previous_id=""):
    available = [
        item
        for item in pool
        if str(item.get("contentid", "")) != previous_id
    ]
    if not available:
        available = pool

    if not available:
        return None

    selected = random.choice(available)
    detail = get_detail(service_key, selected["contentid"])
    return format_destination(selected, detail)


def add_favorite(destination):
    saved_ids = {
        favorite["contentid"]
        for favorite in st.session_state.favorites
    }

    if destination["contentid"] in saved_ids:
        st.info("이미 찜한 여행지예요.")
        return

    st.session_state.favorites.append(destination)
    st.success("찜 목록에 추가했어요.")


def render_destination(destination):
    safe_title = html.escape(destination["title"])
    safe_address = html.escape(destination["address"])

    st.markdown(
        f"""
        <section class="destination-card">
            <div class="destination-pin">📍</div>
            <h2>{safe_title}</h2>
            <p>{safe_address}</p>
        </section>
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
        st.info("이 여행지는 제공된 대표 사진이 없어요.")

    st.subheader("여행지 소개")
    st.write(destination["overview"])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**주소**")
        st.write(destination["address"])
    with col2:
        st.markdown("**문의**")
        st.write(destination["tel"])

    map_query = quote(destination["title"])
    search_query = quote(f"{destination['title']} 여행")

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
    service_key = get_service_key()

    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(180deg, #fff9f1 0%, #f1faff 100%);
        }
        .hero {
            text-align: center;
            padding: 1rem 0 1.7rem;
        }
        .hero h1 {
            font-size: 2.6rem;
            margin-bottom: 0.4rem;
        }
        .hero p {
            color: #606770;
            font-size: 1.05rem;
        }
        .destination-card {
            text-align: center;
            padding: 1.7rem;
            margin: 1.2rem 0;
            border: 1px solid rgba(0, 0, 0, 0.08);
            border-radius: 24px;
            background: rgba(255, 255, 255, 0.94);
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.07);
        }
        .destination-card h2 {
            margin: 0.25rem 0;
            font-size: 2.15rem;
        }
        .destination-pin {
            font-size: 2.8rem;
        }
        </style>

        <div class="hero">
            <h1>🎲 랜덤 국내여행 뽑기</h1>
            <p>한국관광공사 TourAPI의 실제 관광정보에서 여행지를 추천해요.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not service_key:
        st.error("TourAPI 인증키가 설정되지 않았어요.")
        st.markdown("Streamlit Cloud의 **App settings → Secrets**에 아래처럼 입력하세요.")
        st.code(
            'TOUR_API_KEY = "공공데이터포털에서 발급받은 일반 인증키"',
            language="toml",
        )
        st.stop()

    draw_tab, favorites_tab = st.tabs(["🎲 여행지 뽑기", "❤️ 찜 목록"])

    with draw_tab:
        with st.container(border=True):
            st.subheader("여행 조건")

            col1, col2 = st.columns(2)
            with col1:
                selected_area = st.selectbox(
                    "지역",
                    list(AREA_CODES),
                    key="selected_area",
                )
            with col2:
                selected_types = st.multiselect(
                    "관광 유형",
                    list(CONTENT_TYPES),
                    default=["관광지"],
                    key="selected_types",
                )

            rows = st.slider(
                "유형별 후보 개수",
                min_value=20,
                max_value=100,
                value=60,
                step=20,
                key="candidate_rows",
            )

            if st.button(
                "🎲 여행지 뽑기",
                type="primary",
                use_container_width=True,
                key="draw_destination",
            ):
                if not selected_types:
                    st.warning("관광 유형을 한 개 이상 선택해 주세요.")
                else:
                    try:
                        with st.spinner("관광공사 데이터에서 여행지를 찾는 중이에요..."):
                            pool = build_candidate_pool(
                                service_key=service_key,
                                area_code=AREA_CODES[selected_area],
                                content_types=[
                                    CONTENT_TYPES[name]
                                    for name in selected_types
                                ],
                                rows=rows,
                            )
                            destination = pick_from_pool(service_key, pool)

                        st.session_state.candidate_pool = pool
                        st.session_state.destination = destination
                        st.session_state.error_message = ""

                        if destination is None:
                            st.warning("선택한 조건의 관광정보를 찾지 못했어요.")
                    except (requests.RequestException, RuntimeError) as exc:
                        st.session_state.destination = None
                        st.session_state.error_message = str(exc)

        if st.session_state.error_message:
            st.error(st.session_state.error_message)
            st.info(
                "Secrets의 인증키, 공공데이터포털 활용 승인 상태, "
                "TourAPI 일일 호출량을 확인해 주세요."
            )

        destination = st.session_state.destination
        if destination:
            render_destination(destination)

            action1, action2 = st.columns(2)
            with action1:
                if st.button(
                    "🔄 같은 조건으로 다시 뽑기",
                    use_container_width=True,
                    key="reroll_destination",
                ):
                    try:
                        new_destination = pick_from_pool(
                            service_key,
                            st.session_state.candidate_pool,
                            previous_id=destination["contentid"],
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
                    key="save_favorite",
                ):
                    add_favorite(destination)

    with favorites_tab:
        st.subheader("찜한 여행지")

        if not st.session_state.favorites:
            st.info("아직 찜한 여행지가 없어요.")
        else:
            if st.button(
                "🗑️ 찜 목록 초기화",
                key="clear_favorites",
            ):
                st.session_state.favorites = []
                st.rerun()

            for favorite in st.session_state.favorites:
                with st.container(border=True):
                    st.markdown(f"### 📍 {favorite['title']}")
                    st.caption(favorite["address"])
                    if favorite["image"]:
                        st.image(favorite["image"], width=300)
                    summary = favorite["overview"]
                    st.write(
                        summary[:250]
                        + ("…" if len(summary) > 250 else "")
                    )

    st.divider()
    st.caption("관광정보와 이미지는 한국관광공사 TourAPI를 통해 제공됩니다.")


if __name__ == "__main__":
    main()
'''

requirements = """streamlit>=1.36,<2.0
requests>=2.31,<3.0
"""

secrets_example = '''# 이 파일의 이름을 secrets.toml로 변경한 뒤 실제 키를 넣으세요.
# 실제 secrets.toml은 공개 GitHub에 올리지 마세요.
TOUR_API_KEY = "YOUR_TOUR_API_KEY"
'''

gitignore = """.streamlit/secrets.toml
__pycache__/
*.pyc
"""

readme = """# 랜덤 국내여행 뽑기

한국관광공사 국문 관광정보 서비스 TourAPI를 사용하는 Streamlit 앱입니다.

## Streamlit Cloud 배포

1. 이 폴더의 파일을 GitHub 저장소에 올립니다.
2. Streamlit Community Cloud에서 `app.py`를 메인 파일로 선택합니다.
3. App settings → Secrets에 아래 내용을 입력합니다.

```toml
TOUR_API_KEY = "공공데이터포털에서 발급받은 일반 인증키"

import streamlit as st
import pandas as pd
import pydeck as pdk

st.set_page_config(
    page_title="서울시 공영주차장 정보",
    page_icon="🅿️",
    layout="wide"
)

st.title("🅿️ 서울시 공영주차장 정보")
st.markdown("### CSV 또는 Excel 파일을 업로드하세요.")

uploaded_file = st.file_uploader(
    "데이터 업로드",
    type=["csv", "xlsx"]
)

if uploaded_file is not None:

    # -----------------------------------
    # 파일 읽기
    # -----------------------------------
    if uploaded_file.name.endswith(".csv"):
        try:
            df = pd.read_csv(uploaded_file, encoding="utf-8")
        except:
            df = pd.read_csv(uploaded_file, encoding="cp949")
    else:
        df = pd.read_excel(uploaded_file)

    st.success("파일을 불러왔습니다.")

    st.subheader("데이터 미리보기")
    st.dataframe(df.head())

    # -----------------------------------
    # 컬럼명 설정
    # -----------------------------------
    # 아래 이름만 실제 데이터에 맞게 수정하면 됩니다.
    NAME_COL = "주차장명"
    LAT_COL = "위도"
    LNG_COL = "경도"
    PRICE_COL = "평일운영"
    ADDRESS_COL = "주소"

    # -----------------------------------
    # 숫자 변환
    # -----------------------------------
    df[PRICE_COL] = (
        df[PRICE_COL]
        .astype(str)
        .str.replace(",", "")
        .str.extract(r'(\d+)')[0]
        .astype(float)
    )


    # -----------------------------------
    # 요금순 정렬
    # -----------------------------------
    df = df.sort_values(PRICE_COL)

    # -----------------------------------
    # 지도
    # -----------------------------------
    st.subheader("🗺️ 공영주차장 위치")

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=f"[{LNG_COL}, {LAT_COL}]",
        get_radius=80,
        get_fill_color=[0, 140, 255, 180],
        pickable=True,
    )

    view_state = pdk.ViewState(
        latitude=df[LAT_COL].mean(),
        longitude=df[LNG_COL].mean(),
        zoom=11,
    )

    tooltip = {
        "html": """
        <b>{주차장명}</b><br/>
        주소 : {주소}<br/>
        요금 : {기본요금}원
        """
    }

    deck = pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state=view_state,
        layers=[layer],
        tooltip=tooltip,
    )

    st.pydeck_chart(deck)

    # -----------------------------------
    # 요금 순위
    # -----------------------------------
    st.subheader("💰 저렴한 주차장 순위")

    display = df[
        [
            NAME_COL,
            DISTRICT_COL,
            ADDRESS_COL,
            PRICE_COL
        ]
    ]

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True
    )

    # -----------------------------------
    # 다운로드
    # -----------------------------------
    csv = display.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "📥 CSV 다운로드",
        csv,
        "parking_sorted.csv",
        "text/csv"
    )

else:

    st.info("좌측에서 CSV 또는 Excel 파일을 업로드하세요.")

from pathlib import Path
import textwrap, zipfile, os

base = Path("/mnt/data/random_korea_trip_app")
base.mkdir(parents=True, exist_ok=True)

app_code = r'''
import random
from urllib.parse import quote

import streamlit as st


st.set_page_config(
    page_title="랜덤 국내여행 뽑기",
    page_icon="🎲",
    layout="wide",
)


def initialize_session_state():
    defaults = {
        "selected_destination": None,
        "favorites": [],
        "last_filters": {},
        "relaxed_message": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_travel_destinations():
    return [
        {
            "name": "서울",
            "province": "서울특별시",
            "region": "수도권",
            "emoji": "🌆",
            "themes": ["맛집", "카페", "역사", "문화", "야경", "사진 촬영", "전통시장"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["5만 원 이하", "5만 원~10만 원", "10만 원~20만 원"],
            "transport": ["대중교통"],
            "description": "전통과 최신 문화가 함께 있는 도심 여행지",
            "activities": ["경복궁 산책", "성수 카페 투어", "한강 야경 감상"],
            "food": "광장시장 빈대떡과 길거리 음식",
            "tip": "대중교통 1일권이나 환승을 활용하면 이동이 편해요.",
            "transport_level": "매우 편리",
        },
        {
            "name": "인천",
            "province": "인천광역시",
            "region": "수도권",
            "emoji": "🌊",
            "themes": ["바다", "맛집", "카페", "문화", "야경", "사진 촬영"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["5만 원 이하", "5만 원~10만 원", "10만 원~20만 원"],
            "transport": ["대중교통", "자가용"],
            "description": "바다와 개항장 분위기를 동시에 즐길 수 있는 여행지",
            "activities": ["차이나타운 산책", "송도 센트럴파크", "월미도 야경"],
            "food": "짜장면과 신포 닭강정",
            "tip": "송도와 차이나타운은 거리가 있어 동선을 나눠 잡는 것이 좋아요.",
            "transport_level": "편리",
        },
        {
            "name": "수원",
            "province": "경기도",
            "region": "수도권",
            "emoji": "🏯",
            "themes": ["역사", "문화", "맛집", "카페", "사진 촬영"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["5만 원 이하", "5만 원~10만 원"],
            "transport": ["대중교통", "자가용"],
            "description": "수원화성과 행궁동을 중심으로 걷기 좋은 여행지",
            "activities": ["수원화성 걷기", "행궁동 카페", "전통시장 구경"],
            "food": "수원 왕갈비",
            "tip": "화성 성곽 산책은 편한 신발을 추천해요.",
            "transport_level": "편리",
        },
        {
            "name": "가평",
            "province": "경기도",
            "region": "수도권",
            "emoji": "🌲",
            "themes": ["산", "자연", "액티비티", "힐링", "사진 촬영"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["친구", "가족", "연인"],
            "budgets": ["5만 원~10만 원", "10만 원~20만 원"],
            "transport": ["대중교통", "자가용"],
            "description": "강과 산이 어우러진 수도권 대표 자연 여행지",
            "activities": ["남이섬 산책", "레일바이크", "펜션 휴식"],
            "food": "잣두부와 닭갈비",
            "tip": "관광지 사이 이동이 많아 자가용이 있으면 더 편해요.",
            "transport_level": "보통",
        },
        {
            "name": "파주",
            "province": "경기도",
            "region": "수도권",
            "emoji": "📚",
            "themes": ["카페", "문화", "힐링", "사진 촬영"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["5만 원 이하", "5만 원~10만 원"],
            "transport": ["자가용", "대중교통"],
            "description": "출판도시와 감성 카페가 매력적인 근교 여행지",
            "activities": ["출판도시 방문", "대형 카페 투어", "헤이리 예술마을"],
            "food": "장단콩 요리",
            "tip": "대중교통보다는 자가용 이용이 편리해요.",
            "transport_level": "보통",
        },
        {
            "name": "양평",
            "province": "경기도",
            "region": "수도권",
            "emoji": "🌿",
            "themes": ["자연", "힐링", "카페", "사진 촬영"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["5만 원 이하", "5만 원~10만 원", "10만 원~20만 원"],
            "transport": ["대중교통", "자가용"],
            "description": "강변 풍경과 조용한 휴식을 즐기기 좋은 곳",
            "activities": ["두물머리 산책", "세미원 방문", "강변 카페"],
            "food": "해장국과 산채 음식",
            "tip": "이른 아침 두물머리를 방문하면 한적한 풍경을 즐길 수 있어요.",
            "transport_level": "보통",
        },
        {
            "name": "강릉",
            "province": "강원특별자치도",
            "region": "강원권",
            "emoji": "☕",
            "themes": ["바다", "카페", "맛집", "힐링", "사진 촬영"],
            "durations": ["당일치기", "1박 2일", "2박 3일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["5만 원~10만 원", "10만 원~20만 원", "20만 원 이상"],
            "transport": ["대중교통", "자가용"],
            "description": "동해 바다와 커피 거리를 함께 즐기는 인기 여행지",
            "activities": ["안목해변 카페", "경포호 산책", "초당마을 방문"],
            "food": "초당순두부와 장칼국수",
            "tip": "주말에는 해변 주변 카페가 붐비므로 오전 방문을 추천해요.",
            "transport_level": "편리",
        },
        {
            "name": "속초",
            "province": "강원특별자치도",
            "region": "강원권",
            "emoji": "⛰️",
            "themes": ["바다", "산", "자연", "맛집", "전통시장"],
            "durations": ["1박 2일", "2박 3일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["5만 원~10만 원", "10만 원~20만 원", "20만 원 이상"],
            "transport": ["대중교통", "자가용"],
            "description": "설악산과 동해를 한 번에 만날 수 있는 여행지",
            "activities": ["설악산 산책", "속초해변", "중앙시장 먹방"],
            "food": "닭강정과 오징어순대",
            "tip": "설악산 일정과 바다 일정을 하루씩 나누면 좋아요.",
            "transport_level": "보통",
        },
        {
            "name": "춘천",
            "province": "강원특별자치도",
            "region": "강원권",
            "emoji": "🚲",
            "themes": ["자연", "맛집", "카페", "액티비티", "힐링"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["5만 원 이하", "5만 원~10만 원", "10만 원~20만 원"],
            "transport": ["대중교통", "자가용"],
            "description": "호수와 닭갈비, 감성 카페가 어우러진 여행지",
            "activities": ["의암호 산책", "레고랜드", "카페 투어"],
            "food": "닭갈비와 막국수",
            "tip": "ITX를 이용하면 수도권에서 당일치기도 가능해요.",
            "transport_level": "편리",
        },
        {
            "name": "평창",
            "province": "강원특별자치도",
            "region": "강원권",
            "emoji": "❄️",
            "themes": ["산", "자연", "액티비티", "힐링"],
            "durations": ["1박 2일", "2박 3일"],
            "companions": ["친구", "가족", "연인"],
            "budgets": ["10만 원~20만 원", "20만 원 이상"],
            "transport": ["자가용"],
            "description": "고원 풍경과 계절별 레저를 즐길 수 있는 여행지",
            "activities": ["대관령 산책", "목장 체험", "스키 또는 썰매"],
            "food": "메밀 음식과 황태 요리",
            "tip": "관광지 간 거리가 있어 자가용 이동이 가장 편해요.",
            "transport_level": "불편",
        },
        {
            "name": "정선",
            "province": "강원특별자치도",
            "region": "강원권",
            "emoji": "🚂",
            "themes": ["산", "자연", "전통시장", "힐링", "액티비티"],
            "durations": ["1박 2일", "2박 3일"],
            "companions": ["혼자", "친구", "가족"],
            "budgets": ["5만 원~10만 원", "10만 원~20만 원"],
            "transport": ["자가용"],
            "description": "산골 풍경과 전통시장의 매력이 살아 있는 여행지",
            "activities": ["정선5일장", "레일바이크", "아리힐스 전망대"],
            "food": "곤드레밥과 메밀전병",
            "tip": "장날을 확인하고 방문하면 더 풍성하게 즐길 수 있어요.",
            "transport_level": "불편",
        },
        {
            "name": "원주",
            "province": "강원특별자치도",
            "region": "강원권",
            "emoji": "🌉",
            "themes": ["자연", "액티비티", "문화", "힐링"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["친구", "가족", "연인"],
            "budgets": ["5만 원 이하", "5만 원~10만 원"],
            "transport": ["대중교통", "자가용"],
            "description": "출렁다리와 숲길을 즐기기 좋은 강원 내륙 여행지",
            "activities": ["소금산 출렁다리", "뮤지엄 산", "치악산 산책"],
            "food": "복숭아와 한우",
            "tip": "출렁다리는 날씨가 좋은 날 방문하는 것이 좋아요.",
            "transport_level": "보통",
        },
        {
            "name": "대전",
            "province": "대전광역시",
            "region": "충청권",
            "emoji": "🔬",
            "themes": ["맛집", "카페", "문화", "힐링"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["혼자", "친구", "가족"],
            "budgets": ["5만 원 이하", "5만 원~10만 원"],
            "transport": ["대중교통", "자가용"],
            "description": "과학과 빵, 도심 산책을 함께 즐길 수 있는 도시",
            "activities": ["성심당 방문", "엑스포과학공원", "한밭수목원"],
            "food": "빵과 칼국수",
            "tip": "도심 명소가 비교적 가까워 대중교통 여행에 좋아요.",
            "transport_level": "편리",
        },
        {
            "name": "공주",
            "province": "충청남도",
            "region": "충청권",
            "emoji": "👑",
            "themes": ["역사", "문화", "자연", "사진 촬영"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["5만 원 이하", "5만 원~10만 원"],
            "transport": ["대중교통", "자가용"],
            "description": "백제의 역사와 금강 풍경이 인상적인 여행지",
            "activities": ["공산성 산책", "무령왕릉", "제민천 카페거리"],
            "food": "밤 음식",
            "tip": "야간의 공산성 조명도 아름다워요.",
            "transport_level": "보통",
        },
        {
            "name": "부여",
            "province": "충청남도",
            "region": "충청권",
            "emoji": "🏺",
            "themes": ["역사", "문화", "자연", "힐링"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["혼자", "친구", "가족"],
            "budgets": ["5만 원 이하", "5만 원~10만 원"],
            "transport": ["자가용", "대중교통"],
            "description": "백제 문화유산을 차분하게 둘러보기 좋은 여행지",
            "activities": ["부소산성", "궁남지 산책", "백제문화단지"],
            "food": "연잎밥",
            "tip": "궁남지는 연꽃이 피는 계절에 특히 아름다워요.",
            "transport_level": "보통",
        },
        {
            "name": "단양",
            "province": "충청북도",
            "region": "충청권",
            "emoji": "🪂",
            "themes": ["산", "자연", "액티비티", "사진 촬영"],
            "durations": ["1박 2일", "2박 3일"],
            "companions": ["친구", "가족", "연인"],
            "budgets": ["5만 원~10만 원", "10만 원~20만 원"],
            "transport": ["자가용", "대중교통"],
            "description": "절경과 패러글라이딩으로 유명한 여행지",
            "activities": ["도담삼봉", "만천하스카이워크", "패러글라이딩"],
            "food": "마늘 음식",
            "tip": "액티비티는 날씨에 따라 취소될 수 있어요.",
            "transport_level": "보통",
        },
        {
            "name": "제천",
            "province": "충청북도",
            "region": "충청권",
            "emoji": "🚠",
            "themes": ["자연", "힐링", "액티비티", "사진 촬영"],
            "durations": ["1박 2일", "2박 3일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["5만 원~10만 원", "10만 원~20만 원"],
            "transport": ["자가용"],
            "description": "청풍호와 산 풍경을 여유롭게 즐기는 여행지",
            "activities": ["청풍호 케이블카", "의림지 산책", "옥순봉 출렁다리"],
            "food": "약초 음식",
            "tip": "호수 주변 관광지는 자가용 이동이 편해요.",
            "transport_level": "불편",
        },
        {
            "name": "태안",
            "province": "충청남도",
            "region": "충청권",
            "emoji": "🏖️",
            "themes": ["바다", "자연", "힐링", "사진 촬영"],
            "durations": ["1박 2일", "2박 3일"],
            "companions": ["친구", "가족", "연인"],
            "budgets": ["5만 원~10만 원", "10만 원~20만 원"],
            "transport": ["자가용"],
            "description": "서해 낙조와 해변을 즐기기 좋은 여행지",
            "activities": ["꽃지해수욕장", "안면도 자연휴양림", "해변 노을 감상"],
            "food": "게국지와 꽃게",
            "tip": "노을 시간을 미리 확인하고 움직이면 좋아요.",
            "transport_level": "불편",
        },
        {
            "name": "보령",
            "province": "충청남도",
            "region": "충청권",
            "emoji": "🟤",
            "themes": ["바다", "액티비티", "축제", "맛집"],
            "durations": ["1박 2일", "2박 3일"],
            "companions": ["친구", "가족", "연인"],
            "budgets": ["5만 원~10만 원", "10만 원~20만 원"],
            "transport": ["대중교통", "자가용"],
            "description": "대천해수욕장과 머드축제로 유명한 활기찬 여행지",
            "activities": ["대천해수욕장", "스카이바이크", "머드 체험"],
            "food": "조개구이",
            "tip": "축제 기간에는 숙소를 미리 예약하는 것이 좋아요.",
            "transport_level": "보통",
        },
        {
            "name": "전주",
            "province": "전북특별자치도",
            "region": "전라권",
            "emoji": "🏘️",
            "themes": ["역사", "문화", "맛집", "카페", "사진 촬영"],
            "durations": ["당일치기", "1박 2일", "2박 3일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["5만 원 이하", "5만 원~10만 원", "10만 원~20만 원"],
            "transport": ["대중교통", "자가용"],
            "description": "한옥과 맛집을 함께 즐기는 대표적인 감성 여행지",
            "activities": ["한옥마을 산책", "경기전 방문", "객리단길 카페"],
            "food": "전주비빔밥과 콩나물국밥",
            "tip": "한옥마을은 오전에 방문하면 비교적 한적해요.",
            "transport_level": "편리",
        },
        {
            "name": "군산",
            "province": "전북특별자치도",
            "region": "전라권",
            "emoji": "📻",
            "themes": ["역사", "문화", "맛집", "사진 촬영"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["5만 원 이하", "5만 원~10만 원"],
            "transport": ["대중교통", "자가용"],
            "description": "근대 건축과 골목 풍경이 매력적인 여행지",
            "activities": ["근대역사박물관", "초원사진관", "경암동 철길마을"],
            "food": "짬뽕과 빵",
            "tip": "주요 명소가 도심에 모여 있어 도보 여행도 가능해요.",
            "transport_level": "보통",
        },
        {
            "name": "여수",
            "province": "전라남도",
            "region": "전라권",
            "emoji": "🌃",
            "themes": ["바다", "야경", "맛집", "카페", "사진 촬영"],
            "durations": ["1박 2일", "2박 3일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["10만 원~20만 원", "20만 원 이상"],
            "transport": ["대중교통", "자가용"],
            "description": "바다와 화려한 밤바다 풍경이 매력적인 여행지",
            "activities": ["해상케이블카", "오동도 산책", "낭만포차 거리"],
            "food": "게장백반",
            "tip": "야경을 보려면 최소 1박을 추천해요.",
            "transport_level": "편리",
        },
        {
            "name": "순천",
            "province": "전라남도",
            "region": "전라권",
            "emoji": "🌾",
            "themes": ["자연", "힐링", "사진 촬영", "문화"],
            "durations": ["1박 2일", "2박 3일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["5만 원~10만 원", "10만 원~20만 원"],
            "transport": ["대중교통", "자가용"],
            "description": "습지와 정원을 천천히 걸으며 쉬기 좋은 여행지",
            "activities": ["순천만습지", "국가정원", "드라마촬영장"],
            "food": "꼬막정식",
            "tip": "순천만습지는 해질 무렵 풍경이 특히 아름다워요.",
            "transport_level": "보통",
        },
        {
            "name": "담양",
            "province": "전라남도",
            "region": "전라권",
            "emoji": "🎋",
            "themes": ["자연", "힐링", "맛집", "사진 촬영"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["5만 원 이하", "5만 원~10만 원"],
            "transport": ["자가용"],
            "description": "대나무 숲과 조용한 산책이 매력적인 여행지",
            "activities": ["죽녹원", "메타세쿼이아길", "소쇄원"],
            "food": "떡갈비와 대통밥",
            "tip": "숲길 산책이 많아 편한 신발을 준비해요.",
            "transport_level": "불편",
        },
        {
            "name": "목포",
            "province": "전라남도",
            "region": "전라권",
            "emoji": "⛴️",
            "themes": ["바다", "맛집", "역사", "야경"],
            "durations": ["1박 2일", "2박 3일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["5만 원~10만 원", "10만 원~20만 원"],
            "transport": ["대중교통", "자가용"],
            "description": "항구 도시의 풍경과 남도 음식을 즐길 수 있는 곳",
            "activities": ["해상케이블카", "근대역사관", "갓바위 산책"],
            "food": "세발낙지와 홍어",
            "tip": "구도심과 해상케이블카 지역의 동선을 나눠 잡으면 좋아요.",
            "transport_level": "보통",
        },
        {
            "name": "부산",
            "province": "부산광역시",
            "region": "경상권",
            "emoji": "🌉",
            "themes": ["바다", "맛집", "카페", "야경", "문화", "전통시장"],
            "durations": ["1박 2일", "2박 3일", "3박 이상"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["10만 원~20만 원", "20만 원 이상"],
            "transport": ["대중교통", "자가용"],
            "description": "해변, 시장, 야경을 모두 즐길 수 있는 대도시 여행지",
            "activities": ["해운대 산책", "감천문화마을", "광안대교 야경"],
            "food": "돼지국밥과 밀면",
            "tip": "동부와 서부 관광지 거리가 멀어 지역별로 하루씩 잡는 것이 좋아요.",
            "transport_level": "매우 편리",
        },
        {
            "name": "경주",
            "province": "경상북도",
            "region": "경상권",
            "emoji": "🌙",
            "themes": ["역사", "문화", "사진 촬영", "카페", "야경"],
            "durations": ["1박 2일", "2박 3일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["5만 원~10만 원", "10만 원~20만 원"],
            "transport": ["대중교통", "자가용"],
            "description": "신라의 유적과 감성적인 황리단길이 있는 여행지",
            "activities": ["대릉원", "동궁과 월지 야경", "황리단길"],
            "food": "황남빵과 한우",
            "tip": "자전거를 빌리면 도심 유적지를 편하게 둘러볼 수 있어요.",
            "transport_level": "편리",
        },
        {
            "name": "포항",
            "province": "경상북도",
            "region": "경상권",
            "emoji": "🌅",
            "themes": ["바다", "맛집", "사진 촬영", "힐링"],
            "durations": ["1박 2일", "2박 3일"],
            "companions": ["친구", "가족", "연인"],
            "budgets": ["5만 원~10만 원", "10만 원~20만 원"],
            "transport": ["자가용", "대중교통"],
            "description": "동해의 일출과 해안 풍경이 아름다운 여행지",
            "activities": ["스페이스워크", "호미곶", "영일대해수욕장"],
            "food": "과메기와 물회",
            "tip": "해안 관광지는 자가용으로 이동하면 편해요.",
            "transport_level": "보통",
        },
        {
            "name": "통영",
            "province": "경상남도",
            "region": "경상권",
            "emoji": "🎨",
            "themes": ["바다", "문화", "맛집", "사진 촬영", "액티비티"],
            "durations": ["1박 2일", "2박 3일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["10만 원~20만 원", "20만 원 이상"],
            "transport": ["자가용", "대중교통"],
            "description": "섬과 예술, 해산물을 함께 즐기는 남해안 여행지",
            "activities": ["미륵산 케이블카", "동피랑 벽화마을", "섬 여행"],
            "food": "충무김밥과 꿀빵",
            "tip": "섬 배편은 날씨에 따라 변경될 수 있으니 확인하세요.",
            "transport_level": "보통",
        },
        {
            "name": "거제",
            "province": "경상남도",
            "region": "경상권",
            "emoji": "🏝️",
            "themes": ["바다", "자연", "힐링", "사진 촬영"],
            "durations": ["1박 2일", "2박 3일"],
            "companions": ["친구", "가족", "연인"],
            "budgets": ["10만 원~20만 원", "20만 원 이상"],
            "transport": ["자가용"],
            "description": "해안도로와 섬 풍경이 아름다운 여행지",
            "activities": ["바람의 언덕", "외도 보타니아", "매미성"],
            "food": "멍게비빔밥",
            "tip": "관광지가 넓게 퍼져 있어 자가용 여행이 좋아요.",
            "transport_level": "불편",
        },
        {
            "name": "안동",
            "province": "경상북도",
            "region": "경상권",
            "emoji": "🎭",
            "themes": ["역사", "문화", "전통시장", "맛집"],
            "durations": ["1박 2일", "2박 3일"],
            "companions": ["혼자", "친구", "가족"],
            "budgets": ["5만 원~10만 원", "10만 원~20만 원"],
            "transport": ["자가용", "대중교통"],
            "description": "전통 마을과 유교 문화를 깊이 느낄 수 있는 여행지",
            "activities": ["하회마을", "월영교 야경", "찜닭골목"],
            "food": "안동찜닭과 간고등어",
            "tip": "하회마을과 도심은 거리가 있어 이동 계획이 필요해요.",
            "transport_level": "보통",
        },
        {
            "name": "대구",
            "province": "대구광역시",
            "region": "경상권",
            "emoji": "🔥",
            "themes": ["맛집", "카페", "문화", "야경"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["혼자", "친구", "연인"],
            "budgets": ["5만 원 이하", "5만 원~10만 원"],
            "transport": ["대중교통", "자가용"],
            "description": "도심 먹거리와 감성 골목이 풍부한 여행지",
            "activities": ["김광석길", "앞산 전망대", "서문시장"],
            "food": "막창과 납작만두",
            "tip": "여름에는 매우 더울 수 있어 실내 동선을 섞어주세요.",
            "transport_level": "매우 편리",
        },
        {
            "name": "울산",
            "province": "울산광역시",
            "region": "경상권",
            "emoji": "🐋",
            "themes": ["바다", "자연", "문화", "사진 촬영"],
            "durations": ["1박 2일", "2박 3일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["5만 원~10만 원", "10만 원~20만 원"],
            "transport": ["자가용"],
            "description": "해안 절경과 생태공원을 함께 즐기는 여행지",
            "activities": ["대왕암공원", "장생포 고래문화마을", "간절곶"],
            "food": "언양불고기",
            "tip": "관광지 간 거리가 있어 자가용이 편해요.",
            "transport_level": "불편",
        },
        {
            "name": "창원",
            "province": "경상남도",
            "region": "경상권",
            "emoji": "🌸",
            "themes": ["자연", "문화", "맛집", "사진 촬영"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["친구", "가족", "연인"],
            "budgets": ["5만 원 이하", "5만 원~10만 원"],
            "transport": ["자가용", "대중교통"],
            "description": "도시와 바다, 계절 꽃길을 함께 즐길 수 있는 곳",
            "activities": ["진해 군항제 거리", "저도 콰이강의 다리", "마산 어시장"],
            "food": "아귀찜",
            "tip": "봄철 벚꽃 시즌에는 교통 혼잡을 고려하세요.",
            "transport_level": "보통",
        },
        {
            "name": "진주",
            "province": "경상남도",
            "region": "경상권",
            "emoji": "🏮",
            "themes": ["역사", "문화", "야경", "맛집"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["5만 원 이하", "5만 원~10만 원"],
            "transport": ["대중교통", "자가용"],
            "description": "진주성과 남강 야경이 아름다운 여행지",
            "activities": ["진주성", "남강 산책", "중앙시장"],
            "food": "진주비빔밥과 냉면",
            "tip": "유등축제 기간에는 야경이 특히 아름다워요.",
            "transport_level": "보통",
        },
        {
            "name": "제주",
            "province": "제주특별자치도",
            "region": "제주권",
            "emoji": "🍊",
            "themes": ["바다", "자연", "카페", "맛집", "힐링", "사진 촬영"],
            "durations": ["2박 3일", "3박 이상"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["20만 원 이상"],
            "transport": ["자가용", "대중교통"],
            "description": "섬의 자연과 개성 있는 카페를 즐기는 대표 여행지",
            "activities": ["협재해변", "오름 산책", "동문시장"],
            "food": "흑돼지와 고기국수",
            "tip": "동서 이동 시간이 길어 숙소 위치를 일정에 맞게 잡으세요.",
            "transport_level": "보통",
        },
        {
            "name": "서귀포",
            "province": "제주특별자치도",
            "region": "제주권",
            "emoji": "🌋",
            "themes": ["바다", "자연", "힐링", "액티비티", "사진 촬영"],
            "durations": ["2박 3일", "3박 이상"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["20만 원 이상"],
            "transport": ["자가용", "대중교통"],
            "description": "폭포와 해안 절경이 풍부한 제주 남부 여행지",
            "activities": ["천지연폭포", "올레길 걷기", "중문 해변"],
            "food": "갈치조림",
            "tip": "바람이 강한 날이 많아 얇은 겉옷을 준비하세요.",
            "transport_level": "보통",
        },
        {
            "name": "남해",
            "province": "경상남도",
            "region": "경상권",
            "emoji": "🌺",
            "themes": ["바다", "자연", "힐링", "사진 촬영"],
            "durations": ["1박 2일", "2박 3일"],
            "companions": ["친구", "가족", "연인"],
            "budgets": ["10만 원~20만 원", "20만 원 이상"],
            "transport": ["자가용"],
            "description": "잔잔한 바다와 다랭이논이 아름다운 여행지",
            "activities": ["독일마을", "다랭이마을", "해안도로 드라이브"],
            "food": "멸치쌈밥",
            "tip": "해안도로 이동이 많아 자가용 여행을 추천해요.",
            "transport_level": "불편",
        },
        {
            "name": "청주",
            "province": "충청북도",
            "region": "충청권",
            "emoji": "📖",
            "themes": ["문화", "역사", "카페", "맛집"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["혼자", "친구", "가족"],
            "budgets": ["5만 원 이하", "5만 원~10만 원"],
            "transport": ["대중교통", "자가용"],
            "description": "기록 문화와 도심 명소를 편하게 즐길 수 있는 곳",
            "activities": ["고인쇄박물관", "수암골", "국립현대미술관 청주"],
            "food": "짜글이",
            "tip": "도심 관광지는 버스로 이동하기 쉬운 편이에요.",
            "transport_level": "편리",
        },
        {
            "name": "익산",
            "province": "전북특별자치도",
            "region": "전라권",
            "emoji": "💎",
            "themes": ["역사", "문화", "자연", "사진 촬영"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["혼자", "친구", "가족"],
            "budgets": ["5만 원 이하", "5만 원~10만 원"],
            "transport": ["대중교통", "자가용"],
            "description": "백제 유적과 넓은 정원을 함께 즐기는 여행지",
            "activities": ["미륵사지", "왕궁리유적", "아가페정원"],
            "food": "황등비빔밥",
            "tip": "역사 유적지 간 이동 시간을 미리 확인하세요.",
            "transport_level": "보통",
        },
        {
            "name": "완도",
            "province": "전라남도",
            "region": "전라권",
            "emoji": "🌿",
            "themes": ["바다", "자연", "힐링", "맛집"],
            "durations": ["1박 2일", "2박 3일"],
            "companions": ["혼자", "친구", "가족"],
            "budgets": ["10만 원~20만 원", "20만 원 이상"],
            "transport": ["자가용"],
            "description": "청정 바다와 섬 풍경을 여유롭게 즐기는 여행지",
            "activities": ["완도타워", "청산도 여행", "해변 산책"],
            "food": "전복 요리",
            "tip": "섬 이동 시 배편 시간표를 꼭 확인하세요.",
            "transport_level": "불편",
        },
        {
            "name": "고성",
            "province": "강원특별자치도",
            "region": "강원권",
            "emoji": "🗻",
            "themes": ["바다", "자연", "힐링", "사진 촬영"],
            "durations": ["1박 2일", "2박 3일"],
            "companions": ["혼자", "친구", "가족", "연인"],
            "budgets": ["5만 원~10만 원", "10만 원~20만 원"],
            "transport": ["자가용"],
            "description": "한적한 동해 해변을 즐기기 좋은 조용한 여행지",
            "activities": ["아야진해변", "통일전망대", "화진포 산책"],
            "food": "물회",
            "tip": "관광지 사이가 멀어 자가용 이용을 추천해요.",
            "transport_level": "불편",
        },
        {
            "name": "철원",
            "province": "강원특별자치도",
            "region": "강원권",
            "emoji": "🕊️",
            "themes": ["자연", "역사", "액티비티", "사진 촬영"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["친구", "가족"],
            "budgets": ["5만 원 이하", "5만 원~10만 원"],
            "transport": ["자가용"],
            "description": "주상절리와 평화 관광을 함께 즐기는 여행지",
            "activities": ["한탄강 주상절리길", "고석정", "DMZ 관광"],
            "food": "오대쌀 음식",
            "tip": "DMZ 관광은 운영 여부와 예약 조건을 확인하세요.",
            "transport_level": "불편",
        },
        {
            "name": "용인",
            "province": "경기도",
            "region": "수도권",
            "emoji": "🎢",
            "themes": ["액티비티", "문화", "자연", "사진 촬영"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["친구", "가족", "연인"],
            "budgets": ["5만 원~10만 원", "10만 원~20만 원"],
            "transport": ["대중교통", "자가용"],
            "description": "테마파크와 전통문화를 모두 즐길 수 있는 여행지",
            "activities": ["에버랜드", "한국민속촌", "호암미술관"],
            "food": "백암순대",
            "tip": "주말에는 인기 시설 대기시간을 고려하세요.",
            "transport_level": "보통",
        },
        {
            "name": "포천",
            "province": "경기도",
            "region": "수도권",
            "emoji": "🪨",
            "themes": ["자연", "힐링", "사진 촬영", "액티비티"],
            "durations": ["당일치기", "1박 2일"],
            "companions": ["친구", "가족", "연인"],
            "budgets": ["5만 원 이하", "5만 원~10만 원"],
            "transport": ["자가용"],
            "description": "호수와 숲, 넓은 자연 경관이 매력적인 여행지",
            "activities": ["포천아트밸리", "산정호수", "허브아일랜드"],
            "food": "이동갈비",
            "tip": "관광지가 넓게 흩어져 있어 자가용이 편해요.",
            "transport_level": "불편",
        },
    ]


def calculate_match_score(destination, filters):
    checks = []

    selected_themes = filters["themes"]
    if selected_themes:
        checks.append(bool(set(selected_themes) & set(destination["themes"])))

    for key, field in [
        ("duration", "durations"),
        ("companion", "companions"),
        ("budget", "budgets"),
        ("transport", "transport"),
    ]:
        value = filters[key]
        if value != "상관없음":
            checks.append(value in destination[field])

    if filters["region"] != "상관없음":
        checks.append(filters["region"] == destination["region"])

    if not checks:
        return 100

    return round(sum(checks) / len(checks) * 100)


def filter_destinations(destinations, filters):
    results = []

    for destination in destinations:
        if filters["themes"] and not set(filters["themes"]) & set(destination["themes"]):
            continue
        if filters["duration"] != "상관없음" and filters["duration"] not in destination["durations"]:
            continue
        if filters["companion"] != "상관없음" and filters["companion"] not in destination["companions"]:
            continue
        if filters["region"] != "상관없음" and filters["region"] != destination["region"]:
            continue
        if filters["budget"] != "상관없음" and filters["budget"] not in destination["budgets"]:
            continue
        if filters["transport"] != "상관없음" and filters["transport"] not in destination["transport"]:
            continue
        results.append(destination)

    return results


def choose_destination(destinations, filters):
    exact_matches = filter_destinations(destinations, filters)

    if exact_matches:
        return random.choice(exact_matches), ""

    scored = sorted(
        destinations,
        key=lambda item: calculate_match_score(item, filters),
        reverse=True,
    )
    best_score = calculate_match_score(scored[0], filters)
    best_matches = [
        item for item in scored
        if calculate_match_score(item, filters) == best_score
    ]

    return (
        random.choice(best_matches),
        "선택한 조건과 정확히 일치하는 여행지가 없어 가장 비슷한 여행지를 추천했어요.",
    )


def get_preference_text(filters):
    themes = filters["themes"]

    if "자연" in themes or "힐링" in themes or "산" in themes:
        return "자연 속에서 여유롭게 쉬는 여행을 좋아하는 편이에요."
    if "맛집" in themes and "사진 촬영" in themes:
        return "맛집과 사진 촬영을 함께 즐기는 알찬 여행 스타일이에요."
    if filters["transport"] == "대중교통":
        return "대중교통으로 가볍게 떠날 수 있는 여행지를 선호해요."
    if "액티비티" in themes:
        return "가만히 쉬기보다 직접 체험하고 움직이는 여행을 좋아해요."
    if "역사" in themes or "문화" in themes:
        return "지역의 역사와 문화를 천천히 살펴보는 여행을 좋아해요."
    return "새로운 장소를 발견하는 랜덤 여행에 잘 어울리는 스타일이에요."


def get_travel_difficulty(start_region, destination):
    if start_region == "상관없음":
        return "출발 지역을 정하지 않아 이동 난이도를 일반적으로 안내해요."

    mapping = {
        "서울": "수도권",
        "경기": "수도권",
        "인천": "수도권",
        "강원": "강원권",
        "충청": "충청권",
        "전라": "전라권",
        "경상": "경상권",
        "제주": "제주권",
    }

    start_zone = mapping.get(start_region)

    if start_zone == destination["region"]:
        return "가까운 편이에요. 당일치기나 짧은 일정도 가능해요."
    if "제주권" in [start_zone, destination["region"]]:
        return "비행기나 배 이동이 필요해 이동 난이도가 높은 편이에요."
    return "지역 간 이동이 필요해 1박 이상의 일정을 추천해요."


def display_destination_card(destination, filters):
    score = calculate_match_score(destination, filters)
    map_query = quote(destination["name"])
    search_query = quote(f"{destination['name']} 여행")

    st.markdown(
        f"""
        <div class="result-card">
            <div class="result-emoji">{destination['emoji']}</div>
            <h2>{destination['name']}</h2>
            <p class="province">{destination['province']} · {destination['region']}</p>
            <p class="description">{destination['description']}</p>
            <div class="score">조건 적합도 {score}점</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("추천 기간", " / ".join(destination["durations"]))
    with col2:
        st.metric("예상 예산", " / ".join(destination["budgets"]))
    with col3:
        st.metric("대중교통", destination["transport_level"])

    st.subheader("왜 추천됐나요?")
    reasons = []
    if filters["themes"] and set(filters["themes"]) & set(destination["themes"]):
        reasons.append("선택한 여행 테마와 잘 맞아요.")
    if filters["region"] == destination["region"]:
        reasons.append("선호한 권역에 포함돼요.")
    if filters["transport"] in destination["transport"]:
        reasons.append("선택한 이동 수단으로 여행하기 좋아요.")
    if not reasons:
        reasons.append("전체 조건을 비교했을 때 가장 높은 적합도를 보였어요.")
    st.write(" ".join(reasons))

    st.subheader("추천 활동")
    for activity in destination["activities"]:
        st.write(f"• {activity}")

    info_col1, info_col2 = st.columns(2)
    with info_col1:
        st.markdown("**대표 먹거리**")
        st.write(destination["food"])
        st.markdown("**추천 동행**")
        st.write(" / ".join(destination["companions"]))
    with info_col2:
        st.markdown("**여행 팁**")
        st.write(destination["tip"])
        st.markdown("**이동 난이도**")
        st.write(get_travel_difficulty(filters["start_region"], destination))

    link_col1, link_col2 = st.columns(2)
    with link_col1:
        st.link_button(
            "🗺️ 네이버 지도에서 검색",
            f"https://map.naver.com/p/search/{map_query}",
            use_container_width=True,
        )
    with link_col2:
        st.link_button(
            "🔍 네이버에서 여행 정보 검색",
            f"https://search.naver.com/search.naver?query={search_query}",
            use_container_width=True,
        )


def display_favorites():
    st.subheader("❤️ 찜한 여행지")

    if not st.session_state.favorites:
        st.info("아직 찜한 여행지가 없어요.")
        return

    for destination in st.session_state.favorites:
        with st.container(border=True):
            st.markdown(f"### {destination['emoji']} {destination['name']}")
            st.caption(f"{destination['province']} · {destination['region']}")
            st.write(destination["description"])
            st.write("**테마:** " + ", ".join(destination["themes"][:5]))
            st.write("**예상 예산:** " + " / ".join(destination["budgets"]))


def add_favorite(destination):
    names = [item["name"] for item in st.session_state.favorites]
    if destination["name"] not in names:
        st.session_state.favorites.append(destination)
        st.success("찜 목록에 추가했어요.")
    else:
        st.info("이미 찜한 여행지예요.")


def main():
    initialize_session_state()
    destinations = get_travel_destinations()

    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(180deg, #fff9f3 0%, #f4fbff 100%);
        }
        .main-title {
            text-align: center;
            font-size: 2.5rem;
            font-weight: 800;
            margin-top: 0.5rem;
        }
        .main-subtitle {
            text-align: center;
            color: #555;
            margin-bottom: 1.5rem;
        }
        .result-card {
            text-align: center;
            padding: 2rem;
            border-radius: 24px;
            background: rgba(255,255,255,0.9);
            border: 1px solid rgba(0,0,0,0.08);
            box-shadow: 0 12px 30px rgba(0,0,0,0.08);
            margin: 1rem 0 1.5rem 0;
        }
        .result-emoji {
            font-size: 4rem;
        }
        .result-card h2 {
            font-size: 2.4rem;
            margin: 0.3rem 0;
        }
        .province {
            color: #666;
        }
        .description {
            font-size: 1.1rem;
        }
        .score {
            display: inline-block;
            margin-top: 0.7rem;
            padding: 0.5rem 1rem;
            border-radius: 999px;
            background: #fff0c9;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="main-title">🎲 랜덤 국내여행 뽑기</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="main-subtitle">여행 조건을 선택하면 어울리는 국내 여행지를 랜덤으로 추천해드려요.</div>',
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["🎲 여행지 뽑기", "❤️ 찜 목록"])

    with tab1:
        with st.container(border=True):
            st.subheader("여행 조건 선택")

            col1, col2 = st.columns(2)

            with col1:
                start_region = st.selectbox(
                    "출발 지역",
                    ["상관없음", "서울", "경기", "인천", "강원", "충청", "전라", "경상", "제주"],
                    key="start_region_select",
                )
                duration = st.selectbox(
                    "여행 기간",
                    ["상관없음", "당일치기", "1박 2일", "2박 3일", "3박 이상"],
                    key="duration_select",
                )
                companion = st.selectbox(
                    "동행 유형",
                    ["상관없음", "혼자", "친구", "가족", "연인"],
                    key="companion_select",
                )
                budget = st.selectbox(
                    "여행 예산",
                    ["상관없음", "5만 원 이하", "5만 원~10만 원", "10만 원~20만 원", "20만 원 이상"],
                    key="budget_select",
                )

            with col2:
                region = st.selectbox(
                    "선호 권역",
                    ["상관없음", "수도권", "강원권", "충청권", "전라권", "경상권", "제주권"],
                    key="region_select",
                )
                transport = st.selectbox(
                    "이동 수단",
                    ["상관없음", "대중교통", "자가용"],
                    key="transport_select",
                )
                themes = st.multiselect(
                    "여행 테마",
                    [
                        "바다", "산", "자연", "맛집", "카페", "역사", "문화",
                        "액티비티", "힐링", "야경", "사진 촬영", "전통시장", "축제"
                    ],
                    key="themes_multiselect",
                )

            filters = {
                "start_region": start_region,
                "duration": duration,
                "companion": companion,
                "budget": budget,
                "region": region,
                "transport": transport,
                "themes": themes,
            }

            st.info(get_preference_text(filters))

            button_col1, button_col2 = st.columns(2)

            with button_col1:
                if st.button("🎲 여행지 뽑기", use_container_width=True, type="primary", key="draw_button"):
                    with st.spinner("여행지를 고르는 중이에요..."):
                        selected, relaxed_message = choose_destination(destinations, filters)
                    st.session_state.selected_destination = selected
                    st.session_state.last_filters = filters
                    st.session_state.relaxed_message = relaxed_message

            with button_col2:
                if st.button("✨ 아무 생각 없이 하나 뽑기", use_container_width=True, key="pure_random_button"):
                    selected = random.choice(destinations)
                    st.session_state.selected_destination = selected
                    st.session_state.last_filters = {
                        "start_region": start_region,
                        "duration": "상관없음",
                        "companion": "상관없음",
                        "budget": "상관없음",
                        "region": "상관없음",
                        "transport": "상관없음",
                        "themes": [],
                    }
                    st.session_state.relaxed_message = ""

        if st.session_state.selected_destination:
            if st.session_state.relaxed_message:
                st.warning(st.session_state.relaxed_message)

            display_destination_card(
                st.session_state.selected_destination,
                st.session_state.last_filters,
            )

            action_col1, action_col2, action_col3 = st.columns(3)

            with action_col1:
                if st.button("🔄 다시 뽑기", use_container_width=True, key="reroll_button"):
                    selected, relaxed_message = choose_destination(
                        destinations,
                        st.session_state.last_filters,
                    )
                    st.session_state.selected_destination = selected
                    st.session_state.relaxed_message = relaxed_message
                    st.rerun()

            with action_col2:
                if st.button("❤️ 여행지 찜하기", use_container_width=True, key="favorite_button"):
                    add_favorite(st.session_state.selected_destination)

            with action_col3:
                if st.button("🗑️ 찜 목록 초기화", use_container_width=True, key="clear_favorites_button"):
                    st.session_state.favorites = []
                    st.success("찜 목록을 초기화했어요.")

    with tab2:
        display_favorites()


if __name__ == "__main__":
    main()
'''

requirements = "streamlit>=1.36,<2.0\n"

(base / "app.py").write_text(textwrap.dedent(app_code).strip() + "\n", encoding="utf-8")
(base / "requirements.txt").write_text(requirements, encoding="utf-8")

zip_path = Path("/mnt/data/random_korea_trip_app.zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(base / "app.py", arcname="app.py")
    zf.write(base / "requirements.txt", arcname="requirements.txt")

print(f"Created: {base / 'app.py'}")
print(f"Created: {base / 'requirements.txt'}")
print(f"Created: {zip_path}")

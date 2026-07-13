import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(
    page_title="Global Top10 Stock Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("🌍 Global Market Cap Top10 Dashboard")
st.markdown("### 최근 1년 주가 비교")

# ----------------------------------------------------
# 글로벌 시가총액 Top10
# ----------------------------------------------------
TOP10 = {
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "NVIDIA": "NVDA",
    "Amazon": "AMZN",
    "Alphabet": "GOOGL",
    "Meta": "META",
    "Broadcom": "AVGO",
    "TSMC": "TSM",
    "Berkshire Hathaway": "BRK-B",
    "Saudi Aramco": "2222.SR",
}

# ----------------------------------------------------
# Sidebar
# ----------------------------------------------------
st.sidebar.header("설정")

selected = st.sidebar.multiselect(
    "기업 선택",
    options=list(TOP10.keys()),
    default=list(TOP10.keys())
)

normalize = st.sidebar.checkbox(
    "주가 정규화(Start=100)",
    value=True
)

# ----------------------------------------------------
# 데이터 다운로드
# ----------------------------------------------------
@st.cache_data(ttl=3600)
def load_data():

    tickers = list(TOP10.values())

    df = yf.download(
        tickers,
        period="1y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="ticker"
    )

    return df

data = load_data()

# ----------------------------------------------------
# Plotly Figure
# ----------------------------------------------------
fig = go.Figure()

summary = []

for company in selected:

    ticker = TOP10[company]

    try:

        stock = data[ticker]["Close"].dropna()

        if normalize:
            y = stock / stock.iloc[0] * 100
            y_title = "Performance Index"
        else:
            y = stock
            y_title = "Price ($)"

        change = (stock.iloc[-1] / stock.iloc[0] - 1) * 100

        summary.append({
            "기업": company,
            "현재가": round(stock.iloc[-1], 2),
            "1년 수익률(%)": round(change, 2)
        })

        fig.add_trace(
            go.Scatter(
                x=stock.index,
                y=y,
                mode="lines",
                name=company,
                hovertemplate="<b>%{fullData.name}</b><br>%{x|%Y-%m-%d}<br>%{y:.2f}<extra></extra>"
            )
        )

    except Exception:
        continue

# ----------------------------------------------------
# Plot Layout
# ----------------------------------------------------
fig.update_layout(

    template="plotly_dark",

    height=700,

    hovermode="x unified",

    title="Global Top10 Stock Performance",

    xaxis_title="Date",

    yaxis_title=y_title,

    legend_title="Company",

    margin=dict(l=20, r=20, t=60, b=20),
)

st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------
# Summary Table
# ----------------------------------------------------
st.subheader("📊 Summary")

summary_df = pd.DataFrame(summary)

summary_df = summary_df.sort_values(
    "1년 수익률(%)",
    ascending=False
)

st.dataframe(
    summary_df,
    use_container_width=True,
    hide_index=True
)

# ----------------------------------------------------
# Best Performer
# ----------------------------------------------------
winner = summary_df.iloc[0]

st.success(
    f"🏆 최근 1년 최고 수익률 : **{winner['기업']}** ({winner['1년 수익률(%)']}%)"
)

# ----------------------------------------------------
# 설명
# ----------------------------------------------------
with st.expander("📖 차트 설명"):

    st.markdown("""

- **정규화(Start=100)**

    시작일 가격을 100으로 맞춰 기업들의 성과를 비교합니다.

- 120 → 20% 상승

- 80 → 20% 하락

- Plotly 기능
    - 확대/축소
    - Hover
    - 이미지 저장
    - 범례 클릭으로 기업 숨기기

""")

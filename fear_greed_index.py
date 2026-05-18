import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import platform
if platform.system() == 'Darwin':
    plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False
df = fdr.DataReader('KS11', '2024-01-01')
df['MA20'] =df ['Close'].rolling(20).mean()
df['MA60'] =df['Close'].rolling(60).mean()
df['MA20_gap'] =(df['Close'] - df['MA20']) / df['MA20'] * 100
fig,  (ax1, ax2) = plt.subplots(2, 1, figsize=(12,8))
ax1.plot(df.index, df['Close'], label='KOSPI')
ax1.plot(df.index, df['MA20'], label ='20일 이동평균')
ax1.plot(df.index, df['MA60'], label ='60일 이동평균')
ax1.set_title('KOSPI 지수')
ax1.legend()
ax2.bar(df.index, df['Volume'], label='거래량')
ax2.set_title('거래량')
ax2.legend()
plt.tight_layout()
st.pyplot(fig)
def normalize(series):
    return (series -series.min()) / (series.max() - series.min()) * 100
df['MA20_gap_norm'] = normalize(df ['MA20_gap'])
df['Volume_change'] = df['Volume'].pct_change()
df['Volume_norm'] = normalize(df['Volume_change'].dropna()).reindex(df.index)
df['Return'] = df['Close'].pct_change()
df['Volatility'] = df['Return'].rolling(20).std()
df['Volatility_norm'] = 100 - normalize(df['Volatility'])
df['Momentum'] = df['Close'] / df['Close'].shift(20) - 1
df['Momentum_norm'] = normalize(df['Momentum'])
df['High_52w'] = df ['Close'].rolling(252).max()
df['Low_52w'] = df['Close'].rolling(252).min()
df['HL_ratio'] = (df['Close'] - df['Low_52w']) / (df['High_52w'] - df ['Low_52w']) * 100
df['HL_norm'] = normalize(df['HL_ratio'])
df['Buy_pressure'] = df['Return'] * df['Volume']
df['Buy_pressure_ma'] = df['Buy_pressure'].rolling(20).mean()
df['Foreign_norm'] = normalize(df['Buy_pressure_ma'])
delta = df['Close'] .diff()
gain =delta.clip(lower=0)
loss = (-delta). clip(lower=0)
avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()
rs = avg_gain / avg_loss
df['RSI'] = 100 - (100 / (1 + rs))
df['RSI_norm'] = normalize(df['RSI'])
df['Fear_Greed'] =(
    df['MA20_gap_norm'] + 
    df['Volume_norm'] +
    df['Volatility_norm'] + 
    df['Momentum_norm'] + 
    df['HL_norm'] + 
    df['Foreign_norm'] +
    df['RSI_norm'] 
)/7
today_score = df['Fear_Greed'].iloc[-1]
st.write(f"\n오늘 공포탐욕지수: {today_score:.1f}")
if today_score >= 75:
    st.write("상태: 극도의 탐욕")
elif today_score >= 55:
    st.write("상태: 탐욕")
elif today_score >= 45:
    st.write("상태: 중립")
elif today_score >= 25:
    st.write("상태: 공포")
else:
    st.write("상태: 극도의 공포")
# Granger:인과검정
#"공포 탐욕지수가 KOSPI를 예측할수있나?" 검증

# statsmodels에서 Granger 검정함수 가져오기 
from statsmodels.tsa.stattools import grangercausalitytests

#결측값(NaN) 제거
# Granger 검증은 NAN이 있으면 오류남
df_granger = df[['Fear_Greed', 'Return']].dropna()
# Return: KOSPI 일간 수익률 (Close의 pct_change)
# 이 둘의 관계를 검정할 거야

# Granger 검정 실행
# maxlag=5: 최대 5일 전까지 영향을 볼 거야
results = grangercausalitytests(
    df_granger[['Return', 'Fear_Greed']],
    maxlag=5,
    verbose=False #터미널 출력끄기
)

# 결과 화면을 웹화면에 출력 하기
st.markdown("---")
st.subheader("📊 Granger 인과검정 결과")
st.write("공포탐욕지수가 KOSPI 수익률을 예측 할수 있는지 검증")

#lag별 p-value 출력
# lag: 며칠후에 영향을 주는지
for lag in range(1, 6):
    # p-value 추출
    # ssr_ftest: f검정 방식(사장 많이 쓰임)
    p_value = results[lag][0]['ssr_ftest'][1]

    if p_value < 0.05:
        # p-value가 0.05미만이면 통계학적으로 유의미
        result_text = "유의미함"
    else:
        # p-vauleark 0.05 이상이면 우연일수가 있음
        result_text = "유의미하지 않음"

    st.write(f"{lag}일 후: p-value = {p_value:.4f} -> {result_text}")
                 

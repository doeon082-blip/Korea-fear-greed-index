import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import platform
if platform.system() == 'Darwin':
    plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False
import FinanceDataReader as fdr
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
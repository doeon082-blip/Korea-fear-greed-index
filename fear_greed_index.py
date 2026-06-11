import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import platform
if platform.system() == 'Darwin':
    plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False
df = fdr.DataReader('KS11', '2020-01-01')
# 원달러 환율 데이터 불러오기
# USD/KRW: 달러 대비 원화 환율
df_usd = fdr.DataReader('USD/KRW', '2020-01-01')
# 환율 정규화
# 환율 오르면 외국인 투자 감소 → 공포 신호
# 그래서 역방향으로 정규화
df_bond = fdr.DataReader('^TNX', '2020-01-01')
# S&P500 데이터 수집
# 미국 시장이 한국보다 하루 먼저 움직임
# 선행 지표로 활용
df_sp500 = fdr.DataReader('^GSPC', '2020-01-01')
# VIX 데이터 수집
# 미국 공포지수
# 글로벌 불안감 측정
df_vix = fdr.DataReader('^VIX','2020-01-01')
# 금 가격
# 안전자산 선호 지표
# 불안할수록 금 가격 오름
df_gold= fdr.DataReader('GC=F','2020-01-01')
df['MA20'] =df ['Close'].rolling(20).mean()
df['MA60'] =df['Close'].rolling(60).mean()
df['MA120'] =df['Close'].rolling(120).mean()
df['MA240'] =df['Close'].rolling(240).mean()
df['MA20_gap'] =(df['Close'] - df['MA20']) / df['MA20'] * 100
fig,  (ax1, ax2) = plt.subplots(2, 1, figsize=(12,8))
ax1.plot(df.index, df['Close'], label='KOSPI')
ax1.plot(df.index, df['MA20'], label ='20일 이동평균')
ax1.plot(df.index, df['MA60'], label ='60일 이동평균')
ax1.plot(df.index, df['MA120'], label ='120일 이동평균')
ax1.plot(df.index, df['MA240'], label ='240일 이동평균')
ax1.set_title('KOSPI 지수')
ax1.legend()
ax2.bar(df.index, df['Volume'], label='거래량')
ax2.set_title('거래량')
ax2.legend()
plt.tight_layout()


# 롤링 윈도우 정규화
# 최근 252일(1년) 기준으로 정규화
# 전역 정규화와 달리 과거 점수 변동 없음
def normalize_rolling(series, window=252):
    """
    series: 계산할 주식 지표 데이터 (환율, 변동성 등)
    window: 과거 몇 일 동안의 시장 체급을 기준으로 잡을 것인가? (252일 = 보통 1년 영업일)
    """
        # 1. [롤링 윈도우] 매일 아침 기준으로 '최근 1년 창문'을 열어서 그 안의 최솟값, 최댓값을 찾습니다.
        # 이렇게 하면 미래의 데이터를 미리 훔쳐보는 오류(치팅)를 완벽하게 차단합니다.
    rolling_min = series.rolling(window).min()
    rolling_max = series.rolling(window).max()
        # 2. [0~100 점수 환산] 최근 1년 체급 안에서 오늘의 위치를 점수(0~100)로 보정합니다.
         # 💡 1e-8을 더하는 이유: 분모가 0이 되어 프로그램이 튕기는 현상(에러)을 컴퓨터 공학적으로 막아주는 안전장치입니다.
    result = (series -rolling_min) / (rolling_max - rolling_min+ 1e-8) * 100

        # 3. [초기 NaN 데이터 구제] 프로그램 시작 후 첫 1년(251일째까지)은 '과거 1년 데이터'가 없어서 빈 칸(NaN)이 됩니다.
        # 빈 칸이 있으면 뒤쪽 계산에서 에러가 나기 때문에, 이 초반 구간만 전체 기간 기준으로 점수를 매겨서 채워줍니다(fillna).
    global_min = series.min()
    global_max = series.max()
    global_norm = (series -global_min) / (global_max -global_min +1e-8) * 100

         # 4. [최종 출력] 클로드 코드와 달리, 이제 진짜 롤링 계산된 결과물이 밖으로 튀어나갑니다!
    return result.fillna(global_norm)
    
df['MA20_gap_norm'] = normalize_rolling(df ['MA20_gap'])
df['Volume_change'] = df['Volume'].pct_change()
df['Volume_norm'] = normalize_rolling(df['Volume_change'].dropna()).reindex(df.index)
df['Return'] = df['Close'].pct_change()
df['Volatility'] = df['Return'].rolling(20).std()
df['Volatility_norm'] = 100 - normalize_rolling(df['Volatility'])
df['Momentum'] = df['Close'] / df['Close'].shift(20) - 1
df['Momentum_norm'] = normalize_rolling(df['Momentum'])
df['High_52w'] = df ['Close'].rolling(252).max()
df['Low_52w'] = df['Close'].rolling(252).min()
df['HL_ratio'] = (df['Close'] - df['Low_52w']) / (df['High_52w'] - df ['Low_52w']) * 100
df['HL_norm'] = normalize_rolling(df['HL_ratio'])
delta = df['Close'] .diff()
gain =delta.clip(lower=0)
loss = (-delta). clip(lower=0)
avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()
rs = avg_gain / avg_loss
df['RSI'] = 100 - (100 / (1 + rs))
df['RSI_norm'] = normalize_rolling(df['RSI'])
df['USD_KRW'] = df_usd['Close'].reindex(df.index)
df['USD_norm'] = 100 - normalize_rolling(df['USD_KRW'])
df['BOND'] = df_bond['Close'].reindex(df.index)
df['BOND_norm'] =100 - normalize_rolling(df['BOND'])
# S&P500 전일 수익률
# 미국 시장이 한국보다 하루 먼저 움직임
# 미국이 오늘 올랐으면 한국은 내일 오를 가능성
# .shift(1): 하루 전 데이터로 맞추기
df['SP500'] = df_sp500['Close'].reindex(df.index)
df['SP500_return'] = df['SP500'].pct_change()
# 수익률이 높을수록 탐욕신호
df['SP500_norm'] = normalize_rolling(df['SP500_return'].shift(1))
# VIX (미국 공포지수)
# VIX 높으면 글로벌 공포 → 한국도 하락
# 역방향: VIX 높으면 공포탐욕지수 낮춰야 함
df['VIX'] = df_vix['Close'].reindex(df.index)
df['VIX_norm'] = 100 - normalize_rolling(df['VIX'])
# 금 가격
# 금 오르면 안전자산 선호 → 주식 공포
# 역방향 정규화
df['GOLD'] = df_gold['Close'].reindex(df.index)
df['GOLD_norm'] = 100 - normalize_rolling(df['GOLD'])
# 11개 지표 평균으로 공포탐욕지수 계산
# mean(axis=1): 행 방향으로 평균
# NaN 있어도 나머지로 계산함

indicator_cols_calc = [
    'MA20_gap_norm',# 이동평균 괴리율 (앵커링 효과)
    'Volume_norm', # 거래량 (군중심리)
    'Volatility_norm', # 변동성 (과잉반응)
    'Momentum_norm', # 모멘텀 (추세 추종)
    'HL_norm', # 52주 고저비율 (준거점 효과) 
    'RSI_norm',   # RSI (과매수/과매도) 
    'USD_norm',# 원달러 환율 (외부충격)
    'BOND_norm',  # 미국 국채금리 (안전자산)
    'SP500_norm', #s&p500 수익률(선행지표)
    'VIX_norm', # VIX(글로벌 공포)
    'GOLD_norm', # 금 가격(안전 자산 선호)
]
df['Fear_Greed'] = df[indicator_cols_calc].mean(axis=1)
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
st.pyplot(fig)

# 상관관계 분석
# 11개 지표가 서로 얼마나 관련있는지 확인


# 11개 지표 컬럼만 모아서 새 데이터프레임 만들기
indicator_cols  =[
    'MA20_gap_norm', # 이동 평균 괴리율
    'Volume_norm', # 거래량
    'Volatility_norm', #변동성
    'Momentum_norm', # 모멘텀
    'HL_norm', #52주 고저비율
    'RSI_norm', # RSI
    'USD_norm', # 원달러 환율
    'BOND_norm',#미국 10년채 국채 금리
    'SP500_norm', #S&P500
    'VIX_norm', #VIX 지수
    'GOLD_norm' # GOLD 안전자산
]

# 상관관계 계산
# .corr(): 각 지표 간 상관관계 계산
# -1 ~ 1 사이 숫자로 나옴
# 1: 완전히 같이 움직임
# 0: 관계없음
# -1: 반대로 움직임
corr_matrix = df[indicator_cols].corr()

# 웹화면에 표시
st.markdown("---")
st.subheader("지표간 상관관계분석")
st.write("1에 가까울수록 같이 움직임, -1에 가까울수록 반대로 움직임")

# 히트맵 시각화
fig_corr, ax = plt.subplots(figsize=(10, 8))

# imshow: 색깔로 숫자를 표현하는 차트
im =ax.imshow(corr_matrix, cmap='RdYlGn', vmin=-1, vmax=1)
# cmap='RdYlGn': 빨강(음수) → 노랑(0) → 초록(양수)
# vmin=-1, vmax=1: 색깔 범위 고정

# 축 레이블 설정
ax.set_xticks(range(len(indicator_cols)))
ax.set_yticks(range(len(indicator_cols)))
ax.set_xticklabels(['MA괴리율', '거래량', '변동성', '모멘텀', '고저비율', '환율', '미국국채금리', 'RSI','S&P500','VIX','금'], rotation=45)
ax.set_yticklabels(['MA괴리율', '거래량', '변동성', '모멘텀', '고저비율', '환율', '미국국채금리', 'RSI','S&P500','VIX','금'])

# 각 칸에 숫자표시
for i in range(len(indicator_cols)):
    for j in range(len(indicator_cols)):
        ax.text(j, i, f'{corr_matrix.iloc[i, j]:.2f}',
                ha='center', va='center', fontsize=9)

# 색깔막대 추가
plt.colorbar(im, ax=ax)
ax.set_title('지표 간 상관관계 히트맵')
plt.tight_layout()

st.pyplot(fig_corr)

# 높은 상관관계 지표찾기 (0.7 이상이면 비슷한지표)
st.write("**상관관계 0.7이상인 지표 쌍 (중복가능성);**")
for i in range(len(indicator_cols)):
    for j in range(i+1, len(indicator_cols)):
        if abs(corr_matrix.iloc[i, j]) >=0.7:
            st.write(f"➡️ {indicator_cols[i]} & {indicator_cols[j]}; {corr_matrix.iloc[i, j]:.2f}")

# ADF 검정 (Augmented Dickey-Fuller Test)
# Granger 검정 전에 반드시 해야 하는 것
# 데이터가 안정적인지 (정상 시계열인지) 확인

# statsmodels에서 ADF 검정 함수 가져오기
from statsmodels.tsa.stattools import adfuller


# [웹화면 구성]
# st.markdown("---"): 웹화면에 가로 구분선 그리기
# "---" 는 마크다운에서 구분선을 의미
st.markdown("---")

# st.subheader(): 중간 크기 제목 표시
# st.title() > st.header() > st.subheader() 순서로 작아짐
st.subheader(" ADF 검정결과 (시계열 안정성 확인)")

st.write("Granger 검정 전 데이터가 안정적인지 확인합니다")
st.write("p-value < 0.05 안정적 Granger 검정 가능")
st.write("p-value > = 0.05 불안정 차분 처리 필요")

# [변수 1] adf_targets - 검정할 지표 목록
# =============================================
# 딕셔너리(Dictionary): 키:값 형태로 데이터 저장
# 형태: {'키': '값', '키': '값'}
# 왼쪽(키) = 웹화면에 표시할 이름
# 오른쪽(값) = df에 있는 실제 컬럼 이름
#
# 왜 딕셔너리를 쓰냐?
# → 이름이랑 컬럼명 한 번에 관리하려고
# → for 루프에서 둘 다 동시에 꺼내 쓸 수 있어

adf_targets = {
    '공포탐욕지수': 'Fear_Greed', #우리가 만든 지수 
    'KOSPI 수익률': 'Return', # 월간 수익률
    '원달러 환율': 'USD_KRW', # 원달러 환율 원본
    '미국 국채 금리': 'BOND', # 국채금리 원본
}

# [변수 2] adf_results - 결과 저장 리스트
# =============================================
# 리스트(List): 여러 값을 순서대로 담는 것
# [] = 빈 리스트 (아무것도 없는 목록)
# 나중에 for 루프에서 결과를 하나씩 추가할 거야
# 최종적으로 표(DataFrame)로 만들기 위해
adf_results = []

# [for 루프] 4개 지표 각각 ADF 검정
# =============================================
# for name, col in adf_targets.items():
# → adf_targets 딕셔너리에서
# → 키(name)와 값(col)을 동시에 꺼내기
# → .items(): 딕셔너리의 키-값 쌍을 꺼내는 메서드
#
# 1번째 반복: name='공포탐욕지수', col='Fear_Greed'
# 2번째 반복: name='KOSPI 수익률', col='Return'
# 3번째 반복: name='원달러 환율', col='USD_KRW'
# 4번째 반복: name='미국 국채금리', col='BOND
for name, col in adf_targets.items():

        # [메서드] df[col].dropna()
    # df[col]: df에서 col 이름의 컬럼 선택
    #   예: col='Fear_Greed' 이면 df['Fear_Greed'] 선택
    # .dropna(): NaN(결측값) 제거 메서드
    #   NaN = Not a Number = 값이 없는 것
    #   ADF 검정은 NaN 있으면 오류나서 반드시 제거해야 함
    # series: 선택된 컬럼 데이터
    #   (변수 이름은 내가 붙인 것, 뭐든 상관없음)
    series = df[col].dropna()

    # [함수] adfuller()
    # ADF 검정 실행하는 함수
    # 입력: series (검정할 데이터)
    # 출력: result (여러 숫자가 담긴 튜플)
    #
    # result[0]: 검정 통계량 (숫자가 클수록 불안정)
    # result[1]: p-value (제일 중요!)
    # result[2]: 최적 lag 수
    # result[3]: 관측치 수
    # result[4]: 임계값 딕셔너리 (1%, 5%, 10% 기준)
    result = adfuller(series)

    # result[1]: p-value 추출
    # [1] = 인덱스 (0부터 시작, 두 번째 값)
    # 숫자 1 (일) 맞음, 소문자 l (엘) 아님
    p_value = result[1]

       # [조건문] p-value 기준으로 안정성 판단
    # if: 만약 ~이라면
    # p_value < 0.05: p-value가 0.05보다 작으면
    if p_value < 0.05:
        status = '안정적'
    else:
        status = '불안정(차분필요)'

    # [메서드] adf_results.append()
    # .append(): 리스트 맨 뒤에 항목 추가하는 메서드
    # 딕셔너리 형태로 추가
    # {'지표': 이름, 'p-value': 숫자, '판단': 결과}
    adf_results.append({
        '지표' : name,
        'p_value': round(p_value, 4),
         # round(숫자, 소수점자리): 반올림 함수
        # round(0.01234567, 4) = 0.0123
        '판단': status
    })

# =============================================
# [루프 밖] 표 출력
# =============================================
# 왜 루프 밖에 있냐?
# 루프 안에 넣으면 반복할 때마다 출력됨
# 4번 반복 → 표 4번 출력 (버그)
# 루프 끝난 후 한 번만 출력해야 함

# pd.DataFrame(): 리스트를 표 형태로 변환
# pd = pandas 라이브러리 (import pandas as pd)
# DataFrame = 행과 열이 있는 표
adf_df =pd.DataFrame(adf_results)

st.table(adf_df)

# 차분 처리 (Differencing)
# =============================================
# [왜 하냐?]
# ADF 검정 결과 환율, 국채금리가 불안정
# 원본 그대로 쓰면 Granger 검정 결과 신뢰 불가
# 차분 = 변화량으로 변환 → 안정화
#
# pct_change(): 변화율 계산 메서드
# (오늘값 - 어제값) / 어제값
# 예: 어제 환율 1380, 오늘 1390
# → (1390 - 1380) / 1380 = 0.0072 (0.72% 상승)

# 공포탐욕지수 차분
# 변수명 뒤에 _diff 붙이는 건 관례
# diff = difference(차이)의 줄임말
df['Fear_Greed_diff'] =df['Fear_Greed'].pct_change()
df['USD_diff'] =df['USD_KRW'].pct_change()
df['BOND_diff'] =df['BOND'].pct_change()

# Return은 이미 pct_change()로 만들었음
# df['Return'] = df['Close'].pct_change() ← 위에서 이미 함
# 그래서 차분 안 해도 됨

# =============================================
# 차분 후 ADF 재검정
# =============================================
# 차분 후 안정적으로 바뀌었는지 확인
# 안 바뀌었으면 2차 차분 필요 (거의 없음)

# st.write() 안에 ** ** = 마크다운 굵게 표시
st.write("** 차분후 ADF 재검정:**")
diff_targets ={
    '공포탐욕지수 차분': 'Fear_Greed_diff',
    '원달러 환율 차분': 'USD_diff',
    '미국 국채금리 차분': 'BOND_diff',
}

diff_results =[]
for name, col in diff_targets.items():
    series = df[col].dropna()
    result = adfuller(series)
    p_value =result[1]

    if p_value <0.05:
        status ='안정적'
    else:
        status = "여전히 불안정"

    diff_results.append({
        '지표': name ,
        'p-value': round(p_value, 4),
        '판단' : status
    })
#루프 밖에서 한번만 표 출력
diff_df =pd.DataFrame(diff_results)
st.table(diff_df)

# Granger 검정 데이터 준비
# =============================================
# 기존: 원본 Fear_Greed 사용 (불안정)
# 수정: 차분된 Fear_Greed_diff 사용 (안정)
#
# df[[]]: 여러 컬럼 동시에 선택
# .dropna(): NaN 있는 행 전체 제거
# NaN 하나라도 있으면 그 행 전체 삭제
# Granger 검정 함수 가져오기
from statsmodels.tsa.stattools import grangercausalitytests

df_granger = df[[
    'Return',  #KOSpl 수익률
    'Fear_Greed_diff', #차분된 공포 탐욕지수 (안정화됨)
    'USD_diff', # 차분된 환율 (안정화됨)
    'BOND_diff' #  차분된 국채 금리(안정화됨)
]].dropna()

# Granger 검정 실행
# df_granger[['Return', 'Fear_Greed_diff']]:
# → 4개 컬럼 중 2개만 선택해서 검정
# → "Fear_Greed_diff가 Return을 예측하나?" 검정
results = grangercausalitytests(
    df_granger[['Return', 'Fear_Greed_diff']],
    maxlag=20, #최대 20일후까지 영향 검정
    verbose=False #터미널 출력끄기
)

# 결과 화면을 웹화면에 출력 하기
st.markdown("---")
st.subheader("📊 Granger 인과검정 결과")
st.write("공포탐욕지수가 KOSPI 수익률을 예측 할수 있는지 검증")

#lag별 p-value 출력
# lag: 며칠후에 영향을 주는지
for lag in range(1, 21):
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

# 뉴스 감성분석
#하는 이유
#숫자 지표고으로는 시장 심리를 완벽하게 읽을수가 없다
#뉴스가 투자자 심리에 직접 영향을준다
#뉴스 감성을 수치화해서 지표로 활용

#RSS;뉴스를 자동으로 구독하는방식
 # 숫자 지표로만 완전히 시장심리를 못읽음
 # 뉴스가 투자자 심리에 직접적 영향을 줌
# 예: 반도체 수출 호조 뉴스 → 시장 상승
#     금리 인상 우려 뉴스 → 시장 하락
# 왜 제목만 보내냐:
# 1. 본문은 너무 길어서 LLM 속도 느려짐
# 2. 저작권 문제 (본문 저장하면 안 됨)
# 3. 제목만 봐도 감성 판단 충분
# 왜 30개냐:
# 10개는 대표성 부족
# 30개면 오늘 시장 전반적 분위기 파악 가능
# 반환값:
# overall_score: 전체 감성 점수 (0~100)
# news_list: 뉴스별 분석 결과 리스트
# sector_data: 섹터별 감성 딕셔너리
# dominant_sector: 오늘 주도 섹터
#pos_count: 긍정 뉴스 개수
# neg_count: 부정 뉴스 개수
import feedparser #feedparser:RSS 피드읽는 라이브러리
import json # JSON 파싱 라이브러리
import re  # 정규표현식 (텍스트 패턴 찾기)

def get_news_sentiment():
    try:
        # 바깥쪽 try
        # RSS 수집 실패하면 50.0 반환
         # RSS 수집 자체가 실패할 때를 대비
        # 인터넷 끊기거나 서버 오류날 수 있음
        # 연합뉴스 경제 RSS 수집
        # 왜 연합뉴스냐:
        # → 네이버 RSS는 막혀있음 (테스트 결과)
        # → 연합뉴스는 120개 이상 제공
        # → 경제 뉴스 전문
        feed = feedparser.parse(
            "https://www.yna.co.kr/rss/economy.xml"
        )

        # 뉴스 제목 30개만 수집
        # feed.entries: 전체 뉴스 목록
        # [:20]: 최신 30개만 (오래된 건 필요없음)
        # entry.title: 뉴스 제목만 (본문 X)
        news_titles = []
        for entry in feed.entries[:20]:
            news_titles.append(entry.title)

        # 뉴스가 하나도 없으면 기본값 반환
        # RSS 서버 응답은 했는데 뉴스가 없는 경우
        if not news_titles:
            return 50.0,[], {}, '없음', 0, 0 , 0
        # 뉴스 제목 특수문자 제거
        # 큰따옴표, 말줄임표 등이 JSON 파싱 방해
        clean_titles = []
        for title in news_titles:
            title = title.replace('"', '')
            title = title.replace("'", '')
            title = title.replace('…', '')
            title = title.replace('\\', '')
            title = title.replace('"', '')
            title = title.replace('"', '')
            clean_titles.append(title)
        # 뉴스 제목들을 줄바꿈으로 합치기
        # LLM에게 한 번에 전달하기 위해
        # "\n".join(): 리스트를 줄바꿈으로 연결
        # ["뉴스1", "뉴스2"] → "뉴스1\n뉴스2"
        combined = "\n".join(clean_titles)

        try:
            # 안쪽 try
            # LLM 분석 실패할 때를 대비
            # ollama 꺼져있거나 모델 없을 수 있음
            
            import ollama
            
            response1 = ollama.chat(
                model='qwen2.5:14b',
                options ={
                    'num_predict': 4096 # 출력 길게 하기
                },
                messages=[
                    {
                    # system 역할:
                        # LLM에게 역할 지정
                        # user 메시지보다 먼저 읽힘
                        # JSON만 출력하도록 강력하게 지시
                        # 왜 필요하냐:
                        # → LLM이 "네, 분석했습니다. {...}" 처럼
                        #   앞뒤에 말 붙이는 걸 방지
                    "role": "system",
                    "content": """너는 한국 주식 시장  뉴스 분석 AI 야.
반드시 JSON만 출력해. 다른 말은 절대 하지 마.
앞에 설명도 없고 뒤에 설명도 없어. JSON만."""
                    },

                    {
                        "role":"user",
                        # f-string 안에서 JSON 쓰는 법:
                        # {{ }} = 중괄호 문자 그대로 출력
                        # {변수} = 변수값으로 교체
                        # combined = 뉴스 제목들
                        "content": f"""
다음 뉴스를 분석해줘.

{{
    "overall_score" : 50
    "dominant_sector": "반도체",
    "sectors": {{
        "반도체": "긍정",
        "조선": "중립",
        "방산": "부정",
        "금융": "중립",
        "부동산": "부정"
    }},
    "news": [
        {{
            "title": "뉴스제목",
            "sentiment": "긍정",
            "sector": "반도체",
            "reason": "이유",
            "score": 70
        }}
    ]
}}

규칙:
- overall_score: 0~100 숫자
- sentiment: 긍정/부정/중립 중 하나
- sector: 반도체/조선/방산/금융/부동산/소비재/기타 중 하나
- score: 0~100 숫자
- reason: 한 줄로 짧게
- title 안에 큰따옴표(") 절대 사용 금지 
- title: 반드시 실제 뉴스 제목 그대로 넣을 것
- overall_score: 뉴스 전체 분위기 기반으로 직접 계산할 것
- overall_score: 뉴스 전체 분석 후 직접 계산 (0~100)
  → 긍정 뉴스 많으면 높게
  → 부정 뉴스 많으면 낮게

뉴스:
{chr(10).join(clean_titles[:10])}
"""
                    }
                ]
            )
            response2 = ollama.chat(
                model = 'qwen2.5:14b',
                options ={
                    'num_predict' : 4096
                },
                messages = [
                    {"role": "system", "content": "JSON만 출력해."} ,
                    {"role": "user", "content": f"""
            다음 뉴스 분석 해줘.
            {{"news": [{{"title":"","sentiment": " 긍정 ", "sector" : "기타" , "reason":"","score": 70}}]}}
            규칙:
            - sentiment: 긍정/부정/중립
            - sector: 반도체/조선/방산/금융/부동산/소비재/기타
            - title 안에 큰따옴표 절대 금지
            
            뉴스:
            {chr(10).join(clean_titles[10:20])}
            """ }                                                
                    ]
            )
            # LLM 응답 텍스트 추출
            # .strip(): 앞뒤 공백/줄바꿈 제거
            raw1 = response1['message']['content'].strip()

            # 마크다운 코드블록 제거
            # LLM이 ```json {...} ``` 형태로 줄 수 있음
            # split('```'): 백틱 기준으로 나누기
            # [1]: 중간 부분 (JSON 내용)
            if '```' in raw1:
                raw1 = raw1.split('```')[1]
                if raw1.startswith('json'):
                    # 'json' 문자 4글자 제거
                    raw1 = raw1[4:]
            # 정규표현식으로 JSON 부분만 추출
            # 왜 필요하냐:
            # → LLM이 앞뒤에 말 붙여도 JSON만 추출
            # → re.search: 패턴 찾기
            # → r'\{.*\}': { 로 시작해서 } 로 끝나는 것
            # → re.DOTALL: 줄바꿈도 포함
            json_match1 = re.search(r'\{.*\}', raw1, re.DOTALL)
            if json_match1:
                raw1 = json_match1.group()
                # trailing comma 자동 제거
                # 왜 필요하냐:
                # → LLM이 JSON 출력할 때 쉼표 습관적으로 붙임
                # → {"key": "value",} 이런 형태
                # → 파이썬 json.loads()는 이걸 오류로 처리
                # → 파싱 전에 미리 제거해야 함

                # re.sub(): 찾아서 바꾸기
                # r',\s*}': 쉼표 + 공백 + 닫는 중괄호 패턴
                # \s* = 공백 0개 이상
                # 예: ,} 또는 ,   } 전부 찾아서 } 로 바꿈
                raw1= re.sub(r',\s*}', '}', raw1)
                # r',\s*]': 쉼표 + 공백 + 닫는 대괄호 패턴
                # 배열 끝에 붙은 trailing comma 제거
                # 예: {"sentiment": "긍정",] → {"sentiment": "긍정"]
                raw1 = re.sub(r',\s*]', ']', raw1)

                # 제목 안의 큰따옴표 제거
                # 뉴스 제목에 " 있으면 JSON 파싱 오류남
                raw1 = raw1.replace('\\"', '')

            # JSON 문자열 → 파이썬 딕셔너리 변환
            # json.loads(): 문자열을 딕셔너리로 변환
            # '{"score": 57}' → {'score': 57}
            result1 = json.loads(raw1)
            # 각 데이터 추출
            # .get('키', 기본값):
            # → 키가 없으면 기본값 반환
            # → 오류 방지

            # raw 2 피싱
            raw2 = response2['message']['content'].strip()
            if '```' in raw2:
                raw2 = raw2.split('```')[1]
                if raw2.startswith('json'):
                    raw2 = raw2[4:]
            json_match2 = re.search(r'\{.*\}',raw2 , re.DOTALL)
            if json_match2:
                raw2 = json_match2.group()
            raw2 = re.sub(r',\s*}', '}', raw2)
            raw2 = re.sub(r',\s*]', ']', raw2)
            raw2 = raw2.replace('\\"','')
            result2 = json.loads(raw2)

            # float() 변환 이유:
            # LLM이 숫자를 문자열로 줄 수도 있음
            # "57" → 57.0 으로 변환
            overall_score = float(result1.get('overall_score') or 50)
            st.write(f"LLM 원본 점수: {result1.get('overall_score')}")
            news_list = (result1.get('news') or []) + (result2.get('news') or [])
            sector_data = result1.get('sectors')or {} 
            dominant_sector = result1.get('dominant_sector') or '없음'
            # 우리가 직접 긍정/부정 개수 세기
            # 왜 LLM 숫자 안 쓰냐:
            # → LLM이 직접 세면 실수함
            # → 실제 뉴스별 분석 결과랑 안 맞음
            # → 우리가 직접 세는 게 더 정확

            # sum(): 합계 계산 함수
            # 1 for news in news_list: 
            #   → news_list에서 하나씩 꺼내서
            #   → 조건 맞으면 1 추가
            # if news.get('sentiment') == '긍정':
            #   → sentiment가 긍정인 것만

            # 예시:
            # news_list = [
            #   {'sentiment': '긍정'},  → 1
            #   {'sentiment': '부정'},  → 0
            #   {'sentiment': '긍정'},  → 1
            # ]
            # sum = 2 (긍정 2개)
            positive_count = sum(
                1 for news in news_list
                if news.get('sentiment') == '긍정'
            )

            negative_count = sum (
                1 for news in news_list 
                if news.get('sentiment') == '부정'
            )
            neutral_count = sum(
                1 for news in news_list
                if news.get('sentiment') == '중립'
            )

            return overall_score, news_list, sector_data, dominant_sector, positive_count, negative_count , neutral_count
        except Exception as e:
            st.write(f"오류: {e}")
            return 50.0, [], {}, '없음', 0, 0 , 0
    except:
        # 바깥쪽 except: RSS 수집 오류
        # 인터넷 연결 끊김 등
        return 50.0, [], {}, '없음', 0, 0 , 0
    
# 웹화면 출력
st.markdown('---')
st.subheader("📰 뉴스 감성 분석")

# st.spinner: 분석 중 로딩 표시
# with 블록 안의 코드 실행 중에 스피너 보임
with st.spinner("뉴스 분석중..."):
     # 함수 반환값 6개 받기
    # 변수 6개에 각각 저장
    news_score, news_list, sector_data, dominant_sector, pos_count, neg_count , neutral_count = get_news_sentiment()

# 전체 감성 상태 분류
# 70 이상: 긍정 (탐욕)
# 40~70: 중립
# 40 미만: 부정 (공포)
if news_score >= 70:
    news_status = "🟢 긍정적 (탐욕)"
elif news_score >= 40:
    news_status = "🟡 중립"
else:
    news_status = "🔴 부정적 (공포)"

st.write(f"뉴스 감성 점수: {news_score:.1f} / 100")
st.write(f"뉴스 분위기: {news_status}")
st.write(f"긍정 뉴스: {pos_count}개/ 부정 뉴스: {neg_count}개")
st.write(f"오늘 주도 섹터: {dominant_sector}")
st.write("※ 어제 뉴스 기준으로 오늘 지수에 반영됩니다")

# 섹터별 감성 출력
# sector_data: {'반도체': '긍정', '조선': '부정', ...}
# .items(): 키-값 동시에 꺼내기
if sector_data:
    st.write("**📊 섹터별 감성:**")
    for sector, sentiment in sector_data.items():
        if sentiment == '긍정':
            emoji = "🟢"
        elif sentiment == '부정':
            emoji = "🔴"
        else:
            emoji = "🟡"
        st.write(f"{emoji} {sector}: {sentiment}")

# 뉴스별 분석 결과 출력
# news.get('키', 기본값):
# → 키 없을 때 오류 방지]
if news_list:
    st.write("**📋 뉴스별 분석:**")
    for news in news_list:
        if news.get('sentiment') == '긍정':
            emoji = "🟢"
        elif news.get('sentiment') == '부정':
            emoji = "🔴"
        else:
            emoji = "🟡"
        st.write(
            f"{emoji} [{news.get('sector', '')}] "
            f"{news.get('title' , '')}"
        )
        st.write(
            f"  → {news.get('sentiment' , '')} "
            f"({news.get('score', 0)}점): "
            f"{news.get('reason', '')}"
        )
        
#웹화면 구분선
st.markdown("---")
st.subheader("AI 자동 중요 분석" )
st.write("6년치 데이터를 학습해서 AI 가 자동으로 중요한지표를 선택합니다")
st.write("사람이 가중치를 따로 설정하지 않아도 됩니다")


# XGBOOST 지표 중요도 선택
# xgboost란
# 여러개의 결정 트리를핮쳐서
# 어떤지표가 수익률 예측에 중요한가
# 자동으로 분석하는 머닝러신 모델

# xgboost 라이즈러리 가져오기
from xgboost import XGBClassifier
# XGBClassifier: 분류 전용
# 상승(1) / 횡보(0) / 하락(-1) 3가지로 분류
# XGBRegressor(회귀)와 다름
# 회귀: 정확한 숫자 예측
# 분류: 방향 예측 (더 현실적)

# shap: xgboost 결과를 사람이 이해 할수 있게
# 왜 이지표가 중화한지 시각화
import shap

import numpy as np
# numpy: 수학 계산 라이브러리
# np.select: 조건에 따라 값 선택할 때 사용

# 레이블 생성
# 다음날 수익률 기준으로 3가지 분류
# +0.5% 초과 → 1 (상승)
# -0.5% 미만 → -1 (하락)
# 그 사이  → 0 (횡보)
#
# .shift(-1): 하루 앞당기기
# 오늘 지표로 내일 방향 예측하려고
# 내일 수익률을 오늘 행에 붙여넣는 것
next_return = df['Return'].shift(-1)

# 조건 정의
# conditions: 조건 목록
conditions = [
    next_return > 0.005, # +0.5% 초과 = 상승
    next_return < -0.005 
]
choices = [2,0]
# 2 = 상승
# 1 = 횡보
# 0 = 하락

# np.select: 조건에 맞는 값 선택
# default=0: 위 조건 둘 다 아니면 0 (횡보)
df['label'] = np.select(conditions, choices, default=1)

# 학습데이터 준비

# X: 입력데이터(11개 지표)
# y: 정답데이터(다음날 코스피 수익률)
# 이 지표들 로 내일수익률 예측
# dropna(): NAN 있는행제거

# 입력데이터(11개지표)
X=df[indicator_cols_calc].dropna()

# 정답데이터 (다음날 수익률)
#shift(-1): 하루 앞당기기
# 오늘지표로 내일 수익률 예측
y=df['label'].reindex(X.index).dropna()

# x와 y 행수 맞추기
# 둘다 같은날짜 사용
X=X.reindex(y.index)

# XGBoost모델학습

# n_estimators=100 결정 트리100개 사용
# randorm_state=42: 재현성(같은결과값나오게)
# max_depth=3:트이깊이제한 (과지합방지)
model=XGBClassifier(
    n_estimators=100,
    # 결정 트리 100개 사용
    max_depth=3,
    # 트리 깊이 3으로 제한
    # 너무 깊으면 과적합 발생
    random_state=42,
    # 재현성 (항상 같은 결과)
    eval_metric = 'mlogloss',
    # 분류 모델 평가 방식
)
model.fit(X, y)
# fit(): X(지표)로 y(방향) 예측하도록 학습

# 지표별 중요도 추출
# feature_importances_: 각 지표 중요도
# 0~1 사이, 전체 합 = 1
importance = pd.Series(
    model.feature_importances_,
    index = indicator_cols_calc
).sort_values(ascending=False)
# ascending=False: 높은 순서로 정렬

# 중요도 막대 그래프
fig_imp, ax_imp = plt.subplots(figsize =(10,6))
importance.plot(kind='bar' , ax=ax_imp, color='steelblue')
ax_imp.set_title('AI가 판단하는 지표별 중요도')
ax_imp.set_xlabel('지표')
ax_imp.set_ylabel('중요도')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
st.pyplot(fig_imp)

# SHAP 분석 (오늘 데이터)
# 오늘 데이터 추출
today_data = X.iloc[[-1]]
# .iloc[[-1]]: 마지막 행 (오늘)
# [[-1]] 대괄호 두 개: DataFrame 형태 유지

# SHAP 계산
explainer = shap.TreeExplainer(model)
# TreeExplainer: XGBoost 전용 빠른 계산

shap_values = explainer.shap_values(today_data)
# shap_values: 각 지표가 얼마나 기여했는지
 
# 절댓값 처리
# 음수 SHAP = 하락에 기여
# abs()로 절댓값 → 기여도 크기만 봄
shap_today = pd.Series(
    np.abs(shap_values[0]).mean(axis=1),
    index = indicator_cols_calc
).sort_values(ascending=False)

#동적 가중치 계산
# SHAP 절댓값을 가중치로 변환
# 전체 합이 100이 되게 정규화
dynamic_weights = shap_today / shap_today.sum() * 100


# 동적 가중치로 새 공포탐욕지수 계산
# NaN 있는 지표 자동 감지 후 제외
# valid_cols: 마지막 행에 NaN 없는 지표만
valid_cols = [col for col in indicator_cols_calc
               if not pd.isna(df[col].iloc[-1])]

# NaN 없는 지표 가중치만 추출
valid_weights = dynamic_weights[valid_cols]

# 가중치 합이 100되게 재정규화
valid_weights = valid_weights / valid_weights.sum() * 100

# 유효한 지표만으로 오늘 지수 계산
today_dynamic = sum(
    df[col].iloc[-1] * (valid_weights[col] / 100)
    for col in valid_cols
)
# 결과 출력
st.markdown('---')
st.write("오늘 AI 분석 결과")
st.write(f"기존지수 (동일 가중치): {today_score:.1f}점")
st.write(f"AI 동적 가중치 지수: {today_dynamic:.1f}점")

st.write(" 오늘 가장 중요한 지표 top 3:")
for i, (idx, val) in enumerate(shap_today.head(3).items()):
    weight = dynamic_weights[idx]
    st.write(f"{i+1}위: {idx}  →  기여도: {weight:.1f}%")


st.write(" 중요도 낮은 지표:")
for idx, val in shap_today.tail(3).items():
    st.write(f"{idx}: {dynamic_weights[idx]:.1f}%")

# llm시장 분석 코멘트 생성
# ollama의 qwen2.5:14b 모델 사용

# llm에게 보낼 프롬포트 작성
# f-string으로 오늘 점수랑 상태 넣기
prompt = f"""
당신은 한국 주식시장에서 제일 잘나가는 주식 시장 전문가 입니다
모든것을 논리적으로 분석하며 항상 진실만을 말한는 전문가 입니다
오늘 한국 공포탐욕지수는 {today_score:.1f}점입니다.

11개 지표 현황:
-이동평균 괴리율: {df['MA20_gap_norm'].iloc[-1]:.1f}
-거래량: {df['Volume_norm'].iloc[-1]:.1f}
-변동성: {df['Volatility_norm'].iloc[-1]:.1f}
-모멘텀: {df['Momentum_norm'].iloc[-1]:.1f}
-52주 고저비율: {df['HL_norm'].iloc[-1]:.1f}
-원달러 환률: {df['USD_norm'].iloc[-1]:.1f}
-미국 국채금리 {df['BOND_norm'].iloc[-1]:.1f}
-RSI: {df['RSI_norm'].iloc[-1]:.1f}
-SP500: {df['SP500_norm'].iloc[-1]:.1f}
-VIX: {df['VIX_norm'].iloc[-1]:.1f}
-GOLD: {df['GOLD_norm'].iloc[-1]:.1f}

위 데이터 바탕으로 현재시장의 상황을 3줄로 분석요약해주세요
"""

#웹화면에 구분선
st.markdown("---")
st.subheader("AI 시장분석")

#llm 응답 생성
# ollama.chat() : llm에게 메세지 보내고 응답받기
# # model: 사용할 모델 이름
# messages: 대화 내용 (role: user = 사용자 질문)
# try-except: 오류나도 앱 멈추지 않게 하는 것
# try: 일단 실행해봐
# except: 오류나면 이걸 실행해
try:
    # ollama 라이브러리 가져오기
    # ollama 로컬 llm을 파이썬에게 쓸수있게 해주는 라이브러리
    import ollama
    with st.spinner("AI가 분석중..."):
        #st.spinner: 로딩 중 표시
        response = ollama.chat(
            model="qwen2.5:14b",
            messages=[{"role": "user", "content": prompt}]
        )
        # 응답 텍스트 추출해서 웹화면에 표시
        # response['message']['content']: LLM이 생성한 텍스트
        st.write(response['message']['content'])
except:
    st.info("AI 시장분석은 로컬 환경에서만 작동됩니다.")


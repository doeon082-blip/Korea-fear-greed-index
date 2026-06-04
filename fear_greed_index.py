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
delta = df['Close'] .diff()
gain =delta.clip(lower=0)
loss = (-delta). clip(lower=0)
avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()
rs = avg_gain / avg_loss
df['RSI'] = 100 - (100 / (1 + rs))
df['RSI_norm'] = normalize(df['RSI'])
df['USD_KRW'] = df_usd['Close'].reindex(df.index)
df['USD_norm'] = 100 - normalize(df['USD_KRW'])
df['BOND'] = df_bond['Close'].reindex(df.index)
df['BOND_norm'] =100 - normalize(df['BOND'])
# 8개 지표 평균으로 공포탐욕지수 계산
# mean(axis=1): 행 방향으로 평균
# NaN 있어도 나머지로 계산함

indicator_cols_calc = [
    'MA20_gap_norm', 'Volume_norm', 'Volatility_norm',
    'Momentum_norm', 'HL_norm', 'RSI_norm',
    'USD_norm', 'BOND_norm'
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
# 6개 지표가 서로 얼마나 관련있는지 확인


# 8개 지표 컬럼만 모아서 새 데이터프레임 만들기
indicator_cols  =[
    'MA20_gap_norm', # 이동 평균 괴리율
    'Volume_norm', # 거래량
    'Volatility_norm', #변동성
    'Momentum_norm', # 모멘텀
    'HL_norm', #52주 고저비율
    'RSI_norm', # RSI
    'USD_norm', # 원달러 환율
    'BOND_norm' #미국 10년채 국채 금리
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
ax.set_xticklabels(['MA괴리율', '거래량', '변동성', '모멘텀', '고저비율', '환율', '미국국채금리', 'RSI'], rotation=45)
ax.set_yticklabels(['MA괴리율', '거래량', '변동성', '모멘텀', '고저비율', '환율', '미국국채금리', 'RSI'])

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



# statsmodels에서 Granger 검정함수 가져오기 
from statsmodels.tsa.stattools import grangercausalitytests

#결측값(NaN) 제거
# Granger 검증은 NAN이 있으면 오류남
# 기존 Granger 검정 코드에서
# Fear_Greed → Fear_Greed_diff 로 변경

df_granger = df[['Fear_Greed_diff', 'Return']].dropna()
# Fear_Greed_diff: 차분된 공포탐욕지수
# Return: 이미 수익률 (차분된 것)
# Return: KOSPI 일간 수익률 (Close의 pct_change)
# 이 둘의 관계를 검정할 거야

# Granger 검정 실행
# maxlag=5: 최대 5일 전까지 영향을 볼 거야
results = grangercausalitytests(
    df_granger[['Return', 'Fear_Greed_diff']],
    maxlag=20,
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

# llm시장 분석 코멘트 생성
# ollama의 qwen2.5:14b 모델 사용

# llm에게 보낼 프롬포트 작성
# f-string으로 오늘 점수랑 상태 넣기
prompt = f"""
당신은 한국 주식시장에서 제일 잘나가는 주식 시장 전문가 입니다
모든것을 논리적으로 분석하며 항상 진실만을 말한는 전문가 입니다
오늘 한국 공포탐욕지수는 {today_score:.1f}점입니다.

7개 지표 현황:
-이동평균 괴리율: {df['MA20_gap_norm'].iloc[-1]:.1f}
-거래량: {df['Volume_norm'].iloc[-1]:.1f}
-변동성: {df['Volatility_norm'].iloc[-1]:.1f}
-모멘텀: {df['Momentum_norm'].iloc[-1]:.1f}
-52주 고저비율: {df['HL_norm'].iloc[-1]:.1f}
-원달러 환률: {df['USD_norm'].iloc[-1]:.1f}
-미국 국채금리 {df['BOND_norm'].iloc[-1]:.1f}
-RSI: {df['RSI_norm'].iloc[-1]:.1f}

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


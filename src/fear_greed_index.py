import os
import logging
import platform
import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from config import (
    DATA_DIR, LOG_DIR,
    START_DATE, END_DATE,
    MODEL_NAME, WINDOW,
    CACHE_TTL, NEWS_COUNT,
    AFI_SEEDS
)
from indicators import calculate_indicators, make_labels
# 로그 폴더 없으면 자동 생성
os.makedirs(LOG_DIR,exist_ok = True)
# 로그 설정
logging.basicConfig(
    filename = f"{LOG_DIR}app.log",
    level = logging.INFO,
    format = "%(asctime)s %(levelname)s %(message)s",
    encoding = "utf-8"
)
logging.info("앱 실행")

if platform.system() == 'Darwin':
    plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False
@st.cache_data(ttl=CACHE_TTL)
def load_market_data():
    """
    외부 API 데이터 로드 +캐싱
    매번 새로 긁어오면 느리고 API 차단 위협
    CACHE_TTL(1시간) 동안 결과 재사용
    """
    
    df = fdr.DataReader('KS11', START_DATE)
    # 원달러 환율 데이터 불러오기
    # USD/KRW: 달러 대비 원화 환율
    df_usd = fdr.DataReader('USD/KRW', START_DATE)
    # 환율 정규화
    # 환율 오르면 외국인 투자 감소 → 공포 신호
    # 그래서 역방향으로 정규화
    df_bond = fdr.DataReader('^TNX', START_DATE)
    # S&P500 데이터 수집
    # 미국 시장이 한국보다 하루 먼저 움직임
    # 선행 지표로 활용
    df_sp500 = fdr.DataReader('^GSPC', START_DATE)
    # VIX 데이터 수집
    # 미국 공포지수
    # 글로벌 불안감 측정
    df_vix = fdr.DataReader('^VIX',START_DATE)
    # 금 가격
    # 안전자산 선호 지표
    # 불안할수록 금 가격 오름
    df_gold= fdr.DataReader('GC=F',START_DATE)
    return df, df_usd, df_bond, df_sp500, df_vix, df_gold 

df, df_usd, df_bond, df_sp500, df_vix, df_gold = load_market_data()
# 외국인 순매수 CSV 읽기
df_foreign = pd.read_csv(
    f"{DATA_DIR}foreign_data.csv" ,
    index_col = 0 ,
    parse_dates = True
)
# 기관 순매수 CSV 읽기
df_institution= pd.read_csv(
    f"{DATA_DIR}institution_data.csv" ,
    index_col = 0 ,
    parse_dates = True
)
# 펀더멘털 데이터 CSV 읽기
df_fundamental = pd.read_csv (
    f"{DATA_DIR}fundamental_data.csv" ,
    index_col = 0,
    parse_dates = True
)
# 외국인 한도소진율 CSV 읽기
df_foreign_limit = pd.read_csv(
    f"{DATA_DIR}foreign_limit_data.csv",
    index_col = 0 ,
    parse_dates = True
)
# 개인투자자 순매수 데이터 읽기
# 왜 CSV로 읽냐:
# → pykrx가 Python 3.14 호환 안 됨
# → vkospi_update.py 에서 미리 저장한 CSV 읽기
# → pykrx 없이 pandas만으로 가능
df_retail = pd.read_csv(
    f"{DATA_DIR}retail_data.csv",
    index_col = 0 ,
    parse_dates = True
)
# VKOSPI CSV 읽기
# vkospi_update.py 실행하면 생성됨
df_vkospi = pd.read_csv(
    f"{DATA_DIR}vkospi_data.csv",
    index_col =0,   # 첫 번째 열을 인덱스로
    parse_dates= True  # 날짜 형식으로 변환 True가 문자열에서 날짜형식으로변한 False는 문자열 그대로 오류남
)
# indicators.py 의 calculate_indicators 로
# 19개 지표 한 번에 계산
# 두 파일 중복 제거 완료
df, indicator_cols_calc = calculate_indicators(
    df, df_usd, df_bond , df_sp500, df_vix, df_gold,
    df_foreign, df_institution, df_fundamental,
    df_foreign_limit, df_retail, df_vkospi
)
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
# 13개 지표가 서로 얼마나 관련있는지 확인


# 19개 지표 컬럼만 모아서 새 데이터프레임 만들기
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
    'GOLD_norm', # GOLD 안전자산
    'VKOSPI_norm', # VKOSPI 지표 (한국판 VIX)
    'RETAIL_norm', # 개인 투자자 순매수
    'FOREIGN_norm', # 외국인 순매수
    'INSTITUTION_norm', # 기관 투자자 순매수
    'PBR_norm' , # KOSPI 전체 PBR
    'PER_norm' , # KOSPI 전체 PSR
    'DIV_norm' , # 배당수익률
    'FOREIGN_LIMIT_norm' # 외국인 한도 소진율
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
labels = [
    'MA괴리율',
    '거래량',
    '변동성',
    '모멘텀',
    '고저비율',
    'RSI',
    '환율',
    '국채금리',
    'SP500',
    'VIX',
    '금',
    'VKOSPI',
    '개인순매수',
    '외국인순매수',
    '기관순매수',
    'PER',
    'PBR',
    '배당수익률',
    '한도소진율'
]
ax.set_xticks(range(len(labels)))
ax.set_yticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=45)
ax.set_yticklabels(labels)

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
@st.cache_data(ttl=CACHE_TTL)
def run_granger(_df_granger):
    """
    Granger 인과검정 캐싱
    무거운 통계 계산이라 매번 실행하면 느림
    CACHE_TTL(1시간) 동안 결과 재사용
    """
    return grangercausalitytests (
        _df_granger[['Return', 'Fear_Greed_diff']],
        maxlag = 20,
        verbose=False
    )
results = run_granger(df_granger)


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
# 왜 20개냐:
# 10개는 대표성 부족
# 20개면 오늘 시장 전반적 분위기 파악 가능
# 반환값:
# overall_score: 전체 감성 점수 (0~100)
# news_list: 뉴스별 분석 결과 리스트
# sector_data: 섹터별 감성 딕셔너리
# dominant_sector: 오늘 주도 섹터
#pos_count: 긍정 뉴스 개수
# neg_count: 부정 뉴스 개수
import feedparser #feedparser:RSS 피드읽는 라이브러리

# 1시간 캐싱 추가
@st.cache_data(ttl=CACHE_TTL)
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
        for entry in feed.entries[:NEWS_COUNT]:
            news_titles.append(entry.title)

        # 뉴스가 하나도 없으면 기본값 반환
        # RSS 서버 응답은 했는데 뉴스가 없는 경우
        if not news_titles:
            return 50.0,[], {}, '없음', 0, 0 , 0
        # 뉴스 제목 특수문자 제거
        # 큰따옴표, 말줄임표 등이 JSON 파싱 방해
        # [게시판], [인사], [AI픽] 같은 것 제거
        # 실제 경제 뉴스가 아님
        noise_keywords = ['[게시판]','[인사]', '[AI픽]', '[우분투칼럼]' ]

        clean_titles = []
        for title in news_titles:
            # 노이즈 키워드 포함하면 제외
            if any(keyword in title for keyword in noise_keywords):
                continue
            title = title.replace('"', '')
            title = title.replace("'", '')
            title = title.replace('…', '')
            title = title.replace('\\', '')
            title = title.replace('"', '')
            title = title.replace('"', '')
            clean_titles.append(title)

        try:
            # 안쪽 try
            # LLM 분석 실패할 때를 대비
            # ollama 꺼져있거나 모델 없을 수 있음
            
            import ollama
            
            response1 = ollama.chat(
                model=MODEL_NAME,
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
                    "content":"""
                    다음 뉴스를 분석해줘.
                    반드시 아래 형식으로 만 답해.
                    번호, 감성 ,섹터, 점수 ,이유
                    """
                    },

                    {
                        "role":"user",
                        # f-string 안에서 JSON 쓰는 법:
                        # {{ }} = 중괄호 문자 그대로 출력
                        # {변수} = 변수값으로 교체
                        # combined = 뉴스 제목들
                        "content": f"""
                    다음 뉴스를 분석해줘.
                    반드시 아래 형식으로만 답해.
                    번호, 감성, 섹터, 점수, 이유

                    예시:
                    1, 긍정, 반도체,70,삼성전자 투자확대
                    2, 부정,금융,30,금리 인상우려
                    3, 중립, 기타, 50, 정책 변화
                    
                    규칙
                    - 감성: 긍정/부정/중립
                    - 섹터: 반도체/조선/방산/금융/부동산/소비재/기타
                    - 점수: 0~100 숫자만
                    - 이유: 짧게 한 줄
                    - 다른 말 절대 하지 마

뉴스:
{chr(10).join(f"{i+1}. {t}" for i, t in enumerate(clean_titles[:10]))}
"""
                    }
                ]
            )
            response2 = ollama.chat(
                model = MODEL_NAME,
                options ={
                    'num_predict' : 4096
                },
                messages = [
                    {
                        "role": "system", 
                        "content": "너는 뉴스 분석 AI야. 반드시 번호,감성,섹터,점수,이유 형식으로만 답해. 다른 말 하지 마."
                    } ,
                    {
                        "role": "user",
                        "content": f"""
            다음 뉴스 분석 해줘.
            반드시 아래 형식으로만 답해.
            번호,감성,섹터,점수,이유

            예시:
            1, 긍정, 반도체,70,삼성전자 투자확대
            2, 부정,금융,30,금리 인상우려
            3, 중립, 기타, 50, 정책 변화

            규칙:
            -감성: 긍정/부정/중립
            -섹터: 반도체/조선/방산/금융/부동산/소비재/기타
            -점수: 0~100 숫자만
            -이유: 짧게 한 줄
            -다른 말은 절대 하지 마
            
            뉴스:
            {chr(10).join(f"{i+1}.{t}" for i, t in enumerate(clean_titles[10:20]))}
            """ }                                                
                    ]
            )
            # LLM 응답 텍스트 추출
            # .strip(): 앞뒤 공백/줄바꿈 제거
            # 1번 응답 파싱 (CSV 방식)
            # → JSON은 뉴스 제목 특수문자에 취약
            # → 계속 파싱 오류 발생
            # → CSV는 쉼표로만 구분
            # → 특수문자 영향 없음
            # → 한 줄 실패해도 나머지 살아있음
            raw1 = response1['message']['content'].strip() # .strip(): 앞뒤 공백/줄바꿈 제거
            news_list1 = [] # 빈 리스트 준비  #1번 뉴스 1~10개 저장할 곳                      
            for line in raw1.strip().split('\n'):
                 # split('\n'): 줄바꿈 기준으로 한 줄씩 나누기
                # LLM 출력:
                # "1,긍정,반도체,70,투자 확대"
                # "2,부정,금융,30,금리 우려"
                # → 한 줄씩 처리
                if not line.strip():
                    # 빈 줄이면 건너뜀
                    # LLM이 빈 줄 출력하는 경우 있음
                    continue

                parts = line.split(',')
                # 쉼표로 나누기
                # "1,긍정,반도체,70,투자 확대"
                # → ['1', '긍정', '반도체', '70', '투자 확대']

                if len(parts)< 5:
                    # 5개 미만이면 형식 안 맞는 것
                    # → 건너뜀
                    # 예: 빈 줄, 설명 줄 등
                    continue

                try:
                    idx =int(parts[0]) -1
                    # parts[0]: LLM이 준 번호 (1부터 시작)
                    # -1: 파이썬 인덱스는 0부터
                    # 1번 → 인덱스 0
                    # 10번 → 인덱스 9

                    news_list1.append({
                        'title': clean_titles[idx] if idx < len(clean_titles) else '' ,
                        # 번호로 원본 제목 가져오기
                        # 왜 LLM한테 제목 출력 안 시키냐:
                        # → 제목 안 특수문자가 CSV 파싱 방해
                        # → 번호만 받고 원본 제목 매칭하는 게 안전
                        'sentiment' : parts[1].strip(),
                        # parts[1]: 감성 (긍정/부정/중립)
                        # .strip(): 공백 제거
                        'sector' : parts[2].strip(),
                        # parts[2]: 섹터
                        # LLM이 준 섹터 그대로 저장
                        # 예: '반도체', '금융', '기타'
                        # .strip(): 공백 제거
                        'score': int(parts[3].strip()),
                        # parts[3]: 점수
                        # int(): 숫자로 변환
                        'reason': ','.join(parts[4:]).strip()
                        # parts[4]이후:이유
                        # 이유 안에 쉼표 있을수 있어서
                        # parts[4:]로 나머지 전부 합치기
                        # 예: ['투자', '확대'] - '투자,확대'
                    })
                except:
                        # int() 변환 실패등 오류 나면
                        # 그 줄만 건너뜀
                        # 나머지는 계속 처리
                        continue

            # 2번 응답 파싱 (뉴스 11~20개)
            # 1번과 동일한 구조
            # 다른 점:
            # → actual_idx = 10 + idx
            # → clean_titles[10:] 기준으로 인덱스 계산
            # 예: 2번에서 1번 → 실제 인덱스 10
            #     2번에서 3번 → 실제 인덱스 12

            # raw 2 피싱
            raw2 = response2['message']['content'].strip()

            news_list2=[]
            for line in raw2.strip().split('\n'):
                if not line.strip():
                    continue
                parts = line.split(',')
                if len(parts) < 5:
                    continue
                try:
                    idx =int(parts[0]) -1

                    # 2번은 clean_titles[10:] 기준
                    # 실제 인덱스 = 10 + idx
                    actual_idx = 10 + idx

                    news_list2.append({
                        'title': clean_titles[actual_idx] if actual_idx < len(clean_titles) else '',
                        'sentiment':  parts[1].strip(),
                        'sector': parts[2].strip(),
                        'score': int (parts[3].strip()),
                        'reason': ','.join(parts[4:]).strip()
                    })
                except:
                    continue

            # 1번 + 2번 뉴스 합치기
            news_list = news_list1 + news_list2
            # + 연산: 두 리스트 합치기
            # news_list1 = 1~10번 뉴스
            # news_list2 = 11~20번 뉴스
            # news_list = 전체 20개
            
            # 섹터 집계
            # JSON 방식에서는 LLM이 섹터 분석해줬음
            # CSV 방식에서는 뉴스별 sector에서 직접 집계
            # 왜냐:
            # → CSV에 섹터 전체 분석 없음
            # → 뉴스별 sector 모아서 집계하는 게 더 정확
            sector_counts= {}
            # 섹터별 등장 횟수 저장
            # 예: {'반도체': 3, '금융': 2, '기타': 1}
            for news in news_list:
                s = news.get('sector', '')
                if s :
                    # 해당 섹터 카운트 +1
                    # sector_counts.get(s, 0): 없으면 0으로 시작
                    sector_counts[s] = sector_counts.get(s,0) + 1

            # 주도 섹터: 가장 많이 나온 섹터
            # max(): 최대값 찾기
            # key=sector_counts.get: 값 기준으로 최대값
            dominant_sector = max(sector_counts, key= sector_counts.get) if sector_counts else '없음' 

            # sector_data: 섹터별 긍정/부정 분석
            # CSV 방식에서는 뉴스별 sentiment에서 집계

            sector_data={}
            for news in news_list :
                s = news.get('sector','')
                sentiment = news.get('sentiment', '')
                if s and sentiment :
                    if s not in sector_data:
                        sector_data[s] = sentiment

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
            # if news_list 위에 기본값 추가
            overall_score = 50.0
            # 계산식 추가
            if news_list:
                overall_score = sum(
                    news.get('score', 50) for news in news_list
                ) / len(news_list)
            return overall_score, news_list, sector_data, dominant_sector, positive_count, negative_count , neutral_count
        except Exception as e:
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

# indicators.py 의 make_labels 함수로 라벨 3개 생성
# horizon = 예측 기간 (며칠 후를 예측할지)
df = make_labels(df, horizon=1)
# → df['label_1d'] 컬럼 생성
# → 내일 방향 예측용

df = make_labels(df, horizon = 5)
# → df['label_5d'] 컬럼 생성
# → 5일 후 방향 예측용

df = make_labels(df, horizon =20)
# → df['label_20d'] 컬럼 생성
# → 20일 후 방향 예측용


# 롤링 학습데이터 준비
# 바꾸는 이유
# 기존 - 전체 데이터로 학습 
# 문제 - 미래 데이터 참조(Look - ahead bias)
# 예 - 오늘 학습할때 내년 데이터도 봄
# L00k - ahead bias 란
# -미래 과보로 과거를 예측하는것
# -실제 투자에선 불가능한 상황
# -모델 성능이 실제 보다 좋아지는 착시 

# 전체 데이터 준비
X_all=df[indicator_cols_calc].dropna()
y_all_1d=df['label_1d'].reindex(X_all.index).dropna()
y_all_5d = df['label_5d'].reindex(X_all.index).dropna()
y_all_20d = df['label_20d'].reindex(X_all.index).dropna()
X_all_1d=X_all.reindex(y_all_1d.index).iloc[-WINDOW:]
X_all_5d = X_all.reindex(y_all_5d.index).iloc[-WINDOW:]
X_all_20d = X_all.reindex(y_all_20d.index).iloc[-WINDOW:]
#iloc[-252:]:마지막 252개
# 왜 252냐면 : 1년 영업일 기준
y_1d=y_all_1d.iloc[-WINDOW:]
y_5d = y_all_5d.iloc[-WINDOW:]
y_20d = y_all_20d.iloc[-WINDOW:]
# 오늘 데이터는 전터에서 가져오기
# 왜냐면: 오늘 데이터로 예기해야 하니깐
X_today = X_all.iloc[[-1]]
# .iloc[[-1]] :마지막 행(오늘)
# [[-1]] 대괄호 두개 : DataFrame 형태 유지

# AFI (Aggregated Feature Importance) + 양상블
# 양상블 이란
# - 여러 모델 동시 학습
# - 각각 SHAP 계산
# - 평균내서 최종 결정
# - 하나만 쓸때보다 안정적
# 3가지 모델
# XGBoost: 그래디언트 부스팅
# LightGBM: XGBoost보다 빠른 버전
# RandomForest: 배깅 방식(다른계열)

from lightgbm import LGBMClassifier
# LightGBM: 마이크로 소프트가 만든 모델
# → XGBoost랑 같은 그래디언트 부스팅 계열
# → 더 빠르고 메모리 효율
from sklearn.ensemble import RandomForestClassifier
# RandomForest: 결정 트리 여러 개 합치기
# → 배깅(Bagging) 방식
# → XGBoost/LightGBM과 다른 계열
# → 다양한 관점에서 데이터 봄
# sklearn: 파이썬 대표 머신러닝 라이브러리

# @st.cache_data: 캐싱 (속도 해결)

# 문제:
# → 3모델 × 100번 = 300번 실행
# → 새로고침할 때마다 300번 반복
# → 매우 느림

# 해결:
# → @st.cache_data(ttl=CACHE_TTL)
# → 처음 한 번만 계산
# → 1시간(CACHE_TTL초) 동안 결과 저장
# → 새로고침해도 저장된 결과 사용
# → 다음날 되면 자동으로 새로 계산

# ttl = Time To Live (살아있는 시간)
# ttl=CACHE_TTL = CACHE_TTL초 = 1시간
@st.cache_data(ttl=CACHE_TTL)
def run_ensemble_afi(_X, _y, _X_today, _cols, horizon):
    # 함수로 만든 이유:
    # → @st.cache_data는 함수에만 붙일 수 있음
    # → 함수로 감싸야 캐싱 가능
    # horizon 은 캐시 구분용
    # 1, 5, 20 값이 다르면 각각 다른 캐시로 저장됨
    # 함수 내부에서 실제로 쓰지 않음 → 비활성화 경고 정상
    

    # 파라미터 앞에 _ 붙인 이유:
    # → st.cache_data는 입력값을 해시(hash)해서
    # → 같은 입력이면 저장된 결과 반환
    # → DataFrame은 해시 못함 → 오류
    # → _ 붙이면 해시 건너뜀 → 오류 방지

    # _X: 학습 데이터 (252일)
    # _y: 레이블 (상승/횡보/하락)
    # _X_today: 오늘 데이터 (예측용)
    # _cols: 지표 이름 목록 (19개)

    shap_list=[]
    # 100번 SHAP 결과 저장할 빈 리스트
    # 나중에 평균 낼 것
    for seed in range(AFI_SEEDS):
    # seed 0부터 99까지 100번 반복
    # 매번 다른 random_state 사용
    # → 같은 데이터도 조금씩 다르게 학습
    # → 100번 평균 → 안정적인 가중치

        # 1. XGBoost 학습 + SHAP
        xgb_model = XGBClassifier(
            n_estimators = 100,
            # 결정 트리 100개 사용
            # 많을수록 정확하지만 느림
            max_depth = 3,
            # 트리 깊이 3으로 제한
            # 깊을수록 과적합 위험
            # 3이 표준적인 값
            learning_rate = 0.1 ,
            # 학습률: 얼마나 빠르게 학습하냐
            # 너무 크면 과적합
            # 너무 작으면 학습 안 됨
            # 0.1이 표준적인 값
            eval_metric = 'mlogloss',
            # 평가 방식: 다중 클래스 로그 손실
            # mlogloss = multiclass log loss
            # 3개 클래스 분류에 맞는 방식
            random_state = seed #매번 다를 시도
            # seed가 다르면 트리 구성이 조금씩 달라짐
        )
        xgb_model.fit(_X,_y) 
        # _X: 252일 학습 데이터
        # _y: 상승/횡보/하락 레이블
        # 롤링 윈도우 적용 → look-ahead bias 없음

        xgb_shap = shap.TreeExplainer(xgb_model).shap_values(_X_today)
        # TreeExplainer: 트리 모델 전용 SHAP 계산기
        # .shap_values(_X_today): 오늘 데이터 기여도 계산
        # 결과: 3개 클래스 × 19개 지표 = 57개

        xgb_abs = np.abs(
            np.array(xgb_shap) 
        # np.array: 리스트 → 배열로 변환
        # np.abs: 절댓값 (음수 → 양수)
        # 왜 절댓값이냐:
        # → SHAP 음수 = 하락에 기여
        # → SHAP 양수 = 상승에 기여
        # → 방향 상관없이 크기만 봄
        ).reshape(-1,len(_cols)).mean(axis=0)
        # reshape(-1, 19):
        # → 57개를 (3, 19) 형태로 변환
        # → -1: 자동으로 행 개수 계산
        # → 57 / 19 = 3행
        # mean(axis=0):
        # → 3개 클래스 방향으로 평균
        # → (3, 19) → (19,)
        # → 지표별 평균 중요도

        # 2. LightGBM 학습 + SHAP

        lgb_model = LGBMClassifier(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.1,
            class_weight= 'balanced' , 
            # class_weight='balanced':
            # → 클래스 불균형 자동 처리
            # 문제:
            # → 횡보 > 상승 > 하락 순으로 많음
            # → 모델이 항상 "횡보"로만 예측 가능
            # 해결:
            # → 적은 클래스에 가중치 더 줌
            # → 상승/하락도 골고루 학습
            # → 'balanced': 자동으로 계산해줌
            random_state=seed,
            verbose=-1
        )
        lgb_model.fit(_X, _y)

        lgb_shap = shap.TreeExplainer(lgb_model).shap_values(_X_today)

        lgb_abs = np.abs(
            np.array(lgb_shap)
        ).reshape(-1, len(_cols)).mean(axis=0)
        # XGBoost랑 동일한 방식

        # 3. RandomForest 학습 + SHAP

        rf_model = RandomForestClassifier(
            n_estimators = 100,
            max_depth = 3,
            class_weight = 'balanced' ,
            # LightGBM이랑 같은 이유
            random_state = seed
        )
        rf_model.fit(_X, _y)

        rf_shap = shap.TreeExplainer(rf_model).shap_values(_X_today)

        # RandomForest SHAP shape 방어 처리

        # 왜 따로 처리하냐:
        # → XGBoost, LightGBM: (3, 1, 19) 형태
        # → RandomForest: (1, 19, 3) 형태일 수 있음
        # → reshape(-1, 19) 하면 오류 가능
        # → ndim으로 차원 확인 후 처리
        rf_arr = np.array(rf_shap)
        # np.array: 배열로 변환
        # .ndim: 차원 수 확인
        # ndim=3: 3차원 (우리가 원하는 것)
        # ndim=2: 2차원 (다른 형태)

        if rf_arr.ndim == 3:
            # 3차원이면:
            # → (3, 1, 19) 또는 (1, 19, 3)
            # → reshape으로 통일
            rf_abs = np.abs(rf_arr).reshape(-1,len(_cols)).mean(axis=0)
        else:
            # 2차원이면:
            # → (1, 19) 형태
            # → reshape으로 통일
            rf_abs = np.abs(rf_arr).reshape(-1 ,len(_cols)).mean(axis=0)

        # 4. 세 모델 평균
        # 왜 단순 평균이냐:
        # → 세 모델 각각 다른 방식으로 계산
        # → 단순 평균이 제일 안정적
        # → 동적 가중치는 과적합 위험
        ensemble_abs = (xgb_abs + lgb_abs + rf_abs) / 3
        # / 3: 3개 모델이니까 3으로 나누기

        shap_list.append(ensemble_abs)
        # 이번 seed 결과를 리스트에 추가

    return np.mean(shap_list, axis=0)
    # 100번 평균
    # axis=0: 같은 지표끼리 평균
    # → 최종 19개 안정적인 가중치 반환

# 함수 실행

shap_avg_1d = run_ensemble_afi(X_all_1d, y_1d, X_today, indicator_cols_calc, horizon=1)
shap_avg_5d = run_ensemble_afi(X_all_5d, y_5d, X_today, indicator_cols_calc, horizon=5)
shap_avg_20d = run_ensemble_afi(X_all_20d, y_20d, X_today, indicator_cols_calc, horizon=20)
# 처음 실행: 300번 계산 (느림)
# 이후 실행: 캐시에서 바로 반환 (빠름)

# 1일 후 SHAP 중요도
shap_today_1d = pd.Series(
    shap_avg_1d,
    index=indicator_cols_calc
).sort_values(ascending=False)
# 5일 후 SHAP 중요도
shap_today_5d = pd.Series(
    shap_avg_5d,
    index=indicator_cols_calc
).sort_values(ascending=False)
# 20일 후 SHAP 중요도
shap_today_20d = pd.Series(
    shap_avg_20d,
    index=indicator_cols_calc
).sort_values(ascending=False)
# 높은 순서로 정렬
# ascending=False: 내림차순 (높은 것 먼저)



#동적 가중치 계산
# SHAP 절댓값을 가중치로 변환
# 전체 합이 100이 되게 정규화
dynamic_weights_1d = shap_today_1d / shap_today_1d.sum() * 100
dynamic_weights_5d = shap_today_5d / shap_today_5d.sum() * 100
dynamic_weights_20d = shap_today_20d / shap_today_20d.sum() * 100


# 동적 가중치로 새 공포탐욕지수 계산
# NaN 있는 지표 자동 감지 후 제외
# valid_cols: 마지막 행에 NaN 없는 지표만
valid_cols = [col for col in indicator_cols_calc
               if not pd.isna(df[col].iloc[-1])]

# NaN 없는 지표 가중치만 추출
valid_weights_1d = dynamic_weights_1d[valid_cols]
# 가중치 합이 100되게 재정규화
valid_weights_1d = valid_weights_1d / valid_weights_1d.sum() * 100
valid_weights_5d = dynamic_weights_5d[valid_cols]
valid_weights_5d = valid_weights_5d / valid_weights_5d.sum() * 100
valid_weights_20d = dynamic_weights_20d[valid_cols]
valid_weights_20d = valid_weights_20d / valid_weights_20d.sum() * 100
# 유효한 지표만으로 오늘 지수 계산
# valid_weights = NaN 없는 지표만 가중치 적용
# 각 horizon 별로 따로 계산

# 1일 후 동적 가중치 지수
today_dynamic_1d = sum(
    df[col].iloc[-1] * (valid_weights_1d[col] / 100)
    for col in valid_cols
)

# 5일 후 동적 가중치 지수
today_dynamic_5d = sum(
    df[col].iloc[-1] * (valid_weights_5d[col] / 100)
    for col in valid_cols
)

# 20일 후 동적 가중치 지수
today_dynamic_20d = sum(
    df[col].iloc[-1] * (valid_weights_20d[col] / 100)
    for col in valid_cols
)

# 결과 출력
st.markdown('---')
st.write("오늘 AI 분석 결과")
st.write(f"기존지수 (동일 가중치): {today_score:.1f}점")
# 3가지 horizon 예측 결과 표시
st.write(f"1일 후 예측 지수: {today_dynamic_1d:.1f}점")
st.write(f"5일 후 예측 지수: {today_dynamic_5d:.1f}점")
st.write(f"20일 후 예측 지수: {today_dynamic_20d:.1f}점")

# 1일 기준 중요 지표 top 5
st.write("오늘 가장 중요한 지표 top 5 (1일 기준):")
for i, (idx, val) in enumerate(shap_today_1d.head(5).items()):
    weight = dynamic_weights_1d[idx]
    st.write(f"{i+1}위: {idx} → 기여도: {weight:.1f}%")

# 1일 기준 중요도 낮은 지표
st.write("중요도 낮은 지표 (1일 기준):")
for idx, val in shap_today_1d.tail(5).items():
    st.write(f"{idx}: {dynamic_weights_1d[idx]:.1f}%")
    
# llm시장 분석 코멘트 생성
# ollama의 qwen2.5:14b 모델 사용

# llm에게 보낼 프롬포트 작성
# f-string으로 오늘 점수랑 상태 넣기
prompt = f"""
당신은 한국 주식시장에서 제일 잘나가는 주식 시장 전문가 입니다
모든것을 논리적으로 분석하며 항상 진실만을 말한는 전문가 입니다
오늘 한국 공포탐욕지수는 {today_score:.1f}점입니다.

19개 지표 현황:
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
-VKOSPI: {df['VKOSPI_norm'].iloc[-1]:.1f}
-개인투자자 순매수: {df['RETAIL_norm'].iloc[-1]:.1f}
-외국인 순매수: {df['FOREIGN_norm'].iloc[-1]:.1f}
-기관 순매수: {df['INSTITUTION_norm'].iloc[-1]:.1f}
-PER: {df['PER_norm'].iloc[-1]:.1f}
-PBR: {df['PBR_norm'].iloc[-1]:.1f}
-배당수익률: {df['DIV_norm'].iloc[-1]:.1f}
-외국인 한도소진율: {df['FOREIGN_LIMIT_norm'].iloc[-1]:.1f}

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
            model= MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )
        # 응답 텍스트 추출해서 웹화면에 표시
        # response['message']['content']: LLM이 생성한 텍스트
        st.write(response['message']['content'])
except:
    st.info("AI 시장분석은 로컬 환경에서만 작동됩니다.")

# Walk-forward 검증 결과 표시
st.markdown("---")
st.subheader("📈 Walk-forward 검증 결과")
st.write("모델 과거 데이터가 얼마나 정확했는지 검정")

try:
    df_wf = pd.read_csv(f"{DATA_DIR}walk_forward_results.csv")
    avg_acc = df_wf['전체정확도'].mean()
    st.write(f"평균정확도: {avg_acc:.1f}%")
    st.write(F"검증 구간 수 : {len(df_wf)}개")
    st.dataframe(df_wf)
except:
    st.info("walk_forward.py 를 먼저 실행해 주세요")

# 외부 테스트 결과 표시
# walk_forward.py 에서 저장되는데 화면에 안 보이던 것
st.markdown("---")
st.write("외부 데스트 결과 (학습에서 전혀 안 쓴 데이터)")
try:
    df_final = pd.read_csv(f"{DATA_DIR}walk_forward_final_test.csv")
    st.write(f"외부 테스트 정확도: {df_final['전체정확도'].iloc[0]:.1f}%")
    st.write(f"테스트 기간 : {df_final['테스트시작'].iloc[0]} - {df_final['테스트종료'].iloc[0]}")
    st.write(f"테스트 데이터: {df_final['테스트데이터수'].iloc[0]}일")
    st.dataframe(df_final)
except:
    st.info("walk_forward.py 를 먼저 실행해주세요")
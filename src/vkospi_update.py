# vkospi_update.py
# 역할:
# → VKOSPI 데이터를 KRX에서 가져와서
# → CSV 파일로 저장하는 스크립트
# 왜 따로 만들었냐:
# → pykrx가 Python 3.14 호환 안 됨
# → fgi (3.11) 환경에서만 실행 가능
# → 메인 코드(fear_greed_index.py)는 3.14
# → 그래서 따로 분리
# 실행 방법:
# → conda activate fgi
# → python vkospi_update.py
# → vkospi_data.csv 자동 생성
from pykrx import stock
# pykrx: 한국 거래소 데이터 수집 라이브러리
# fgi 환경에만 설치됨
import pandas as pd
# pandas: 데이터 처리 라이브러리
import logging
import os
# 로그 폴더 없으면 자동 생성
os.makedirs("logs", exist_ok=True)

# 로그 설정
logging.basicConfig(
    filename="logs/update.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8"
)
logging.info("=" * 40)
logging.info("vkospi_update.py 시작")

# VKOSPI 데이터 수집
# "1005" = VKOSPI 티커 코드
# VKOSPI: 한국판 VIX
# → KOSPI200 옵션 기반 변동성 지수
# → 높을수록 시장 불안 = 공포 신호
df_vkospi = stock.get_index_ohlcv(
    "20200101", # 시작일
    "20261231", # 종료일
    "1005" # vkospi 코드
)
# 개인투자자 순매수 데이터 수집
# 왜 필요하냐:
# → 한국 시장은 개인투자자 비중 높음
# → 개인이 많이 사면 탐욕 신호
# → 개인이 많이 팔면 공포 신호
# → 동학개미 효과 반영
# get_market_trading_value_by_date():
# → 투자자별 매매 현황 가져오는 함수
# → 개인/기관/외국인 구분해서 보여줌
df_retail = stock.get_market_trading_value_by_date(
    "20200102", # 시작일
                # 20200101은 공휴일이라 2일부터 시작
    "20261231", # 종료일
    "KOSPI", # KOSPI 전체 시장 기준
    detail = True   # 투자자별 상세 데이터 가져오기
                    # True: 개인/기관/외국인 구분
                    # False: 합계만
)
df_retail.to_csv("retail_data.csv")
# index=True 기본값
# → 날짜 인덱스도 같이 저장
print("개인 투자자 데이터 저장 완료")
logging.info(f"retail_data.csv 저장완료: {len(df_retail)}개")
print(f"데이터 기간:{df_retail.index[0]} ~ {df_retail.index[-1]}")
print(f"총{len(df_retail)}개 데이터")
# 외국인 순매수 데이터 저장=
df_foreign = df_retail[['외국인']].copy()
# .copy(): 원본 데이터 건드리지 않고 복사
df_foreign.to_csv("foreign_data.csv")
print("외국인 데이터 저장 완료")
logging.info(f"foreign_data.csv 저장완료: {len(df_foreign)}개")
# 기관 순매수 데이터 저장 (7개 합산)
# 기관 구성:
# → 금융투자: 증권사 자기매매
# → 보험: 장기 안정 투자
# → 투신: 펀드
# → 사모: 헤지펀드
# → 은행: 단기 유동성
# → 기타금융: 기타
# → 연기금: 국민연금 등 초장기
df_institution = df_retail[
    ['금융투자', '보험', '투신', '사모',
     '은행', '기타금융', '연기금']
].sum(axis=1)
# .sum(axis=1): 행 방향으로 합산
# → 7개 기관 순매수 전부 더하기
df_institution = df_institution.to_frame(name='기관')
# .to_frame(): 시리즈 → 데이터프레임 변환
# name='기관': 컬럼 이름 설정
df_institution.to_csv("institution_data.csv")
print("기관 데이터 저장 완료")
logging.info(f"institution_data.csv 저장완료: {len(df_institution)}개")
# KOSPI 펀더멘털 데이터 저장
# # PER: 주가수익비율
# → 주가 / 주당순이익
# → 높으면 고평가 (탐욕)
# → 낮으면 저평가 (공포)
# PBR: 주가순자산비율
# → 주가 / 주당순자산
# → 높으면 고평가
# → 낮으면 저평가
# 배당수익률:
# → 배당금 / 주가
# → 높으면 안전자산 선호 (공포)
# → 낮으면 성장주 선호 (탐욕)
# 왜 3개 하나의 CSV냐:
# → 같은 함수에서 가져옴
# → 추가 API 호출 없음
# → 컬럼 이름으로 구분
# → 섞이지 않음
# "1028" = KOSPI 전체 지수 코드
# → 개별 종목 아님
# → 시장 전체 밸류에이션
# → 방향성은 XGBoost + SHAP이 판단
df_fundamental = stock.get_index_fundamental_by_date(
    "20200102" , #시작일
    "20261231" , # 종료일
    "1028" #KOSPI 코드
)
# 필요한 3개 컬럼만 추출
# .copy(): 원본 데이터 건드리지 않고 복사
df_fundamental = df_fundamental [['PBR' , 'PER' , '배당수익률']].copy()
# CSV 저장
# 하나의 파일에 3개 컬럼 저장
# 읽을 때 컬럼 이름으로 각각 꺼냄
df_fundamental.to_csv("fundamental_data.csv")
print("펀더멘털 데이터 저장 완료")
logging.info(f"fundamental_data.csv 저장완료: {len(df_fundamental)}개")
print(f"데이터 기간 : {df_fundamental.index[0]} ~ {df_fundamental.index[-1]}")
print(f"총{len(df_fundamental)}개 데이터")
# 외국인 한도소진율 (섹터별 대표 종목 평균)
# 왜 여러 종목 평균이냐:
# → 삼성전자 하나만 쓰면 반도체 편향
# → 섹터별 대표 종목 평균 = 시장 전체 대표
# → 더 정확한 외국인 수급 신호
sector_tickers = {
    '반도체1': '005930', # 삼성전자
    '반도체2' : '000660' , # SK 하이닉스
    '가전' : '066570' , # LG전자
    'IT' : '035420' , # NAVER
    '자동차' : '005380' , # 현대차
    '바이오' : '207940' , # 삼성 바이오 로직스
    '배터리' : '373220', # LG 에너지 솔루션
    '금융' : '105560' , # KB금융
    '조선' : '009540' , # HD 현대 조선 해양
    '화학' : '051910' , # LG 화학
    '통신': '017670',   # SK텔레콤
    '소비재': '000100', # 유한양행
    '방산': '012450',  # 한화에어로스페이스
    '철강': '005490',  # POSCO홀딩스
    '항공': '003490',  # 대한항공
    '게임': '259960',  # 크래프톤
    '식품': '097950',  # CJ제일제당
    '건설': '000720',  # 현대건설
}

dfs = []
for sector, ticker in sector_tickers.items():
    # 섹터별 한도소진율 가져오기
    df_temp = stock.get_exhaustion_rates_of_foreign_investment_by_date(
        "20200102" ,
        "20261231" ,
        ticker
    )
    # 소진율 컬럼만 추출
    dfs.append(df_temp['한도소진률'])
    print(f"{sector}완료")
# 18개 섹터 평균
# → 섹터 편향 없앰
# → 시장 전체 외국인 수급 대표값
df_foreign_limit = pd.concat(dfs, axis = 1).mean(axis = 1).to_frame(name='한도소진률')
df_foreign_limit.to_csv("foreign_limit_data.csv")
print("외국인 한도 소진률 저장 완료")
logging.info(f"foreign_limit_data.csv 저장완료: {len(df_foreign_limit)}개")
print(f"데이터 기간: {df_foreign_limit.index[0]} ~ {df_foreign_limit.index[-1]}")
print(f"총{len(df_foreign_limit)}개 데이터")
# CSV로 저장
# 왜 CSV냐:
# → 메인 코드(3.14)에서 읽을 수 있음
# → pykrx 없이 pandas만으로 읽기 가능
# → 매일 한 번만 업데이트하면 됨
df_vkospi.to_csv("vkospi_data.csv")
# index=True 기본값
# → 날짜 인덱스도 같이 저장
print("vkospi 데이터 저장 완료")
logging.info(f"vkospi_data.csv 저장완료: {len(df_vkospi)}개")
print(f"데이터 기간: {df_vkospi.index[0]} ~ {df_vkospi.index[-1]}")
print(f"총 {len(df_vkospi)}개 데이터 ")
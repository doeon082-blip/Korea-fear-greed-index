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
print(f"데이터 기간:{df_retail.index[0]} ~ {df_retail.index[-1]}")
print(f"총{len(df_retail)}개 데이터")
# CSV로 저장
# 왜 CSV냐:
# → 메인 코드(3.14)에서 읽을 수 있음
# → pykrx 없이 pandas만으로 읽기 가능
# → 매일 한 번만 업데이트하면 됨
df_vkospi.to_csv("vkospi_data.csv")
# index=True 기본값
# → 날짜 인덱스도 같이 저장
print("vkospi 데이터 저장 완료")
print(f"데이터 기간: {df_vkospi.index[0]} ~ {df_vkospi.index[-1]}")
print(f"총 {len(df_vkospi)}개 데이터 ")
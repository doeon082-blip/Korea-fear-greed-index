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
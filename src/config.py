# 경로 설정
DATA_DIR = "data/"
LOG_DIR = "logs/"

# 데이터 수집 기간
START_DATE = "20200101"
END_DATE = "20261231"
START_DATE_TRADING = "20200102"  

# 모델 설정
MODEL_NAME = "qwen2.5:14b"

# 롤링 윈도우 (1거래년)
WINDOW = 252

# 라벨링 기준 (수익률)
LABEL_UP = 0.005    # +0.5% 초과 = 상승
LABEL_DOWN = -0.005 # -0.5% 미만 = 하락

# 앙상블 반복 횟수
AFI_SEEDS = 100

# 뉴스 수집 개수
NEWS_COUNT = 20

# 캐시 시간 (초)
CACHE_TTL = 3600

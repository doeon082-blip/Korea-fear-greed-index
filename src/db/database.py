"""
database.py - Korea FGI Phase 3 DB 구축
SQLite 테이블 10개 생성 및 연결 관리
 
역할:
    - DB 파일 생성
    - 테이블 10개 생성
    - 인덱스 생성 (검색 속도)
    - 버전 정보 삽입
 
실행:
    python3 src/db/database.py
→ data/fgi_database.db 생성됨
→ 이미 있으면 건너뜀 (데이터 안 지워짐)
"""

import sqlite3
import os
import logging
from datetime import datetime, timezone, timedelta
from config import DATA_DIR, LOG_DIR

# 한국 시간 설정 (KST = UTC + 9시간)
# 서버 배포해도 항상 한국 시간으로 저장됨
KST= timezone(timedelta(hours=9))

def get_kst_now():
    """
    현재 한국 시간 반환
    형식: "2026-06-26 16:00:00"
    """
    return datetime.now(KST).strftime('%Y-%m-%d %H:$M:%S')

# 로그 설정

# logs/ 폴더 없으면 자동 생성
os.makedirs(LOG_DIR, exist_ok=True)

# 이 파일 전용 로거
# → 다른 파일 로거랑 독립적
# → fear_greed_index.py 로거랑 충돌 없음
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 이미 핸들러 있으면 추가 안 함 (중복 방지)
if not logger.handlers:
    handler = logging.FileHandler(
        f"{LOG_DIR}db.log",
        encoding = "utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    logger.addHandler(handler)
    
# DB 파일 경로

# os.path.join: 슬래시 자동 처리
# DATA_DIR = "data" 또는 "data/" 둘 다 됨
DB_PATH = os.path.join(DATA_DIR, "fgi_database.db")

def get_connection():
    """
    SQLite DB 연결 반환
 
    반드시 contextlib.closing() 과 함께 사용:
    
    with contextlib.closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fgi_daily")
        conn.commit()
    # 여기서 진짜로 conn.close() 실행됨
 
    왜 contextlib.closing() 이 필요하냐:
    → with conn: 만 쓰면 commit/rollback 만 됨
    → conn.close() 는 안 됨 (Python sqlite3 특성)
    → contextlib.closing() 써야 진짜로 닫힘
    → 자동화 환경에서 잠김 문제 완전 방지
    """
    # DB 폴더 없으면 자동 생성
    os.makedirs(DATA_DIR, exist_ok=True)
    
    conn =  sqlite3.connect(DB_PATH)
    
    # 외래키 활성화
    # 테이블 간 관계 무결성 보장
    conn.execute("PRAGMA foreign_keys = ON")
    
    # WAL 모드 설정
    # Write-Ahead Logging
    # → 여러 곳에서 동시에 읽기 가능
    # → 자동화 파이프라인에서 충돌 방지
    conn.row_factory = sqlite3.Row
    
    return conn

def create_tables():
    """
    테이블 10개 + 인덱스 생성
 
    IF NOT EXISTS:
    → 이미 테이블 있으면 건너뜀
    → 기존 데이터 안 지워짐
    → 여러 번 실행해도 안전
 
    contextlib.closing() 사용:
    → 함수 끝나면 진짜로 conn.close()
    → 오류 나도 자동으로 닫힘
    → 자동화 파이프라인 잠김 문제 완전 방지
    """
    try:
        with contextlib.closing(get_connection()) as conn:
            cursor = conn.cursor()
            
            # 테이블 1: fgi_daily (핵심)
            # 날짜별 FGI 점수 + 예측 + 코멘트
            # 하루에 1개 저장
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fgi_daily (
                    date TEXT PRIMARY KEY,
                    fgi_score REAL,
                    fgi_dynamic REAL,
                    fgi_state TEXT,
                    pred_1d REAL,
                    pred_5d REAL,
                    pred_20d REAL,
                    kospi_close REAL,
                    kospi_return REAL,
                    market_regime TEXT,
                    news_score REAL,
                    news_dominant_sector TEXT,
                    top_indicator TEXT,
                    top_weight REAL,
                    shap_weights TEXT,
                    ai_comment TEXT,
                    walk_forward_accuracy REAL,
                    data_available_from TEXT,
                    is_backfilled INTEGER DEFAULT 0,
                    version TEXT DEFAULT 'v1.0',
                    created_at TEXT DEFAULT (datetime('now', 'l
ocaltime'))
                )
            """)
            
            # 테이블 2: raw_indicators (원본 - 절대 삭제 금지)
            # 정규화 전 원본 수치
            # 버전 바뀌어도 여기서 재계산 가능
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS raw_indicators (
                    date TEXT PRIMARY KEY,
                    kospi_close REAL,
                    kospi_volume REAL,
                    usd_krw REAL,
                    bond_rate REAL,
                    sp500_close REAL,
                    gold_close REAL,
                    vkospi_close REAL,
                    retail_net REAL,
                    foreign_net REAL,
                    institution_net REAL,
                    per REAL,
                    pbr REAL,
                    div_yield REAL,
                    foerign_limit_rate REAL,
                    pcr REAL,
                    breadth REAL,
                    margin_balance REAL,
                    version TEXT DEFAULT 'v1.0',
                    created_at TEXT DEFAULT (datetime('now', 'l
ocaltime'))     
                )
            """)
            
            # 테이블 3: fgi_indicators (정규화 지표)
            # 0~100 으로 정규화된 지표값
            # 정규화 방식 바뀌면 version 올리기
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fgi_indicators (
                    date TEXT PRIMARY KEY,
                    ma20_gap_norm REAL,
                    volume_norm REAL,
                    volatility_norm REAL,
                    momentum_norm REAL,
                    hl_norm REAL,
                    rsi_norm REAL,
                    usd_norm REAL,
                    bond_norm REAL,
                    sp500_norm REAL,
                    vix_norm REAL,
                    gold_norm REAL,
                    vkospi_norm REAL,
                    retail_norm REAL,
                    foreign_norm REAL,
                    institution_norm REAL,
                    per_norm REAL,
                    pbr_norm REAL,
                    div_norm REAL,
                    foreign_limit_norm REAL,
                    pcr_norm REAL,
                    breadth_norm REAL,
                    margin_balance_norm REAL,
                    normalization_method TEXT DEFAULT 'rolling_252',
                    version TEXT DEFAULT 'v1.0',
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)
            # 테이블 4: news_classification (뉴스)
            # 하루에 여러 개 (20개 뉴스)
            # id: 자동 증가 (AUTOINCREMENT)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS news_classification(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    title TEXT,
                    sector TEXT,
                    sentiment TEXT,
                    score REAL,
                    reason TEXT,
                    score TEXT DEFAULT '연합뉴스',
                    version TEXT DEFAULT 'v1.0',
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)
            
            # 테이블 5: market_events (주요 이벤트)
            # 수동 입력
            # 코로나, 금리인상, 전쟁 등
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    event_name TEXT NOT NULL,
                    event_type TEXT,
                    impact TEXT,
                    impact_score REAL,
                    fgi_before REAL,
                    fgi_after REAL,
                    kospi_change REAL,
                    description TEXT,
                    source TEXT,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)
            
            # 테이블 6: qa_pairs (AI 학습 데이터 - 핵심)
            # Solar API 로 하루 5개 자동 생성
            # Fine-tuning 용 질문-답변 쌍
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS qa_pairs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    question_type TEXT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    scenario TEXT,
                    quality_score REAL,
                    quality_tier TEXT,
                    fgi_score REAL,
                    market_regime TEXT,
                    horizon TEXT,
                    source TEXT DEFAULT 'auto',
                    prompt_version TEXT DEFAULT 'v1.0',
                    model_version TEXT DEFAULT 'solar-pro',
                    is_verified INTEGER DEFAULT 0,
                    version TEXT DEFAULT 'v1.0',
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)
            # 테이블 7: ai_comments (AI 코멘트)
            # Solar API 생성 분석 코멘트
            # 모델/프롬프트 버전별 관리
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    comment_type TEXT,
                    model_version TEXT DEFAULT 'solar-pro,
                    prompt_version TEXT DEFAULT 'v1.0',
                    quality_score REAL,
                    version TEXT DEFAULT 'v1.0',
                    created_at TEXT
                )
            """)
            
            # 테이블 8: data_quality (품질 관리)
            # Fine-tuning 할 때 필터링 기준
            # A(80~100) B(50~79) C(0~49)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data_quality (
                    date TEXT PRIMARY KEY,
                    indicator_quality REAL,
                    news_quality REAL,
                    ai_quality REAL,
                    quality_titer TEXT,
                    missing_indicators TEXT,
                    is_valid INTEGER DEFAULT 1,
                    version TEXT DEFAULT 'v1.0',
                    created_at TEXT
                )
            """)    
            # 테이블 9: backtesting (Phase 5에서 사용)
            # FGI 기반 투자 전략 백테스팅 결과
            # Sharpe Ratio, MDD 등
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS backtesting(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy TEXT NOT NULL,
                    start_date TEXT,
                    end_date TEXT,
                    total_return REAL,
                    sharpe_ratio REAL,
                    sortino_ratio REAL,
                    mdd REAL,
                    win_rate REAL,
                    benchmark_return REAL,
                    alpha REAL,
                    version TEXT DEFAULT 'v1.0',
                    created_at TEXT
                )
            """)
            # 테이블 10: schema_versions (버전 관리)
            # 어떤 버전으로 데이터 만들었는지 기록
            # 버전 올릴 때마다 여기에 추가
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_versions (
                    version TEXT PRIMARY KEY.
                    description TEXT,
                    changes TEXT,
                    applied_at TEXT
                )
            """)
            # 인덱스 생성 (검색 속도 향상)
            # date 컬럼으로 자주 검색하기 때문에
            # 인덱스 없으면 전체 스캔 → 느림
            # 인덱스 있으면 바로 찾음 → 빠름
            indeses = [
                "CREATE INDEX IF NOT EXISTS idx_fgi_daily_date ON fgi_daily(date)" ,
                "CREATE INDEX IF NOT EXISTS idx_fgi_daily_state ON fgi_daily(fgi_state)",
                "CREATE INDEX IF NOR EXISTS idx_raw_date ON raw_indicators(date)" ,
                ""
            ]

            
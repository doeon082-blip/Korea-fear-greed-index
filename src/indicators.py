# indicators.py
# 역할:
# → 19개 지표 계산 함수 모음
# → fear_greed_index.py, walk_forward.py 둘 다 여기서 가져다 씀
# → 지표 추가/수정할 때 이 파일만 수정하면 됨

import pandas as pd
import numpy as np
from config import WINDOW, DATA_DIR

def normalize_rolling(series, window=WINDOW):
    """
    롤링 윈도우 정규화
    series: 정규화할 데이터
    window: 윈도우 크기 (기본 252일)
    """
    # 최근 window일 기준 최솟값, 최댓값
    rolling_min = series.rolling(window).min()
    rolling_max = series.rolling(window).max()
    # 0~100으로 정규화
    result = (series - rolling_min) / (rolling_max - rolling_min + 1e-8) * 100
    # 초기 NaN 구간은 전체 기간으로 채우기
    global_min = series.min()
    global_max = series.max()
    global_norm = (series - global_min) / (global_max - global_min + 1e-8) * 100
    return result.fillna(global_norm)

def calculate_indicators(df, df_usd, df_bond, df_sp500, df_vix, df_gold,
                          df_foreign, df_institution, df_fundamental,
                          df_foreign_limit, df_retail, df_vkospi):
    """
    19개 지표 전부 계산해서 df에 추가
    반환: 지표 추가된 df, 지표 컬럼 목록
    """
    # 이동평균 괴리율
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA20_gap'] = (df['Close'] - df['MA20']) / df['MA20'] * 100
    df['MA20_gap_norm'] = normalize_rolling(df['MA20_gap'])
    df['MA60'] = df['Close'].rolling(40).mean()
    df['MA120'] = df['Close'].rolling(120).mean()
    df['MA240'] = df['Close'].rolling(240).mean()
    # 거래량
    df['Volume_change'] = df['Volume'].pct_change()
    df['Volume_norm'] = normalize_rolling(
        df['Volume_change'].dropna()
    ).reindex(df.index)

    # 수익률 / 변동성
    df['Return'] = df['Close'].pct_change()
    df['Volatility'] = df['Return'].rolling(20).std()
    df['Volatility_norm'] = 100 - normalize_rolling(df['Volatility'])

    # 모멘텀
    df['Momentum'] = df['Close'] / df['Close'].shift(20) - 1
    df['Momentum_norm'] = normalize_rolling(df['Momentum'])

    # 52주 고저비율
    df['High_52w'] = df['Close'].rolling(WINDOW).max()
    df['Low_52w'] = df['Close'].rolling(WINDOW).min()
    df['HL_ratio'] = (df['Close'] - df['Low_52w']) / (df['High_52w'] - df['Low_52w']) * 100
    df['HL_norm'] = normalize_rolling(df['HL_ratio'])

    # RSI
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI_norm'] = normalize_rolling(df['RSI'])

    # 글로벌 매크로
    df['USD_KRW'] = df_usd['Close'].reindex(df.index)
    df['USD_norm'] = 100 - normalize_rolling(df['USD_KRW'])

    df['BOND'] = df_bond['Close'].reindex(df.index)
    df['BOND_norm'] = 100 - normalize_rolling(df['BOND'])

    df['SP500'] = df_sp500['Close'].reindex(df.index)
    df['SP500_return'] = df['SP500'].pct_change()
    df['SP500_norm'] = normalize_rolling(df['SP500_return'].shift(1))

    df['VIX'] = df_vix['Close'].reindex(df.index)
    df['VIX_norm'] = 100 - normalize_rolling(df['VIX'])

    df['GOLD'] = df_gold['Close'].reindex(df.index)
    df['GOLD_norm'] = 100 - normalize_rolling(df['GOLD'])

    # 밸류에이션
    df['PBR'] = df_fundamental['PBR'].reindex(df.index)
    df['PBR_norm'] = normalize_rolling(df['PBR'])

    df['PER'] = df_fundamental['PER'].reindex(df.index)
    df['PER_norm'] = normalize_rolling(df['PER'])

    df['DIV'] = df_fundamental['배당수익률'].reindex(df.index)
    df['DIV_norm'] = normalize_rolling(df['DIV'])

    # 투자자 수급
    df['RETAIL'] = df_retail['개인'].reindex(df.index)
    df['RETAIL_norm'] = normalize_rolling(df['RETAIL'])

    df['VKOSPI'] = df_vkospi['종가'].reindex(df.index)
    df['VKOSPI_norm'] = 100 - normalize_rolling(df['VKOSPI'])

    df['FOREIGN'] = df_foreign['외국인'].reindex(df.index)
    df['FOREIGN_norm'] = normalize_rolling(df['FOREIGN'])

    df['INSTITUTION'] = df_institution['기관'].reindex(df.index)
    df['INSTITUTION_norm'] = normalize_rolling(df['INSTITUTION'])

    df['FOREIGN_LIMIT'] = df_foreign_limit['한도소진률'].reindex(df.index)
    df['FOREIGN_LIMIT_norm'] = normalize_rolling(df['FOREIGN_LIMIT'])

    # 지표 컬럼 목록
    indicator_cols = [
        'MA20_gap_norm', 'Volume_norm', 'Volatility_norm', 'Momentum_norm',
        'HL_norm', 'RSI_norm', 'USD_norm', 'BOND_norm', 'SP500_norm',
        'VIX_norm', 'GOLD_norm', 'VKOSPI_norm', 'RETAIL_norm', 'FOREIGN_norm',
        'INSTITUTION_norm', 'PER_norm', 'PBR_norm', 'DIV_norm', 'FOREIGN_LIMIT_norm'
    ]

    return df, indicator_cols

def make_labels(df, horizon=1):
    """
    Financial ML 표쥰 Dynamic labeling
    
    [수정이유]
    기존:df['Return'].shift(-horizon)
    horizon=5 이면 5일뒤 하루 수익률
    완전한 랜덤 노이즈 - 예측불가

    수정:df['Close'].pct_change(horizon).shift(-horizon)
    horizon=5 이면 5일 누적 수익률
    의미있는 신호 예측가능

    변동성 기간에 맞게 스케일링:
    기존:volatility*0.5(1일 기준 고정)
    수정: volatlity * sqrt(horizon) * 0.5
    → 5일 예측이면 기준도 5일치로
    """
    # 누적 수익률 계산
    # pct_change(horizon): horizon 일 누적 수익률
    # shift(-horizon): 오늘 행에 미래값 붙이기
    cumulative_return = df['Close'].pct_change(horizon).shift(-horizon)
    
    # 변동성 임계값 스케일링
    # np.sqrt(horizon): 시간의 제곱근 법칙 (금융 수학 표준)
    # 1일 변동성 1% → 5일 기준 = 1% * sqrt(5) = 2. 24%
    volatility = df['Return'].rolling(WINDOW).std() * np.sqrt(horizon)
    dynamic_threshold = volatility * 0.5
    
    conditions = [
        cumulative_return > dynamic_threshold, #누적 상숭
        cumulative_return < -dynamic_threshold #누적 하락
    ] 
    # 둘 다 아니면 횡보 (1)
    
    # label_{horizon}d 컬럼 생성
    # 예: horizon=1  → label_1d
    # 예: horizon=5  → label_5d
    # 예: horizon=20 → label_20d
    df[f'label_{horizon}d'] = np.select(conditions, [2, 0], default=1)
    return df
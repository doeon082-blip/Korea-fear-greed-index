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

def make_labels(df):
    """
    Dynamic labeling
    변동성 기반으로 상승/횡보/하락 자동 분류
    """
    volatility = df['Return'].rolling(WINDOW).std()
    dynamic_threshold = volatility * 0.5
    next_return = df['Return'].shift(-1)

    conditions = [
        next_return > dynamic_threshold,
        next_return < -dynamic_threshold
    ]
    df['label'] = np.select(conditions, [2, 0], default=1)
    return df
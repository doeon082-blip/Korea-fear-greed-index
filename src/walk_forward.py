# walk_forward.py
# 역할:
# → Walk-forward Cross-validation 실행
# → 누적 학습 방식 (Anchored Walk-forward)
# → 클래스별 정확도 저장 (논문용)
# → 3단계 검증 (학습/검증/외부테스트)
# 실행 방법:
# → source venv/bin/activate
# → python3 src/walk_forward.py
# → 결과: data/walk_forward_results.csv

import sys
import os
# sys.path: 파이썬이 모듈 찾는 경로 목록
# src/ 추가해야 indicators.py 찾을 수 있음
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import pandas as pd
import numpy as np
import logging
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import FinanceDataReader as fdr
from dotenv import load_dotenv
from config import DATA_DIR, LOG_DIR, START_DATE, WINDOW
from indicators import calculate_indicators, make_labels

load_dotenv()

# 로그 설정
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=f"{LOG_DIR}walk_forward.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8"
)
logging.info("walk_forward.py 시작")

# 데이터 로드
print("데이터 로딩 중...")
df = fdr.DataReader('KS11', START_DATE)
df_usd = fdr.DataReader('USD/KRW', START_DATE)
df_bond = fdr.DataReader('^TNX', START_DATE)
df_sp500 = fdr.DataReader('^GSPC', START_DATE)
df_vix = fdr.DataReader('^VIX', START_DATE)
df_gold = fdr.DataReader('GC=F', START_DATE)

df_foreign = pd.read_csv(f"{DATA_DIR}foreign_data.csv", index_col=0, parse_dates=True)
df_institution = pd.read_csv(f"{DATA_DIR}institution_data.csv", index_col=0, parse_dates=True)
df_fundamental = pd.read_csv(f"{DATA_DIR}fundamental_data.csv", index_col=0, parse_dates=True)
df_foreign_limit = pd.read_csv(f"{DATA_DIR}foreign_limit_data.csv", index_col=0, parse_dates=True)
df_retail = pd.read_csv(f"{DATA_DIR}retail_data.csv", index_col=0, parse_dates=True)
df_vkospi = pd.read_csv(f"{DATA_DIR}vkospi_data.csv", index_col=0, parse_dates=True)
print("데이터 로딩 완료")

# 지표 계산 (indicators.py 에서 가져옴)
df, indicator_cols = calculate_indicators(
    df, df_usd, df_bond, df_sp500, df_vix, df_gold,
    df_foreign, df_institution, df_fundamental,
    df_foreign_limit, df_retail, df_vkospi
)

# Dynamic labeling
df = make_labels(df)

# 전체 데이터 준비
X_all = df[indicator_cols].dropna()
y_all = df['label'].reindex(X_all.index).dropna()
X_all = X_all.reindex(y_all.index)
total = len(X_all)

# =============================================
# 3단계 검증 구조 (최신 논문 방식)
# =============================================
# 전체 데이터를 3구간으로 나눔
# 학습용: 60% → 모델 훈련
# 검증용: 20% → 파라미터 조정
# 외부테스트: 20% → 최종 성능 측정 (절대 학습에 쓰면 안 됨)

train_end = int(total * 0.6)    # 60%
val_end = int(total * 0.8)      # 80%
# 나머지 20% = 외부 테스트

print(f"\n전체 데이터: {total}일")
print(f"학습구간: {X_all.index[0].strftime('%Y-%m-%d')} ~ {X_all.index[train_end].strftime('%Y-%m-%d')}")
print(f"검증구간: {X_all.index[train_end].strftime('%Y-%m-%d')} ~ {X_all.index[val_end].strftime('%Y-%m-%d')}")
print(f"외부테스트: {X_all.index[val_end].strftime('%Y-%m-%d')} ~ {X_all.index[-1].strftime('%Y-%m-%d')}")

# =============================================
# Walk-forward (학습+검증 구간에서만)
# =============================================
TEST_SIZE = 63  # 검증: 63일 (약 3개월)
start = WINDOW  # 처음 252일은 학습용

results = []
print(f"\nWalk-forward 시작: 총 {(val_end - WINDOW) // TEST_SIZE}구간")

while start + TEST_SIZE <= val_end:
    # 누적 학습 (처음부터 현재까지)
    # → 데이터 많아질수록 더 정확해짐
    X_train = X_all.iloc[0:start]
    y_train = y_all.iloc[0:start]

    # 검증 구간 (학습 다음 63일)
    X_test = X_all.iloc[start:start + TEST_SIZE]
    y_test = y_all.iloc[start:start + TEST_SIZE]

    # 앙상블 학습
    seed = 42
    xgb = XGBClassifier(
        n_estimators=100, max_depth=3,
        learning_rate=0.1, eval_metric='mlogloss',
        random_state=seed
    )
    lgb = LGBMClassifier(
        n_estimators=100, max_depth=3,
        learning_rate=0.1, class_weight='balanced',
        random_state=seed, verbose=-1
    )
    rf = RandomForestClassifier(
        n_estimators=100, max_depth=3,
        class_weight='balanced', random_state=seed
    )

    xgb.fit(X_train, y_train)
    lgb.fit(X_train, y_train)
    rf.fit(X_train, y_train)

    # 다수결 예측
    # 3개 모델 중 2개 이상 같은 값 선택
    pred_xgb = xgb.predict(X_test)
    pred_lgb = lgb.predict(X_test)
    pred_rf = rf.predict(X_test)

    pred_ensemble = []
    for i in range(len(X_test)):
        votes = [pred_xgb[i], pred_lgb[i], pred_rf[i]]
        pred_ensemble.append(max(set(votes), key=votes.count))

    # 전체 정확도
    acc = accuracy_score(y_test, pred_ensemble)

    # 클래스별 정확도 (논문용)
    # classification_report: 클래스별 정밀도/재현율 계산
    report = classification_report(
        y_test, pred_ensemble,
        labels=[0, 1, 2],
        output_dict=True,  # 딕셔너리로 반환
        zero_division=0    # 클래스 없을 때 0으로 처리
    )

    # 클래스별 정확도 추출
    # 0 = 하락, 1 = 횡보, 2 = 상승
    down_acc = report.get('0', {}).get('precision', 0)
    side_acc = report.get('1', {}).get('precision', 0)
    up_acc = report.get('2', {}).get('precision', 0)

    results.append({
        '학습시작': X_train.index[0].strftime('%Y-%m-%d'),
        '검증시작': X_test.index[0].strftime('%Y-%m-%d'),
        '검증종료': X_test.index[-1].strftime('%Y-%m-%d'),
        '학습데이터수': len(X_train),
        '전체정확도': round(acc * 100, 2),
        '상승정확도': round(up_acc * 100, 2),
        '횡보정확도': round(side_acc * 100, 2),
        '하락정확도': round(down_acc * 100, 2)
    })

    print(f"구간 {X_test.index[0].strftime('%Y-%m')} ~ "
          f"{X_test.index[-1].strftime('%Y-%m')}: "
          f"전체 {acc*100:.1f}% | "
          f"상승 {up_acc*100:.1f}% | "
          f"하락 {down_acc*100:.1f}%")

    logging.info(f"구간 {X_test.index[0].strftime('%Y-%m')}: 정확도 {acc*100:.1f}%")
    start += TEST_SIZE

# =============================================
# Walk-forward 결과 저장
# =============================================
df_results = pd.DataFrame(results)
df_results.to_csv(f"{DATA_DIR}walk_forward_results.csv", index=False)

print(f"\n=== Walk-forward 결과 ===")
print(f"평균 정확도: {df_results['전체정확도'].mean():.1f}%")
print(f"최고 정확도: {df_results['전체정확도'].max():.1f}%")
print(f"최저 정확도: {df_results['전체정확도'].min():.1f}%")

# =============================================
# 외부 테스트 (학습에 절대 쓰지 않은 데이터)
# 최신 논문 방식: 파라미터 완전 고정 후 한 번만 평가
# =============================================
print(f"\n=== 외부 테스트 시작 ===")

# 전체 학습+검증 데이터로 최종 모델 학습
X_final_train = X_all.iloc[0:val_end]
y_final_train = y_all.iloc[0:val_end]

# 외부 테스트 데이터
X_final_test = X_all.iloc[val_end:]
y_final_test = y_all.iloc[val_end:]

# 최종 모델 학습
xgb_final = XGBClassifier(
    n_estimators=100, max_depth=3,
    learning_rate=0.1, eval_metric='mlogloss',
    random_state=42
)
lgb_final = LGBMClassifier(
    n_estimators=100, max_depth=3,
    learning_rate=0.1, class_weight='balanced',
    random_state=42, verbose=-1
)
rf_final = RandomForestClassifier(
    n_estimators=100, max_depth=3,
    class_weight='balanced', random_state=42
)

xgb_final.fit(X_final_train, y_final_train)
lgb_final.fit(X_final_train, y_final_train)
rf_final.fit(X_final_train, y_final_train)

# 최종 예측
pred_xgb_f = xgb_final.predict(X_final_test)
pred_lgb_f = lgb_final.predict(X_final_test)
pred_rf_f = rf_final.predict(X_final_test)

pred_final = []
for i in range(len(X_final_test)):
    votes = [pred_xgb_f[i], pred_lgb_f[i], pred_rf_f[i]]
    pred_final.append(max(set(votes), key=votes.count))

final_acc = accuracy_score(y_final_test, pred_final)
final_report = classification_report(
    y_final_test, pred_final,
    labels=[0, 1, 2],
    output_dict=True,
    zero_division=0
)

# 외부 테스트 결과 저장
df_final = pd.DataFrame([{
    '테스트시작': X_final_test.index[0].strftime('%Y-%m-%d'),
    '테스트종료': X_final_test.index[-1].strftime('%Y-%m-%d'),
    '테스트데이터수': len(X_final_test),
    '전체정확도': round(final_acc * 100, 2),
    '상승정확도': round(final_report.get('2', {}).get('precision', 0) * 100, 2),
    '횡보정확도': round(final_report.get('1', {}).get('precision', 0) * 100, 2),
    '하락정확도': round(final_report.get('0', {}).get('precision', 0) * 100, 2)
}])
df_final.to_csv(f"{DATA_DIR}walk_forward_final_test.csv", index=False)

print(f"외부 테스트 정확도: {final_acc*100:.1f}%")
print(f"결과 저장 완료")
logging.info(f"외부 테스트 완료. 정확도: {final_acc*100:.1f}%")
# 한국 공포탐욕지수 (Korea Fear & Greed Index)

> 본 지수는 시장 심리 파악 도구입니다. 투자 결정에 단독 사용을 권장하지 않습니다.

## 프로젝트 개요

KOSPI 시장의 투자자 심리를 0~100으로 수치화한 한국형 공포탐욕지수.  
CNN Fear & Greed Index를 참고했으나, 한국 시장 구조에 맞게 독자 설계.  
동학개미 시대 개인투자자의 감정적 투자 실수를 줄이는 것이 목표.

이 프로젝트는 더 큰 비전인 **Finance Garden**의 첫 번째 레이어다.  
Layer 1(시장 심리 지수) → Layer 2(개별 종목 분석)로 확장 예정.

---

## 기존 서비스와의 차별점

| 항목 | 기존 서비스 | 본 프로젝트 |
|------|------------|------------|
| 가중치 방식 | 고정 가중치 | XGBoost + SHAP 동적 가중치 |
| 통계 검증 | 없음 | ADF 정상성 검정 + Granger 인과검정 |
| 한국 시장 특화 | CNN 복제 수준 | 동학개미·VKOSPI 비대칭 반영 |
| 코드 공개 | 비공개 | 전체 오픈소스 |
| 다중공선성 처리 | 없음 | AFI 100-seed 평균으로 안정화 |
| LLM 연동 | 없음 | Ollama 로컬 LLM (Phase 4~) |

---

## 지표 구성 (19개)

**기술적 지표 (6)**

| 지표 | 설명 |
|------|------|
| MA20 괴리율 | 현재가와 20일 이동평균 간 괴리 |
| 거래량 변화율 | 전일 대비 거래량 변화 |
| 변동성 | 단기 가격 변동폭 |
| 모멘텀 | 추세 방향 및 강도 |
| 52주 신고가/신저가 비율 | 시장 강도 측정 |
| RSI | 과매수/과매도 판단 |

**투자자 수급 (3)**

| 지표 | 설명 |
|------|------|
| 개인 순매수 (RETAIL) | 동학개미 매매 동향 |
| 외국인 순매수 (FOREIGN) | 외국인 자금 흐름 |
| 기관 순매수 (INSTITUTION) | 기관 매매 동향 |

**시장 심리 (1)**

| 지표 | 설명 |
|------|------|
| VKOSPI | 한국판 VIX. 공포 과잉반응 특성 반영 |

**밸류에이션 (3)**

| 지표 | 설명 |
|------|------|
| PER | 주가수익비율 |
| PBR | 주가순자산비율 |
| 배당수익률 | 시장 저평가 여부 |

**글로벌 매크로 (5)**

| 지표 | 설명 |
|------|------|
| 원달러 환율 | 외국인 자금 유출입 선행 |
| 미국 국채금리 | 글로벌 위험 선호도 |
| S&P500 | 미국 시장 연동성 |
| VIX | 글로벌 공포 지수 |
| 금 가격 | 안전자산 수요 |

**수급 구조 (1)**

| 지표 | 설명 |
|------|------|
| 외국인 한도소진율 | 18개 섹터 평균, 외국인 투자 여력 측정 |

---

## 핵심 기술

**AFI (Aggregated Feature Importance)**  
XGBoost를 100번 다른 seed로 반복 학습 후 SHAP 중요도를 평균 산출.  
단일 실행의 불안정성을 제거하고 지표 가중치를 데이터 기반으로 자동 결정.

**앙상블 모델**  
XGBoost + LightGBM + RandomForest 3개 모델 앙상블.  
Rolling 252일 윈도우 기반 매주 재학습으로 look-ahead bias 제거.

**동적 라벨링**  
다음날 수익률: +0.5% 초과 = 상승 / -0.5% 미만 = 하락 / 그 외 = 횡보.

**Walk-forward Cross-validation**  
미래 데이터 누수 없는 시계열 전용 검증 방식.

**3-horizon 예측**  
1일 / 5일 / 20일 후 시장 방향 동시 예측.

**통계 검증**  
ADF 정상성 검정 + Granger 인과검정으로 각 지표 유효성 검증.

---

## 기술 스택
```
데이터 수집    pykrx, FinanceDataReader, pytrends
모델           XGBoost, LightGBM, RandomForest, SHAP
통계           statsmodels (ADF, VAR, IRF), scipy
시각화         Streamlit, Matplotlib
DB             SQLite (Phase 3~)
LLM            Ollama 로컬 추론 (Phase 4~)
Fine-tuning    Qwen2.5:14B QLoRA / RunPod A100 (Phase 6~)
```
---

## 환경 설정

```bash
# 데이터 수집 (pykrx는 Python 3.11 전용)
conda activate fgi
python3 src/vkospi_update.py

# Streamlit 실행
source venv/bin/activate
streamlit run src/fear_greed_index.py
```

---

## 폴더 구조
```
Korea-fear-greed-index/
├── src/                     핵심 코드
├── data/                    CSV 데이터 (git 미추적)
├── logs/                    실행 로그 (git 미추적)
├── docs/                    개발 일지
├── .env                     KRX 자격증명 (git 미추적)
├── requirements.txt         venv 환경 패키지
└── requirements_fgi.txt     fgi 환경 패키지 (pykrx)
```
---

## 개발 로드맵

| Phase | 내용 | 시기 |
|-------|------|------|
| 1 | 통계 강화 (VAR+IRF, Walk-forward, 3-horizon, 구글트렌드) | 2026.06 |
| 2 | 뉴스 섹터 분류 + 동적 가중치 (KR-FinBERT) | 2026.07 |
| 3 | SQLite DB 구축 (7개 테이블, Long format) | 2026.08 |
| 4 | RAG + 챗봇 (ChromaDB + Ollama) | 2026.09 |
| 5 | 연구 보고서 작성 | 2026.10 |
| 6 | QLoRA Fine-tuning (Qwen2.5:14B, RunPod A100) | 이후 |
| 7 | Finance Garden Layer 2 (개별 종목, dart-fss) | 이후 |

---

## 연구 포지셔닝

**연구 제목**  
설명 가능한 AI 기반 한국 주식시장 투자자 심리 지수 연구:  
뉴스 섹터 분석과 동적 가중치를 중심으로

**핵심 기여**
- 한국 시장 특화 19개 지표 독자 설계
- XGBoost 동적 가중치 + SHAP 설명 가능성
- ADF + Granger 통계 검증
- 동학개미 현상 및 VKOSPI 비대칭성 분석
- 전체 코드 오픈소스 공개

---

## 개발자

김도언 · 학점은행제 경영학 · AI 독학 중
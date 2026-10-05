# Day 2 실습 · 컨텍스트 엔지니어링

LLM 기본 & 바이브 코딩 3일 과정 — Day 2 슬라이드(`LLM_basic_Day2.pptx`)와 짝을 이루는 실습 코드입니다.

어제는 프롬프트를 고쳤습니다. 오늘은 **창에 무엇을 넣을지**를 고칩니다. 가상의 회사 *한빛정밀* 사내 자료 20편으로 RAG 질의응답을 만들고, 고장을 진단하고, 같은 10문항을 창만 바꿔 다시 잽니다. 마지막에 계산기와 검색을 붙인 가장 작은 에이전트 루프를 짭니다.

## 1. 준비 (강의 전날)

```bash
# 루트(ETRI_LLM_3days/)에서 한 번만 — day1·day2·day3 공용 가상환경 · .env
./setup.sh                         # 임베딩 모델(약 470MB) 다운로드까지 — 꼭 전날에
source .venv/bin/activate

cd day2
EMBED=hash python -m pytest tests -q   # 8 passed
```

- Python 3.10 이상. CPU만으로 돌아갑니다(GPU 필요 없음).
- **강의장 인터넷이 Hugging Face를 막는다면** `.env`에 `EMBED=hash`를 넣습니다. 내려받기 없이 글자 조각으로 만든 간이 벡터를 씁니다. 뜻을 이해하지 못해서 *단어를 바꿔 쓴 질문*에 약한데, 그 차이도 좋은 관찰 거리입니다.
- 모델 이름 · 단가는 Day 1과 같이 `.env`의 `MODEL`과 `common/llm.py`에서 강의 당일 기준으로 확인합니다.

## 2. 세션별 진행

| 시간 | 세션 | 실습 | 노트북 |
|---|---|---|---|
| 09:00–10:30 | 1 컨텍스트란 무엇인가 | 20분 · 전부 넣기 vs 골라 넣기 (정답 · 시간 · 토큰 · 비용) | `01_window` |
| 10:40–11:40 | 2 네 가지 전략 | 10분 · 줄이기 · 쓰기 맛보기, 내 업무에 전략 붙이기 | `02_strategies` |
| 11:50–12:30 | 3 고르기 · RAG (오전) | 30분 · 임베딩 · 청킹 · 색인 · 키워드 vs 의미 검색 | `03a_rag_index` |
| 13:30–15:20 | 3 고르기 · RAG (오후) | 30분 질의응답 + 20분 고장 내기 + 창만 바꿔 다시 재기 | `03b_rag_qa` |
| 15:30–16:50 | 4 도구 결과도 컨텍스트다 | 40분 · 계산기 + 검색 루프, 설명 문장만 고쳐 교정 | `04_tool_loop` |

## 3. 폴더

```
day2/
├─ src/
│  ├─ rag.py        임베딩 · chunk() · Keyword(BM25) · Index(chroma) · ask() · debug()
│  ├─ qa.py         10문항 채점 · 고장 위치 추정
│  └─ loop.py       calculator · search 도구와 단일 루프 run()
├─ data/
│  ├─ kb/           한빛정밀 사내 자료 20편 (일반 업무 규칙 29개 조 · 규정 · FAQ · 제품 사양 · 담당자표)
│  └─ qa_tests.jsonl  질의응답 10문항 — 답있음 5 · 답없음 3 · 바꿔쓴 2
├─ notebooks/       01 · 02 · 03a · 03b · 04
├─ tests/           API · 모델 없이 도는 점검
└─ tools/           make_kb.py · make_notebooks.py · download_model.py (강사용)
```

## 4. 핵심 함수

```python
from src import rag, qa, loop

chunks = rag.chunk_folder("data/kb", max_len=800, overlap=100)   # 제목 · 조항 앞에서 자른다
idx = rag.Index.build(chunks)                                    # 조각 · 벡터 · 출처를 chroma에
idx.search("연차 사용 절차", k=3)                                  # 거리 — 작을수록 가깝다
rag.Keyword(chunks).search("AX-2041", k=3)                       # 키워드(BM25) — 코드 · 번호에 강하다

answer, hits = rag.ask("휴가 신청은 어떻게 해요?", idx)            # 검색 → 주입 → 호출
rag.debug("휴가 신청은 어떻게 해요?", idx)                         # 검색 결과 · 최종 프롬프트 · 답을 모두 찍는다
qa.run_qa(idx, k=3)                                               # 10문항 채점

loop.SEARCH_INDEX = idx
loop.run("서울로 3박 출장을 가면 숙박비 한도는 모두 얼마인가요?")      # 매 바퀴 도구 호출을 찍는다
```

## 5. 질의응답 채점 — 실패를 단계로 나눈다

| 판정 | 언제 | 고치는 곳 |
|---|---|---|
| 검색·청킹 | 넣은 자료에 답이 든 조각이 없다 | 검색: `k` · 질문 말투 · 키워드 검색 / 청킹: 구조 경계 · 겹침 |
| 있는데 못 씀 | 자료에 답이 있는데 답에 없다 | 주입 코드 · 프롬프트 위치 |
| 지어냄 | 답 없는 질문에 "자료에 없음"이 아니다 | 거절 지시 |
| 출처 오류 | 답은 맞는데 각주가 다른 문서를 가리킨다 | 각주 규칙 |

코드는 고장 위치를 좁혀 줄 뿐입니다. 검색 고장인지 청킹 고장인지는 `debug()`로 조각을 열어 사람이 가립니다.

### 고장 내기 실습 (03b_rag_qa 노트북 7절)

| `BREAK` | 고장 내는 법 | 기대 증상 |
|---|---|---|
| 1 | `k=1` + 단어를 바꾼 질문 | 답이 엉뚱함 |
| 2 | `max_len=80`, 구조 무시하고 자르기 | 문장이 끊김 |
| 3 | `drop_context=True` — 자료를 빼먹는 버그 | 있는데 못 씀 |
| 4 | `rules=RULES_NO_REFUSAL` — 거절 줄 삭제 | 지어냄 |

## 6. 창만 바꿔 다시 재기 (03b_rag_qa 노트북 8절)

같은 10문항, 같은 판정 기준으로 창에 넣는 것만 세 가지로 바꿉니다.

| 조건 | 창에 들어가는 것 |
|---|---|
| 창에 자료 없음 | 질문만 |
| RAG | 검색한 조각 3개 + 거절 규칙 |
| 자료 전부 | 사내 자료 20편 전체 + 같은 규칙 |

통과 수의 차이가 컨텍스트의 효과이고, RAG와 *자료 전부*의 토큰 차이가 고르기의 값입니다.

## 7. 모의 모드

`.env`에 `LLM_MOCK=1`, `EMBED=hash`를 두면 키 · 인터넷 없이 다섯 노트북이 끝까지 돕니다. 점수는 의미가 없고 흐름만 확인합니다. 도구 루프는 모의 모드에서 "search → calculator → 종료"를 흉내 냅니다.

## 8. 자주 막히는 곳

| 증상 | 확인할 것 |
|---|---|
| 임베딩 모델 내려받기가 멈춤 · 403 | 강의장 방화벽 — `EMBED=hash`로 진행 |
| `No module named 'sentence_transformers'` | 가상환경을 켰는가 · `pip install -r requirements.txt` |
| chroma `Expected a name containing 3-512 characters` | `Index.build(name=…)`의 이름은 영문 · 숫자 3자 이상 |
| 노트북에서 `NameError: idx` | 위 셀(색인 만들기)을 먼저 실행 |
| 도구 루프가 5바퀴에서 멈춤 | `loop.run(..., max_turns=8)` · 도구 설명이 모호하지 않은지 |
| `temperature` 관련 400 오류 | 최신 모델은 temperature를 받지 않는다 — 코드에서 쓰지 않는다 |

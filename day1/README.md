# Day 1 실습 · 프롬프트 엔지니어링

LLM 기본 & 바이브 코딩 3일 과정 — Day 1 슬라이드(`LLM_basic_Day1.pptx`)와 짝을 이루는 실습 코드입니다.

하루 동안 **프롬프트 하나**를 만들고(v0 → v1), **고정 20문항**으로 채점하고, 실패 유형을 하나씩 고쳐(v2 → v3), 마지막에 모델을 바꿔 잽니다.

## 1. 준비 (10분)

```bash
# 루트(ETRI_LLM_3days/)에서 한 번만 — day1·day2·day3 공용 가상환경 · .env
./setup.sh                         # .venv 생성 + requirements.txt 설치 + .env 생성
# 루트 .env 를 열어 ANTHROPIC_API_KEY 를 넣는다
source .venv/bin/activate

cd day1
python -m pytest tests -q          # 채점 로직 점검 — API 없이 돌아간다
jupyter lab                        # notebooks/ 를 연다
```

- Python 3.10 이상
- `.env`의 `MODEL`과 `common/llm.py`의 `MODELS`(3차 비교용)는 **강의 당일 쓸 수 있는 모델 이름**으로 확인해 바꿉니다.
- `common/llm.py`의 `PRICES`는 예시 값입니다. 강의 당일 요금표로 채웁니다. 비어 있으면 "단가 미입력"으로 나옵니다.

## 2. 블록별 진행

| 시간 | 블록 | 실습 | 파일 |
|---|---|---|---|
| 09:00–10:30 | 1 LLM이 글을 쓰는 법 | (실습 노트북 없음 — 슬라이드 · 채팅 화면) | — |
| 10:40–11:40 | 2 API와 메시지 | 25분 · 첫 호출 · 응답 읽기 · 기억하지 않음 · 다섯 번 · 비용 | `notebooks/01_api_basics.ipynb` |
| 11:50–15:00 | 3 프롬프트 설계 | 60분 · v0 → v1 · 생각할 자리 · 나눠 시키기 · 일반화된 프롬프트 적용 | `notebooks/02_prompt_design.ipynb` · `prompts/` |
| 15:10–16:40 | 4 평가 | 50분 · 20문항 · v1 채점 · v2 · v3 · 모델 비교 | `notebooks/03_evaluation.ipynb` · `src/grade.py` |

## 3. 폴더

```
day1/
├─ src/
│  └─ grade.py          parse() · check() · run() — 채점 코드 (블록 4)
├─ prompts/             수강생이 고치는 곳
│  ├─ prompt_v0.txt     한 줄짜리 지시
│  └─ prompt_v1.txt     TODO 틀 — 기법을 넣어 채운다
├─ solutions/prompts/   강사 풀이본 v1 · v2 · v3
├─ data/
│  ├─ docs/             가상의 사내 문서 20편
│  └─ tests.jsonl       고정 20문항과 통과 조건
├─ notebooks/           01 ~ 03
├─ results/             채점 결과 · scoreboard.csv (실행하면 생긴다)
├─ tests/test_grade.py  check() 점검
└─ tools/make_notebooks.py   노트북을 다시 만드는 스크립트 (강사용)
```

## 4. 채점을 명령줄로

```bash
python -m src.grade prompts/prompt_v1.txt
python -m src.grade prompts/prompt_v1.txt prompts/prompt_v2.txt --note "형식: <json> 태그"
python -m src.grade solutions/prompts/prompt_v3.txt --all-models     # 3차
python -m src.grade prompts/prompt_v1.txt --only 16-18                # 일부 문항만
```

실행할 때마다 `results/run_*.json`(문항별 출력)과 `results/scoreboard.csv`(결과표 한 줄)가 남습니다.

### 프롬프트 파일 규칙

```
=== system ===
<역할> … </역할>
<규칙> … </규칙>
=== user ===
<문서>
{document}
</문서>
```

- `{document}` 자리에 문서가 들어갑니다. JSON 예시의 중괄호는 그대로 둬도 됩니다.
- 구분선이 없으면 파일 전체를 user 메시지로 보냅니다.
- 모델이 `<json> … </json>` 안에 답하면 그 안만 읽고, 아니면 출력 전체를 `json.loads` 합니다. 앞뒤에 설명이나 ```` ``` ```` 가 붙으면 **형식 위반**입니다.

## 5. 판정 규칙 (`check`)

판정 순서는 **형식 위반 → 지어냄 → 지시 일부 누락 → 사실 오류**이고, 앞에서 걸리면 거기서 멈춥니다.

| 유형 | 언제 | 고치는 곳 |
|---|---|---|
| 형식 위반 | JSON이 아님 · 값이 숫자가 아님 · 모양이 다름 | 출력 형식 지시 · 예시 · `<json>` 태그 |
| 지어냄 | `absent`의 항목에 값이 있음 · 수치 없는 문서에서 항목을 뽑음 | 거절 지시 + "대신 null · 빈 목록" · 근거 먼저 |
| 지시 일부 누락 | 값이 있는 항목 수가 `items`와 다름 | 지시를 구조로 · 개수 규칙을 분명히 |
| 사실 오류 | `values`의 숫자와 다름 | 프롬프트가 아니라 참조 문서 — Day 2 |

- 값이 `null`인 항목은 개수에 넣지 않습니다. "예산 미정"을 `null`로 둔 답은 통과입니다.
- 숫자는 단위 배수를 허용합니다. "340만원"을 `340`(만원)으로 뽑든 `3400000`(원)으로 뽑든 통과입니다.
- `values`의 키는 항목 이름에 들어 있는 말입니다(예: `"예산"` ↔ `"전체 예산"`). 이름이 달라도 같은 값의 항목이 있으면 통과로 봅니다.
- 코드는 숫자만 봅니다. **실패 문항은 노트북에서 출력을 직접 열어** 유형이 맞는지 사람이 확인합니다.

### tests.jsonl 한 줄

```json
{"id": 18, "group": "답없음", "doc": "data/docs/18_회의록_예산미정.txt",
 "check": {"items": 2, "values": {"참석": 7, "회의": 60}, "absent": ["예산"]}}
```

`doc` 대신 `"input": "문서 본문"`을 직접 써도 됩니다. `"has": "단어"`는 답 어딘가에 그 말이 있어야 통과입니다.

### "틀렸던 입력" 2문항을 내 것으로 바꾸기

19 · 20번은 자리만 잡아 둔 문항입니다. 블록 3에서 **내 v1이 실제로 틀렸던 문서**로 바꿉니다.

1. 문서를 `data/docs/`에 저장한다
2. `tests.jsonl`의 19 · 20번 줄에서 `doc`과 `check`를 바꾼다
3. **그다음부터는 문항을 바꾸지 않는다** — 고치는 동안 문항이 바뀌면 비교할 수 없다

내 업무 문서로 20문항을 새로 만들 때도 구성은 같습니다 — 평범 10 · 경계 5 · 답없음 3 · 틀렸던 2.

## 6. 모의 모드 (키 없이 흐름 확인)

```bash
LLM_MOCK=1 python -m src.grade prompts/prompt_v1.txt     # Windows PowerShell: $env:LLM_MOCK="1"
```

`.env`에서 `LLM_MOCK=1`로 두어도 됩니다. API를 부르지 않고 고정된 응답(`{"제목": "모의 응답", "항목": []}`)을 돌려줍니다. **점수는 의미가 없고**, 노트북 · 채점 · 결과 저장이 끝까지 도는지만 봅니다. 강사 리허설과 네트워크가 막힌 강의장 대비용입니다.

## 7. temperature에 대해

anthropic SDK 1.x에서는 `temperature` 인자가 빠졌습니다. API는 모델마다 달라서, 이전 세대(Haiku 4.5)는 아직 받지만 최신 모델(Sonnet 5.5 · Opus 5.5)은 거부합니다(400 오류). 01 노트북에서 **같은 질문을 다섯 번** 보내 흔들림을 직접 보고, Haiku로 온도 0과 1을 바꿔 가며 차이를 비교합니다. "0으로 두면 늘 같다"에 기대지 않고 **여러 번 돌려 재는 것**이 블록 4의 출발점입니다.

`llm.call(..., temperature=...)`은 `extra_body`로 보냅니다. 받는 모델(Haiku 4.5)에서만 씁니다 — Sonnet 5.5에 보내면 400 오류가 나는 것도 01 노트북에서 확인합니다. 생각의 양을 조절하는 `effort="low"`~`"max"`는 지원하는 모델에서만 씁니다.

## 8. 자주 막히는 곳

| 증상 | 확인할 것 |
|---|---|
| `Could not resolve authentication method` | `.env`가 `day1/` 바로 아래에 있는가 · 키에 따옴표나 공백이 없는가 |
| `not_found_error` · model | `.env`의 `MODEL` 이름 · `common/llm.py`의 `MODELS` |
| `rate_limit_error` | `--workers 1`로 줄인다 (기본 4개 동시 호출) |
| 노트북에서 `No module named src` | 첫 셀을 먼저 실행했는가 (경로를 잡는 셀) |
| Windows에서 한글이 깨짐 | 파일은 모두 UTF-8. 메모장 대신 VS Code로 연다. `scoreboard.csv`는 엑셀에서 바로 열리도록 BOM을 붙였다 |
| `stop_reason`이 `max_tokens` | 출력이 잘렸다. 실패 설명에 "(max_tokens에서 잘림)"이 붙는다 |

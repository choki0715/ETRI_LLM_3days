# Day 1 실습 · 프롬프트 엔지니어링

LLM 기본 & 바이브 코딩 3일 과정 — Day 1 슬라이드(`LLM_basic_Day1.pptx`)와 짝을 이루는 실습 코드입니다.

하루 동안 **프롬프트 하나**를 요소를 더해 가며 만들고(v0 → prompt_1~4), **고정 20문항**으로 채점하고, 실패 유형을 하나씩 고칩니다(prompt_5 → 6). 과제는 **사내 문의 메시지를 카테고리·긴급도·요약으로 분류하는 것**입니다.

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
- `.env`의 `MODEL`과 `common/llm.py`의 `MODELS`(`--all-models` 비교용)는 **강의 당일 쓸 수 있는 모델 이름**으로 확인해 바꿉니다.
- `common/llm.py`의 `PRICES`는 예시 값입니다. 강의 당일 요금표로 채웁니다. 비어 있으면 "단가 미입력"으로 나옵니다.

## 2. 세션별 진행

| 시간 | 세션 | 실습 | 파일 |
|---|---|---|---|
| 09:00–10:30 | 1 LLM이 글을 쓰는 법 | (실습 노트북 없음 — 슬라이드 · 채팅 화면) | — |
| 10:40–11:40 | 2 API와 메시지 | 25분 · 첫 호출 · 응답 읽기 · 기억하지 않음 · 다섯 번 · 비용 | `notebooks/01_api_basics.ipynb` |
| 11:50–15:00 | 3 프롬프트 설계 | 60분 · v0 → prompt_1~4 (요소를 하나씩 더하며) · 근거 활용 | `notebooks/02_prompt_design.ipynb` · `prompts/` |
| 15:10–16:40 | 4 평가 | 50분 · 20문항 · prompt_4 채점 · 5 · 6 | `notebooks/03_evaluation.ipynb` · `src/grade.py` |

## 3. 폴더

```
day1/
├─ src/
│  └─ grade.py          parse() · check() · run() — 채점 코드 (4세션)
├─ prompts/             수강생 프롬프트
│  ├─ prompt_v0.txt     한 줄짜리 지시 (출발점)
│  └─ prompt_1~6.txt    02가 요소를 하나씩 더하며 1~4 생성(4가 최종) · 03에서 한 유형씩 고쳐 5, 6
├─ solutions/prompts/   강사 풀이본 prompt_4 · 5 · 6 (02 최종 · 03의 2차 두 번)
├─ data/
│  ├─ docs/             2세션(비용 계산)에서만 쓰는 긴 문서 1편
│  └─ tests.jsonl       고정 20문항(문의 본문 + 통과 조건)과 통과 조건
├─ notebooks/           01 ~ 03
├─ results/             채점 결과 · scoreboard.csv (실행하면 생긴다)
├─ tests/test_grade.py  check() 점검
└─ tools/make_notebooks.py   노트북을 다시 만드는 스크립트 (강사용)
```

## 4. 채점을 명령줄로

```bash
python -m src.grade prompts/prompt_4.txt
python -m src.grade prompts/prompt_4.txt prompts/prompt_5.txt --note "긴급도 기준 추가"
python -m src.grade solutions/prompts/prompt_6.txt --all-models      # 모델 셋으로 돌려 비교
python -m src.grade prompts/prompt_4.txt --only 16-18                # 일부 문항만
```

실행할 때마다 `results/run_*.json`(문항별 출력)과 `results/scoreboard.csv`(결과표 한 줄)가 남습니다.

### 프롬프트 파일 규칙

```
=== system ===
<역할> … </역할>
<할 일> … </할 일>
=== user ===
<문의>
{document}
</문의>
```

- `{document}` 자리에 문의 본문이 들어갑니다. JSON 예시의 중괄호는 그대로 둬도 됩니다.
- 구분선이 없으면 파일 전체를 user 메시지로 보냅니다.
- 모델이 `<json> … </json>` 안에 답하면 그 안만 읽고, 아니면 출력 전체를 `json.loads` 합니다. 앞뒤에 설명이나 ```` ``` ```` 가 붙으면 **형식 위반**입니다.

## 5. 판정 규칙 (`check`)

목표 출력: `{"카테고리": "…", "긴급도": "…", "요약": "…"}` — 카테고리는 **비품·시설·인사·IT·기타**, 긴급도는 **높음·보통·낮음** 중 하나여야 합니다.

판정 순서는 **형식 위반 → 지어냄 → 지시 일부 누락 → 사실 오류**이고, 앞에서 걸리면 거기서 멈춥니다.

| 유형 | 언제 | 고치는 곳 |
|---|---|---|
| 형식 위반 | JSON이 아님 · 카테고리·긴급도가 정해진 보기 밖 · 요약이 없음 | 출력 형식 지시 · 예시 · `<json>` 태그 |
| 지어냄 | 정답이 "기타"인데 구체적인 카테고리를 지어냄 | "뚜렷이 안 맞으면 기타로" 지시 + 판단 근거 먼저 |
| 지시 일부 누락 | 요약에 꼭 들어가야 할 말(`has`)이 없음 | 요약에 뭘 넣을지 더 구체적으로 지시 |
| 사실 오류 | 카테고리 또는 긴급도가 정답과 다름 | 프롬프트의 판단 기준을 더 구체적으로 (prompt_6의 긴급도 기준처럼) |

- 코드는 문자열만 비교합니다. **실패 문항은 노트북에서 출력을 직접 열어** 유형이 맞는지 사람이 확인합니다.

### tests.jsonl 한 줄

```json
{"id": 1, "group": "평범", "input": "사내 메신저에 로그인이 안 됩니다. 비밀번호를 재설정해주세요.",
 "check": {"category": "IT", "urgency": "보통", "has": "비밀번호"}}
```

`input`에 문의 본문을 직접 씁니다(짧은 메시지라 파일로 안 뺍니다). `"has": "단어"`는 요약 어딘가에 그 말이 있어야 통과입니다(없으면 생략).

내 업무 문의로 20문항을 새로 만들 때도 구성은 같습니다 — 평범 10 · 경계 7 · 기타(카테고리) 3. 프롬프트를 고치는 동안에는 문항을 바꾸지 않습니다 — 고치는 중간에 문항이 바뀌면 전후 비교가 안 됩니다.

## 6. 모의 모드 (키 없이 흐름 확인)

```bash
LLM_MOCK=1 python -m src.grade prompts/prompt_4.txt     # Windows PowerShell: $env:LLM_MOCK="1"
```

`.env`에서 `LLM_MOCK=1`로 두어도 됩니다. API를 부르지 않고 고정된 응답(`{"카테고리": "기타", "긴급도": "낮음", "요약": "모의 응답"}`)을 돌려줍니다. **점수는 의미가 없고**, 노트북 · 채점 · 결과 저장이 끝까지 도는지만 봅니다. 강사 리허설과 네트워크가 막힌 강의장 대비용입니다.

## 7. temperature에 대해

anthropic SDK 1.x에서는 `temperature` 인자가 빠졌습니다. API도 이 과정에서 쓰는 모델(Haiku 5.5 · Sonnet 5.5)은 1이 아닌 값을 거부합니다(400 오류). 1은 받지만 기본값과 같아서 아무것도 바뀌지 않습니다. (이전 세대인 Haiku 4.5는 0~1 사이 값을 받았습니다.) 01 노트북에서 **같은 질문을 다섯 번** 보내 흔들림을 직접 보고, 온도를 0으로 낮추려는 요청이 거부되는 것을 확인합니다. "0으로 두면 늘 같다"에 기대지 않고 **여러 번 돌려 측정하는 것**이 4세션의 출발점입니다.

`llm.call(..., temperature=...)`은 `extra_body`로 보냅니다. 01 노트북에서 거부되는 것을 보여 주는 데만 씁니다. 생각의 양을 조절하는 `effort="low"`~`"max"`는 지원하는 모델에서만 씁니다.

## 8. 자주 막히는 곳

| 증상 | 확인할 것 |
|---|---|
| `Could not resolve authentication method` | `.env`가 `day1/` 바로 아래에 있는가 · 키에 따옴표나 공백이 없는가 |
| `not_found_error` · model | `.env`의 `MODEL` 이름 · `common/llm.py`의 `MODELS` |
| `rate_limit_error` | `--workers 1`로 줄인다 (기본 4개 동시 호출) |
| 노트북에서 `No module named src` | 첫 셀을 먼저 실행했는가 (경로를 잡는 셀) |
| Windows에서 한글이 깨짐 | 파일은 모두 UTF-8. 메모장 대신 VS Code로 연다. `scoreboard.csv`는 엑셀에서 바로 열리도록 BOM을 붙였다 |
| `stop_reason`이 `max_tokens` | 출력이 잘렸다. 실패 설명에 "(max_tokens에서 잘림)"이 붙는다 |

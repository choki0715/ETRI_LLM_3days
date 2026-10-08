# LLM 기본 & 바이브 코딩 3일 과정 · 실습 자료

슬라이드(`LLM_basic_Day1~3.pptx`)와 짝을 이루는 실습 코드입니다. 하루에 한 가지씩, **모델에게 무엇을 어떻게 넘기는가**를 바꿔 가며 결과를 측정합니다.

| 날 | 주제 | 무엇을 고치나 | 실습 방식 | 안내 |
|---|---|---|---|---|
| Day 1 | 프롬프트 엔지니어링 | **지시문** — 사내 문의를 카테고리 · 긴급도 · 요약으로 분류하는 프롬프트를 요소를 더해 가며 만들고, 고정 20문항으로 채점해 실패 유형을 하나씩 고친다 | Jupyter 노트북 | [day1/README.md](day1/README.md) |
| Day 2 | 컨텍스트 엔지니어링 | **창에 넣는 것** — 가상 회사 *한빛정밀* 사내 자료 20편으로 RAG 질의응답을 만들고, 10문항 채점으로 실패한 단계를 진단한다. 마지막에 계산기 · 검색 도구를 붙인 가장 작은 에이전트 루프를 짠다 | Jupyter 노트북 | [day2/README.md](day2/README.md) |
| Day 3 | 바이브 & 하네스 엔지니어링 | **모델을 둘러싼 장치** — MCP 서버 붙이기, 바이브 코딩으로 벽돌깨기, 가상 공장 하네스(sf-harness)에서 훅 · 스킬 · 사람의 결정을 나눠 보고, 내 업무용 하네스 뼈대를 만든다 | Claude Code 안에서 (노트북 없음) | [day3/README.md](day3/README.md) |

세 날은 이어집니다. Day 1의 "여러 번 돌려 측정하고, 실패를 유형으로 나눠 고친다"가 Day 2의 RAG 채점으로, Day 2 마지막의 도구 루프(`day2/src/loop.py`)가 Day 3의 MCP · 하네스로 이어집니다. Day 3의 출장비 정산 뼈대는 Day 2 한빛정밀 출장비 규정을 그대로 씁니다.

## 1. 준비 (강의 전날)

```bash
git clone https://github.com/choki0715/ETRI_LLM_3days
cd ETRI_LLM_3days
./setup.sh                    # .venv 생성 · 패키지 설치 · .env 생성 · day2 임베딩 모델(약 420MB) 다운로드 · 각 day 점검
# 루트 .env 를 열어 ANTHROPIC_API_KEY 를 넣는다
source .venv/bin/activate     # 모든 day가 이 가상환경 하나를 쓴다
```

`setup.sh`가 하는 일 — 끝에 모두 ○가 나오면 준비 끝입니다.

| 항목 | 내용 |
|---|---|
| 가상환경 | 루트에 `.venv` 하나, `requirements.txt` 하나로 day1 · day2 · day3 패키지를 모두 설치 |
| `common/` 경로 등록 | 어느 폴더에서든 `from common import llm`이 되게 한다 |
| `.env` | 없으면 `.env.example`을 복사해 만든다 — API 키는 직접 채운다 |
| day1 | pytest |
| day2 | 한국어 임베딩 모델(jhgan/ko-sroberta-multitask) 다운로드, pytest |
| day3 | chromium(자동 플레이 테스트용), Claude Code · git · sf-harness 저장소 접근 확인 |

옵션: `--skip-model-download`(임베딩 모델 다운로드 건너뛰기), `--skip-playwright`(chromium 설치 건너뛰기).

- Python 3.10 이상. CPU만으로 돌아갑니다(GPU 필요 없음).
- Windows는 WSL(Ubuntu) 안에서 진행합니다.
- Day 3에는 Claude Code CLI가 필요합니다. `setup.sh`는 설치 여부만 확인합니다 — 설치는 `curl -fsSL https://claude.ai/install.sh | bash` 후 새 터미널에서 `claude`를 실행해 로그인까지 해 둡니다.

## 2. 설정 — `.env`

```bash
ANTHROPIC_API_KEY=sk-ant-...           # 강사가 나눠 준 키
MODEL=claude-haiku-4-5-20251001        # 기본 실습 모델 (빠르고 쌈)
MODEL_ADVANCED=claude-sonnet-5-5       # 고급 모델이 필요한 문항에서만
LLM_MOCK=0                             # 1이면 API를 부르지 않고 흐름만 확인
EMBED=st                               # day2 임베딩 — st(한국어 모델) · hash(테스트용 간이 벡터)
```

모델 이름과 단가(`common/llm.py`의 `PRICES`)는 **강의 당일 쓸 수 있는 모델과 요금표**로 확인해 바꿉니다. `.env`는 `.gitignore`에 걸려 있어 커밋되지 않습니다.

## 3. 폴더

```
ETRI_LLM_3days/
├─ setup.sh              환경 설정 (한 번만)
├─ requirements.txt      day1 · day2 · day3 공용 패키지
├─ .env.example          API 키 · 모델 설정 견본
├─ common/
│  └─ llm.py             모델 호출 · 토큰 세기 · 비용 계산 · 모의 모드 (day1 · day2 공용)
├─ day1/                 프롬프트 엔지니어링 — notebooks/01~03 · src/grade.py · prompts/ · data/tests.jsonl
├─ day2/                 컨텍스트 엔지니어링 — notebooks/01~05 · src/rag.py · qa.py · loop.py · data/kb/
└─ day3/                 바이브 & 하네스 엔지니어링
   ├─ 00_setup/          설치 점검
   ├─ 01_mcp/            MCP 서버 하나 붙이기
   ├─ 02_breakout/       바이브 코딩 · 벽돌깨기
   ├─ 03_sf_harness/     sf-harness 실습 안내 · 과제 · 강사 풀이
   └─ 04_my_harness/     내 하네스 한 장 + 동작하는 뼈대
```

## 4. 하루씩 시작하기

```bash
source .venv/bin/activate

# Day 1 · Day 2 — 노트북
cd day1 && jupyter lab           # notebooks/ 를 순서대로 연다 (day2도 같은 방식)

# Day 3 — 터미널 + Claude Code 채팅창
cd day3 && bash 00_setup/check_env.sh     # 모두 ○ 이면 01_mcp/README.md 부터
```

세션별 시간표 · 실습 순서 · 자주 막히는 곳은 각 day의 README에 있습니다.

## 5. 수강생 코드 원칙

수강생이 읽고 고치는 코드(각 day의 `src/`, 노트북 셀, day3 스크립트 · 훅 · 테스트)는 **중급 이하 눈높이**로 씁니다.

- 컴프리헨션 · 조건 표현식 · `**kwargs` 풀기 · `lambda` 대신 `for` / `if`로 풀어 쓴다
- `r` · `b` 같은 한 글자 대신 `response` · `block`처럼 뜻이 보이는 이름을 쓴다
- 객체가 어디서 만들어지는지 그 파일 안에서 보이게 한다 (전역에 비워 두고 바깥에서 넣지 않는다)
- 응답 객체처럼 눈에 안 보이는 것은 docstring에 실제 모양(예시 값)을 적는다

노트북은 `day*/tools/make_notebooks.py`가 만듭니다. 노트북을 고칠 때는 이 스크립트를 고치고 `python tools/make_notebooks.py`로 다시 만듭니다 — 노트북 파일만 고치면 다음에 다시 만들 때 덮어써집니다.

## 6. 모의 모드 (키 없이 흐름 확인)

`.env`에 `LLM_MOCK=1`을 두면 API를 부르지 않고 고정된 응답을 돌려줍니다. day2는 `EMBED=hash`를 함께 두면 임베딩 모델 없이도 돕니다. **점수는 의미가 없고** 노트북 · 채점 · 결과 저장이 끝까지 도는지만 봅니다 — 강사 리허설과 네트워크가 막힌 강의장 대비용입니다.

## 7. 점검

```bash
source .venv/bin/activate
(cd day1 && python -m pytest tests -q)                    # 14 passed
(cd day2 && EMBED=hash python -m pytest tests -q)         # 8 passed
bash day3/04_my_harness/template/test/run-tests.sh        # 26개 통과
(cd day3/01_mcp && python check_server.py)                # 결과: OK (다른 터미널에서 python hanbit_mcp.py로 서버를 먼저 띄운다)
```

day1 · day2 · day3 테스트는 API 키 없이 돕니다. 노트북은 실제 API로 처음부터 끝까지 돌려 오류 없이 끝나는 것을 확인했습니다. 다만 모델 출력은 실행마다 달라서, 노트북에 적힌 관찰(예: 도구 설명을 잘못 적으면 실패한다)이 수업 중 같은 모양으로 재현되지 않을 수 있습니다. 강의 전에 한 번씩 돌려 봅니다.

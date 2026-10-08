# Day 3 실습 · 바이브 & 하네스 엔지니어링

LLM 기본 & 바이브 코딩 3일 과정 — Day 3 슬라이드(`LLM_basic_Day3.pptx`)와 짝을 이루는 실습 자료입니다.

오늘은 노트북이 아니라 **터미널 + Claude Code 채팅창**에서 실습합니다. 이 폴더는 실습 안내 · 지시 문장 · 체크리스트 · 확인 도구 · 강사 풀이를 담고 있습니다.

## 하루 흐름

| 시간 | 세션 | 실습 | 폴더 |
|---|---|---|---|
| 전날 밤 | 0 준비 | 설치 · 점검 | `00_setup/` |
| 09:00–10:20 | 1 에이전트와 도구 — 툴 콜링에서 MCP까지 | 20분 · MCP 서버 하나 붙이기 | [`01_mcp/`](01_mcp/README.md) |
| 10:30–12:30 | 2 바이브 코딩 · 벽돌깨기 | 80분 · 한 문장 → 플레이 → 하나만 고친다 → 커밋 | [`02_breakout/`](02_breakout/README.md) |
| 13:30–16:30 | 3 하네스 엔지니어링 · sf-harness | 110분 · 설치 · 한 바퀴 · 훅 · 내 손으로 고치기 | [`03_sf_harness/`](03_sf_harness/README.md) |
| 16:40–17:20 | 4 정리 · 나만의 하네스 | 내 하네스 한 장 + 동작하는 뼈대 | [`04_my_harness/`](04_my_harness/README.md) |

세션마다 폴더의 README를 위에서 아래로 따라가면 됩니다. 각 README의 번호가 곧 순서입니다.

## 0. 준비 — 전날 밤

```bash
# 1) Claude Code — 설치 후 새 터미널을 열고 로그인까지
curl -fsSL https://claude.ai/install.sh | bash        # Windows는 WSL(Ubuntu) 안에서
claude

# 2) 실습 저장소 · 공용 가상환경 (mcp · playwright 포함)
git clone https://github.com/choki0715/ETRI_LLM_3days ~/ETRI_LLM_3days
cd ~/ETRI_LLM_3days && ./setup.sh
source .venv/bin/activate

# 3) 점검 — 모두 ○ 이면 끝
bash day3/00_setup/check_env.sh
```

설치 방법은 바뀔 수 있습니다. 강의 전에 공식 문서(code.claude.com/docs)로 한 번 더 확인합니다.

### 경로 약속

오늘 안내의 명령은 아래 두 변수를 씁니다. **터미널을 새로 열 때마다** 먼저 칩니다.

```bash
source ~/ETRI_LLM_3days/.venv/bin/activate
export DAY3=~/ETRI_LLM_3days/day3                      # 이 폴더
export PY=~/ETRI_LLM_3days/.venv/bin/python            # 공용 가상환경의 파이썬 (mcp가 깔린 곳)
```

저장소를 다른 곳에 받았다면 두 줄의 경로만 바꿉니다.

## 세션별 순서 한눈에

**1 · MCP** — `hanbit_mcp.py` 읽기(설명이 곧 도구 설명) → `check_server.py`로 서버 확인 → `claude mcp add` 등록 → 채팅창에서 부르는지 → 설명을 줄여 다시 → 정리

**2 · 벽돌깨기** — 프로젝트 · CLAUDE.md · 첫 커밋 → 1~6회차(한 문장 → 플레이 → 체크리스트 → 커밋, 나빠지면 되돌리기) → 한 번에 시키기 비교 → 실패 하나를 "현상 · 기대 · 재현 · 범위" 지시로 고치기

**3 · sf-harness** — Claude Code 설치 확인 → 플러그인 설치 · LLM 없이 스크립트로 사실 보기 → `/sf-harness:run` 한 바퀴 · 사람이 터미널에서 결정 → 에이전트에게 시켜 훅이 막는지 → 내 clone에서 과제 하나 고치고 테스트 통과

**4 · 나만의 하네스** — 내 업무로 한 장 채우기 → 동작하는 뼈대를 돌려 보기 → (과제) 뼈대를 내 업무로 바꾸기

---

## 강사 메모 · 확인한 것

- `01_mcp` — 서버는 sf-harness 없이 Day 2 한빛정밀 자료(`day2/data/kb`)만 읽는다. mcp 2.2.0에서 `check_server.py`로 도구 목록 · 호출 결과("서울 출장 숙박비 한도" → 출장비 규정 제3조가 1위)를 확인했고, Claude Code 2.1.266에서 `claude mcp add --transport stdio … -- $PY hanbit_mcp.py` 후 `claude mcp list`가 **Connected**
- `02_breakout` — 강사 답안이 자동 플레이 테스트 12개 통과. 일부러 고장 낸 판에서는 패들 이탈 · 모서리 다중 파괴를 잡아냄
- `03_sf_harness` — 풀이 패치 셋이 sf-harness 0.2.0에 그대로 적용되고 테스트 통과 (가: 159 · 나: 166 · 다: 161). 안내의 터미널 명령 결과(CRIT 연속 12 → 17, CONV-01 STALE 45, PRESS-01 FLATLINE)를 실제로 돌려 확인
- `04_my_harness` — 뼈대 테스트 26개 통과, `claude plugin validate` 경고 없이 통과

Claude Code 채팅창 안에서 모델이 실제로 도구를 고르고 스킬을 따르는 부분(LLM 동작)은 이 환경에서 돌려 보지 못했습니다. 강의 전에 한 번씩 돌려 봅니다.

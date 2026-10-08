# Day 3 실습 · 바이브 & 하네스 엔지니어링

LLM 기본 & 바이브 코딩 3일 과정 — Day 3 슬라이드(`LLM_basic_Day3.pptx`)와 짝을 이루는 실습 자료입니다. Day 3 폴더만으로 진행합니다.

오늘은 노트북이 아니라 **Claude Code 안에서** 실습합니다. 이 폴더는 실습 안내 · 지시 문장 · 체크리스트 · 확인 도구 · 강사 풀이를 담고 있습니다.

| 시간 | 세션 | 실습 | 폴더 |
|---|---|---|---|
| 전날 밤 | 준비 | 설치 점검 | `00_setup/` |
| 09:00–10:20 | 1 에이전트와 도구 — 툴 콜링에서 MCP까지 | 20분 · MCP 서버 하나 붙이기 | `01_mcp/` |
| 10:30–12:30 | 2 바이브 코딩 · 벽돌깨기 | 80분 · 한 문장 → 플레이 → 하나만 고친다 → 커밋 | `02_breakout/` |
| 13:30–16:30 | 3 하네스 엔지니어링 · sf-harness | 110분 · 설치 · 한 바퀴 · 훅 · 내 손으로 고치기 | `03_sf_harness/` |
| 16:40–17:20 | 4 정리 · 나만의 하네스 | 15분 · 내 하네스 한 장 + 동작하는 뼈대 | `04_my_harness/` |

## 전날 밤 준비

```bash
curl -fsSL https://claude.ai/install.sh | bash        # Windows는 WSL(Ubuntu) 안에서
# 새 터미널을 열고
claude                                                 # 로그인까지
./setup.sh                                             # 루트에서 — 공용 .venv에 mcp · playwright 설치
source .venv/bin/activate
bash day3/00_setup/check_env.sh                        # 모두 ○ 이면 끝
```

설치 방법은 바뀔 수 있습니다. 강의 전에 공식 문서(code.claude.com/docs)로 한 번 더 확인합니다.

## 확인한 것

- `01_mcp` — mcp 2.2.0에서 `check_server.py`로 서버의 도구 목록 · 호출 결과(170줄, `SF_SIGNALS_OK`)를 확인했고, Claude Code 2.1.266에서 `claude mcp add --transport stdio … -- python3 sf_mcp.py` 후 `claude mcp list`가 **Connected**
- `02_breakout` — 강사 답안이 자동 플레이 테스트 12개 통과. 일부러 고장 낸 판에서는 패들 이탈 · 모서리 다중 파괴를 잡아냄
- `03_sf_harness` — 풀이 패치 셋이 sf-harness 0.2.0에 그대로 적용되고 테스트 통과 (가: 159 · 나: 166 · 다: 161). 안내의 터미널 명령 결과(CRIT 연속 12 → 17, CONV-01 STALE 45, PRESS-01 FLATLINE)를 실제로 돌려 확인
- `04_my_harness` — 뼈대 테스트 26개 통과, `claude plugin validate` 경고 없이 통과

Claude Code 채팅창 안에서 모델이 실제로 도구를 고르고 스킬을 따르는 부분(LLM 동작)은 이 환경에서 돌려 보지 못했습니다. 강의 전에 한 번씩 돌려 봅니다.

# 실습 · 바이브 코딩 — 아타리 벽돌깨기 (블록 2 · 80분)

코드를 안 보는 것이 아니라, **검증 지점을 결과로 옮기는** 연습입니다. 한 문장 → 플레이 → 하나만 고친다 → 커밋.

| 파일 | 쓰임 |
|---|---|
| `CLAUDE.md.example` | 내 환경의 상수 10줄 — 복사해서 고쳐 쓴다 |
| `prompts.md` | 회차별 한 문장 · 한 번에 시키기 비교 · 실패를 지시로 바꾸는 틀 · 되돌리기 · 확장 과제 |
| `checklist.md` | 플레이 테스트 8개 + 회차 기록표 — 인쇄해서 쓴다 |
| `playtest.py` | (선택) 자동 플레이 테스트 — 체크리스트 중 코드로 볼 수 있는 것을 대신 본다 |
| `solution/index.html` | 강사 참고 답안 — 막힌 사람에게 플레이 화면만 보여 준다 |

## 진행

| 시간 | 할 일 |
|---|---|
| 10분 | 프로젝트 세우기 · CLAUDE.md 10줄 · 첫 커밋 |
| 10분 | 한 번에 시키기 비교 실험 (`prompts.md`) |
| 50분 | 1~6회차 — 회차마다 체크리스트를 돌리고 기록표에 한 줄 |
| 10분 | 실패 하나를 골라 "현상 · 기대 · 재현 · 범위" 지시로 고치기 |

```bash
mkdir ~/breakout && cd ~/breakout && git init
cp ~/day3/02_breakout/CLAUDE.md.example CLAUDE.md     # 내 환경에 맞게 고친다 — 10줄 이내
git add -A && git commit -m "CLAUDE.md"
claude                                                 # Shift+Tab 으로 Accept edits 모드
```

CLAUDE.md 점검 — 10줄 이내인가 · 한 달 뒤에도 참인가 · "잘", "적당히"가 없는가 · 옆 사람이 내 환경을 그릴 수 있는가.

## 자동 플레이 테스트 (선택)

```bash
pip install playwright && python3 -m playwright install chromium      # 처음 한 번
python3 ~/day3/02_breakout/playtest.py ~/breakout/index.html
```

- 누구의 게임이든 본다 — 콘솔 에러 · 캔버스 · 키 입력 · 창 크기 (화면을 `playtest_*.png`로 남긴다)
- CLAUDE.md에 아래 한 줄을 넣고 만들면 **체크 1~7까지** 코드가 본다

```
- 테스트용으로 게임 상태를 window.game 에 둔다: paddle{x}, ball{x,y,vx,vy,stuck}, bricks[{x,y,w,h,alive}], score, lives, state(ready·play·over·clear). 스페이스바로 시작 · 재시작
```

이 한 줄이 오후 하네스의 예고편입니다 — **사람이 눈으로 보던 검증을 코드가 볼 수 있게 꺼내 놓는 것.**
자동 테스트가 통과해도 직접 한 판은 합니다. 손맛(속도 · 각도)은 코드가 못 봅니다.

강사 답안으로 돌린 결과 — 통과 12 · 실패 0. 패들 클램프를 빼고 벽돌 충돌의 `break`를 지운 고장판에서는 1번(패들 이탈)과 3번(모서리에서 10개 사라짐)이 실패로 잡혔습니다.

## 강사가 보는 것

산출물 품질이 아니라 **사이클**입니다 — 한 문장씩 넣는가, 회차마다 커밋하는가, 나빠지면 되돌리는가. 큰 지시를 한 번에 넣는 사람을 잡아 줍니다.

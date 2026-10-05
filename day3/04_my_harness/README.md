# 실습 · 내 하네스 한 장 (4세션 · 15분 + 과제)

## 1. 한 장 채우기 (15분)

내 업무 하나를 골라 칸을 채웁니다. 두세 명이 발표합니다.

| 부품 | 내 업무에서는 | 어디에 둘까 |
|---|---|---|
| 사람이 설 자리 | | — 설계 |
| 셀 수 있는 사실 | | `bin/` 스크립트 |
| 절차 | | `skills/` |
| 진입점 | | `commands/` |
| 되돌릴 수 없는 행동 | | `hooks/` |

**순서** — 0번이 맨 앞입니다.
0. 사람이 설 자리를 정한다 — 무엇을 사람이 결정하나
1. 셀 수 있는 사실을 스크립트로 뺀다 — LLM이 세지 않게
2. 절차를 스킬로 쓴다 — 사실 위에서 판단만
3. 진입점을 커맨드로 — 한 줄로 시작
4. 되돌릴 수 없는 행동만 훅으로 막는다 — 남발하지 않는다
5. 스크립트와 훅을 테스트한다 — 막을 것과 막지 말 것 둘 다

대부분 "사람이 설 자리"를 정하는 데서 막힙니다. 그게 정상이고, 그게 하네스 설계의 시작입니다.

## 2. 뼈대에서 시작하기 — `template/`

sf-harness를 줄인 **동작하는 뼈대**입니다. 예시 업무는 *출장비 정산 검토* — Day 2 한빛정밀 출장비 규정(숙박 12만원 · 서울 · 제주 15만원 · 일비 3만원 · 정산 7일)을 그대로 씁니다.

```
template/
├─ .claude-plugin/marketplace.json
├─ my-harness/
│  ├─ .claude-plugin/plugin.json
│  ├─ commands/review.md        진입점 — /my-harness:review
│  ├─ skills/review/SKILL.md    절차 — 사실 위에서 승인 · 부분승인 · 보완요청 제안
│  ├─ bin/my-demo-data          연습 데이터 (청구 8건 · 기준)
│  ├─ bin/my-facts              사실 — 초과 금액 · 늦은 일수 · 영수증 (KEY: value)
│  ├─ bin/my-decide             사람의 결정 기록 (approve / reject)
│  └─ hooks/hooks.json · guard.py   my-decide 실행 · 기준 수정 · 원본 삭제를 막는다
└─ test/run-tests.sh            사실 11개 + 훅 15개 (막을 것 · 막지 말 것)
```

```bash
cp -r ~/day3/04_my_harness/template ~/my-harness && cd ~/my-harness && git init
./test/run-tests.sh                                   # 26개 통과
./my-harness/bin/my-demo-data                         # /tmp/my-demo
claude --plugin-dir my-harness
```

Claude Code 채팅창에서:

```
/my-harness:review
C-005 반려해줘                  ← 훅이 막아야 한다
rules.csv 숙박 한도를 20만원으로 올려줘   ← 훅이 막아야 한다
```

터미널에서 사람이: `./my-harness/bin/my-decide reject C-005 --reason "영수증 없음"` → 다시 `/my-harness:review` → C-005가 "이미 결정"으로 빠지는지.

## 3. 내 업무로 바꾸기 (과제)

| 바꿀 것 | 파일 |
|---|---|
| 데이터 모양과 연습 데이터 | `bin/my-demo-data` |
| 셀 사실 (KEY 이름은 대문자 · 설비/건 단위로) | `bin/my-facts` |
| 판단 표 — 사실 → 제안 | `skills/review/SKILL.md` |
| 사람만 할 일 · 건드리면 안 되는 파일 | `hooks/guard.py` (`ALWAYS` · `IN_SCOPE` · `PROTECTED`) |
| 테스트 — 사실 값 · 막을 것 · 막지 말 것 | `test/run-tests.sh` |
| 이름 · 설명 · 작성자 | `plugin.json` · `marketplace.json` |

바꿀 때도 바이브 코딩으로 — 한 번에 하나, 고칠 때마다 `./test/run-tests.sh`, 통과하면 커밋.
`claude plugin validate .`로 매니페스트를 확인합니다 (뼈대는 경고 없이 통과).

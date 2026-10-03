---
name: review
description: 출장비 정산 청구를 my-facts 사실 위에서 검토해 청구별 승인 · 반려 · 보완요청을 제안하고 reports/review.md에 쓴다. "정산 검토", "출장비 확인", "청구 봐줘" 요청에 사용한다.
---

# 정산 검토 — 제안까지

## 0. 사실을 받는다
`/my-harness:review` 커맨드가 `my-facts` 출력을 붙여 놓았다. 없으면 `${CLAUDE_PLUGIN_ROOT}/bin/my-facts <경로>` 를 부른다.
첫 줄 `MY_FACTS_PROTO: 1`, 마지막 줄 `MY_FACTS_OK` 를 확인한다. `ERROR:` 면 멈추고 알린다.
**금액 · 일수를 네가 다시 계산하지 마라.** 스크립트가 센 값을 그대로 인용한다.

## 1. 청구별 제안

| 사실 | 제안 | 이유 |
|---|---|---|
| `DECIDED: yes` | 제안 없음 | 이미 사람이 결정했다 |
| `RECEIPT: no` | 보완요청 | 증빙 없이 지급하지 않는다. 반려가 아니라 보완 |
| `LODGING_OVER` 또는 `PERDIEM_OVER` > 0 | 부분 승인 (초과분 제외) | 초과 금액을 숫자로 적는다 |
| `LATE_DAYS` > 0 | 승인 + "팀장 사유서 필요" | 기한을 넘긴 정산은 사유서를 첨부한다 |
| 위에 해당 없음 | 승인 | |

## 2. 보고 — reports/review.md 에 쓰고, 화면에도 같은 표

| 청구 | 이름 · 출장지 | 제안 | 근거 (사실 키와 값) |
|---|---|---|---|

마지막에 담당자가 칠 명령을 적는다:
```
my-decide --dir <경로> approve C-001 --reason "..."
my-decide --dir <경로> reject  C-005 --reason "..."
```

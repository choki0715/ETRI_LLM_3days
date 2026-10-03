---
description: 출장비 정산 청구를 검토해 승인 · 반려를 '제안'한다 (결정은 사람이)
argument-hint: [데이터 경로] (생략하면 /tmp/my-demo)
allowed-tools: Bash, Read, Write
---

사실:
!`"${CLAUDE_PLUGIN_ROOT}/bin/my-facts" $ARGUMENTS 2>&1`

---

`review` 스킬을 따라라. 위 사실만 쓰고, CSV를 직접 열어 다시 계산하지 마라.
승인 · 반려는 실행하지 마라. 담당자가 칠 `my-decide` 명령을 적어 주는 것까지가 네 일이다.

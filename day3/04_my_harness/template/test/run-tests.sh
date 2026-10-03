#!/usr/bin/env bash
# 하네스도 코드다 — 스크립트와 훅은 결정적이니 전부 테스트한다.
# 가드레일은 양쪽을 본다: 막아야 할 것이 막히는가, 막지 말아야 할 것이 통과하는가.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$ROOT/my-harness/bin"; GUARD="$ROOT/my-harness/hooks/guard.py"
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "  ○ $1"; }
bad() { FAIL=$((FAIL+1)); echo "  × $1 — 기대 $2, 실제 $3"; }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
D="$TMP/demo"

echo "my-demo-data · my-facts"
"$BIN/my-demo-data" "$D" >/dev/null
OUT="$("$BIN/my-facts" "$D")"
f() { echo "$OUT" | grep -m1 "^$1:" | sed "s/^$1:[[:space:]]*//"; }
chk() { got="$(f "$2")"; [ "$got" = "$3" ] && ok "$1" || bad "$1" "$3" "$got"; }
chk "청구 8건"                       CLAIM_COUNT 8
chk "부산 2박 24만원은 한도 안"      C-001.LODGING_OVER 0
chk "서울은 15만원 한도"            C-002.LODGING_OVER 0
chk "서울 2박 33만원 → 3만원 초과"   C-007.LODGING_OVER 30000
chk "광주 2박 28만원 → 4만원 초과"   C-004.LODGING_OVER 40000
chk "일비 2일 8만원 → 2만원 초과"    C-006.PERDIEM_OVER 20000
chk "12일 만에 청구 → 5일 늦음"      C-003.LATE_DAYS 5
chk "영수증 없음"                    C-005.RECEIPT no
chk "걸린 청구 목록"                 FLAGGED "C-003 C-004 C-005 C-006 C-007"
echo "$OUT" | tail -1 | grep -q MY_FACTS_OK && ok "봉투 끝 줄" || bad "봉투" MY_FACTS_OK "$(echo "$OUT" | tail -1)"
o="$("$BIN/my-facts" "$TMP/none")"; case "$o" in ERROR:*) ok "데이터 없으면 ERROR" ;; *) bad "ERROR" "ERROR:" "$o" ;; esac

echo "guard.py (연습 폴더 안)"
cd "$D"
g() { out="$(python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$3" | python3 "$GUARD")"
      got=$([ -n "$out" ] && echo DENY || echo PASS); [ "$got" = "$2" ] && ok "$1" || bad "$1" "$2" "$got"; }
gf() { out="$(python3 -c 'import json,sys; print(json.dumps({"tool_name":sys.argv[1],"tool_input":{"file_path":sys.argv[2]}}))' "$3" "$4" | python3 "$GUARD")"
       got=$([ -n "$out" ] && echo DENY || echo PASS); [ "$got" = "$2" ] && ok "$1" || bad "$1" "$2" "$got"; }
g  "승인은 사람만"              DENY "my-decide approve C-001 --reason x"
g  "옵션 뒤 반려도 막는다"      DENY "my-decide --dir /tmp/x reject C-005 --reason x"
g  "기준 sed -i 수정"           DENY "sed -i 's/120000/200000/' rules.csv"
g  "기준 덮어쓰기"              DENY "echo x > rules.csv"
g  "원본 삭제"                  DENY "rm claims.csv"
gf "Write 로 기준 편집"         DENY Write "$D/rules.csv"
g  "사실 보기는 통과"           PASS "my-facts ."
g  "기준 읽기는 통과"           PASS "cat rules.csv"
g  "따옴표 안 문자열은 통과"    PASS "echo 'my-decide approve 예시'"
gf "보고서 쓰기는 통과"         PASS Write "$D/reports/review.md"
out="$(echo 'not json' | python3 "$GUARD")"; [ -z "$out" ] && ok "깨진 입력은 통과" || bad "fail-open" PASS DENY

echo "guard.py (연습 폴더 밖 = 남의 저장소)"
cd "$TMP"
g  "우리 명령은 어디서든 막는다"         DENY "my-decide approve C-001 --reason x"
g  "절대 경로로 범위를 안다"             DENY "rm $D/claims.csv"
g  "마커 없는 곳의 rules.csv 는 통과"    PASS "sed -i 's/a/b/' rules.csv"
g  "마커 없는 곳의 claims.csv 는 통과"   PASS "rm claims.csv"

echo; [ "$FAIL" -eq 0 ] && { echo "${PASS}개 통과, 실패 없음"; exit 0; } || { echo "${PASS}개 통과, ${FAIL}개 실패"; exit 1; }

#!/usr/bin/env bash
# 하네스도 코드다 — 스크립트와 훅은 결정적이니 전부 테스트한다.
# 가드레일은 양쪽을 본다: 막아야 할 것이 막히는가, 막지 말아야 할 것이 통과하는가.
#
# 테스트를 더할 때는 아래 세 줄 모양 중 하나를 복사해서 고친다.
#   check_fact "이름"  KEY 기대값                       — my-facts 출력의 KEY 값이 기대값인가
#   guard_bash "이름"  DENY|PASS "명령"                 — 에이전트가 이 Bash 명령을 치면 막히는가
#   guard_file "이름"  DENY|PASS Write|Edit 파일경로     — 에이전트가 이 파일을 편집하면 막히는가
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$ROOT/my-harness/bin"
GUARD="$ROOT/my-harness/hooks/guard.py"
PASS=0
FAIL=0

ok() {
  PASS=$((PASS + 1))
  echo "  ○ $1"
}

bad() {          # bad 이름 기대 실제
  FAIL=$((FAIL + 1))
  echo "  × $1 — 기대 $2, 실제 $3"
}

# 테스트용 임시 폴더 — 끝나면 지운다
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
D="$TMP/demo"

# fact KEY  →  my-facts 출력($OUT)에서 그 KEY의 값만 뽑는다
fact() {
  echo "$OUT" | grep -m1 "^$1:" | sed "s/^$1:[[:space:]]*//"
}

check_fact() {   # check_fact 이름 KEY 기대값
  local name="$1" key="$2" want="$3"
  local got
  got="$(fact "$key")"
  if [ "$got" = "$want" ]; then ok "$name"; else bad "$name" "$want" "$got"; fi
}

# 훅에 넘길 입력(JSON)을 만들어 guard.py에 넣고, 무언가 찍히면 DENY · 아무것도 없으면 PASS
guard_bash() {   # guard_bash 이름 기대(DENY|PASS) 명령
  local name="$1" want="$2" command="$3"
  local input out got
  input="$(python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$command")"
  out="$(echo "$input" | python3 "$GUARD")"
  if [ -n "$out" ]; then got=DENY; else got=PASS; fi
  if [ "$got" = "$want" ]; then ok "$name"; else bad "$name" "$want" "$got"; fi
}

guard_file() {   # guard_file 이름 기대(DENY|PASS) 도구(Write|Edit) 파일경로
  local name="$1" want="$2" tool="$3" file="$4"
  local input out got
  input="$(python3 -c 'import json,sys; print(json.dumps({"tool_name":sys.argv[1],"tool_input":{"file_path":sys.argv[2]}}))' "$tool" "$file")"
  out="$(echo "$input" | python3 "$GUARD")"
  if [ -n "$out" ]; then got=DENY; else got=PASS; fi
  if [ "$got" = "$want" ]; then ok "$name"; else bad "$name" "$want" "$got"; fi
}


echo "my-demo-data · my-facts"
"$BIN/my-demo-data" "$D" >/dev/null
OUT="$("$BIN/my-facts" "$D")"
check_fact "청구 8건"                       CLAIM_COUNT 8
check_fact "부산 2박 24만원은 한도 안"      C-001.LODGING_OVER 0
check_fact "서울은 15만원 한도"            C-002.LODGING_OVER 0
check_fact "서울 2박 33만원 → 3만원 초과"   C-007.LODGING_OVER 30000
check_fact "광주 2박 28만원 → 4만원 초과"   C-004.LODGING_OVER 40000
check_fact "일비 2일 8만원 → 2만원 초과"    C-006.PERDIEM_OVER 20000
check_fact "12일 만에 청구 → 5일 늦음"      C-003.LATE_DAYS 5
check_fact "영수증 없음"                    C-005.RECEIPT no
check_fact "걸린 청구 목록"                 FLAGGED "C-003 C-004 C-005 C-006 C-007"

last_line="$(echo "$OUT" | tail -1)"
if [ "$last_line" = "MY_FACTS_OK" ]; then ok "봉투 끝 줄"; else bad "봉투" MY_FACTS_OK "$last_line"; fi

no_data="$("$BIN/my-facts" "$TMP/none")"
case "$no_data" in
  ERROR:*) ok "데이터 없으면 ERROR" ;;
  *)       bad "ERROR" "ERROR:" "$no_data" ;;
esac


echo "guard.py (연습 폴더 안)"
cd "$D"
guard_bash "승인은 사람만"              DENY "my-decide approve C-001 --reason x"
guard_bash "옵션 뒤 반려도 막는다"      DENY "my-decide --dir /tmp/x reject C-005 --reason x"
guard_bash "기준 sed -i 수정"           DENY "sed -i 's/120000/200000/' rules.csv"
guard_bash "기준 덮어쓰기"              DENY "echo x > rules.csv"
guard_bash "원본 삭제"                  DENY "rm claims.csv"
guard_file "Write 로 기준 편집"         DENY Write "$D/rules.csv"
guard_bash "사실 보기는 통과"           PASS "my-facts ."
guard_bash "기준 읽기는 통과"           PASS "cat rules.csv"
guard_bash "따옴표 안 문자열은 통과"    PASS "echo 'my-decide approve 예시'"
guard_file "보고서 쓰기는 통과"         PASS Write "$D/reports/review.md"

broken_input="$(echo 'not json' | python3 "$GUARD")"
if [ -z "$broken_input" ]; then ok "깨진 입력은 통과"; else bad "fail-open" PASS DENY; fi


echo "guard.py (연습 폴더 밖 = 남의 저장소)"
cd "$TMP"
guard_bash "우리 명령은 어디서든 막는다"         DENY "my-decide approve C-001 --reason x"
guard_bash "절대 경로로 범위를 안다"             DENY "rm $D/claims.csv"
guard_bash "마커 없는 곳의 rules.csv 는 통과"    PASS "sed -i 's/a/b/' rules.csv"
guard_bash "마커 없는 곳의 claims.csv 는 통과"   PASS "rm claims.csv"


echo
if [ "$FAIL" -eq 0 ]; then
  echo "${PASS}개 통과, 실패 없음"
  exit 0
else
  echo "${PASS}개 통과, ${FAIL}개 실패"
  exit 1
fi

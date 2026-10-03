#!/usr/bin/env bash
# ETRI LLM 3일 과정 — 환경 설정 (가상환경 하나 · requirements.txt 하나 · .env 하나)
#
#   ./setup.sh                          # 전체
#   ./setup.sh --skip-model-download    # day2 임베딩 모델(약 470MB) 다운로드 건너뛰기
#   ./setup.sh --skip-playwright        # day3 자동 플레이 테스트용 chromium 설치 건너뛰기
#
# 루트에 .venv 하나를 만들고 requirements.txt 하나로 day1·day2·day3 패키지를 모두 설치합니다.
# API 키는 루트 .env 하나에 넣습니다 (common/llm.py가 읽습니다).
# Claude Code CLI 자체는 설치하지 않고 있는지만 확인합니다.

set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$ROOT/.venv/bin/python"

FAIL=0
ok()   { echo "  ○ $1"; }
bad()  { echo "  × $1"; [ -n "${2:-}" ] && echo "      → $2"; FAIL=1; }
info() { echo "  - $1"; }

SKIP_MODEL_DOWNLOAD=0
SKIP_PLAYWRIGHT=0
for arg in "$@"; do
  case "$arg" in
    --skip-model-download) SKIP_MODEL_DOWNLOAD=1 ;;
    --skip-playwright) SKIP_PLAYWRIGHT=1 ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "알 수 없는 인자: $arg"; exit 1 ;;
  esac
done

echo "== 가상환경 (.venv) =="
if [ ! -d "$ROOT/.venv" ]; then
  python3 -m venv "$ROOT/.venv" && ok ".venv 생성" || { bad ".venv 생성 실패"; exit 1; }
else
  ok ".venv 이미 있음"
fi
info "requirements.txt 설치 중 (torch 포함 — 처음엔 몇 분 걸림)"
"$ROOT/.venv/bin/pip" install -q -r "$ROOT/requirements.txt" \
  && ok "requirements.txt 설치" || bad "pip install 실패"
# 어느 폴더에서든 `from common import llm` 이 되도록 루트를 가상환경 경로에 등록
SITE="$("$PY" -c 'import site; print(site.getsitepackages()[0])')"
echo "$ROOT" > "$SITE/etri_llm_3days.pth" && ok "common/ 경로 등록 (from common import llm)"

echo
echo "== .env =="
if [ ! -e "$ROOT/.env" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env" && ok ".env 생성 — ANTHROPIC_API_KEY를 직접 채워야 함"
else
  ok ".env 이미 있음"
fi

echo
echo "== day1 =="
(cd "$ROOT/day1" && "$PY" -m pytest tests -q) >/tmp/day1_test.log 2>&1 \
  && ok "pytest 통과" || bad "pytest 실패" "cat /tmp/day1_test.log"

echo
echo "== day2 =="
if [ "$SKIP_MODEL_DOWNLOAD" = "1" ]; then
  info "임베딩 모델 다운로드 건너뜀 — 필요하면 .env 에 EMBED=hash"
else
  (cd "$ROOT/day2" && "$PY" tools/download_model.py) \
    && ok "임베딩 모델 다운로드" || bad "임베딩 모델 다운로드 실패" "인터넷이 막혔다면 .env 에 EMBED=hash"
fi
(cd "$ROOT/day2" && EMBED=hash "$PY" -m pytest tests -q) >/tmp/day2_test.log 2>&1 \
  && ok "pytest 통과" || bad "pytest 실패" "cat /tmp/day2_test.log"

echo
echo "== day3 =="
if [ "$SKIP_PLAYWRIGHT" = "1" ]; then
  info "chromium 설치 건너뜀 — 02_breakout 자동 플레이 테스트는 못 돌림"
else
  "$PY" -m playwright install chromium >/dev/null 2>&1 \
    && ok "chromium 설치 (playwright)" || bad "chromium 설치 실패 (선택 사항)" "건너뛰려면 --skip-playwright"
fi
command -v claude >/dev/null && ok "Claude Code $(claude --version 2>/dev/null | head -1)" \
  || bad "Claude Code 없음" "curl -fsSL https://claude.ai/install.sh | bash  (새 터미널에서 'claude' 실행해 로그인)"
command -v git >/dev/null && ok "git $(git --version | awk '{print $3}')" || bad "git 없음" "sudo apt install -y git"
git config user.name >/dev/null 2>&1 && ok "git 사용자 이름 설정됨" \
  || bad "git 사용자 이름 없음" 'git config --global user.name "이름"; git config --global user.email "메일"'
git ls-remote https://github.com/choki0715/sf-harness >/dev/null 2>&1 \
  && ok "sf-harness 저장소 접근" || bad "sf-harness 저장소에 닿지 않음" "네트워크 · 프록시 확인"

echo
[ "$FAIL" -eq 0 ] && echo "모두 준비 끝." || echo "× 항목을 고친 뒤 다시 실행하세요."
echo
echo "사용법:"
echo "  source .venv/bin/activate        # 모든 day가 이 가상환경 하나를 씁니다"
echo "  cd day1 && jupyter lab           # day2도 같은 방식"
echo "  day3 MCP: claude mcp add --transport stdio sf -- $PY $ROOT/day3/01_mcp/sf_mcp.py"
exit $FAIL

#!/usr/bin/env bash
# Day 3 준비 점검 — 강의 전날 밤에 한 번. 모두 ○ 이면 준비 끝.
#   bash 00_setup/check_env.sh
ok()  { echo "  ○ $1"; }
bad() { echo "  × $1"; echo "      → $2"; FAIL=1; }
FAIL=0
echo "Day 3 준비 점검"

command -v claude >/dev/null && ok "Claude Code $(claude --version 2>/dev/null | head -1)" \
  || bad "Claude Code 없음" "curl -fsSL https://claude.ai/install.sh | bash  (설치 뒤 새 터미널)"
command -v git >/dev/null && ok "git $(git --version | awk '{print $3}')" || bad "git 없음" "sudo apt install -y git"
git config user.name >/dev/null && ok "git 사용자 이름 설정됨" || bad "git 사용자 이름 없음" 'git config --global user.name "이름"; git config --global user.email "메일"'
command -v python3 >/dev/null && ok "python3 $(python3 -c 'import sys;print(sys.version.split()[0])')" || bad "python3 없음" "sudo apt install -y python3 python3-pip"
python3 -c "import mcp" 2>/dev/null && ok "mcp 패키지" || bad "mcp 패키지 없음 (블록 1)" "pip install mcp   (Ubuntu 시스템 파이썬이면 --break-system-packages 또는 venv)"
python3 -c "import playwright" 2>/dev/null && ok "playwright (선택 · 자동 플레이 테스트)" || echo "  – playwright 없음 — 선택 사항: pip install playwright && python3 -m playwright install chromium"
if git ls-remote https://github.com/choki0715/sf-harness >/dev/null 2>&1; then ok "github.com/choki0715/sf-harness 접근"; else bad "sf-harness 저장소에 닿지 않음" "네트워크 · 프록시 확인"; fi
case "$(uname -s)" in
  Linux|Darwin) ok "OS $(uname -s)" ;;
  *) bad "OS $(uname -s)" "Windows는 WSL(Ubuntu) 안에서 진행합니다" ;;
esac
echo
[ "$FAIL" -eq 0 ] && echo "준비 끝. claude 를 한 번 실행해 로그인까지 해 둡니다." || echo "× 항목을 고친 뒤 다시 돌립니다."

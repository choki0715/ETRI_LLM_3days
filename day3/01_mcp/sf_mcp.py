"""sf-plant MCP 서버 — sf-harness의 sf-signals를 MCP 도구 하나로 감싼다 (Day 3 1세션 실습).

    pip install mcp                      # mcp 2.x
    claude mcp add --transport stdio sf-plant -- python3 /절대/경로/sf_mcp.py
    (Claude Code 안에서) /mcp  → sf-plant · Connected

관찰 실험: 도구 설명을 짧게 바꿔 등록하면 모델이 언제 부르는지가 달라진다.
    claude mcp add --transport stdio sf-plant-short --env SF_MCP_DESC=short -- python3 /절대/경로/sf_mcp.py

파일 순서
    1. 도구 설명       — LONG / SHORT (모델이 읽고 언제 부를지 정하는 글)
    2. sf-signals 찾기  — find_sf_signals (실제 일을 하는 스크립트의 위치)
    3. 도구           — signals (모델이 부르면 sf-signals를 실행해 결과를 돌려준다)
"""
import glob
import os
import shutil
import subprocess

from mcp.server.mcpserver import MCPServer

DEFAULT_PLANT = "/tmp/sf-demo"          # 가상 플랜트 폴더 (sf-demo-data가 만든다)


# ================================================================ 1. 도구 설명 — 모델이 읽는 것
LONG = """설비 4대(CNC-01 · CNC-02 · PRESS-01 · CONV-01)의 센서 사실을 KEY: value 줄로 돌려준다.
설비 상태 · 센서 추세 · 연속 초과 · 데이터 끊김 · 정비 경과일을 물을 때 쓴다.
판단은 하지 않는다 — 값만 돌려준다. plant는 가상 플랜트 경로(생략하면 /tmp/sf-demo)."""

SHORT = "설비 정보"

# 환경변수 SF_MCP_DESC=short 로 등록하면 짧은 설명을 쓴다 (관찰 실험용)
if os.environ.get("SF_MCP_DESC") == "short":
    DESCRIPTION = SHORT
else:
    DESCRIPTION = LONG


# ================================================================ 2. sf-signals 찾기
def find_sf_signals():
    """sf-signals 실행 파일의 경로를 돌려준다. 못 찾으면 None.

    찾는 순서: SF_BIN 환경변수 → PATH → 설치한 플러그인 → 옆에 clone한 저장소
    """
    candidates = []

    # 1) SF_BIN 환경변수에 bin 폴더를 적어 두었으면 거기
    sf_bin = os.environ.get("SF_BIN")
    if sf_bin:
        candidates.append(os.path.join(sf_bin, "sf-signals"))

    # 2) PATH에 있으면 거기
    on_path = shutil.which("sf-signals")
    if on_path:
        candidates.append(on_path)

    # 3) Claude Code에 설치한 플러그인 — 버전 폴더가 여럿이면 최신(이름 역순 첫째)부터
    plugin_pattern = os.path.expanduser("~/.claude/plugins/cache/sf-harness/sf-harness/*/bin/sf-signals")
    for path in sorted(glob.glob(plugin_pattern), reverse=True):
        candidates.append(path)

    # 4) clone한 저장소 — 이 파일 옆, 또는 홈 폴더
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(here, "..", "sf-harness", "sf-harness", "bin", "sf-signals"))
    candidates.append(os.path.expanduser("~/sf-harness/sf-harness/bin/sf-signals"))

    # 후보 중 실제로 있고 실행할 수 있는 첫 번째
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


# ================================================================ 3. 도구 — 모델이 부르면 우리 코드가 실행한다
mcp = MCPServer("sf-plant")


@mcp.tool(description=DESCRIPTION)
def signals(plant: str = DEFAULT_PLANT) -> str:
    """도구 이름은 함수 이름(signals), 입력 스키마는 인자와 타입 힌트(plant: str)에서 만들어진다."""
    exe = find_sf_signals()
    if exe is None:
        return ("ERROR: sf-signals를 찾지 못했다. sf-harness 플러그인을 설치하거나 "
                "SF_BIN 환경변수에 bin 폴더 경로를 넣는다.")

    result = subprocess.run([exe, plant], capture_output=True, text=True, timeout=30)
    if result.stdout:
        return result.stdout          # 정상 — KEY: value 줄들
    return result.stderr              # 출력이 없으면 에러 메시지라도 돌려준다


# 승인 · 정지 같은 '쓰는' 도구는 일부러 만들지 않는다.
# 되돌릴 수 없는 행동은 MCP로 노출하지 않고 사람에게 남긴다.

if __name__ == "__main__":
    mcp.run()          # 기본은 stdio — Claude Code가 이 프로그램을 띄우고 표준 입출력으로 대화한다

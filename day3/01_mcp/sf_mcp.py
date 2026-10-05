"""sf-plant MCP 서버 — sf-harness의 sf-signals를 MCP 도구 하나로 감싼다 (Day 3 1세션 실습).

    pip install mcp
    claude mcp add --transport stdio sf-plant -- python3 /절대/경로/sf_mcp.py
    (Claude Code 안에서) /mcp  → sf-plant · Connected

관찰 실험: 도구 설명을 짧게 바꿔 등록하면 모델이 언제 부르는지가 달라진다.
    claude mcp add --transport stdio sf-plant-short --env SF_MCP_DESC=short -- python3 /절대/경로/sf_mcp.py
"""
import glob
import os
import shutil
import subprocess

from mcp.server.fastmcp import FastMCP

DEFAULT_PLANT = "/tmp/sf-demo"

LONG = """설비 4대(CNC-01 · CNC-02 · PRESS-01 · CONV-01)의 센서 사실을 KEY: value 줄로 돌려준다.
설비 상태 · 센서 추세 · 연속 초과 · 데이터 끊김 · 정비 경과일을 물을 때 쓴다.
판단은 하지 않는다 — 값만 돌려준다. plant는 가상 플랜트 경로(생략하면 /tmp/sf-demo)."""
SHORT = "설비 정보"

mcp = FastMCP("sf-plant")


def find_sf_signals() -> str | None:
    """sf-signals 위치: SF_BIN 환경변수 → PATH → 설치한 플러그인 → 옆에 clone한 저장소."""
    candidates = []
    if os.environ.get("SF_BIN"):
        candidates.append(os.path.join(os.environ["SF_BIN"], "sf-signals"))
    if shutil.which("sf-signals"):
        candidates.append(shutil.which("sf-signals"))
    candidates += sorted(glob.glob(os.path.expanduser(
        "~/.claude/plugins/cache/sf-harness/sf-harness/*/bin/sf-signals")), reverse=True)
    here = os.path.dirname(os.path.abspath(__file__))
    candidates += [os.path.join(here, "..", "sf-harness", "sf-harness", "bin", "sf-signals"),
                   os.path.expanduser("~/sf-harness/sf-harness/bin/sf-signals")]
    for c in candidates:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


@mcp.tool(description=SHORT if os.environ.get("SF_MCP_DESC") == "short" else LONG)
def signals(plant: str = DEFAULT_PLANT) -> str:
    exe = find_sf_signals()
    if not exe:
        return ("ERROR: sf-signals를 찾지 못했다. sf-harness 플러그인을 설치하거나 "
                "SF_BIN 환경변수에 bin 폴더 경로를 넣는다.")
    out = subprocess.run([exe, plant], capture_output=True, text=True, timeout=30)
    return out.stdout or out.stderr


# 승인 · 정지 같은 '쓰는' 도구는 일부러 만들지 않는다.
# 되돌릴 수 없는 행동은 MCP로 노출하지 않고 사람에게 남긴다.

if __name__ == "__main__":
    mcp.run()          # 기본은 stdio

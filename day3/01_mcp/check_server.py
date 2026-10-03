"""Claude Code 없이 sf_mcp.py가 제대로 도는지 확인한다 — MCP 클라이언트로 붙어 도구 목록을 보고 한 번 부른다.

    python3 check_server.py                 # 기본 설명
    SF_MCP_DESC=short python3 check_server.py
"""
import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = os.path.dirname(os.path.abspath(__file__))


async def main(plant: str):
    params = StdioServerParameters(command=sys.executable, args=[os.path.join(HERE, "sf_mcp.py")],
                                   env={**os.environ})
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            info = await s.initialize()
            print("서버:", info.serverInfo.name)
            tools = (await s.list_tools()).tools
            for t in tools:
                print(f"도구: {t.name}\n  설명: {t.description}\n  입력: {t.inputSchema}")
            res = await s.call_tool("signals", {"plant": plant})
            text = "".join(c.text for c in res.content if getattr(c, "type", "") == "text")
            lines = text.splitlines()
            print(f"\n호출 결과 {len(lines)}줄 — 앞부분:")
            print("\n".join(lines[:12]))
            ok = text.startswith("SF_SIGNALS_PROTO") and "SF_SIGNALS_OK" in text
            print("\n결과:", "OK — Claude Code에 등록해도 된다" if ok else "확인 필요 — 위 메시지를 본다")
            return ok


if __name__ == "__main__":
    plant = sys.argv[1] if len(sys.argv) > 1 else "/tmp/sf-demo"
    sys.exit(0 if asyncio.run(main(plant)) else 1)

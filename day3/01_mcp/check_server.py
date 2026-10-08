"""Claude Code 없이 hanbit_mcp.py가 제대로 도는지 확인한다 — MCP 클라이언트로 붙어 도구 목록을 보고 한 번 부른다.

    python3 check_server.py                          # 기본 질문으로
    python3 check_server.py "회의실 예약 횟수"         # 내 질문으로
    MCP_DESC=short python3 check_server.py           # 짧은 설명판

Claude Code가 MCP 서버에 붙을 때 하는 일을 그대로 따라 한다.
    1. 서버 프로그램(hanbit_mcp.py)을 띄우고 표준 입출력으로 연결한다
    2. 인사(initialize) — 서버 이름을 받는다
    3. 도구 목록(list_tools) — 이름 · 설명 · 입력 스키마를 받는다. 모델이 보는 것이 이것이다
    4. 도구 호출(call_tool) — search_docs를 한 번 불러 결과를 받는다
"""
import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = os.path.dirname(os.path.abspath(__file__))


async def main(query):
    # 1. 서버 프로그램을 띄울 명령 — 지금 쓰는 파이썬으로 hanbit_mcp.py를 실행한다
    server_file = os.path.join(HERE, "hanbit_mcp.py")
    params = StdioServerParameters(command=sys.executable, args=[server_file], env=dict(os.environ))

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # 2. 인사
            info = await session.initialize()
            print("서버:", info.server_info.name)

            # 3. 도구 목록 — 모델은 이 설명만 보고 도구를 고른다
            tool_list = await session.list_tools()
            for tool in tool_list.tools:
                print(f"도구: {tool.name}")
                print(f"  설명: {tool.description}")
                print(f"  입력: {tool.input_schema}")

            # 4. 도구 호출
            print(f"\n호출: search_docs(query={query!r})")
            result = await session.call_tool("search_docs", {"query": query})
            text = ""
            for content in result.content:
                if content.type == "text":
                    text += content.text
            print(text)

            # 출처가 달린 자료가 하나라도 오면 정상이다
            ok = '<자료 번호="1"' in text
            if ok:
                print("결과: OK — Claude Code에 등록해도 된다")
            else:
                print("결과: 확인 필요 — 위 메시지를 본다")
            return ok


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = "서울 출장 숙박비 한도"
    ok = asyncio.run(main(query))
    if ok:
        sys.exit(0)
    sys.exit(1)

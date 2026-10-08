"""hanbit-docs MCP 서버에 접속하는 클라이언트 — Claude Code 대신 도구 목록을 보고 한 번 부른다.

서버(hanbit_mcp.py)를 다른 터미널에서 먼저 띄워 둔다.

    # 터미널 1
    python hanbit_mcp.py

    # 터미널 2
    python check_server.py                          # 기본 질문으로
    python check_server.py "회의실 예약 횟수"         # 내 질문으로

Claude Code가 MCP 서버에 붙을 때 하는 일을 그대로 따라 한다.
    1. 서버 주소(http://127.0.0.1:9800/mcp)로 접속한다
    2. 인사(initialize) — 서버 이름을 받는다
    3. 도구 목록(list_tools) — 이름 · 설명 · 입력 스키마를 받는다. 모델이 보는 것이 이것이다
    4. 도구 호출(call_tool) — search_docs를 한 번 불러 결과를 받는다
"""
import asyncio
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

SERVER_URL = "http://127.0.0.1:9800/mcp"       # hanbit_mcp.py의 HOST · PORT와 같아야 한다


async def main(query):
    # 1. 서버에 접속한다 — 서버는 이미 떠 있어야 한다
    async with streamable_http_client(SERVER_URL) as (read_stream, write_stream):
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

    try:
        ok = asyncio.run(main(query))
    except Exception as error:
        # 서버가 안 떠 있으면 접속 단계에서 실패한다
        print(f"서버에 접속하지 못했다 — {SERVER_URL}")
        print("다른 터미널에서 서버를 먼저 띄운다:  python hanbit_mcp.py")
        print(f"(오류: {type(error).__name__})")
        sys.exit(1)

    if ok:
        sys.exit(0)
    sys.exit(1)

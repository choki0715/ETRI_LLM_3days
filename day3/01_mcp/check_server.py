"""hanbit-docs MCP 서버에 접속하는 클라이언트 — 검색어를 직접 넣어 가며 도구를 불러 본다 (모델 없음).

서버(hanbit_mcp.py)를 다른 터미널에서 먼저 띄워 둔다.

    # 터미널 1
    python hanbit_mcp.py

    # 터미널 2
    python check_server.py                          # 검색어를 계속 입력 (빈 줄이면 끝, "계산 1.2 * 10"이면 계산기)
    python check_server.py "서울 출장 숙박비 한도"     # 한 번만 부르고 끝 (점검용)

Claude Code가 MCP 서버에 붙을 때 하는 일을 그대로 따라 한다.
    1. 서버 주소(http://127.0.0.1:9800/mcp)로 접속한다
    2. 인사(initialize) — 서버 이름을 받는다
    3. 도구 목록(list_tools) — 이름 · 설명 · 입력 스키마를 받는다. 모델이 보는 것이 이것이다
    4. 도구 호출(call_tool) — 내가 넣은 검색어로 search_docs를, "계산 …"이면 calculator를 부른다
여기서는 어떤 도구를 무슨 값으로 부를지 사람이 정한다. 모델이 정하게 하는 것은 mcp_client.py.
"""
import asyncio
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

SERVER_URL = "http://127.0.0.1:9800/mcp"       # hanbit_mcp.py의 HOST · PORT와 같아야 한다


def root_error(error):
    """async 코드의 오류는 ExceptionGroup에 싸여 온다 — 맨 안쪽의 진짜 오류를 꺼낸다."""
    while isinstance(error, BaseExceptionGroup):
        error = error.exceptions[0]
    return error


async def call_search(session, query):
    """search_docs를 한 번 부르고 결과를 찍는다. 출처가 달린 자료가 왔으면 True."""
    print(f"\n호출: search_docs(query={query!r})")
    result = await session.call_tool("search_docs", {"query": query})
    text = ""
    for content in result.content:
        if content.type == "text":
            text += content.text
    print(text)
    return '<자료 번호="1"' in text


OPERATORS = {"+": "add", "-": "sub", "*": "mul", "/": "div"}       # 기호 → calculator의 op


async def call_calculator(session, text):
    """"1.2 * 10" 같은 글을 잘라 calculator를 부른다. 모양이 틀리면 알려 주고 False."""
    parts = text.split()                         # ["1.2", "*", "10"]
    if len(parts) != 3 or parts[1] not in OPERATORS:
        print("계산은 '계산 숫자 기호 숫자' 모양으로 — 예: 계산 1.2 * 10   (기호: + - * /)")
        return False
    try:
        a = float(parts[0])
        b = float(parts[2])
    except ValueError:
        print("숫자 자리에 숫자가 아니다 — 예: 계산 1.2 * 10")
        return False
    op = OPERATORS[parts[1]]
    print(f"\n호출: calculator(a={a}, b={b}, op={op!r})")
    result = await session.call_tool("calculator", {"a": a, "b": b, "op": op})
    for content in result.content:
        if content.type == "text":
            print("결과:", content.text)
    return True


async def main(queries):
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

            # 4-가. 검색어를 인자로 줬으면 — 한 번만 부르고 끝 (점검용)
            if len(queries) > 0:
                ok = await call_search(session, queries[0])
                if ok:
                    print("결과: OK — 서버가 제대로 돈다")
                else:
                    print("결과: 확인 필요 — 위 메시지를 본다")
                return ok

            # 4-나. 검색어를 계속 입력받는다 — 빈 줄이면 끝
            print("\n검색어를 넣으면 search_docs를, '계산 1.2 * 10'처럼 넣으면 calculator를 부른다.")
            print("서버 터미널에 [호출] 줄이 찍히는지도 본다.")
            print("예: 서울 출장 숙박비 한도 · 회의실 예약 횟수 · AX-2041 무게 · 점심 메뉴 · 계산 1.2 * 10")
            while True:
                # input()은 기다리는 동안 프로그램 전체를 멈추게 하므로, 따로 떼어 기다린다
                query = await asyncio.to_thread(input, "\n검색어 (끝내려면 엔터): ")
                query = query.strip()
                if query == "":
                    print("끝")
                    return True
                if query.startswith("계산"):
                    await call_calculator(session, query[len("계산"):].strip())
                    continue
                found = await call_search(session, query)
                if not found:
                    print("(찾은 문단이 없다 — 문서에 쓰였을 법한 말로 바꿔 본다)")


if __name__ == "__main__":
    queries = sys.argv[1:]
    try:
        ok = asyncio.run(main(queries))
    except (KeyboardInterrupt, EOFError):
        print("\n끝")
        sys.exit(0)
    except Exception as error:
        error = root_error(error)
        if isinstance(error, (KeyboardInterrupt, EOFError)):
            print("\n끝")
            sys.exit(0)
        if "Connect" in type(error).__name__:           # 서버가 안 떠 있으면 ConnectError
            print(f"서버에 접속하지 못했다 — {SERVER_URL}")
            print("다른 터미널에서 서버를 먼저 띄운다:  python hanbit_mcp.py")
        else:
            print(f"오류: {type(error).__name__}: {error}")
        sys.exit(1)

    if ok:
        sys.exit(0)
    sys.exit(1)

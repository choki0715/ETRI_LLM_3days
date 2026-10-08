"""hanbit-docs MCP 서버를 쓰는 파이썬 클라이언트 — 모델(Claude API)이 도구를 고르고, 도구 실행은 MCP 서버가 한다.

서버(hanbit_mcp.py)를 다른 터미널에서 먼저 띄워 둔다.

    # 터미널 1
    python hanbit_mcp.py

    # 터미널 2
    python mcp_client.py "서울로 출장 가면 숙박비는 하루 얼마까지 나와?"     # 질문 하나
    python mcp_client.py                                                   # 질문을 계속 입력 (빈 줄이면 끝)

Day 2 loop.py와 같은 루프다 — 모델 호출 → 도구 요청이면 실행 → 결과를 붙여 다시 모델 호출.
다른 점은 딱 하나:
    loop.py        도구 정의(TOOLS)를 파일에 직접 적고, 도구도 우리 코드(call_tool)가 실행했다
    mcp_client.py  도구 정의를 MCP 서버에서 받아 오고(list_tools), 실행도 서버에 부탁한다(call_tool)
Claude Code가 MCP 서버를 쓸 때 속에서 하는 일이 바로 이것이다.

API 키는 루트 .env 의 ANTHROPIC_API_KEY 를 쓴다 (Day 1 · 2와 같다).
"""
import asyncio
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from common import llm

SERVER_URL = "http://127.0.0.1:9800/mcp"       # hanbit_mcp.py의 HOST · PORT와 같아야 한다
MAX_ATTEMPTS = 5                               # 모델을 최대 몇 번 부를지


def mcp_tools_to_claude_tools(mcp_tools):
    """MCP 서버의 도구 목록을 Claude API의 tools 형식으로 바꾼다.

    MCP 도구        tool.name · tool.description · tool.input_schema
    Claude API     {"name": ..., "description": ..., "input_schema": ...}   — 이름만 같은 세 칸
    """
    tools = []
    for tool in mcp_tools:
        tools.append({
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        })
    return tools


async def ask(session, tools, question):
    """질문 하나에 답한다. 모델이 도구를 요청하면 MCP 서버에 실행을 부탁한다."""
    messages = [{"role": "user", "content": question}]

    for attempt in range(MAX_ATTEMPTS):
        # ① 모델을 부른다 — 서버에서 받아 온 도구 정의를 함께 보낸다
        response = llm.client().messages.create(model=llm.MODEL, max_tokens=800,
                                                tools=tools, messages=messages)

        # ② 도구 요청이 없으면 답을 다 낸 것
        if response.stop_reason != "tool_use":
            answer = ""
            for block in response.content:
                if block.type == "text":
                    answer += block.text
            print(f"[{attempt}] 종료")
            return answer

        # ③ 도구 요청이 있으면 — 모델의 응답을 대화 기록에 붙이고
        messages.append({"role": "assistant", "content": response.content})

        # ④ 요청된 도구를 MCP 서버에 실행해 달라고 한다
        tool_results = []
        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(f"[{attempt}] 모델: {block.text.strip()[:80]}")
            if block.type == "tool_use":
                print(f"[{attempt}] 도구 요청: {block.name} {block.input}  → MCP 서버에 call_tool")
                result = await session.call_tool(block.name, block.input)       # 실행은 서버가 한다
                text = ""
                for content in result.content:
                    if content.type == "text":
                        text += content.text
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": text,
                })

        # ⑤ 결과를 붙인다 — 다음 시도에서 모델이 읽는다
        messages.append({"role": "user", "content": tool_results})

    return "(최대 반복 도달)"


def root_error(error):
    """async 코드의 오류는 ExceptionGroup에 싸여 온다 — 맨 안쪽의 진짜 오류를 꺼낸다."""
    while isinstance(error, BaseExceptionGroup):
        error = error.exceptions[0]
    return error


async def main(questions):
    async with streamable_http_client(SERVER_URL) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            info = await session.initialize()

            # 서버에서 도구 목록을 받아 온다 — 도구 정의를 이 파일에 적지 않는다
            tool_list = await session.list_tools()
            tools = mcp_tools_to_claude_tools(tool_list.tools)
            print(f"서버 {info.server_info.name} 에 접속 — 받아 온 도구:")
            for tool in tools:
                print(f"  {tool['name']}: {tool['description'].splitlines()[0][:60]}")
            print(f"모델: {llm.MODEL}")

            if len(questions) > 0:
                for question in questions:
                    print("=" * 70)
                    print("Q", question)
                    answer = await ask(session, tools, question)
                    print("A", answer)
                return

            # 질문을 주지 않았으면 계속 입력받는다
            while True:
                print("=" * 70)
                # input()은 기다리는 동안 프로그램 전체를 멈추게 하므로, 따로 떼어 기다린다
                question = await asyncio.to_thread(input, "질문 (끝내려면 엔터): ")
                question = question.strip()
                if question == "":
                    print("끝")
                    break
                answer = await ask(session, tools, question)
                print("A", answer)


if __name__ == "__main__":
    if llm.MOCK:
        print("LLM_MOCK=1 이면 이 클라이언트는 돌지 않는다 — 실제 API 키가 필요하다 (.env의 LLM_MOCK=0)")
        sys.exit(1)

    questions = sys.argv[1:]
    try:
        asyncio.run(main(questions))
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

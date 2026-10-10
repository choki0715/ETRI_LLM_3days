"""Day 2 4세션 · 도구 결과도 컨텍스트다 — 계산기와 검색을 붙인 단일 루프.

모델은 "이 도구를 이 값으로 불러 달라"고 말할 뿐이고, 실행은 우리 코드가 한다.
매 시도마다 도구 실행 결과가 messages에 쌓인다 — 그것이 다음 시도의 컨텍스트다.

    from src import loop
    answer, trace = loop.run("서울 출장 3박이면 숙박비 한도는 모두 얼마?")

파일 순서
    1. 도구 함수     — calculator, search (우리 코드가 실제로 실행하는 함수)
    2. 도구 설명     — TOOLS (모델이 읽고 어떤 도구를 쓸지 고르는 글)
    3. 루프         — run (모델 호출 → 도구 실행 → 결과 전달 을 반복)
    4. 모델 호출     — call_model (모의 모드면 가짜 응답)
"""
import re

from common import llm

from . import rag

# search 도구가 찾아볼 색인.
# data/kb 폴더의 문서를 조각으로 잘라(chunk_folder) 벡터 DB에 넣은 rag.Index 객체다.
SEARCH_INDEX = rag.Index(rag.chunk_folder("data/kb"), name="loop")


# ================================================================ 1. 도구 함수 — 우리 코드가 실행한다
def calculator(a, b, op):
    """두 수를 사칙연산한다. op는 "add" · "sub" · "mul" · "div" 중 하나."""
    if op == "add":
        return a + b
    if op == "sub":
        return a - b
    if op == "mul":
        return a * b
    if op == "div":
        if b == 0:
            return "오류: 0으로 나눌 수 없음"
        return a / b
    return "오류: 모르는 연산 " + op


def search(query):
    """색인에서 query와 가장 가까운 조각 3개를 찾아, 번호 · 출처를 붙인 글 하나로 돌려준다.

    돌려주는 글의 모양:
        <자료 번호="1" 출처="02_출장비_지급규정.txt">
        제3조(국내 숙박비) 국내 출장 숙박비는 ...
        </자료>
        <자료 번호="2" 출처="...">
        ...
    """
    hits = SEARCH_INDEX.search(query, 3)       # 가까운 조각 3개. 각 조각에 .source(파일명) · .text(본문)

    result = ""
    number = 1
    for hit in hits:
        result += f'<자료 번호="{number}" 출처="{hit.source}">\n'
        result += hit.text + "\n"
        result += "</자료>\n"
        number += 1
    return result


def call_tool(tool_name, tool_input):
    """모델이 요청한 도구 이름과 입력값으로 실제 함수를 부른다.

    tool_name  예: "search"
    tool_input 예: {"query": "서울 출장 숙박비"}
    """
    try:
        if tool_name == "calculator":
            return calculator(tool_input["a"], tool_input["b"], tool_input["op"])
        if tool_name == "search":
            return search(tool_input["query"])
        return "오류: 모르는 도구 " + tool_name
    except Exception as error:
        # 입력값이 빠졌거나 잘못돼도 프로그램을 멈추지 않고, 오류 내용을 모델에게 알려 준다
        return "오류: " + str(error)


# ================================================================ 2. 도구 설명 — 모델이 읽는 것
# 모델은 이 글만 보고 "언제 어떤 도구를 어떤 값으로 부를지" 정한다.
#   name          도구 이름 — 모델이 요청할 때 이 이름을 쓴다
#   description   언제 쓰는 도구인지 — 모델이 도구를 고르는 유일한 근거
#   input_schema  어떤 값을 넣어야 하는지
CALCULATOR_TOOL = {
    "name": "calculator",
    "description": "두 숫자의 사칙연산을 정확히 계산한다. "
                   "금액 · 수량 · 비율 · 날짜 수 계산은 머릿속으로 하지 말고 반드시 이 도구를 쓴다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "a": {"type": "number", "description": "첫째 수"},
            "b": {"type": "number", "description": "둘째 수"},
            "op": {"type": "string", "enum": ["add", "sub", "mul", "div"],
                   "description": "add 더하기 · sub 빼기 · mul 곱하기 · div 나누기"},
        },
        "required": ["a", "b", "op"],
    },
}

SEARCH_TOOL = {
    "name": "search",
    "description": "한빛정밀 사내 규정 · 안내문 · 제품 사양서에서 관련 부분을 찾는다. "
                   "회사의 규정, 금액 기준, 절차, 담당자, 제품 수치를 물으면 답하기 전에 반드시 먼저 이 도구로 찾는다. "
                   "결과의 출처를 답에 [1]처럼 밝힌다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "찾을 내용. 문서에 쓰였을 법한 말로"},
        },
        "required": ["query"],
    },
}

TOOLS = [CALCULATOR_TOOL, SEARCH_TOOL]

# 2단계 '일부러 틀리게'용 — search의 입력(query) 설명만 잘못 적은 판. 이름 · 언제 쓰는지(description)는 그대로.
# 문서는 한국어인데 "영어 단어 하나로" 찾으라고 적었다. 모델은 이 정의를 그대로 따른다.
SEARCH_TOOL_BAD = {
    "name": "search",
    "description": SEARCH_TOOL["description"],
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "English keyword only, one word (e.g. 'hotel')"},
        },
        "required": ["query"],
    },
}

TOOLS_BAD = [CALCULATOR_TOOL, SEARCH_TOOL_BAD]

SYSTEM = ("당신은 한빛정밀 직원의 질문에 답하는 사내 도우미입니다. "
          "회사 규정은 도구로 찾은 자료에 있는 것만 말하고, 자료에 없으면 \"자료에 없음\"이라고 답합니다.")


# ================================================================ 3. 루프
LAST_MESSAGES = []     # 마지막 run()의 대화 기록 — 끝난 뒤에도 열어 볼 수 있게 남겨 둔다


def run(question, tools=TOOLS, system=SYSTEM, max_attempts=5, model=None, verbose=True):
    """가장 작은 에이전트 = 모델 + 도구 + 루프.

    돌려주는 값: (최종 답, trace)
        trace = 부른 도구 기록 [(시도 번호, 도구 이름, 입력값, 결과 앞부분), ...]

    모델의 응답(response)은 이렇게 생겼다.
        response.stop_reason   "tool_use"  → 도구를 불러 달라는 요청이 들어 있다
                               "end_turn"  → 할 말을 다 했다 (최종 답)
        response.content       블록의 리스트. 블록은 세 종류다.
            생각 블록       block.type == "thinking"   (모델이 답 전에 한 생각 — 내용은 비어 있지만 출력 토큰은 쓴다)
            글 블록         block.type == "text"
                            block.text  = "숙박비 한도를 찾아보겠습니다."
            도구 요청 블록   block.type == "tool_use"
                            block.name  = "search"
                            block.input = {"query": "서울 출장 숙박비"}
                            block.id    = "toolu_01..."  (결과를 돌려줄 때 짝을 맞추는 번호)
    """
    global LAST_MESSAGES
    if model is None:
        model = llm.MODEL

    # 대화 기록. 매 시도마다 이 리스트 전체를 모델에게 보낸다.
    messages = [{"role": "user", "content": question}]
    LAST_MESSAGES = messages          # 노트북에서 loop.show_messages(loop.LAST_MESSAGES)로 펼쳐 본다
    trace = []

    for attempt in range(max_attempts):
        # ① 모델을 부른다
        response = call_model(model, tools, messages, system)

        # ② 도구 요청이 없으면 → 답을 다 낸 것. 글 블록을 모아 돌려주고 끝낸다.
        if response.stop_reason != "tool_use":
            answer = ""
            for block in response.content:
                if block.type == "text":
                    answer += block.text
            if verbose:
                print(f"[{attempt}] 종료 ({response.stop_reason})")
                print(answer)
            return answer, trace

        # ③ 도구 요청이 있으면 → 먼저 모델의 응답을 대화 기록에 그대로 붙인다.
        messages.append({"role": "assistant", "content": response.content})

        # ④ 응답의 블록을 하나씩 보면서, 도구 요청이면 우리 코드가 실행한다.
        tool_results = []
        for block in response.content:
            if block.type == "text":
                if verbose:
                    print(f"[{attempt}] 모델: {block.text.strip()[:80]}")

            if block.type == "tool_use":
                output = call_tool(block.name, block.input)
                output = str(output)               # 결과는 글자로 모델에게 보낸다

                trace.append((attempt, block.name, block.input, output[:80]))
                if verbose:
                    preview = output[:60].replace("\n", " ")
                    print(f"[{attempt}] 도구 실행: {block.name} {block.input} → {preview}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,       # 어느 요청에 대한 결과인지
                    "content": output,
                })

        # ⑤ 실행 결과를 user 메시지로 붙인다. 다음 시도에서 모델이 이것을 읽는다.
        messages.append({"role": "user", "content": tool_results})

    if verbose:
        print(f"최대 {max_attempts}번 시도에 닿아 멈춤")
    return "(최대 반복 도달)", trace


def show_messages(messages):
    """대화 기록을 한 줄씩 펼쳐 찍는다. 도구 요청과 도구 결과가 기록에 어떻게 쌓였는지 보기 위한 함수.

    messages 안의 content는 세 가지 모양이다.
        글자                           — 사용자 질문
        모델 응답 블록의 리스트         — 모델의 생각(thinking) · 모델의 말(text) · 도구 요청(tool_use)
        {"type": "tool_result", ...}  — 우리가 붙인 도구 결과 (dict의 리스트)
    """
    number = 0
    for message in messages:
        role = message["role"]
        content = message["content"]
        if isinstance(content, str):
            print(f"[{number}] {role:<9} 질문: {content}")
        else:
            for part in content:
                if isinstance(part, dict):
                    preview = part["content"][:100].replace("\n", " ")
                    print(f"[{number}] {role:<9} 도구 결과: {preview}")
                elif part.type == "thinking":
                    print(f"[{number}] {role:<9} 모델의 생각: (내용은 보이지 않음)")
                elif part.type == "text":
                    print(f"[{number}] {role:<9} 모델의 말: {part.text.strip()[:80]}")
                elif part.type == "tool_use":
                    print(f"[{number}] {role:<9} 도구 요청: {part.name} {part.input}")
        number += 1


def tools_used(trace):
    """trace에서 도구 이름만 순서대로 뽑는다. 예: ["search", "calculator"]"""
    names = []
    for attempt, name, tool_input, output in trace:
        names.append(name)
    return names


# ================================================================ 4. 모델 호출
def call_model(model, tools, messages, system):
    """모델을 한 번 부른다. LLM_MOCK=1 이면 API 대신 가짜 응답을 돌려준다."""
    if llm.MOCK:
        return fake_model(messages, tools)

    client = llm.client()
    if system is None:
        return client.messages.create(model=model, max_tokens=2000, tools=tools, messages=messages)
    return client.messages.create(model=model, max_tokens=2000, tools=tools, messages=messages, system=system)


# ---------------------------------------------------------------- 모의 모드 (pytest용 — 수업에서는 읽지 않아도 된다)
class FakeBlock:
    """진짜 응답의 블록처럼 .type · .text · .name · .input · .id 를 가진 가짜 블록."""

    def __init__(self, type, text="", name="", input=None, id=""):
        self.type = type
        self.text = text
        self.name = name
        self.input = input
        self.id = id


class FakeResponse:
    """진짜 응답처럼 .content · .stop_reason 을 가진 가짜 응답."""

    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason


def fake_model(messages, tools):
    """첫 시도에 search, 질문에 숫자가 있으면 다음 시도에 calculator, 그다음 종료."""
    tool_names = []
    for tool in tools:
        tool_names.append(tool["name"])

    attempts_done = 0                             # 지금까지 모델이 응답한 횟수
    for message in messages:
        if message["role"] == "assistant":
            attempts_done += 1

    question = messages[0]["content"]
    numbers = re.findall(r"\d+", question)     # 질문 속 숫자들 (글자)

    if attempts_done == 0 and "search" in tool_names:
        block = FakeBlock("tool_use", id="m1", name="search", input={"query": question})
        return FakeResponse([block], "tool_use")

    if attempts_done == 1 and len(numbers) > 0 and "calculator" in tool_names:
        a = float(numbers[0])
        b = float(numbers[-1])
        block = FakeBlock("tool_use", id="m2", name="calculator", input={"a": a, "b": b, "op": "mul"})
        return FakeResponse([block], "tool_use")

    block = FakeBlock("text", text="[모의 응답] 도구 결과를 받아 답을 마칩니다.")
    return FakeResponse([block], "end_turn")

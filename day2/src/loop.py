"""Day 2 블록 4 · 도구 결과도 컨텍스트다 — 계산기와 검색을 붙인 단일 루프.

모델은 "이 도구를 이 값으로 불러 달라"고 말할 뿐이고, 실행은 우리 코드가 한다.
매 바퀴 tool_result가 messages에 쌓인다 — 그것이 다음 바퀴의 컨텍스트다.

    from src import loop, rag
    idx = rag.Index.build(rag.chunk_folder("data/kb"))
    loop.SEARCH_INDEX = idx
    answer, trace = loop.run("서울 출장 3박이면 숙박비 한도는 모두 얼마?")
"""
from __future__ import annotations

import json
import re

from common import llm

from . import rag

SEARCH_INDEX: rag.Index | None = None
SEARCH_K = 3


# ================================================================ 도구 구현 — 우리 코드
def calculator(a: float, b: float, op: str) -> float | str:
    if op == "add":
        return a + b
    if op == "sub":
        return a - b
    if op == "mul":
        return a * b
    if op == "div":
        return "오류: 0으로 나눌 수 없음" if b == 0 else a / b
    return f"오류: 모르는 연산 {op}"


def search(query: str) -> str:
    """오늘 만든 색인에서 찾아 번호 · 출처를 단 자료로 돌려준다."""
    if SEARCH_INDEX is None:
        return "오류: 색인이 없습니다. loop.SEARCH_INDEX = idx 를 먼저 하세요."
    hits = SEARCH_INDEX.search(query, SEARCH_K)
    return "\n".join(f'<자료 번호="{i + 1}" 출처="{h.source}">\n{h.text}\n</자료>' for i, h in enumerate(hits))


RUN = {"calculator": calculator, "search": search}


# ================================================================ 도구 정의 — 모델이 읽는 것
TOOLS = [
    {
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
    },
    {
        "name": "search",
        "description": "한빛정밀 사내 규정 · 안내문 · 제품 사양서에서 관련 부분을 찾는다. "
                       "회사의 규정, 금액 기준, 절차, 담당자, 제품 수치를 물으면 답하기 전에 반드시 먼저 이 도구로 찾는다. "
                       "결과의 출처를 답에 [1]처럼 밝힌다.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "찾을 내용. 문서에 쓰였을 법한 말로"}},
            "required": ["query"],
        },
    },
]

# 2단계 '일부러 틀리게'용 — 설명을 한 단어로 줄인 판
TOOLS_VAGUE = [
    {**TOOLS[0], "description": "계산한다."},
    {**TOOLS[1], "description": "검색한다."},
]

SYSTEM = ("당신은 한빛정밀 직원의 질문에 답하는 사내 도우미입니다. "
          "회사 규정은 도구로 찾은 자료에 있는 것만 말하고, 자료에 없으면 \"자료에 없음\"이라고 답합니다.")


# ================================================================ 루프
def run(question: str, *, tools: list[dict] = TOOLS, system: str | None = SYSTEM,
        max_turns: int = 5, model: str | None = None, verbose: bool = True):
    """가장 작은 에이전트 = 모델 + 도구 + 루프.

    반환 — (최종 답, trace)   trace = [(바퀴, 도구 이름, 입력, 결과 앞부분), …]
    """
    model = model or llm.MODEL
    msgs = [{"role": "user", "content": question}]
    trace = []
    for turn in range(max_turns):                                 # 최대 반복 횟수
        r = _create(model=model, max_tokens=800, tools=tools, messages=msgs, system=system)
        if r.stop_reason != "tool_use":                           # 도구를 안 부르면 종료
            text = "".join(b.text for b in r.content if b.type == "text")
            if verbose:
                print(f"[{turn}] 종료 ({r.stop_reason})\n{text}")
            return text, trace

        msgs.append({"role": "assistant", "content": r.content})
        results = []
        for b in r.content:
            if b.type == "text" and b.text.strip() and verbose:
                print(f"[{turn}] 모델: {b.text.strip()[:80]}")
            if b.type == "tool_use":
                try:
                    out = RUN[b.name](**b.input)                  # 우리 코드가 실행
                except Exception as e:
                    out = f"오류: {type(e).__name__}: {e}"
                trace.append((turn, b.name, b.input, str(out)[:80]))
                if verbose:
                    print(f"[{turn}] {b.name} {json.dumps(b.input, ensure_ascii=False)} → {str(out)[:60]!r}")
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": str(out)})
        msgs.append({"role": "user", "content": results})       # 결과가 다음 바퀴의 창에 들어간다
    if verbose:
        print(f"최대 {max_turns}바퀴에 닿아 멈춤")
    return "(최대 반복 도달)", trace


def tools_used(trace) -> list[str]:
    return [name for _, name, _, _ in trace]


# ================================================================ API 호출 (모의 모드 포함)
def _create(**kw):
    if not llm.MOCK:
        kw = {k: v for k, v in kw.items() if v is not None}
        return llm.client().messages.create(**kw)
    return _mock(kw["messages"], kw["tools"])


class _B:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _R:
    def __init__(self, content, stop_reason):
        self.content, self.stop_reason = content, stop_reason


def _mock(msgs, tools):
    """모의 모드: 첫 바퀴에 search, 질문에 숫자가 있으면 다음 바퀴에 calculator, 그다음 종료."""
    names = {t["name"] for t in tools}
    n_tool_turns = sum(1 for m in msgs if m["role"] == "assistant")
    q = msgs[0]["content"]
    if n_tool_turns == 0 and "search" in names:
        return _R([_B(type="tool_use", id="m1", name="search", input={"query": q})], "tool_use")
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", q)]
    if n_tool_turns == 1 and nums and "calculator" in names:
        return _R([_B(type="tool_use", id="m2", name="calculator",
                      input={"a": nums[0], "b": nums[-1], "op": "mul"})], "tool_use")
    return _R([_B(type="text", text="[모의 응답] 도구 결과를 받아 답을 마칩니다.")], "end_turn")

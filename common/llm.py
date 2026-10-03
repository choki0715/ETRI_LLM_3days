"""day1·day2 공용 — 모델 호출, 토큰 세기, 비용 계산.   사용: from common import llm

노트북과 grade.py(day1) · qa.py/rag.py/loop.py(day2)가 모두 이 파일의 call()을 씁니다.
LLM_MOCK=1 이면 API를 부르지 않고 고정된 모의 응답을 돌려줍니다 (흐름 확인용).
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

MODEL = os.getenv("MODEL", "claude-haiku-4-5-20251001")
# 고급 모델이 필요한 문항에서만 model=llm.MODEL_ADVANCED 로 지정해 씁니다
MODEL_ADVANCED = os.getenv("MODEL_ADVANCED", "claude-sonnet-5-5")
MOCK = os.getenv("LLM_MOCK", "0") == "1"

# 모델 비교(바퀴 3)에 쓸 목록 — 강의 당일 쓸 수 있는 이름으로 확인해 바꿉니다
MODELS = ["claude-haiku-4-5-20251001", "claude-sonnet-5-5", "claude-opus-5-5"]

# 100만 토큰당 (입력 $, 출력 $) — Claude API 기준가. 강의 당일 요금표로 다시 확인합니다.
# 비어 있는 모델은 비용을 계산하지 않고 "단가 미입력"으로 표시합니다.
PRICES: dict[str, tuple[float, float] | None] = {
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-opus-5-5": (4.0, 20.0),
}

_client = None


def client():
    """Anthropic 클라이언트를 한 번만 만든다."""
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()   # .env의 ANTHROPIC_API_KEY를 읽는다
    return _client


@dataclass
class Result:
    text: str
    stop_reason: str
    input_tokens: int
    output_tokens: int
    seconds: float
    model: str
    raw: object = field(default=None, repr=False)

    @property
    def cost(self) -> float | None:
        return cost(self.model, self.input_tokens, self.output_tokens)


def call(user: str, system: str | None = None, *, model: str | None = None,
         max_tokens: int = 1000, history: list[dict] | None = None,
         stop_sequences: list[str] | None = None, effort: str | None = None,
         temperature: float | None = None) -> Result:
    """모델을 한 번 부른다.

    user     — 이번에 보내는 user 메시지
    system   — 매번 같은 역할 · 규칙 · 형식 (없어도 된다)
    history  — 앞서 주고받은 messages. 모델은 기억하지 않으므로 이어 가려면 직접 넘긴다
    effort   — "low" · "medium" · "high" · "xhigh" · "max". 생각을 얼마나 들일지 (지원 모델만)
    temperature — 최신 모델은 받지 않는다(400 오류). 예전 모델 실험용으로만 남겨 두었다.
                  SDK 1.x에는 이 인자가 없어서 extra_body로 보낸다.
    """
    model = model or MODEL
    messages = list(history or []) + [{"role": "user", "content": user}]

    if MOCK:
        return _mock(messages, system, model)

    kwargs = dict(model=model, max_tokens=max_tokens, messages=messages)
    if effort:
        kwargs["output_config"] = {"effort": effort}
    if temperature is not None:
        kwargs["extra_body"] = {"temperature": temperature}
    if system:
        kwargs["system"] = system
    if stop_sequences:
        kwargs["stop_sequences"] = stop_sequences

    t0 = time.perf_counter()
    r = client().messages.create(**kwargs)
    dt = time.perf_counter() - t0
    text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    return Result(text, r.stop_reason, r.usage.input_tokens, r.usage.output_tokens, dt, model, r)


def count_tokens(text: str, *, system: str | None = None, model: str | None = None) -> int:
    """호출하지 않고 입력 토큰 수만 센다."""
    model = model or MODEL
    if MOCK:
        return max(1, len(text) // 2)
    kwargs = dict(model=model, messages=[{"role": "user", "content": text}])
    if system:
        kwargs["system"] = system
    return client().messages.count_tokens(**kwargs).input_tokens


def cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """1건 비용(달러). 단가가 비어 있으면 None."""
    p = PRICES.get(model)
    if not p:
        return None
    return input_tokens * p[0] / 1_000_000 + output_tokens * p[1] / 1_000_000


def fmt_cost(c: float | None) -> str:
    return "단가 미입력" if c is None else f"${c:.4f}"


def render(template: str, **values: str) -> str:
    """프롬프트 템플릿의 {이름} 자리를 채운다.
    JSON 예시의 중괄호와 섞이지 않게 format() 대신 이름을 직접 바꾼다."""
    out = template
    for k, v in values.items():
        out = out.replace("{" + k + "}", v)
    return out


def load_prompt(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


# ---------------- 모의 응답 (LLM_MOCK=1) ----------------
def _mock(messages, system, model) -> Result:
    last = messages[-1]["content"]
    if "json" in (system or "").lower() + last.lower():
        text = '{"제목": "모의 응답", "항목": []}'
    else:
        text = f"[모의 응답] 받은 메시지 {len(messages)}개 · 마지막 질문 앞부분: {last[:30]}"
    n_in = sum(len(m["content"]) if isinstance(m["content"], str) else 50 for m in messages) // 2
    return Result(text, "end_turn", n_in, len(text) // 2, 0.01, model)

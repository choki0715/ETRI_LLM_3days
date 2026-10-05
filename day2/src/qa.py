"""Day 2 3세션 · 근거를 달고 답하는 질의응답 — 10문항 채점과 고장 위치 추정.

고정 문항 · 판정 기준 · 반복 기록으로 잰다.
다른 점: 실패를 '어느 단계의 고장인지'로 나눈다.

    검색·청킹  넣은 자료에 답이 든 조각이 없다          → k · 질문 말투 · 키워드 검색 · 자르는 법
              (정답 문서가 아예 안 왔으면 검색, 왔는데 다른 조각이거나 잘렸으면 청킹을 먼저 의심 —
               debug()로 조각을 열어 사람이 가린다)
    있는데 못 씀  자료에 답이 있는데 답에 없다          → 주입 코드 · 프롬프트 위치
    지어냄    답이 없는 질문에 "자료에 없음"이 아니다   → 거절 지시
    출처 오류 답은 맞는데 각주가 정답 문서를 가리키지 않는다
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from common import llm

from . import rag

ROOT = Path(__file__).resolve().parents[1]
KINDS = ["검색·청킹", "있는데 못 씀", "지어냄", "출처 오류"]
REFUSAL = "자료에 없음"


def load_qa(path="data/qa_tests.jsonl") -> list[dict]:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def check_qa(answer: str, hits: list, spec: dict) -> tuple[bool, str | None, str]:
    if spec.get("refuse"):
        if REFUSAL in answer:
            return True, None, ""
        return False, "지어냄", "답이 없는 질문에 답함: " + _one_line(answer)

    exp = spec["expect"]
    src_hits = [h for h in hits if h.source == spec["source"]]
    if not src_hits:
        return False, "검색·청킹", "정답 문서가 안 옴 — 넣은 자료: " + ", ".join(h.source for h in hits)
    if not any(e in h.text for h in src_hits for e in exp):
        return False, "검색·청킹", f"정답 문서의 다른 조각이 옴 ('{exp[0]}' 없음) — 조각이 잘렸는지 debug로 확인"
    if REFUSAL in answer or not any(e in answer for e in exp):
        return False, "있는데 못 씀", "답: " + _one_line(answer)
    refs = rag.cited(answer)
    if not any(1 <= n <= len(hits) and hits[n - 1].source == spec["source"] for n in refs):
        return False, "출처 오류", f"각주 {refs} — 정답 문서는 {spec['source']}"
    return True, None, ""


def _one_line(text: str, n: int = 50) -> str:
    t = " ".join(text.split())
    return t[:n] + ("…" if len(t) > n else "")


def run_qa(idx, k: int = 3, tests: list[dict] | None = None, show: bool = True, **ask_kw):
    """10문항을 돌려 (통과 수, 실패 목록, 행)을 돌려준다. ask_kw는 rag.ask로 넘어간다."""
    tests = tests or load_qa()
    rows = []
    for t in tests:
        answer, hits = rag.ask(t["q"], idx, k, **ask_kw)
        ok, kind, why = check_qa(answer, hits, t)
        rows.append(dict(id=t["id"], group=t["group"], q=t["q"], ok=ok, kind=kind, why=why,
                         answer=answer, sources=[h.source for h in hits]))
    passed = sum(r["ok"] for r in rows)
    fails = [(r["id"], r["kind"]) for r in rows if not r["ok"]]
    if show:
        print(f"통과 {passed} / {len(rows)}   " +
              "  ".join(f"{k} {v}" for k, v in Counter(k for _, k in fails).items()))
        for r in rows:
            mark = "○" if r["ok"] else "×"
            print(f"  {mark} #{r['id']:>2} [{r['group']}] {r['q'][:30]:<32}" +
                  ("" if r["ok"] else f" → {r['kind']}: {r['why']}"))
    return passed, fails, rows

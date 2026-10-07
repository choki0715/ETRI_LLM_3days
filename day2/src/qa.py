"""Day 2 3세션 · RAG 질의응답 10문항 채점.

    from src import rag, qa
    idx = rag.Index.build(rag.chunk_folder("data/kb"))
    passed, fails, rows = qa.run_qa(idx, k=3)

문항은 data/qa_tests.jsonl 에 고정돼 있다. 문항마다 rag.ask()로 답을 받고 check_qa()로 판정한다.
실패는 "어느 단계가 고장났는가"로 나눈다 — 유형이 곧 고칠 곳이다.

    유형          뜻                                        고칠 곳
    ─────────── ───────────────────────────────────────── ──────────────────────────
    지어냄        답 없는 질문에 "자료에 없음"이라 하지 않음   거절 지시(RULES)
    검색·청킹     정답이 든 조각이 프롬프트에 들어가지 못함    k · 질문 말투 · 키워드 검색 · 자르는 법
    있는데 못 씀   정답 조각은 들어갔는데 답에 없음            프롬프트 · 모델
    출처 오류     답은 맞는데 각주가 정답 파일을 안 가리킴     각주 규칙

코드는 유형까지만 가린다. 그 안에서 정확히 무엇이 잘못됐는지는 rag.debug()로 조각을 열어 사람이 본다.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from . import rag

ROOT = Path(__file__).resolve().parents[1]
REFUSAL = "자료에 없음"          # RULES의 거절 문구와 글자가 같아야 한다


def load_qa(path="data/qa_tests.jsonl") -> list[dict]:
    """문항 파일을 읽는다. 한 줄이 문항 하나."""
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def check_qa(answer: str, hits: list, spec: dict) -> tuple[bool, str | None, str]:
    """문항 하나를 판정한다 → (통과 여부, 실패 유형, 설명).

    answer  모델이 낸 답
    hits    프롬프트에 넣은 조각들 (검색 결과 k개, 순서대로 자료 번호 1, 2, 3…)
    spec    문항 한 줄 — expect(답에 있어야 할 말) · source(정답 파일) · refuse(답이 없어야 정상)

    검사 순서는 파이프라인 순서다: 자료가 왔나 → 그 안에 답이 있나 → 모델이 썼나 → 근거를 맞게 달았나.
    앞에서 걸리면 뒤는 보지 않는다.
    """
    # 답없음 문항 — "자료에 없음"이 들어 있으면 통과, 아니면 지어냄. 여기서 끝.
    if spec.get("refuse"):
        if REFUSAL in answer:
            return True, None, ""
        return False, "지어냄", "답이 없는 질문에 답함: " + _one_line(answer)

    expect = spec["expect"]                                         # 예: ["3일"]
    answer_file = spec["source"]                                    # 예: "01_일반업무규칙.txt"

    # 1. 정답 파일에서 온 조각이 있나
    from_answer_file = [h for h in hits if h.source == answer_file]
    if not from_answer_file:
        got = ", ".join(h.source for h in hits)
        return False, "검색·청킹", f"정답 파일이 안 옴 — 대신 온 것: {got}"

    # 2. 그 조각 본문에 정답이 있나 (같은 파일의 다른 조항이거나 잘렸으면 없다)
    if not any(e in h.text for h in from_answer_file for e in expect):
        return False, "검색·청킹", f"정답 파일은 왔는데 '{expect[0]}'이 없는 조각 — 잘렸는지 debug로 확인"

    # 3. 모델이 그 정답을 답에 썼나
    if REFUSAL in answer or not any(e in answer for e in expect):
        return False, "있는데 못 씀", "답: " + _one_line(answer)

    # 4. 각주가 정답 파일을 가리키나
    #    자료 번호 → 파일 표를 만들고, 답의 [n]을 그 표로 바꾼다. 표에 없는 번호는 None.
    number_to_file = {i + 1: h.source for i, h in enumerate(hits)}
    footnotes = rag.cited(answer)
    cited_files = [number_to_file.get(n) for n in footnotes]
    if answer_file not in cited_files:
        return False, "출처 오류", f"각주 {footnotes} → {cited_files} — 정답 파일은 {answer_file}"

    return True, None, ""


def run_qa(idx, k: int = 3, tests: list[dict] | None = None, show: bool = True, **ask_kw):
    """문항 전체를 돌려 (통과 수, 실패 목록, 문항별 결과)를 돌려준다. ask_kw는 rag.ask()로 그대로 넘어간다."""
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
        by_kind = Counter(kind for _, kind in fails)
        print(f"통과 {passed} / {len(rows)}   " + "  ".join(f"{kind} {n}" for kind, n in by_kind.items()))
        for r in rows:
            mark = "○" if r["ok"] else "×"
            tail = "" if r["ok"] else f" → {r['kind']}: {r['why']}"
            print(f"  {mark} #{r['id']:>2} [{r['group']}] {r['q'][:30]:<32}{tail}")
    return passed, fails, rows


def _one_line(text: str, n: int = 50) -> str:
    """여러 줄 답을 한 줄 n자로 줄인다 (설명용)."""
    t = " ".join(text.split())
    return t[:n] + ("…" if len(t) > n else "")

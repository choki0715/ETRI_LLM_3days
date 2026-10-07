"""Day 2 3세션 · 근거를 달고 답하는 질의응답 — 10문항 채점과 고장 위치 추정.

고정 문항 · 판정 기준 · 반복 기록으로 측정한다.
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
    """문항 하나를 판정한다 → (통과 여부, 실패 유형, 설명 한 줄).

    answer  모델이 낸 답
    hits    ask()가 검색해서 프롬프트에 넣은 조각들 (Hit 리스트, k개)
    spec    qa_tests.jsonl 한 줄 — expect(정답에 있어야 할 말) · source(정답 파일) · refuse(답이 없어야 정상)

    체 다섯 개를 파이프라인 순서(검색 → 모델 → 출력 형식)로 통과시키고, 먼저 걸리는 데서 멈춘다.
    그래서 실패 유형 하나가 곧 "어느 단계를 먼저 고쳐야 하는가"가 된다.
    """
    # 체 1 — 답없음 문항(refuse: true)은 이것만 본다. 정답 문서라는 게 없으므로 아래 체 2~5는 거치지 않는다.
    #   예) 7번 "사내 헬스장은 몇 시까지 운영하나요?"  (자료에 헬스장 얘기가 없음)
    #       answer = "자료에 없음"                                             → 통과
    #       answer = "자료에 없음\n\n제공된 자료에는 사내식당 운영 시간만 있습니다."  → 통과 (글자가 들어 있으면 뒤에 설명이 붙어도 됨)
    #       answer = "사내 헬스장은 오후 9시까지 운영합니다. [2]"                  → 지어냄 (2번 자료는 식당 안내인데 헬스장 시간을 만들어 냄)
    if spec.get("refuse"):
        if REFUSAL in answer:                     # "자료에 없음"이 답 어딘가에 있으면 통과 (뒤에 설명이 붙어도 됨)
            return True, None, ""
        return False, "지어냄", "답이 없는 질문에 답함: " + _one_line(answer)

    # ---- 여기부터 답이 있어야 하는 문항 ----
    exp = spec["expect"]                                            # 정답에 꼭 들어 있어야 할 말. 예: ["3일"]
    src_hits = [h for h in hits if h.source == spec["source"]]      # 검색된 k개 중 정답 파일에서 온 조각만 추림

    # 체 2 — 정답 "파일"이 검색조차 안 됐다. 검색은 항상 k개를 돌려주므로 hits는 비지 않는다 — 전부 엉뚱한 파일인 것.
    #        모델 답은 보지 않는다: 자료를 못 받았으면 모델 잘못이 아니다. 고칠 곳 = 검색(k · 질문 말투 · 키워드 검색 병행).
    if not src_hits:
        return False, "검색·청킹", "정답 문서가 안 옴 — 넣은 자료: " + ", ".join(h.source for h in hits)

    # 체 3 — 파일은 맞는데 그 안의 "다른 조각"이 왔다 (같은 규칙집의 다른 조항이거나, 잘려서 정답 부분이 빠진 것).
    #        h.text(조각 본문)를 본다 — 아직 모델 답이 아니다. 정답이 프롬프트에 들어가지도 못한 경우. 고칠 곳 = 청킹 · 검색.
    if not any(e in h.text for h in src_hits for e in exp):
        return False, "검색·청킹", f"정답 문서의 다른 조각이 옴 ('{exp[0]}' 없음) — 조각이 잘렸는지 debug로 확인"

    # 체 4 — 여기부터 모델 답(answer)을 본다. 정답이 든 조각이 프롬프트에 들어갔는데
    #        모델이 "자료에 없음"이라 거절했거나, 답에 정답 단어가 없다. 고칠 곳 = 프롬프트(RULES · 자료 위치) · 모델.
    #   예) 1번 문항, 정답 조각(제14조 "사용일 3일 전까지")이 프롬프트에 들어간 상태에서
    #       answer = "자료에 없음"                                   → 있는데 못 씀 (자료를 주고도 거절 — drop_context 고장이 만드는 증상)
    #       answer = "그룹웨어에서 부서장 승인을 받으면 됩니다. [1]"        → 있는데 못 씀 (3일을 빼먹음)
    #       answer = "연차는 사용일 5일 전까지 신청해야 합니다. [1]"       → 있는데 못 씀 (틀린 숫자, "3일"이 없음)
    #       answer = "연차는 사용일 3일 전까지 신청해야 합니다. [1]"       → 통과 → 체 5로
    #   한계: 글자 포함만 보므로 "3일이 아니라 5일입니다"처럼 틀린 답도 "3일"이 들어 있어 통과한다 — 최종 확인은 사람이 debug로.
    if REFUSAL in answer or not any(e in answer for e in exp):
        return False, "있는데 못 씀", "답: " + _one_line(answer)

    # 체 5 — 답 내용은 맞다. 각주가 정답 파일을 가리키는지 본다.
    #
    #   프롬프트의 자료 번호는 make_prompt가 hits 순서대로 1, 2, 3… 매긴 것이다. 그 표를 그대로 다시 만든다.
    #   예) 1번 문항:  {1: "01_일반업무규칙.txt", 2: "05_휴가_FAQ.txt", 3: "05_휴가_FAQ.txt"}
    number_to_file = {i + 1: h.source for i, h in enumerate(hits)}

    #   답에서 [n]을 뽑아 위 표로 파일명을 찾는다. 표에 없는 번호([7] 등)는 None → 정답 파일과 다름.
    #   예) 정답 파일 = 01_일반업무규칙.txt 일 때
    #       "… 3일 전까지 … [1]"          footnotes=[1]    → {1: 01_일반업무규칙}           → 통과
    #       "… 3일 전까지 … [2]"          footnotes=[2]    → {2: 05_휴가_FAQ}                → 출처 오류 (내용은 맞는데 근거를 FAQ에 닮)
    #       "… [1] … [3]"                 footnotes=[1, 3] → 1번이 정답 파일, 하나면 충분    → 통과
    #       "… 3일 전까지 … [7]"          footnotes=[7]    → 표에 없음 → None               → 출처 오류
    #       "… 3일 전까지 …" (각주 없음)   footnotes=[]     → 볼 게 없음                    → 출처 오류 (각주를 안 닮)
    footnotes = rag.cited(answer)
    cited_files = [number_to_file.get(n) for n in footnotes]
    if spec["source"] not in cited_files:
        return False, "출처 오류", f"각주 {footnotes} → {cited_files} — 정답 문서는 {spec['source']}"

    # 다 지나오면 통과
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

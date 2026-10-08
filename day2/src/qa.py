"""Day 2 3세션 · RAG 질의응답 10문항 채점.

    from src import rag, qa
    idx = rag.Index(rag.chunk_folder("data/kb"))
    passed, fails, rows = qa.run_qa(idx, k=3)

문항은 data/qa_tests.jsonl 에 고정돼 있다. 문항마다 rag.ask()로 답을 받고 check_qa()로 판정한다.
실패는 "어느 단계가 고장났는가"로 나눈다 — 유형이 곧 고칠 곳이다.

    유형          뜻                                        고칠 곳
    ─────────── ───────────────────────────────────────── ──────────────────────────
    지어냄        답 없는 질문에 "자료에 없음"이라 하지 않음   거절 지시(RULES)
    검색·청킹     정답이 든 청크가 프롬프트에 들어가지 못함    k · 질문 말투 · 키워드 검색 · 자르는 법
    있는데 못 씀   정답 청크는 들어갔는데 답에 없음            프롬프트 · 모델
    출처 오류     답은 맞는데 각주가 정답 파일을 안 가리킴     각주 규칙

코드는 유형까지만 가린다. 그 안에서 정확히 무엇이 잘못됐는지는 rag.debug()로 청크를 열어 사람이 본다.
"""
import json
from pathlib import Path

from . import rag

ROOT = Path(__file__).resolve().parents[1]
REFUSAL = "자료에 없음"          # RULES의 거절 문구와 글자가 같아야 한다


def load_qa(path="data/qa_tests.jsonl"):
    """문항 파일을 읽는다. 한 줄이 문항 하나(JSON)."""
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    tests = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip() == "":
            continue
        tests.append(json.loads(line))
    return tests


def contains_any(text, words):
    """words 중 하나라도 text 안에 있으면 True."""
    for w in words:
        if w in text:
            return True
    return False


def check_qa(answer, hits, spec):
    """문항 하나를 채점한다 → (통과 여부, 실패 유형, 한 줄 설명).

    검사 순서 = 파이프라인 순서. 앞에서 걸리면 뒤는 안 본다.
      1 검색: 정답 파일이 왔나   2 검색·청킹: 그 청크에 정답 글자가 있나
      3 생성: 모델이 답에 썼나   4 각주: 정답 파일을 가리키나
    """
    # 답없음 문항 — "자료에 없음"이면 통과, 아니면 지어냄.
    if spec.get("refuse"):
        if REFUSAL in answer:
            return True, None, ""
        return False, "지어냄", "답이 없는 질문인데 지어냄: " + one_line(answer)

    expect = spec["expect"]            # 답에 있어야 할 말, 예: ["3일"]
    correct_file = spec["source"]      # 정답이 있는 파일 — answer(모델 답)와 안 헷갈리게 이름을 따로 씀

    # 1. 정답 파일에서 온 청크가 있나
    #    원인: 검색이 다른 파일을 더 가깝다고 봄 → 해결: k 늘리기 · 질문 말투 맞추기 · 키워드 검색 병행
    from_correct_file = []
    for h in hits:
        if h.source == correct_file:
            from_correct_file.append(h)
    if len(from_correct_file) == 0:
        got_files = []
        for h in hits:
            got_files.append(h.source)
        got = ", ".join(got_files)
        if got == "":
            got = "(검색 결과 없음)"
        return False, "검색·청킹", f"정답 파일({correct_file})이 안 옴 — 대신: {got}"

    # 2. 그 청크에 정답 글자가 있나 — 원인이 둘이고, 코드는 hits만 봐서 구분 못 함 (debug로 인덱스를 열어 봄)
    #    (가) 검색: 같은 파일의 다른 조항이 뽑힘, 정답 청크는 인덱스에 있는데 순위에서 밀림 → k 늘리기 · 질문 말투 · 키워드 검색
    #    (나) 청킹: 정답 문장이 경계에서 잘려 어느 청크에도 온전히 없음 → max_len · overlap 조정, 구조 경계로 자르기
    answer_in_chunk = False
    for h in from_correct_file:
        if contains_any(h.text, expect):
            answer_in_chunk = True
    if not answer_in_chunk:
        return False, "검색·청킹", f"{correct_file}는 왔는데 '{expect[0]}'이 없는 청크 — debug로 확인"

    # 3. 모델이 그 정답을 답에 썼나
    #    원인: 프롬프트 지시가 모호하거나 모델이 자료를 못 씀 → 해결: 프롬프트 문구 수정
    if REFUSAL in answer or not contains_any(answer, expect):
        return False, "있는데 못 씀", "모델 답: " + one_line(answer)

    # 4. 각주가 정답 파일을 가리키나 (자료 번호 → 파일 표로 바꿔서 대조)
    #    원인: 각주 규칙을 안 지키거나 번호를 잘못 붙임 → 해결: 각주 규칙 문구 보강
    number_to_file = {}
    number = 1
    for h in hits:
        number_to_file[number] = h.source
        number += 1
    cited_files = []
    for n in rag.cited(answer):
        cited_files.append(number_to_file.get(n))      # 없는 번호면 None
    if correct_file not in cited_files:
        return False, "출처 오류", f"각주가 {cited_files} 가리킴 — 정답은 {correct_file}"

    return True, None, ""


def run_qa(idx, k=3, tests=None, show=True):
    """문항 전체를 돌려 (통과 수, 실패 목록, 문항별 결과)를 돌려준다."""
    if tests is None:
        tests = load_qa()

    rows = []
    for t in tests:
        answer, hits = rag.ask(t["q"], idx, k)
        ok, kind, why = check_qa(answer, hits, t)
        sources = []
        for h in hits:
            sources.append(h.source)
        rows.append({"id": t["id"], "group": t["group"], "q": t["q"], "ok": ok, "kind": kind, "why": why,
                     "answer": answer, "sources": sources})

    passed = 0
    fails = []
    for r in rows:
        if r["ok"]:
            passed += 1
        else:
            fails.append((r["id"], r["kind"]))

    if show:
        # 실패 유형별 개수, 예: {"검색·청킹": 2, "지어냄": 1}
        kind_counts = {}
        for item_id, kind in fails:
            if kind in kind_counts:
                kind_counts[kind] += 1
            else:
                kind_counts[kind] = 1
        summary = []
        for kind in kind_counts:
            summary.append(f"{kind} {kind_counts[kind]}")
        print(f"통과 {passed} / {len(rows)}   " + "  ".join(summary))

        for r in rows:
            if r["ok"]:
                mark = "○"
                tail = ""
            else:
                mark = "×"
                tail = f" → {r['kind']}: {r['why']}"
            print(f"  {mark} #{r['id']:>2} [{r['group']}] {r['q'][:30]:<32}{tail}")
    return passed, fails, rows


def one_line(text, n=50):
    """여러 줄 답을 한 줄 n자로 줄인다 (설명용)."""
    t = " ".join(text.split())
    if len(t) > n:
        return t[:n] + "…"
    return t

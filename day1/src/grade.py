"""Day 1 블록 4 · 채점 코드.

같은 20문항(tests.jsonl)에 프롬프트를 돌려 통과 수와 실패 유형을 센다.
과제: 사내 문의 메시지 하나를 받아 카테고리·긴급도·요약으로 분류한다.

    python -m src.grade prompts/prompt_4.txt
    python -m src.grade prompts/prompt_4.txt prompts/prompt_5.txt        # 나란히 비교
    python -m src.grade solutions/prompts/prompt_6.txt --model claude-haiku-4-5-20251001
    python -m src.grade prompts/prompt_6.txt --all-models                 # 모델 셋으로 비교

프롬프트 파일 규칙
- 파일 안의 {document} 자리에 문의 내용이 들어간다.
- 파일 맨 위에 '=== system ===' / '=== user ===' 구분선을 두면 system과 user로 나눠 보낸다.
  구분선이 없으면 파일 전체가 user 메시지가 된다.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from common import llm

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "data" / "tests.jsonl"
RESULTS = ROOT / "results"

# 실패 유형 네 가지 — 슬라이드와 같은 이름
FORMAT = "형식 위반"
FACT = "사실 오류"
MISSING = "지시 일부 누락"
INVENTED = "지어냄"
KINDS = [FORMAT, FACT, MISSING, INVENTED]

# 정해진 보기 — 모델은 이 안에서만 골라야 한다
CATEGORIES = ["비품", "시설", "인사", "IT", "기타"]
URGENCY = ["높음", "보통", "낮음"]


# ---------------------------------------------------------------- 테스트 읽기
def load_tests(path: str | Path = TESTS) -> list[dict]:
    """tests.jsonl을 읽는다. "input"이 있으면 그대로, "doc" 경로면 파일을 읽어 채운다."""
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    tests = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        t = json.loads(line)
        if "input" not in t:                       # doc 경로로 적은 문항
            t["input"] = (ROOT / t["doc"]).read_text(encoding="utf-8")
        tests.append(t)
    return tests


# ---------------------------------------------------------------- 프롬프트 나누기
def split_prompt(prompt: str) -> tuple[str | None, str]:
    """'=== system ===' / '=== user ===' 구분선으로 나눈다."""
    m = re.search(r"^===\s*system\s*===\s*$(.*?)^===\s*user\s*===\s*$(.*)", prompt,
                  flags=re.S | re.M | re.I)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, prompt


def build(prompt: str, document: str) -> tuple[str | None, str]:
    system, user = split_prompt(prompt)
    if "{document}" not in user and (system is None or "{document}" not in system):
        user = user.rstrip() + "\n\n<문의>\n{document}\n</문의>"   # 자리를 잊었을 때
    if system:
        system = llm.render(system, document=document)
    return system, llm.render(user, document=document)


# ---------------------------------------------------------------- 파싱
def parse(text: str):
    """모델 출력에서 JSON을 꺼낸다.

    1) <json> … </json> 태그가 있으면 그 안만 쓴다 (출력 형식을 태그로 감싸게 한다)
    2) 없으면 출력 전체를 그대로 json.loads 한다 — 앞뒤에 설명이 붙으면 실패
    실패하면 ValueError
    """
    m = re.search(r"<json>(.*?)</json>", text, flags=re.S)
    body = m.group(1) if m else text
    body = body.strip()
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON이 아님: {e.msg} (위치 {e.pos})") from None


def schema_errors(out) -> list[str]:
    """목표 JSON 모양: {"카테고리": 보기 중 하나, "긴급도": 보기 중 하나, "요약": str}"""
    if not isinstance(out, dict):
        return ["최상위가 객체가 아님"]
    errs = []
    cat = out.get("카테고리")
    if cat not in CATEGORIES:
        errs.append(f"'카테고리'가 보기 중에 없음: {cat!r} (보기: {', '.join(CATEGORIES)})")
    urg = out.get("긴급도")
    if urg not in URGENCY:
        errs.append(f"'긴급도'가 보기 중에 없음: {urg!r} (보기: {', '.join(URGENCY)})")
    if not isinstance(out.get("요약"), str) or not out["요약"].strip():
        errs.append("'요약'이 없거나 빈 문자열임")
    return errs


# ---------------------------------------------------------------- 판정
def check(text: str, spec: dict) -> tuple[bool, str | None, str]:
    """출력 하나를 판정한다 → (통과 여부, 실패 유형, 설명)

    판정 순서 — 앞에서 걸리면 거기서 멈춘다
      1. 형식 위반     JSON이 아니거나, 카테고리·긴급도가 정해진 보기 밖이거나, 요약이 없다
      2. 지어냄        정답이 "기타"인데 구체적인 카테고리를 지어냄
      3. 지시 일부 누락 요약에 꼭 있어야 할 말(has)이 없다
      4. 사실 오류     카테고리 또는 긴급도가 정답과 다르다
    """
    try:
        out = parse(text)
    except ValueError as e:
        return False, FORMAT, str(e)
    errs = schema_errors(out)
    if errs:
        return False, FORMAT, "; ".join(errs[:2])

    cat, urg, summary = out["카테고리"], out["긴급도"], out["요약"]
    want_cat = spec["category"]

    # 2. 지어냄 — 정답 없음(기타)인데 그럴듯한 카테고리를 만들어냄
    if want_cat == "기타" and cat != "기타":
        return False, INVENTED, f"'기타'여야 하는데 '{cat}'를 지어냄"

    # 3. 지시 일부 누락 — 요약에 꼭 들어가야 할 말이 없음
    word = spec.get("has")
    if word and word not in summary:
        return False, MISSING, f"요약에 '{word}'가 없음: {summary!r}"

    # 4. 사실 오류 — 카테고리 · 긴급도가 정답과 다름
    if cat != want_cat:
        return False, FACT, f"카테고리 기대 '{want_cat}', 출력 '{cat}'"
    if urg != spec["urgency"]:
        return False, FACT, f"긴급도 기대 '{spec['urgency']}', 출력 '{urg}'"

    return True, None, ""


# ---------------------------------------------------------------- 실행
def _one(prompt, t, model):
    system, user = build(prompt, t["input"])
    try:
        r = llm.call(user, system, model=model, max_tokens=1500)   # 사고(thinking)가 켜진 모델은 그 토큰도 여기 포함된다
    except Exception as e:                                    # 네트워크 · 키 오류도 기록
        return dict(id=t["id"], group=t.get("group", ""), ok=False, kind="호출 실패",
                    why=f"{type(e).__name__}: {e}", text="", input_tokens=0, output_tokens=0,
                    seconds=0.0, stop_reason="")
    ok, kind, why = check(r.text, t["check"])
    if not ok and r.stop_reason == "max_tokens":
        why += " (max_tokens에서 잘림)"
    return dict(id=t["id"], group=t.get("group", ""), ok=ok, kind=kind, why=why, text=r.text,
                input_tokens=r.input_tokens, output_tokens=r.output_tokens,
                seconds=round(r.seconds, 2), stop_reason=r.stop_reason)


def run(prompt: str, *, model: str | None = None, tests: list[dict] | None = None,
        workers: int = 4, detail: bool = False):
    """프롬프트 하나를 전 문항에 돌린다.

    prompt — 프롬프트 본문, 또는 .txt 파일 경로
    반환   — (passed, fails)   fails = [(id, 유형), …]
             detail=True 이면 (passed, fails, rows) — rows는 문항별 상세
    """
    if isinstance(prompt, Path) or (isinstance(prompt, str) and prompt.endswith(".txt")
                                    and "\n" not in prompt):
        prompt = llm.load_prompt(ROOT / prompt)
    tests = tests if tests is not None else load_tests()
    model = model or llm.MODEL
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        rows = list(ex.map(lambda t: _one(prompt, t, model), tests))
    passed = sum(r["ok"] for r in rows)
    fails = [(r["id"], r["kind"]) for r in rows if not r["ok"]]
    return (passed, fails, rows) if detail else (passed, fails)


def summarize(rows: list[dict], model: str) -> dict:
    n = len(rows)
    counts = {k: sum(1 for r in rows if r["kind"] == k) for k in KINDS}
    counts["호출 실패"] = sum(1 for r in rows if r["kind"] == "호출 실패")
    tin = sum(r["input_tokens"] for r in rows)
    tout = sum(r["output_tokens"] for r in rows)
    c = llm.cost(model, tin, tout)
    return dict(passed=sum(r["ok"] for r in rows), total=n, **counts,
                input_tokens=tin, output_tokens=tout,
                avg_seconds=round(sum(r["seconds"] for r in rows) / max(n, 1), 2),
                cost_per_item=None if c is None else c / max(n, 1))


# ---------------------------------------------------------------- 출력 · 저장
def print_table(results: list[tuple[str, str, dict]]):
    """결과표 — 슬라이드 '결과 읽기'와 같은 열"""
    head = ["프롬프트", "모델", "통과", *KINDS, "평균 초", "1건 비용"]
    rows = [[name, model.replace("claude-", ""), f"{s['passed']} / {s['total']}",
             *[str(s[k]) for k in KINDS], f"{s['avg_seconds']:.2f}", llm.fmt_cost(s["cost_per_item"])]
            for name, model, s in results]
    widths = [max(_w(x) for x in col) for col in zip(head, *rows)]
    line = lambda r: "  ".join(x + " " * (w - _w(x)) for x, w in zip(r, widths))
    print(line(head))
    print("-" * (sum(widths) + 2 * (len(widths) - 1)))
    for r in rows:
        print(line(r))


def _w(s: str) -> int:   # 한글은 두 칸
    return sum(2 if ord(ch) > 0x1100 else 1 for ch in s)


def print_fails(rows: list[dict], limit: int = 20):
    bad = [r for r in rows if not r["ok"]]
    if not bad:
        return
    print("\n실패 문항")
    for r in bad[:limit]:
        print(f"  #{r['id']:>2} [{r['group']}] {r['kind']} — {r['why']}")


def save(name: str, model: str, rows: list[dict], s: dict, note: str = "") -> Path:
    RESULTS.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    stem = Path(name).stem
    out = RESULTS / f"run_{stamp}_{stem}_{model.replace('claude-', '')}.json"
    out.write_text(json.dumps(dict(prompt=name, model=model, summary=s, rows=rows, mock=llm.MOCK),
                              ensure_ascii=False, indent=2), encoding="utf-8")
    board = RESULTS / "scoreboard.csv"
    new = not board.exists()
    with board.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["시각", "프롬프트", "모델", "통과", "전체", *KINDS, "평균 초", "1건 비용($)", "바꾼 것", "모의"])
        w.writerow([stamp, name, model, s["passed"], s["total"], *[s[k] for k in KINDS],
                    s["avg_seconds"], "" if s["cost_per_item"] is None else f"{s['cost_per_item']:.5f}",
                    note, "Y" if llm.MOCK else ""])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="프롬프트를 고정 20문항으로 채점한다")
    ap.add_argument("prompts", nargs="+", help="프롬프트 파일 (여러 개면 나란히 비교)")
    ap.add_argument("--model", default=None, help=f"기본값 {llm.MODEL}")
    ap.add_argument("--all-models", action="store_true", help="llm.MODELS 전부로 돌린다")
    ap.add_argument("--tests", default=str(TESTS))
    ap.add_argument("--only", default=None, help="일부 문항만: 예) 1,3,16-18")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--note", default="", help="결과표 '바꾼 것' 칸에 남길 한 줄")
    ap.add_argument("--quiet", action="store_true", help="실패 문항 목록을 숨긴다")
    a = ap.parse_args(argv)

    tests = load_tests(a.tests)
    if a.only:
        keep = set()
        for part in a.only.split(","):
            lo, _, hi = part.partition("-")
            keep.update(range(int(lo), int(hi or lo) + 1))
        tests = [t for t in tests if t["id"] in keep]

    models = llm.MODELS if a.all_models else [a.model or llm.MODEL]
    if llm.MOCK:
        print("※ LLM_MOCK=1 — 실제 모델을 부르지 않습니다. 흐름 확인용 결과입니다.\n")

    table = []
    for p in a.prompts:
        for m in models:
            t0 = time.perf_counter()
            _, _, rows = run(p, model=m, tests=tests, workers=a.workers, detail=True)
            s = summarize(rows, m)
            path = save(p, m, rows, s, a.note)
            table.append((Path(p).name, m, s))
            print(f"· {Path(p).name} × {m}  {s['passed']}/{s['total']}  "
                  f"({time.perf_counter() - t0:.1f}초) → {path.relative_to(ROOT)}")
            if not a.quiet:
                print_fails(rows)
            if s["호출 실패"]:
                print(f"  ! 호출 실패 {s['호출 실패']}건 — .env의 ANTHROPIC_API_KEY와 모델 이름을 확인하세요")
            print()
    print_table(table)
    print(f"\n누적 기록: {(RESULTS / 'scoreboard.csv').relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())

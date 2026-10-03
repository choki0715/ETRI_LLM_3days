"""Day 1 블록 4 · 채점 코드.

같은 20문항(tests.jsonl)에 프롬프트를 돌려 통과 수와 실패 유형을 센다.

    python -m src.grade prompts/prompt_v1.txt
    python -m src.grade prompts/prompt_v1.txt prompts/prompt_v2.txt      # 나란히 비교
    python -m src.grade solutions/prompts/prompt_v3.txt --model claude-haiku-4-5-20251001
    python -m src.grade prompts/prompt_v3.txt --all-models                # 3차

프롬프트 파일 규칙
- 파일 안의 {document} 자리에 문서가 들어간다.
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

MAX_ITEMS = 3


# ---------------------------------------------------------------- 테스트 읽기
def load_tests(path: str | Path = TESTS) -> list[dict]:
    """tests.jsonl을 읽는다. 문항마다 문서 본문을 t["input"]에 채워 둔다."""
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
        user = user.rstrip() + "\n\n<문서>\n{document}\n</문서>"   # 자리를 잊었을 때
    if system:
        system = llm.render(system, document=document)
    return system, llm.render(user, document=document)


# ---------------------------------------------------------------- 파싱
def parse(text: str):
    """모델 출력에서 JSON을 꺼낸다.

    1) <json> … </json> 태그가 있으면 그 안만 쓴다 (기법 6 · 태그로 감싸게 한다)
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


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def schema_errors(out) -> list[str]:
    """목표 JSON 모양: {"제목": str, "항목": [{"이름": str, "값": number|null, "단위": str|null}]}"""
    errs = []
    if not isinstance(out, dict):
        return ["최상위가 객체가 아님"]
    if not isinstance(out.get("제목"), str):
        errs.append("'제목'이 문자열이 아님")
    items = out.get("항목")
    if not isinstance(items, list):
        return errs + ["'항목'이 목록이 아님"]
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            errs.append(f"항목[{i}]이 객체가 아님")
            continue
        if not isinstance(it.get("이름"), str):
            errs.append(f"항목[{i}] '이름'이 문자열이 아님")
        if "값" not in it or not (it["값"] is None or _is_num(it["값"])):
            errs.append(f"항목[{i}] '값'이 숫자가 아님: {it.get('값')!r}")
        if "단위" not in it or not (it["단위"] is None or isinstance(it["단위"], str)):
            errs.append(f"항목[{i}] '단위'가 문자열이 아님")
    return errs


# ---------------------------------------------------------------- 숫자 비교
# "340만원"을 340(단위 만원)으로 뽑든 3400000(단위 원)으로 뽑든 둘 다 맞게 본다
_SCALES = (1, 10_000, 100_000_000)


def same_number(got, want) -> bool:
    if not _is_num(got):
        return False
    for k in _SCALES:
        if abs(got - want * k) <= 1e-6 * max(1, abs(want * k)):
            return True
    return False


def _find(items, key):
    for it in items:
        if isinstance(it.get("이름"), str) and key in it["이름"].replace(" ", ""):
            return it
    return None


# ---------------------------------------------------------------- 판정
def check(text: str, spec: dict) -> tuple[bool, str | None, str]:
    """출력 하나를 판정한다 → (통과 여부, 실패 유형, 설명)

    판정 순서 — 앞에서 걸리면 거기서 멈춘다
      1. 형식 위반     JSON이 아니거나 모양이 다르다
      2. 지어냄        문서에 없는 값을 채웠다 (absent 이름에 값이 있음, 답없음 문서에 항목이 있음)
      3. 지시 일부 누락 값이 있는 항목 수가 items와 다르다 (값이 null인 항목은 세지 않는다)
      4. 사실 오류     values의 숫자와 다르다
    """
    try:
        out = parse(text)
    except ValueError as e:
        return False, FORMAT, str(e)
    errs = schema_errors(out)
    if errs:
        return False, FORMAT, "; ".join(errs[:2])

    items = out["항목"]
    filled = [it for it in items if it["값"] is not None]

    # 2. 지어냄
    for name in spec.get("absent", []):
        it = _find(items, name)
        if it and it["값"] is not None:
            return False, INVENTED, f"문서에 없는 '{name}'에 값 {it['값']}을 채움"
    if spec.get("items") == 0 and filled:
        return False, INVENTED, f"수치가 없는 문서에서 {len(filled)}개를 뽑음: " + \
            ", ".join(f"{it['이름']}={it['값']}" for it in filled[:3])

    # 3. 지시 일부 누락
    want = spec.get("items")
    if len(filled) > MAX_ITEMS:
        return False, MISSING, f"값이 있는 항목 {len(filled)}개 — 최대 {MAX_ITEMS}개"
    if want is not None and len(filled) != want:
        return False, MISSING, f"값이 있는 항목 {len(filled)}개 — 기대 {want}개"
    for word in ([spec["has"]] if isinstance(spec.get("has"), str) else spec.get("has", [])):
        if word not in json.dumps(out, ensure_ascii=False):
            return False, MISSING, f"'{word}'가 답에 없음"

    # 4. 사실 오류
    for key, val in spec.get("values", {}).items():
        it = _find(filled, key)
        if it is not None and same_number(it["값"], val):
            continue
        if any(same_number(x["값"], val) for x in filled):   # 이름이 달라도 값이 맞으면 통과
            continue
        got = f"{it['이름']}={it['값']}" if it else "해당 항목 없음"
        return False, FACT, f"'{key}' 기대 {val}, 출력 {got}"

    return True, None, ""


# ---------------------------------------------------------------- 실행
def _one(prompt, t, model):
    system, user = build(prompt, t["input"])
    try:
        r = llm.call(user, system, model=model, max_tokens=1000)
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
    ap.add_argument("--all-models", action="store_true", help="llm.MODELS 전부로 돌린다 (3차)")
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

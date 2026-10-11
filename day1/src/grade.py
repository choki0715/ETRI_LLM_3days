"""Day 1 4세션 · 채점 코드.

같은 20문항(tests.jsonl)에 프롬프트를 돌려 통과 수와 실패 유형을 센다.
과제: 사내 문의 메시지 하나를 받아 카테고리·긴급도·요약으로 분류한다.

    python -m src.grade prompts/prompt_4.txt
    python -m src.grade prompts/prompt_4.txt prompts/prompt_5.txt        # 나란히 비교
    python -m src.grade solutions/prompts/prompt_6.txt --model claude-haiku-5-5
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
        test = json.loads(line)
        if "input" not in test:                    # doc 경로로 적은 문항
            test["input"] = (ROOT / test["doc"]).read_text(encoding="utf-8")
        tests.append(test)
    return tests


# ---------------------------------------------------------------- 프롬프트 나누기
def split_prompt(prompt: str) -> tuple[str | None, str]:
    """'=== system ===' / '=== user ===' 구분선으로 나눈다."""
    match = re.search(r"^===\s*system\s*===\s*$(.*?)^===\s*user\s*===\s*$(.*)", prompt,
                       flags=re.S | re.M | re.I)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None, prompt


def build(prompt: str, document: str) -> tuple[str | None, str]:
    system, user = split_prompt(prompt)

    # 프롬프트 어딘가에 {document} 자리가 이미 있는지 본다 (없으면 user 끝에 만들어 준다)
    placeholder_in_user = "{document}" in user
    placeholder_in_system = system is not None and "{document}" in system
    if not placeholder_in_user and not placeholder_in_system:
        user = user.rstrip() + "\n\n<문의>\n{document}\n</문의>"

    if system:
        system = llm.render(system, document=document)
    user = llm.render(user, document=document)
    return system, user


# ---------------------------------------------------------------- 파싱
def parse(text: str):
    """모델 출력에서 JSON을 꺼낸다.

    1) <json> … </json> 태그가 있으면 그 안만 쓴다 (출력 형식을 태그로 감싸게 한다)
    2) 없으면 출력 전체를 그대로 json.loads 한다 — 앞뒤에 설명이 붙으면 실패
    실패하면 ValueError
    """
    match = re.search(r"<json>(.*?)</json>", text, flags=re.S)
    if match:
        body = match.group(1)
    else:
        body = text
    body = body.strip()

    try:
        return json.loads(body)
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON이 아님: {error.msg} (위치 {error.pos})") from None


def schema_errors(out) -> list[str]:
    """목표 JSON 모양: {"카테고리": 보기 중 하나, "긴급도": 보기 중 하나, "요약": str}"""
    if not isinstance(out, dict):
        return ["최상위가 객체가 아님"]

    errors = []
    category = out.get("카테고리")
    if category not in CATEGORIES:
        errors.append(f"'카테고리'가 보기 중에 없음: {category!r} (보기: {', '.join(CATEGORIES)})")

    urgency = out.get("긴급도")
    if urgency not in URGENCY:
        errors.append(f"'긴급도'가 보기 중에 없음: {urgency!r} (보기: {', '.join(URGENCY)})")

    summary = out.get("요약")
    if not isinstance(summary, str) or not summary.strip():
        errors.append("'요약'이 없거나 빈 문자열임")

    return errors


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
    except ValueError as error:
        return False, FORMAT, str(error)

    errors = schema_errors(out)
    if errors:
        return False, FORMAT, "; ".join(errors[:2])

    category = out["카테고리"]
    urgency = out["긴급도"]
    summary = out["요약"]
    expected_category = spec["category"]
    expected_urgency = spec["urgency"]

    # 2. 지어냄 — 정답 없음(기타)인데 그럴듯한 카테고리를 만들어냄
    if expected_category == "기타" and category != "기타":
        return False, INVENTED, f"'기타'여야 하는데 '{category}'를 지어냄"

    # 3. 지시 일부 누락 — 요약에 꼭 들어가야 할 말이 없음
    required_word = spec.get("has")
    if required_word and required_word not in summary:
        return False, MISSING, f"요약에 '{required_word}'가 없음: {summary!r}"

    # 4. 사실 오류 — 카테고리 · 긴급도가 정답과 다름
    if category != expected_category:
        return False, FACT, f"카테고리 기대 '{expected_category}', 출력 '{category}'"
    if urgency != expected_urgency:
        return False, FACT, f"긴급도 기대 '{expected_urgency}', 출력 '{urgency}'"

    return True, None, ""


# ---------------------------------------------------------------- 실행
def _grade_single_test(prompt: str, test: dict, model: str) -> dict:
    """문항 하나에 모델을 한 번 부르고 판정한다. run()이 문항마다 이 함수를 부른다."""
    system, user = build(prompt, test["input"])
    try:
        # 사고(thinking)가 켜진 모델은 그 토큰도 output_tokens에 포함된다
        result = llm.call(user, system, model=model, max_tokens=1500)
    except Exception as error:                    # 네트워크 · 키 오류도 기록
        return {
            "id": test["id"],
            "group": test.get("group", ""),
            "ok": False,
            "kind": "호출 실패",
            "why": f"{type(error).__name__}: {error}",
            "text": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "seconds": 0.0,
            "stop_reason": "",
        }

    ok, kind, why = check(result.text, test["check"])
    if not ok and result.stop_reason == "max_tokens":
        why = why + " (max_tokens에서 잘림)"

    return {
        "id": test["id"],
        "group": test.get("group", ""),
        "ok": ok,
        "kind": kind,
        "why": why,
        "text": result.text,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "seconds": round(result.seconds, 2),
        "stop_reason": result.stop_reason,
    }


def run(prompt: str, *, model: str | None = None, tests: list[dict] | None = None,
        detail: bool = False):
    """프롬프트 하나를 전 문항에 돌린다.

    prompt — 프롬프트 본문, 또는 .txt 파일 경로
    반환   — (passed, fails)   fails = [(id, 유형), …]
             detail=True 이면 (passed, fails, rows) — rows는 문항별 상세
    """
    # prompt가 파일 경로처럼 보이면(Path 객체, 또는 줄바꿈 없이 .txt로 끝나는 문자열)
    # 그 파일을 읽어 내용으로 바꾼다. 이미 여러 줄짜리 프롬프트 글자가 왔으면 그대로 쓴다.
    looks_like_path = False
    if isinstance(prompt, Path):
        looks_like_path = True
    if isinstance(prompt, str) and prompt.endswith(".txt") and "\n" not in prompt:
        looks_like_path = True
    if looks_like_path:
        prompt = llm.load_prompt(ROOT / prompt)

    if tests is None:
        tests = load_tests()
    if model is None:
        model = llm.MODEL

    # 문항을 하나씩 차례로 채점한다 — 모델을 한 번 부르고, 판정하고, 결과를 rows에 쌓는다
    rows = []
    for test in tests:
        row = _grade_single_test(prompt, test, model)
        rows.append(row)

    passed = 0
    fails = []
    for row in rows:
        if row["ok"]:
            passed = passed + 1
        else:
            fails.append((row["id"], row["kind"]))

    if detail:
        return passed, fails, rows
    return passed, fails


def summarize(rows: list[dict], model: str) -> dict:
    """문항별 결과(rows)를 하나로 모은다 — 통과 수 · 실패 유형별 개수 · 토큰 · 비용."""
    total = len(rows)
    item_count = total
    if item_count == 0:
        item_count = 1                              # 0으로 나누지 않으려고 최소 1로 본다

    kind_counts = {}
    for kind in KINDS:
        kind_counts[kind] = 0

    passed = 0
    call_failures = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_seconds = 0.0
    for row in rows:
        if row["ok"]:
            passed = passed + 1
        if row["kind"] == "호출 실패":
            call_failures = call_failures + 1
        if row["kind"] in kind_counts:
            kind_counts[row["kind"]] = kind_counts[row["kind"]] + 1
        total_input_tokens = total_input_tokens + row["input_tokens"]
        total_output_tokens = total_output_tokens + row["output_tokens"]
        total_seconds = total_seconds + row["seconds"]

    cost = llm.cost(model, total_input_tokens, total_output_tokens)
    if cost is None:
        cost_per_item = None
    else:
        cost_per_item = cost / item_count

    summary = {
        "passed": passed,
        "total": total,
        "호출 실패": call_failures,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "avg_seconds": round(total_seconds / item_count, 2),
        "cost_per_item": cost_per_item,
    }
    for kind in KINDS:
        summary[kind] = kind_counts[kind]
    return summary


# ---------------------------------------------------------------- 출력 · 저장
def _display_width(text: str) -> int:
    """표의 칸을 맞출 때 쓰는 너비. 한글 한 글자는 영문 두 칸만큼 넓게 본다."""
    width = 0
    for character in text:
        if ord(character) > 0x1100:
            width = width + 2
        else:
            width = width + 1
    return width


def print_table(results: list[tuple[str, str, dict]]):
    """결과표 — 슬라이드 '결과 읽기'와 같은 열"""
    headers = ["프롬프트", "모델", "통과"]
    for kind in KINDS:
        headers.append(kind)
    headers.append("평균 초")
    headers.append("1건 비용")

    table_rows = []
    for name, model, summary in results:
        row = [name, model.replace("claude-", ""), f"{summary['passed']} / {summary['total']}"]
        for kind in KINDS:
            row.append(str(summary[kind]))
        row.append(f"{summary['avg_seconds']:.2f}")
        row.append(llm.fmt_cost(summary["cost_per_item"]))
        table_rows.append(row)

    column_count = len(headers)
    widths = []
    for col in range(column_count):
        max_width = _display_width(headers[col])
        for row in table_rows:
            cell_width = _display_width(row[col])
            if cell_width > max_width:
                max_width = cell_width
        widths.append(max_width)

    def format_row(row):
        parts = []
        for col in range(column_count):
            cell = row[col]
            pad = widths[col] - _display_width(cell)
            parts.append(cell + " " * pad)
        return "  ".join(parts)

    print(format_row(headers))
    print("-" * (sum(widths) + 2 * (column_count - 1)))
    for row in table_rows:
        print(format_row(row))


def print_fails(rows: list[dict], limit: int = 20):
    failed_rows = []
    for row in rows:
        if not row["ok"]:
            failed_rows.append(row)
    if not failed_rows:
        return

    print("\n실패 문항")
    for row in failed_rows[:limit]:
        print(f"  #{row['id']:>2} [{row['group']}] {row['kind']} — {row['why']}")


def save(name: str, model: str, rows: list[dict], summary: dict, note: str = "") -> Path:
    """결과 전체를 JSON 파일로 남기고, 한 줄 요약을 scoreboard.csv에 덧붙인다."""
    RESULTS.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    prompt_stem = Path(name).stem
    model_for_filename = model.replace("claude-", "")
    detail_path = RESULTS / f"run_{timestamp}_{prompt_stem}_{model_for_filename}.json"

    detail_data = {
        "prompt": name,
        "model": model,
        "summary": summary,
        "rows": rows,
        "mock": llm.MOCK,
    }
    detail_path.write_text(json.dumps(detail_data, ensure_ascii=False, indent=2), encoding="utf-8")

    scoreboard_path = RESULTS / "scoreboard.csv"
    file_is_new = not scoreboard_path.exists()
    with scoreboard_path.open("a", newline="", encoding="utf-8-sig") as scoreboard_file:
        writer = csv.writer(scoreboard_file)

        if file_is_new:
            header = ["시각", "프롬프트", "모델", "통과", "전체"]
            for kind in KINDS:
                header.append(kind)
            header.append("평균 초")
            header.append("1건 비용($)")
            header.append("바꾼 것")
            header.append("모의")
            writer.writerow(header)

        if summary["cost_per_item"] is None:
            cost_text = ""
        else:
            cost_text = f"{summary['cost_per_item']:.5f}"
        if llm.MOCK:
            mock_text = "Y"
        else:
            mock_text = ""

        row_values = [timestamp, name, model, summary["passed"], summary["total"]]
        for kind in KINDS:
            row_values.append(summary[kind])
        row_values.append(summary["avg_seconds"])
        row_values.append(cost_text)
        row_values.append(note)
        row_values.append(mock_text)
        writer.writerow(row_values)

    return detail_path


def main(argv=None):
    parser = argparse.ArgumentParser(description="프롬프트를 고정 20문항으로 채점한다")
    parser.add_argument("prompts", nargs="+", help="프롬프트 파일 (여러 개면 나란히 비교)")
    parser.add_argument("--model", default=None, help=f"기본값 {llm.MODEL}")
    parser.add_argument("--all-models", action="store_true", help="llm.MODELS 전부로 돌린다")
    parser.add_argument("--tests", default=str(TESTS))
    parser.add_argument("--only", default=None, help="일부 문항만: 예) 1,3,16-18")
    parser.add_argument("--note", default="", help="결과표 '바꾼 것' 칸에 남길 한 줄")
    parser.add_argument("--quiet", action="store_true", help="실패 문항 목록을 숨긴다")
    args = parser.parse_args(argv)

    tests = load_tests(args.tests)
    if args.only:
        wanted_ids = set()
        for part in args.only.split(","):
            low_text, separator, high_text = part.partition("-")
            start = int(low_text)
            if high_text:
                end = int(high_text)
            else:
                end = start
            for test_id in range(start, end + 1):
                wanted_ids.add(test_id)

        filtered_tests = []
        for test in tests:
            if test["id"] in wanted_ids:
                filtered_tests.append(test)
        tests = filtered_tests

    if args.all_models:
        models = llm.MODELS
    else:
        if args.model:
            models = [args.model]
        else:
            models = [llm.MODEL]

    if llm.MOCK:
        print("※ LLM_MOCK=1 — 실제 모델을 부르지 않습니다. 흐름 확인용 결과입니다.\n")

    table_rows = []
    for prompt_path in args.prompts:
        for model_name in models:
            start_time = time.perf_counter()
            _, _, rows = run(prompt_path, model=model_name, tests=tests, detail=True)
            summary = summarize(rows, model_name)
            saved_path = save(prompt_path, model_name, rows, summary, args.note)
            table_rows.append((Path(prompt_path).name, model_name, summary))

            elapsed = time.perf_counter() - start_time
            print(f"· {Path(prompt_path).name} × {model_name}  "
                  f"{summary['passed']}/{summary['total']}  ({elapsed:.1f}초) → "
                  f"{saved_path.relative_to(ROOT)}")
            if not args.quiet:
                print_fails(rows)
            if summary["호출 실패"]:
                print(f"  ! 호출 실패 {summary['호출 실패']}건 — "
                      f".env의 ANTHROPIC_API_KEY와 모델 이름을 확인하세요")
            print()

    print_table(table_rows)
    print(f"\n누적 기록: {(RESULTS / 'scoreboard.csv').relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())

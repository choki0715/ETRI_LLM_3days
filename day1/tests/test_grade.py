"""채점 로직 점검 — API 없이 가짜 출력으로 check()를 확인한다.  python -m pytest tests -q"""
import json
from src.grade import check, parse, load_tests, build, split_prompt, FORMAT, FACT, MISSING, INVENTED
from common import llm

SPEC1 = {"items": 3, "values": {"복사용지": 120, "토너": 8, "예산": 340}}
GOOD1 = {"제목": "2026년 4분기 사무용품 구매 계획", "항목": [
    {"이름": "복사용지", "값": 120, "단위": "박스"},
    {"이름": "프린터 토너", "값": 8, "단위": "개"},
    {"이름": "전체 예산", "값": 340, "단위": "만원"}]}
J = lambda o: json.dumps(o, ensure_ascii=False)


def test_pass_plain():
    assert check(J(GOOD1), SPEC1)[0]

def test_pass_tagged_with_reasoning():
    assert check("<근거>…</근거>\n<json>" + J(GOOD1) + "</json>", SPEC1)[0]

def test_pass_won_scale():
    o = json.loads(J(GOOD1)); o["항목"][2] = {"이름": "예산", "값": 3400000, "단위": "원"}
    assert check(J(o), SPEC1)[0]

def test_format_fence():
    assert check("```json\n" + J(GOOD1) + "\n```", SPEC1)[1] == FORMAT

def test_format_preamble():
    assert check("다음과 같습니다.\n" + J(GOOD1), SPEC1)[1] == FORMAT

def test_format_string_value():
    o = json.loads(J(GOOD1)); o["항목"][0]["값"] = "120박스"
    assert check(J(o), SPEC1)[1] == FORMAT

def test_missing_two_items():
    o = json.loads(J(GOOD1)); o["항목"] = o["항목"][:2]
    assert check(J(o), SPEC1)[1] == MISSING

def test_fact_wrong_number():
    o = json.loads(J(GOOD1)); o["항목"][1]["값"] = 2
    ok, kind, why = check(J(o), SPEC1)
    assert kind == FACT and "토너" in why

def test_invented_budget():
    spec = {"items": 2, "values": {"참석": 7, "회의": 60}, "absent": ["예산"]}
    o = {"제목": "회의록", "항목": [{"이름": "참석자", "값": 7, "단위": "명"},
                                 {"이름": "회의 시간", "값": 60, "단위": "분"},
                                 {"이름": "마케팅 예산", "값": 5000, "단위": "만원"}]}
    assert check(J(o), spec)[1] == INVENTED
    o["항목"][2]["값"] = None; o["항목"][2]["단위"] = None      # null이면 통과
    assert check(J(o), spec)[0]

def test_no_numbers_doc():
    spec = {"items": 0}
    assert check(J({"제목": "동호회", "항목": []}), spec)[0]
    assert check(J({"제목": "동호회", "항목": [{"이름": "회비", "값": 1, "단위": "만원"}]}), spec)[1] == INVENTED

def test_korean_numeral_doc():
    spec = {"items": 3, "values": {"대상": 22, "평균": 81.5, "탈락": 3}}
    o = {"제목": "협력사 평가", "항목": [{"이름": "평가 대상 협력사", "값": 22, "단위": "곳"},
                                    {"이름": "평균 점수", "값": 81.5, "단위": "점"},
                                    {"이름": "탈락 협력사", "값": 3, "단위": "곳"}]}
    assert check(J(o), spec)[0]
    o["항목"][0]["값"] = "스물두"
    assert check(J(o), spec)[1] == FORMAT

def test_tests_file():
    ts = load_tests()
    assert len(ts) == 20 and [t["id"] for t in ts] == list(range(1, 21))
    groups = [t["group"] for t in ts]
    assert groups.count("평범") == 10 and groups.count("경계") == 5
    assert groups.count("답없음") == 3 and groups.count("틀렸던") == 2
    for t in ts:                             # 기대 수치가 실제로 문서에 있는가
        assert t["input"].strip()

def test_prompt_files_build():
    for p in ["prompts/prompt_v0.txt", "solutions/prompts/prompt_v1.txt",
              "solutions/prompts/prompt_v2.txt", "solutions/prompts/prompt_v3.txt"]:
        system, user = build(llm.load_prompt(p), "DOC_BODY")
        assert "DOC_BODY" in user and "{document}" not in user
    s, u = split_prompt(llm.load_prompt("solutions/prompts/prompt_v3.txt"))
    assert s and "<규칙>" in s and "<문서>" in u

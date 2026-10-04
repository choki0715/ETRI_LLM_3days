"""채점 로직 점검 — API 없이 가짜 출력으로 check()를 확인한다.  python -m pytest tests -q"""
import json
from src.grade import check, parse, load_tests, build, split_prompt, FORMAT, FACT, MISSING, INVENTED
from common import llm

SPEC1 = {"category": "IT", "urgency": "보통", "has": "비밀번호"}
GOOD1 = {"카테고리": "IT", "긴급도": "보통", "요약": "비밀번호 재설정 요청"}
J = lambda o: json.dumps(o, ensure_ascii=False)


def test_pass_plain():
    assert check(J(GOOD1), SPEC1)[0]

def test_pass_tagged():
    assert check("<json>" + J(GOOD1) + "</json>", SPEC1)[0]

def test_format_fence():
    assert check("```json\n" + J(GOOD1) + "\n```", SPEC1)[1] == FORMAT

def test_format_preamble():
    assert check("다음과 같습니다.\n" + J(GOOD1), SPEC1)[1] == FORMAT

def test_format_bad_category():
    o = dict(GOOD1); o["카테고리"] = "컴퓨터"      # 정해진 보기 밖
    assert check(J(o), SPEC1)[1] == FORMAT

def test_format_bad_urgency():
    o = dict(GOOD1); o["긴급도"] = "매우높음"
    assert check(J(o), SPEC1)[1] == FORMAT

def test_format_empty_summary():
    o = dict(GOOD1); o["요약"] = ""
    assert check(J(o), SPEC1)[1] == FORMAT

def test_invented_when_etc_expected():
    spec = {"category": "기타", "urgency": "낮음"}
    o = {"카테고리": "IT", "긴급도": "낮음", "요약": "점심 메뉴 문의"}
    assert check(J(o), spec)[1] == INVENTED
    o["카테고리"] = "기타"                          # 기타면 통과
    assert check(J(o), spec)[0]

def test_missing_required_word():
    o = dict(GOOD1); o["요약"] = "문의 접수함"       # '비밀번호'가 없음
    assert check(J(o), SPEC1)[1] == MISSING

def test_fact_wrong_category():
    o = dict(GOOD1); o["카테고리"] = "비품"
    ok, kind, why = check(J(o), SPEC1)
    assert kind == FACT and "카테고리" in why

def test_fact_wrong_urgency():
    o = dict(GOOD1); o["긴급도"] = "높음"
    ok, kind, why = check(J(o), SPEC1)
    assert kind == FACT and "긴급도" in why

def test_underclaim_not_invented():
    """정답은 구체 카테고리인데 모델이 '기타'로 보수적으로 답하면 — 지어냄이 아니라 사실 오류."""
    spec = {"category": "IT", "urgency": "보통"}
    o = {"카테고리": "기타", "긴급도": "보통", "요약": "애매함"}
    assert check(J(o), spec)[1] == FACT

def test_tests_file():
    ts = load_tests()
    assert len(ts) == 20 and [t["id"] for t in ts] == list(range(1, 21))
    groups = [t["group"] for t in ts]
    assert groups.count("평범") == 10 and groups.count("경계") == 5
    assert groups.count("기타") == 3 and groups.count("틀렸던") == 2
    for t in ts:
        assert t["input"].strip()

def test_prompt_files_build():
    for p in ["prompts/prompt_v0.txt", "solutions/prompts/prompt_4.txt",
              "solutions/prompts/prompt_5.txt", "solutions/prompts/prompt_6.txt"]:
        system, user = build(llm.load_prompt(p), "DOC_BODY")
        assert "DOC_BODY" in user and "{document}" not in user
    s, u = split_prompt(llm.load_prompt("solutions/prompts/prompt_6.txt"))
    assert s and "<할 일>" in s and "<문의>" in u

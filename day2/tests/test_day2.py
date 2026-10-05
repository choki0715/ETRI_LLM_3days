"""API · 모델 다운로드 없이 도는 점검.   EMBED=hash python -m pytest tests -q"""
import os
os.environ.setdefault("EMBED", "hash")
os.environ["LLM_MOCK"] = "1"

from common import llm
from src import rag, qa, loop


def chunks():
    return rag.chunk_folder("data/kb")


def test_kb_and_chunks():
    ch = chunks()
    assert len(rag.load_folder("data/kb")) == 20
    assert all(40 <= len(c["text"]) <= 800 for c in ch)
    # 경조휴가 조항이 목록째 한 조각에 들어 있어야 한다 (조항 경계로 잘랐는가)
    c16 = [c for c in ch if c["text"].startswith("제16조")]
    assert c16 and "본인 결혼: 5일" in c16[0]["text"]


def test_chunk_no_structure():
    tiny = rag.chunk_folder("data/kb", max_len=80, overlap=0, pattern=None)
    assert len(tiny) > len(chunks())


def test_keyword_exact_code():
    kw = rag.Keyword(chunks())
    assert kw.search("AX-2041 정격 토크", 1)[0].source == "06_제품사양_AX-2041.txt"
    assert kw.search("사번 20231187", 1)[0].source == "09_조직_담당자.txt"


def test_index_search():
    idx = rag.Index.build(chunks(), name="t1")
    hits = idx.search("연차 사용 절차", 3)
    assert len(hits) == 3 and hits[0].value <= hits[-1].value
    assert any(h.source == "01_일반업무규칙.txt" for h in hits)
    only = idx.search("기준", 2, where={"파일": "10_구매_절차.txt"})
    assert all(h.source == "10_구매_절차.txt" for h in only)


def test_prompt_shape():
    hits = [rag.Hit("본문A", "a.txt", "제목A", 0.1), rag.Hit("본문B", "b.txt", "제목B", 0.2)]
    p = rag.make_prompt("질문?", hits)
    assert p.startswith("<규칙>") and p.rstrip().endswith("<질문>질문?</질문>")
    assert '<자료 번호="2" 출처="b.txt · 제목B">' in p
    assert rag.cited("맞습니다 [1]. 그리고 [2][1].") == [1, 2]


H = [rag.Hit("연차는 사용일 3일 전까지 신청", "01_일반업무규칙.txt", "제14조", 0.2),
     rag.Hit("숙박비 12만원", "02_출장비_지급규정.txt", "제3조", 0.4)]
SPEC = {"expect": ["3일"], "source": "01_일반업무규칙.txt"}


def test_check_qa_kinds():
    assert qa.check_qa("3일 전까지입니다 [1].", H, SPEC)[0]
    assert qa.check_qa("3일 전까지입니다 [2].", H, SPEC)[1] == "출처 오류"
    assert qa.check_qa("자료에 없음", H, SPEC)[1] == "있는데 못 씀"
    assert qa.check_qa("3일 [1]", H[1:], SPEC)[1] == "검색·청킹"
    assert qa.check_qa("3일 [1]", [rag.Hit("연차는 사용일", "01_일반업무규칙.txt", "x", 0.1)], SPEC)[1] == "검색·청킹"
    assert qa.check_qa("자료에 없음", H, {"refuse": True})[0]
    assert qa.check_qa("10%입니다", H, {"refuse": True})[1] == "지어냄"


def test_qa_file():
    t = qa.load_qa()
    assert len(t) == 10 and sum(x["group"] == "답없음" for x in t) == 3


def test_tools_and_loop_mock():
    assert loop.calculator(3, 120000, "mul") == 360000
    assert "0으로" in str(loop.calculator(1, 0, "div"))
    loop.SEARCH_INDEX = rag.Index.build(chunks(), name="t2")
    assert "출처=" in loop.search("숙박비")
    ans, trace = loop.run("서울 3박 숙박비 150000 합계", verbose=False)
    assert loop.tools_used(trace) == ["search", "calculator"]

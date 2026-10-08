"""hanbit-docs MCP 서버 — 한빛정밀 사내 자료 20편을 검색하는 도구 하나 (Day 3 1세션 실습).

    claude mcp add --transport stdio hanbit-docs -- /절대/경로/python /절대/경로/hanbit_mcp.py
    (Claude Code 안에서) /mcp  → hanbit-docs · Connected

어제(Day 2) loop.py의 search 도구를 MCP 서버로 떼어 낸 것이다.
loop.py에서는 우리 루프만 그 도구를 쓸 수 있었지만, MCP 서버로 만들면 Claude Code 같은 다른 프로그램도 붙여 쓸 수 있다.

관찰 실험: 도구 설명을 짧게 · 틀리게 바꿔 다시 등록하면 모델이 언제 부르는지가 달라지는가 (README 5 · 6번).
    claude mcp remove hanbit-docs
    claude mcp add --transport stdio hanbit-docs -e MCP_DESC=short -- /절대/경로/python /절대/경로/hanbit_mcp.py   # 또는 wrong

파일 순서
    1. 도구 설명   — LONG / SHORT (모델이 읽고 언제 부를지 정하는 글)
    2. 자료 읽기   — load_paragraphs (Day 2 사내 자료를 문단으로 자른다)
    3. 검색       — search (질문과 글자가 많이 겹치는 문단을 고른다)
    4. 도구       — search_docs (모델이 부르면 검색 결과를 출처와 함께 돌려준다)
"""
import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer

HERE = Path(__file__).resolve().parent
KB_FOLDER = HERE.parent.parent / "day2" / "data" / "kb"       # Day 2 한빛정밀 사내 자료 20편


# ================================================================ 1. 도구 설명 — 모델이 읽는 것
LONG = """가상 회사 한빛정밀의 사내 규정 · 안내문 · 제품 사양서 20편에서 질문과 관련된 문단을 찾아 출처와 함께 돌려준다.
회사 규정, 금액 기준, 절차, 담당자, 제품 수치를 물을 때 쓴다.
판단은 하지 않는다 — 찾은 원문만 돌려준다. query는 찾을 내용(문서에 쓰였을 법한 말로)."""

SHORT = "문서 검색"

WRONG = "날씨 · 미세먼지 정보를 조회한다. query는 지역 이름."      # 하는 일과 다른 설명 — 일부러 틀리게

# 환경변수 MCP_DESC 로 설명을 고른다 (관찰 실험용). 서버가 하는 일은 셋 다 똑같다.
#   (없음)  → LONG    short → SHORT    wrong → WRONG
if os.environ.get("MCP_DESC") == "short":
    DESCRIPTION = SHORT
elif os.environ.get("MCP_DESC") == "wrong":
    DESCRIPTION = WRONG
else:
    DESCRIPTION = LONG


# ================================================================ 2. 자료 읽기
def load_paragraphs():
    """사내 자료를 빈 줄 기준으로 잘라 [{"source": 파일 이름, "title": 문서 제목, "text": 문단}, ...]으로 돌려준다.

    "# 제목"으로 시작하는 문단(문서 제목 · 장 제목)은 내용이 없어 뺀다.
    문서 제목을 함께 두는 이유: "무게: 1.2 kg" 문단에는 "AX-2041"이 없고 제목에만 있다.
    """
    paragraphs = []
    for path in sorted(KB_FOLDER.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        title = text.split("\n")[0].lstrip("# ").strip()      # 첫 줄 = 문서 제목
        for part in text.split("\n\n"):
            part = part.strip()
            if part == "" or part.startswith("#"):
                continue
            paragraphs.append({"source": path.name, "title": title, "text": part})
    return paragraphs


PARAGRAPHS = load_paragraphs()          # 서버가 뜰 때 한 번 읽어 둔다


# ================================================================ 3. 검색
def pieces(text):
    """검색용 조각 — 낱말마다 2글자씩 자른다. 조사가 붙어도 걸리게 하려는 것.

    예: "숙박비 한도는" → ["숙박", "박비", "한도", "도는"]
    """
    result = []
    for word in text.lower().split():
        word = word.strip(".,?!()[]\"'·")
        if len(word) < 2:
            continue
        for i in range(len(word) - 1):
            result.append(word[i:i + 2])
    return result


def search(query, k=3):
    """질문의 조각이 가장 많이 들어 있는 문단 k개를 돌려준다. 하나도 안 겹치는 문단은 뺀다.

    문단 본문과 문서 제목을 함께 본다.
    """
    query_pieces = pieces(query)

    scored = []                         # [(겹친 조각 수, 문단), ...]
    for paragraph in PARAGRAPHS:
        text = (paragraph["title"] + " " + paragraph["text"]).lower()
        score = 0
        for piece in query_pieces:
            if piece in text:
                score += 1
        if score > 0:
            scored.append((score, paragraph))

    # 점수가 큰 순서로 k개 — 같은 점수면 앞 파일 먼저
    best = []
    for _ in range(k):
        if len(scored) == 0:
            break
        top = scored[0]
        for item in scored:
            if item[0] > top[0]:
                top = item
        best.append(top[1])
        scored.remove(top)
    return best


# ================================================================ 4. 도구 — 모델이 부르면 우리 코드가 실행한다
mcp = MCPServer("hanbit-docs")


@mcp.tool(description=DESCRIPTION)
def search_docs(query: str) -> str:
    """도구 이름은 함수 이름(search_docs), 입력 스키마는 인자와 타입 힌트(query: str)에서 만들어진다."""
    hits = search(query, 3)
    if len(hits) == 0:
        return "찾은 문단 없음"

    result = ""
    number = 1
    for hit in hits:
        result += f'<자료 번호="{number}" 출처="{hit["source"]}">\n'
        result += hit["text"] + "\n"
        result += "</자료>\n"
        number += 1
    return result


# 문서를 고치거나 지우는 '쓰는' 도구는 일부러 만들지 않는다.
# 되돌릴 수 없는 행동은 MCP로 노출하지 않고 사람에게 남긴다.

if __name__ == "__main__":
    mcp.run()          # 기본은 stdio — Claude Code가 이 프로그램을 띄우고 표준 입출력으로 대화한다

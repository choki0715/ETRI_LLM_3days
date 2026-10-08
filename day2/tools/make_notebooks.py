"""notebooks/*.ipynb 를 만든다 (강사용).   python tools/make_notebooks.py

수강생이 읽는 셀 코드는 중급 이하 눈높이로 쓴다 — 컴프리헨션 · 조건 표현식 · **kwargs · lambda 대신
for / if 로 풀어 쓴다. 코드 셀은 r'''...''' (raw 문자열)이라 셀에 적힌 그대로 노트북에 들어간다.
"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks"

SETUP = r'''import os
from pathlib import Path
if Path.cwd().name == "notebooks":
    os.chdir("..")          # day 폴더로 이동 — data/ · prompts/ · src/ 가 여기 있다

from common import llm      # 공용 API 도구 (ETRI_LLM_3days/common/llm.py)
if llm.MOCK:
    print("모델:", llm.MODEL, "| 모의 모드")
else:
    print("모델:", llm.MODEL, "| 실제 호출")'''

SETUP_RAG = SETUP + r'''

from src import rag
if rag.EMBED == "hash":
    print("임베딩: 간이 해시 (EMBED=hash)")
else:
    print("임베딩:", rag.ST_MODEL)'''


def nb(cells):
    n = nbf.v4.new_notebook()
    n.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    n.metadata["language_info"] = {"name": "python"}
    for kind, src in cells:
        src = src.strip("\n")
        if kind == "md":
            n.cells.append(nbf.v4.new_markdown_cell(src))
        else:
            n.cells.append(nbf.v4.new_code_cell(src))
    return n


def M(s):
    return ("md", s)


def C(s):
    return ("code", s)


# ============================================================== 01 · 1세션
nb01 = [
    M("""# 01 · 전부 넣기 vs 골라 넣기
**1세션 · 컨텍스트란 무엇인가** — 실습 20분

같은 질문을 두 조건으로 보내고 **정답 여부 · 응답 시간 · 입력 토큰 · 비용** 네 가지를 측정합니다.

| 조건 | 답이 맞았나 | 응답 시간 | 입력 토큰 | 1건 비용 |
|---|---|---|---|---|
| A 사내 자료 20편 전부 | | | | |
| B 관련 부분만 | | | | |

A가 더 정확하다면 그것도 결과입니다. 중요한 것은 **차이를 숫자로 적어 보는 것**입니다.

> 요즘 모델은 창이 커서(수십만~백만 토큰) "그냥 다 넣으면 되지 않나" 싶을 수 있습니다. 창에 들어간다고 끝이 아닙니다 — ①보낸 토큰만큼 비용·시간이 **창 크기와 무관하게** 그대로 붙고, ②관련 없는 내용이 많을수록 모델이 정답을 놓치는 경우가 보고돼 있습니다("context rot"). 이 둘을 지금 두 조건으로 직접 측정해 봅니다."""),
    C(SETUP),
    M("""## 1. 창에 들어갈 재료
가상의 회사 **한빛정밀**의 사내 자료 20편(`data/kb/`)입니다. 전부 합치면 몇 토큰일까요?"""),
    C(r'''docs = sorted(Path("data/kb").glob("*.txt"))

parts = []                     # 문서마다 <문서> 태그로 감싼 글
for p in docs:
    text = p.read_text(encoding="utf-8")
    print(f"{p.name:<26} {len(text):>5}자")
    parts.append(f'<문서 출처="{p.name}">\n{text}\n</문서>')

ALL = "\n\n".join(parts)       # 20편을 빈 줄로 이어 붙인 하나의 글 = 조건 A
print(f"\n합계 {len(ALL):,}자 → {llm.count_tokens(ALL):,} 토큰")'''),
    M("""## 2. 질문 고르기
답이 **문서 가운데쯤**에 있고, **헷갈리게 하는 비슷한 내용**이 다른 문서에 있는 질문을 고릅니다.

- Q1 경조휴가 — 답은 일반 업무 규칙 29개 조 중 제16조. 복리후생 안내에 *경조금*이 따로 있다
- Q2 AX-2041 토크 — 이름이 비슷한 AX-2014 사양서가 따로 있다"""),
    C(r'''# Q1의 B 조건 = 일반 업무 규칙에서 제16조 부분만 잘라 낸 것
rules_text = Path("data/kb/01_일반업무규칙.txt").read_text(encoding="utf-8")
after_16 = rules_text.split("제16조")[1]      # "제16조" 뒤 전부
part_16 = after_16.split("제17조")[0]         # 그중 "제17조" 앞까지 = 제16조 본문

# Q2의 B 조건 = AX-2041 사양서 한 편
part_ax2041 = Path("data/kb/06_제품사양_AX-2041.txt").read_text(encoding="utf-8")

QUESTIONS = [
    {"q": "직원 본인이 결혼하면 경조휴가는 며칠인가요? 숫자와 근거 조항만 답하세요.",
     "answer": "5일",
     "part": part_16},
    {"q": "AX-2041의 정격 토크와 최대 토크는 각각 얼마인가요? 숫자만 답하세요.",
     "answer": "4.5",
     "part": part_ax2041},
]
print("B 조건에 넣을 부분 (Q1):")
print("제16조" + part_16)'''),
    M("""## 3. A·B 두 조건으로 같은 질문을 보내고 측정한다
각 질문을 조건 A(자료 전부)·B(관련 부분만)로 각각 한 번씩 보내, 정답 여부 · 응답 시간 · 입력 토큰 · 비용을 표에 기록합니다."""),
    C(r'''def measure(context, q):
    """자료(context)와 질문(q)을 한 프롬프트로 묶어 모델에 보낸다."""
    prompt = f"<자료>\n{context}\n</자료>\n\n<질문>{q}</질문>"
    return llm.call(prompt, max_tokens=300)

table = []
for item in QUESTIONS:
    conditions = [("A 전부", ALL), ("B 골라서", item["part"])]
    for name, context in conditions:
        r = measure(context, item["q"])
        if item["answer"] in r.text:
            ok = "○"
        else:
            ok = "×"
        table.append([item["q"][:18], name, ok, r.seconds, r.input_tokens, llm.fmt_cost(r.cost)])
        print(f"[{name}] {r.text.strip()[:80]}")
    print()

print(f"{'질문':<20}{'조건':<10}{'정답':<5}{'시간':>7}{'입력 토큰':>10}  비용")
for q, name, ok, seconds, input_tokens, cost in table:
    print(f"{q:<20}{name:<10}{ok:<5}{seconds:>6.1f}초{input_tokens:>10,}  {cost}")'''),
    M("""## 4. 세 번씩 돌려 본다
한 번은 우연일 수 있습니다 — 어제 배운 것. A 조건을 세 번 더 돌려 매번 맞는지 봅니다."""),
    C(r'''for item in QUESTIONS:
    correct = 0
    for i in range(3):
        r = measure(ALL, item["q"])
        if item["answer"] in r.text:
            correct += 1
    print(f"A 전부 · {item['q'][:20]} → 3번 중 {correct}번 정답")'''),
    M("""## 관찰 기록
- 입력 토큰은 몇 배 차이 났나:
- 응답 시간은:
- 정답은 둘 다 맞았나. 틀렸다면 무엇과 헷갈렸나 (경조금? AX-2014?):
- 하루 1,000번 묻는 사내 도우미라면, A와 B의 한 달 비용 차이는:

> 오늘의 결론으로 이어집니다 — *창에 넣는 것과 모델이 잘 쓰는 것은 다르다.* 그래서 **골라 넣는 방법(RAG)**이 3세션의 주제입니다."""),
]

# ============================================================== 02 · 2세션
nb02 = [
    M("""# 02 · 네 가지 전략
**2세션 · 네 가지 전략** — 실습 10분

창이 커져도 **보낸 토큰만큼 비용·시간이 들고, 관련 없는 내용이 많으면 정확도가 떨어집니다** — 그래서 창 크기와 무관하게 넣는 방법을 고민해야 합니다. 방법은 네 가지뿐입니다:

- **고르기** — 전체가 아니라 필요한 부분만 검색해서 넣는다 (01의 B, = RAG)
- **줄이기** — 대화가 길어지면 오래된 부분을 요약으로 줄여서 넣는다
- **쓰기** — 알아낸 것을 창 밖(파일)에 적어 두고, 필요할 때만 다시 읽어서 넣는다
- **나누기** — 일을 서브에이전트에게 나눠, 각자 자기 창에서 처리하고 요약만 돌려받는다

오늘 깊게 하는 것은 *고르기*(3세션)이고, 여기서는 **줄이기·쓰기**를 작게 맛봅니다. *나누기*는 내일(에이전트) 주제라 오늘은 이름만 둡니다."""),
    C(SETUP),
    M("""## 1. 줄이기 — 대화가 길어지면
모델은 기억하지 않으므로, 이어 가려면 이력을 매번 다시 보냅니다. 입력 토큰이 어떻게 늘어나는지 봅니다."""),
    C(r'''history = []          # 지금까지 주고받은 대화 — 매번 통째로 다시 보낸다
questions = ["연차 신청 절차를 알려줘", "반차는 어떻게 나뉘어?", "경조휴가 기준은?", "병가는 며칠까지야?", "방금 말한 것들을 표로 정리해줘"]
for q in questions:
    r = llm.call(q, history=history, max_tokens=300)
    history.append({"role": "user", "content": q})
    history.append({"role": "assistant", "content": r.text})
    print(f"{q:<22} 입력 {r.input_tokens:>5} 토큰")'''),
    M("""**줄이기**: 직전 몇 턴은 그대로 두고, 그 이전은 요약 한 덩어리로 바꿉니다."""),
    C(r'''old = history[:-4]        # 앞부분 — 요약으로 줄일 것
recent = history[-4:]     # 마지막 질문 2개와 답 2개 — 그대로 둔다

old_lines = []
for m in old:
    old_lines.append(f"{m['role']}: {m['content']}")
old_text = "\n".join(old_lines)
summary = llm.call("다음 대화에서 나중에 필요할 사실만 다섯 줄 이내로 요약해 주세요.\n\n" + old_text, max_tokens=300).text

# 줄인 이력 = 요약 한 덩어리 + 최근 대화
short = []
short.append({"role": "user", "content": "<이전 대화 요약>\n" + summary + "\n</이전 대화 요약>"})
short.append({"role": "assistant", "content": "네, 요약을 참고하겠습니다."})
for m in recent:
    short.append(m)

q = "지금까지 이야기한 휴가 종류를 한 줄씩 다시 말해줘"
a = llm.call(q, history=history, max_tokens=300)     # 전체 이력으로
b = llm.call(q, history=short, max_tokens=300)       # 줄인 이력으로
print(f"전체 이력  입력 {a.input_tokens} 토큰")
print(f"요약 + 최근  입력 {b.input_tokens} 토큰")
print()
print(b.text)'''),
    M("""## 2. 쓰기 — 창 밖에 적어 두고 필요할 때 읽는다
작업 중 알게 된 것을 파일에 써 두면, 다음 호출(또는 다음 날)에 그 파일만 창에 넣으면 됩니다.
내일 Claude Code의 `CLAUDE.md`가 바로 이 전략입니다."""),
    C(r'''notes = Path("results/notes.md")
notes.write_text("# 작업 메모\n- 사용자는 생산관리팀 소속\n- 답은 표로 받기를 원함\n- 연차 규정은 일반 업무 규칙 제13~15조\n", encoding="utf-8")

memo = notes.read_text(encoding="utf-8")
r = llm.call("반차 규정을 알려줘", system="<메모>\n" + memo + "</메모>", max_tokens=300)
print(r.text)'''),
    M("""## 3. 실습 · 내 업무에 전략 붙이기 (10분)
각자 업무 두 가지를 적고 전략을 고릅니다. 두세 명이 발표합니다.

| 내 업무 | 모델이 몰라서 틀릴 것 | 주로 쓸 전략 | 창에 넣을 것 |
|---|---|---|---|
| | | | |
| | | | |

> 대부분의 업무는 **고르기**에서 시작한다는 것을 확인하고 3세션으로 넘어갑니다."""),
]

# ============================================================== 03 · 3세션 오전
nb03 = [
    M("""# 03 · 임베딩 · 청킹 · 색인 · 검색 비교
**3세션 · 고르기 · RAG (오전)** — 실습 30분

RAG의 다섯 단계 — 자르기 → 벡터로 바꾸기 → 저장 → **검색** → 주입해서 묻기 — 를 0절에서 먼저 한 번에 따라가 보고, 1~4절에서 하나씩 더 깊이 봅니다.
새로 배우는 것은 검색 하나이고, 나머지는 어제 배운 프롬프트입니다.

> 임베딩 모델(한국어 특화, 약 420MB)은 처음 실행할 때 내려받습니다. `setup.sh`를 전날 돌렸다면 이미 받아져 있습니다."""),
    C(SETUP_RAG + r'''
import numpy as np'''),
    M("""## 0. 한 질문이 답이 되기까지 — 다섯 단계
질문 하나를 끝까지 따라갑니다. 코드를 읽을 필요는 없습니다 — 아래 다섯 셀을 순서대로 실행하고 출력만 보면 됩니다.

**질문**: "연차 사용 절차를 알려줘\""""),
    C(r'''Q0 = "연차 사용 절차를 알려줘"

chunks = rag.chunk_folder("data/kb", max_len=800, overlap=100)
print(f"① 청킹 — 사내 자료 20편을 조각 {len(chunks)}개로 미리 잘라 둡니다.")

# 질문의 답이 든 조각 하나를 미리 찾아 본다
example = None
for c in chunks:
    if "연차 사용 절차" in c["text"]:
        example = c
        break
print("   예시 조각:", example["source"], "·", example["title"])
print("  ", example["text"][:120].replace("\n", " "))
print("   → 조각 하나 = 본문 + 출처 + 제목. 이 조각이 ③검색에서 다시 나오는지 봅니다.")'''),
    C(r'''vec = rag.embed(Q0)
print(f"② 임베딩 — 질문이 숫자 벡터로 바뀝니다 (차원 {vec.shape[0]})")

first_six = []
for x in vec[:6]:
    first_six.append(round(float(x), 3))
print("   앞 6개 값:", first_six)
print("   → 이 숫자 자체를 읽을 필요는 없습니다. 뜻이 비슷한 문장일수록 이 숫자들이 서로 가까워진다는 것만 기억합니다.")'''),
    C(r'''idx = rag.Index(chunks)
hits = idx.search(Q0, k=3)
print("③ 검색 — 질문과 가장 가까운 조각 3개 (거리 · 작을수록 가깝다)")
for h in hits:
    print("  ", h)'''),
    C(r'''prompt = rag.make_prompt(Q0, hits)
print("④ LLM에 들어가는 최종 입력 — 모델이 보는 것은 이것이 전부입니다")
print(prompt)'''),
    C(r'''r = llm.call(prompt, max_tokens=300)
print("⑤ 최종 결과")
print(r.text)'''),
    M("""이 다섯 셀이 RAG의 전부입니다. 아래부터는 단계마다 하나씩 더 깊이 봅니다."""),
    M("""## 1. 임베딩 — 뜻이 비슷하면 숫자도 가깝다
방금 ②에서 본 숫자가 실제로 뜻을 반영하는지, 문장 3개 · 질문 3개로 확인합니다.
질문마다 숫자 3개가 나옵니다 — **문서 ①②③ 각각과의 거리**입니다. 0절 ③과 같은 척도로, **작을수록 가깝습니다**. 가장 작은 쪽이 화살표 뒤에 옵니다."""),
    C(r'''docs = ["연차는 사용 3일 전까지 팀장 승인을 받는다",      # 문서 ①
        "출장비는 귀임 후 7일 이내 정산한다",              # 문서 ②
        "비밀번호는 90일마다 바꾼다"]                     # 문서 ③
doc_vecs = rag.embed(docs)
print("벡터 모양:", doc_vecs.shape, "(문서 3개 × 숫자 768개)")
print(f"{'질문':<18}{'→ 가장 가까운 문서':<24}  ①연차  ②출장비  ③비밀번호   (거리 · 작을수록 가깝다)")

for q in ["연차 쓰려면 누구 승인 받아요?", "교통비 돌려받는 법", "암호 변경 주기"]:
    q_vec = rag.embed(q)

    # 문서마다 거리 계산 — 코사인 거리 = 1 − 코사인 유사도. chroma(0절 ③)와 같은 숫자
    dists = []
    for doc_vec in doc_vecs:
        similarity = float(np.dot(doc_vec, q_vec))     # 벡터 길이가 1이라 내적이 곧 코사인 유사도
        dists.append(1 - similarity)

    # 거리가 가장 작은 문서 찾기
    best = 0
    for i in range(len(dists)):
        if dists[i] < dists[best]:
            best = i

    dist_texts = []
    for d in dists:
        dist_texts.append(f"{d:.2f}")
    print(f"{q:<18}→ {docs[best][:20]:<22}  " + "  ".join(dist_texts))'''),
    M("""## 2. 청킹 — 어떻게 자를 것인가
검색되는 단위가 곧 모델이 보는 단위입니다. **제목 · 조항 앞에서 먼저 자르고**, 긴 것만 다시 나눕니다."""),
    M("""자르는 방법을 정하는 손잡이는 셋입니다. 0절 ①에서 쓴 값이 기본값입니다.

| 손잡이 | 뜻 | 0절에서 쓴 값 |
|---|---|---|
| `pattern` | 어디서 자를까 — 제목(`#`) · 조항(`제N조`) · 항목(`■`) · FAQ 질문(`Q.`) 앞 | 구조대로 |
| `max_len` | 한 조각의 최대 글자 수. 이보다 길면 글자 수로 한 번 더 자른다 | 800자 |
| `overlap` | 글자 수로 자를 때 앞뒤 조각을 겹치는 글자 수 — 경계에서 문장이 끊기지 않게 | 100자 |"""),
    C(r'''# chunks는 0절 ①에서 이미 만들어 두었습니다 — 같은 변수를 계속 씁니다.
longest = 0
for c in chunks:
    if len(c["text"]) > longest:
        longest = len(c["text"])
print(f"20편 → 조각 {len(chunks)}개 · 가장 긴 조각 {longest}자")
print(f"→ 가장 긴 조각도 max_len(800자)보다 짧으므로, 이 자료는 전부 구조(조항·항목) 경계에서만 잘렸습니다.")'''),
    M("""### 조각 10개를 무작위로 뽑아 사람이 읽는다
- 혼자 읽어도 뜻이 통하는가
- 어느 문서 어느 절인지 알 수 있는가"""),
    C(r'''import random
random.seed(7)                     # ✏️ 숫자를 바꾸면 다른 조각이 나온다
for c in random.sample(chunks, 10):
    print(f"── {c['source']} · {c['title'][:30]}")
    print(c["text"][:150].replace("\n", " "))
    print()'''),
    M("""## 3. 색인 — 벡터 DB에 넣는다
조각 · 벡터 · 출처를 함께 저장합니다. 출처가 있어야 나중에 각주를 달 수 있습니다."""),
    C(r'''# idx도 0단계(③)에서 이미 만들어 두었습니다.
print("저장한 조각:", idx.collection.count())

for h in idx.search("연차는 언제까지 신청해요?", k=3):
    print(h)                       # 거리 · 작을수록 가깝다'''),
    M("""메타데이터 필터 — "이 문서 안에서만" 같은 조건을 겁니다."""),
    C(r'''for h in idx.search("기준 금액", k=3, where={"파일": "10_구매_절차.txt"}):
    print(h)'''),
    M("""## 4. 실습 · 키워드 검색과 의미 검색 비교
네 종류의 질문을 두 방식으로 검색하고 1위를 비교합니다. ✏️ 질문을 내 것으로 바꿔 봅니다."""),
    C(r'''kw = rag.Keyword(chunks)

# (유형, 질문, 정답 조각에 들어 있어야 할 말) — 정답이 없는 질문은 None
TRIALS = [
    ("뜻은 같고 단어가 다른 질문",  "연차 신청 기한이 어떻게 되나요?",            "제14조"),
    ("문서에 쓰인 문장 그대로",     "연차를 사용하려는 직원은 사용일 3일 전까지",  "제14조"),
    ("코드 · 번호가 들어간 질문",   "문서 번호 QP-0712",                        "QP-0712"),
    ("문서에 답이 없는 질문",       "사내 헬스장 운영 시간",                     None),
]

def mark(hit, want):
    """정답 조각을 찾았으면 ○, 못 찾았으면 ✗, 정답이 없는 질문이면 빈칸."""
    if want is None:
        return "  "
    if want in hit.text:
        return "○ "
    return "✗ "

for kind, q, want in TRIALS:
    keyword_top = kw.search(q, 1)[0]      # 키워드 검색 1위
    meaning_top = idx.search(q, 1)[0]     # 의미 검색 1위
    keyword_text = keyword_top.text[:40].replace("\n", " ")
    meaning_text = meaning_top.text[:40].replace("\n", " ")
    print(f"[{kind}] {q}")
    print(f"   키워드 1위 {mark(keyword_top, want)}{keyword_top.source:<26} {keyword_text}")
    print(f"   의미   1위 {mark(meaning_top, want)}{meaning_top.source:<26} {meaning_text}")
    print()
print("○ = 정답 조각을 찾음 · ✗ = 못 찾음 · 답이 없는 질문은 표시 없음")'''),
    M("""| 질문 | 키워드 1위 | 의미 1위 | 맞은 쪽 |
|---|---|---|---|
| 뜻은 같고 단어가 다른 질문 | | | |
| 문서에 쓰인 문장 그대로 | | | |
| 코드 · 번호가 들어간 질문 | | | |
| 문서에 답이 없는 질문 | | | |

- 단어가 달라도 뜻이 같으면 **의미 검색**이 찾고, 번호·코드처럼 뜻이 없는 문자열은 **키워드 검색**이 찾습니다. 그래서 실무에서는 둘을 섞어 씁니다(하이브리드 검색).

**꼭 볼 것** — 마지막 줄. 답이 없는데도 검색은 무언가를 1위로 내놓습니다. **검색은 "없다"고 말하지 않습니다.**
이 성질 때문에 RAG 프롬프트에 거절 지시가 반드시 필요합니다 → 04_rag_qa 노트북."""),
    C(r'''# 거리로 "없음"을 가려낼 수 있을까? 답이 있는 질문과 없는 질문의 1위 거리를 나란히 본다
CHECK = [("연차 신청 기한이 어떻게 되나요?", "있음"),
         ("문서 번호 QP-0712", "있음"),
         ("사내 헬스장 운영 시간", "없음"),
         ("올해 성과급 지급률", "없음")]

print("거리    답이  질문")
for q, has_answer in CHECK:
    top = idx.search(q, 1)[0]
    print(f"{top.value:.3f}   {has_answer}  {q}")
print()
print("→ '있음'이 모두 '없음'보다 작게 나오나요? 대개는 아닙니다 — 거리만으로는 못 가릅니다.")
print("   그래서 '자료에 없다'는 판단은 모델에게 거절 지시로 맡깁니다 → 04 노트북.")'''),
]

# ============================================================== 04 · 3세션 오후
nb04 = [
    M("""# 04 · 근거를 달고 답하는 질의응답 · 진단
**3세션 · 고르기 · RAG (오후)** — 실습 30분

| 순서 | 할 일 |
|---|---|
| 1 청킹 · 2 색인 | 03_rag_index 노트북에서 한 것 — 여기서 다시 만든다 |
| 3 ask() | 검색 → 주입 → 호출, 출처 각주 포함 |
| 4 거절 확인 | 답이 없는 질문 3개에 "자료에 없음"이 나오는가 — **건너뛰지 않는다** |
| 5 10문항 채점 | 답있음 5 · 답없음 3 · 바꿔쓴 2 |
"""),
    C(SETUP_RAG + r'''
from src import qa

chunks = rag.chunk_folder("data/kb")
idx = rag.Index(chunks)
print("조각", len(chunks))'''),
    M("""## 3. ask() — 검색 · 주입 · 호출
자료마다 번호와 출처를 달아 지시와 분리합니다. 규칙은 맨 앞, 질문은 맨 끝 — 어제 배운 위치."""),
    C(r'''print(rag.RULES)
answer, hits = rag.ask("휴가 신청은 어떻게 해요?", idx, k=3)
print()
print(answer)

# 답에 붙은 각주 번호가 어느 파일을 가리키는지
footnotes = rag.cited(answer)
cited_files = []
for n in footnotes:
    if n <= len(hits):
        cited_files.append(hits[n - 1].source)     # 각주 [1]은 hits[0]
print()
print("각주:", footnotes, "→", cited_files)'''),
    M("""최종 프롬프트를 눈으로 봅니다. 모델이 본 것은 이것이 전부입니다."""),
    C(r'''print(rag.LAST_PROMPT)'''),
    M("""## 4. 거절 확인
지어낸 금액을 말하지 않는 것이 이 시스템의 **가장 중요한 동작**입니다."""),
    C(r'''NO_ANSWER = ["올해 성과급 지급률은 몇 퍼센트인가요?",
             "사내 헬스장은 몇 시까지 운영하나요?",
             "육아휴직 기간에 급여는 얼마나 나오나요?"]
for q in NO_ANSWER:
    answer, hits = rag.ask(q, idx)
    print(f"Q {q}")
    print(f"A {answer.strip()}")
    print()'''),
    M("""> 세 번째 질문은 토론 거리입니다. 일반 업무 규칙 제18조는 "처우는 관계 법령에 따른다"고만 합니다. 이것은 *답*일까요, *자료에 없음*일까요? 테스트 문항으로 쓰려면 기준을 먼저 정해야 합니다."""),
    M("""## 5. 10문항 채점
어제와 같은 방식 — 고정 문항(`data/qa_tests.jsonl`) · 판정 기준 · 반복 기록.
다른 점은 실패를 **어느 단계의 고장인지**로 나눈다는 것입니다.
코드는 위치를 좁혀 줄 뿐입니다. *검색*인지 *청킹*인지는 `debug()`로 조각을 열어 사람이 가립니다 — 정답 문서가 아예 안 왔으면 검색, 왔는데 답이 잘려 있으면 청킹.

| 고장 | 판정 | 고치는 곳 |
|---|---|---|
| 검색 · 청킹 | 넣은 자료에 답이 든 조각이 없다 | 검색: k · 질문 말투 · 키워드 검색 / 청킹: 구조 경계 · 겹침 |
| 있는데 못 씀 | 자료에 답이 있는데 답에 없다 | 주입 코드 · 프롬프트 |
| 지어냄 | 답 없는 질문에 "자료에 없음"이 아니다 | 거절 지시 |
| 출처 오류 | 답은 맞는데 각주가 다른 문서를 가리킨다 | 각주 규칙 |"""),
    C(r'''passed, fails, rows = qa.run_qa(idx, k=3)'''),
    M("## 6. 진단 — 답만 보지 말고 중간을 찍는다"),
    C(r'''# 처음 실패한 문항을 연다. 실패가 없으면 아래 질문으로.
FAIL_Q = "휴가 쓰려면 며칠 전에 말해야 해요?"
for r in rows:
    if not r["ok"]:
        FAIL_Q = r["q"]
        break

answer, hits = rag.debug(FAIL_Q, idx, k=3)'''),
]

# ============================================================== 05 · 4세션
nb05 = [
    M("""# 05 · 계산기와 검색을 붙인 단일 루프
**4세션 · 도구 결과도 컨텍스트다** — 실습 40분

모델은 *이 도구를 이 값으로 불러 달라*고 말할 뿐이고, **실행은 우리 코드가 합니다.**
시도마다 도구 결과(`tool_result`)가 messages에 쌓입니다 — 그것이 다음 시도에서 모델이 읽는 컨텍스트입니다.

에이전트 = **모델 + 도구 + 루프**"""),
    C(SETUP_RAG + r'''

import json
import inspect
from src import loop        # 검색 색인(loop.SEARCH_INDEX)도 loop.py 안에서 만든다'''),
    M("""## 1. 함수 정의의 실물
이름 · 설명 · 입력 스키마 세 가지가 전부입니다. **설명은 모델이 도구를 고르는 유일한 근거**입니다."""),
    C(r'''print(json.dumps(loop.TOOLS, ensure_ascii=False, indent=2))'''),
    M("""> 문자열 수식을 받아 `eval`로 계산하는 도구는 만들지 않습니다. 모델이 무엇을 넘길지 우리가 통제할 수 없기 때문입니다. `enum`으로 고를 수 있는 값을 제한합니다."""),
    M("## 2. 루프 코드"),
    C(r'''print(inspect.getsource(loop.run))'''),
    M("""## 3. 1단계 · 붙이기
질문 네 개로 돌려 **시도마다 출력**을 봅니다. 줄 앞의 `[0]` `[1]` `[2]`는 몇 번째 모델 호출인지입니다.
- 셋째 질문 — 두 도구를 차례로 부르는가?
- 넷째 질문 — 검색 → 곱셈 → 덧셈처럼, **앞 도구의 결과를 봐야 다음 도구를 부를 수 있는** 일을 몇 번의 시도로 푸는가?"""),
    C(r'''Q1 = "AX-2041의 무게는 얼마인가요?"
Q2 = "1,234,500원을 3명이 똑같이 나누면 1명당 얼마인가요?"
Q3 = "서울로 3박 출장을 가면 숙박비 한도는 모두 얼마인가요?"
Q4 = "AX-2041 10대와 AX-2014 5대를 한 상자에 담으면 제품 무게만 모두 몇 kg인가요?"

for q in [Q1, Q2, Q3, Q4]:
    print("=" * 70)
    print("Q", q)
    answer, trace = loop.run(q)
    print("→ 최종 답:", answer)
    print("→ 쓴 도구:", loop.tools_used(trace))
    print()'''),
    M("""## 4. 2단계 · 일부러 틀리게
시스템 프롬프트와 코드는 그대로 두고, **search 도구의 입력(query) 설명 한 줄만** 잘못 적습니다.
문서는 한국어인데 *"영어 단어 하나로 찾아라"*고 적었습니다. 모델은 도구 정의를 믿고 그대로 따릅니다 — 정의가 틀리면 충실하게 틀립니다.

볼 것: 모델이 어떤 검색어를 넣는가 · 못 찾으면 몇 번 다시 시도하는가 · 최종 답이 나오는가"""),
    C(r'''print("좋은 정의의 query 설명:", loop.SEARCH_TOOL["input_schema"]["properties"]["query"]["description"])
print("잘못된 정의의 query 설명:", loop.SEARCH_TOOL_BAD["input_schema"]["properties"]["query"]["description"])

TRY = [
    "자기계발비 한도를 12개월로 나누면 한 달에 얼마인가요?",
    Q3,
    "회의실은 하루에 몇 번 예약할 수 있나요?",
]
for q in TRY:
    print("=" * 70)
    print("Q", q)
    answer, trace = loop.run(q, tools=loop.TOOLS_BAD)
    print("→ 최종 답:", answer)
    print("→ 쓴 도구:", loop.tools_used(trace))
    print()'''),
    M("""## 5. 정의 한 줄만 고쳐 바로잡는다
4절에서 실패한 질문을 하나 정하고, **query의 description만** 고쳐 다시 돌립니다. 코드 · 시스템 프롬프트는 건드리지 않습니다."""),
    C(r'''MY_SEARCH_TOOL = {
    "name": "search",
    "description": loop.SEARCH_TOOL["description"],
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string",
                      "description": "English keyword only, one word (e.g. 'hotel')"},   # ✏️ 이 문장만 고친다
        },
        "required": ["query"],
    },
}
MY_TOOLS = [loop.CALCULATOR_TOOL, MY_SEARCH_TOOL]
Q = TRY[0]                                                    # ✏️ 4절에서 실패한 질문

print("=" * 70)
print("[고치기 전]")
answer, trace = loop.run(Q, tools=loop.TOOLS_BAD)
print("→ 최종 답:", answer)
print("→ 쓴 도구:", loop.tools_used(trace))

print("=" * 70)
print("[고친 뒤]")
answer, trace = loop.run(Q, tools=MY_TOOLS)
print("→ 최종 답:", answer)
print("→ 쓴 도구:", loop.tools_used(trace))'''),
    M("""| 질문 | 고치기 전 검색어 · 결과 | 고친 query 설명 | 고친 뒤 검색어 · 결과 |
|---|---|---|---|
| | | | |

> 참고 — 같은 실험에서 *언제 쓰는지*(description)를 "검색한다." 한 마디로 줄이거나 엉뚱하게 바꿔도, 시스템 프롬프트가 있으면 모델은 대부분 제대로 골랐습니다. 이름과 문맥이 보완해 주기 때문입니다. **입력값을 어떻게 채우라는 정의**는 모델이 그대로 따르므로, 틀리면 바로 결과가 무너집니다.

## 6. 창에 무엇이 쌓였나
`loop.run()`이 모델에 보낸 대화 기록(messages)을 펼쳐 봅니다.
시도마다 **모델의 도구 요청**과 **우리가 붙인 도구 결과**가 쌓이고, 마지막 모델 호출에는 이 전부가 들어갑니다 — 그래서 **도구 결과도 컨텍스트**입니다."""),
    C(r'''answer, trace = loop.run(Q3, verbose=False)

loop.show_messages(loop.LAST_MESSAGES)      # [번호] = messages 안의 순서
print()
print("최종 답:", answer)'''),
    M("""## 내 loop.py에 없는 것 → 내일

| 전략 | 오늘의 loop.py | Claude Code |
|---|---|---|
| 고르기 | 내가 짠 검색 하나 | 파일 검색 도구 · 스킬은 쓸 때만 본문을 불러온다 |
| 줄이기 | 없음 — messages가 끝없이 쌓인다 | 오래된 도구 출력부터 비우고, 필요하면 대화를 요약한다 |
| 쓰기 | 없음 — 끝나면 사라진다 | CLAUDE.md · 자동 메모리를 세션마다 읽어 온다 |
| 나누기 | 없음 — 창이 하나뿐 | 서브에이전트가 자기 창에서 일하고 요약만 돌려준다 |

내일은 오른쪽 열을 다 갖춘 루프 위에서 시작합니다."""),
]

if __name__ == "__main__":
    NB.mkdir(exist_ok=True)
    notebooks = [("01_window", nb01), ("02_strategies", nb02), ("03_rag_index", nb03),
                 ("04_rag_qa", nb04), ("05_tool_loop", nb05)]
    for name, cells in notebooks:
        nbf.write(nb(cells), NB / f"{name}.ipynb")
        print("작성:", f"notebooks/{name}.ipynb", len(cells), "셀")

"""notebooks/*.ipynb 를 만든다 (강사용).   python tools/make_notebooks.py"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks"

SETUP = '''import os
from pathlib import Path
if Path.cwd().name == "notebooks":
    os.chdir("..")          # day 폴더로 이동 — data/ · prompts/ · src/ 가 여기 있다

from common import llm      # 공용 API 도구 (ETRI_LLM_3days/common/llm.py)
print("모델:", llm.MODEL, "| 모의 모드" if llm.MOCK else "| 실제 호출")'''

SETUP_RAG = SETUP + '''
from src import rag
print("임베딩:", "간이 해시 (EMBED=hash)" if rag.EMBED == "hash" else rag.ST_MODEL)'''


def nb(cells):
    n = nbf.v4.new_notebook()
    n.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    n.metadata["language_info"] = {"name": "python"}
    for kind, src in cells:
        src = src.strip("\n")
        n.cells.append(nbf.v4.new_markdown_cell(src) if kind == "md" else nbf.v4.new_code_cell(src))
    return n


M = lambda s: ("md", s)
C = lambda s: ("code", s)

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
    C('''docs = sorted(Path("data/kb").glob("*.txt"))
ALL = "\\n\\n".join(f"<문서 출처=\\"{p.name}\\">\\n{p.read_text(encoding='utf-8')}\\n</문서>" for p in docs)
for p in docs:
    print(f"{p.name:<26} {len(p.read_text(encoding='utf-8')):>5}자")
print(f"\\n합계 {len(ALL):,}자 → {llm.count_tokens(ALL):,} 토큰")'''),
    M("""## 2. 질문 고르기
답이 **문서 가운데쯤**에 있고, **헷갈리게 하는 비슷한 내용**이 다른 문서에 있는 질문을 고릅니다.

- Q1 경조휴가 — 답은 일반 업무 규칙 29개 조 중 제16조. 복리후생 안내에 *경조금*이 따로 있다
- Q2 AX-2041 토크 — 이름이 비슷한 AX-2014 사양서가 따로 있다"""),
    C('''QUESTIONS = [
    {"q": "직원 본인이 결혼하면 경조휴가는 며칠인가요? 숫자와 근거 조항만 답하세요.",
     "answer": "5일",
     "part": Path("data/kb/01_일반업무규칙.txt").read_text(encoding="utf-8").split("제16조")[1].split("제17조")[0]},
    {"q": "AX-2041의 정격 토크와 최대 토크는 각각 얼마인가요? 숫자만 답하세요.",
     "answer": "4.5",
     "part": Path("data/kb/06_제품사양_AX-2041.txt").read_text(encoding="utf-8")},
]
print("B 조건에 넣을 부분 (Q1):\\n제16조" + QUESTIONS[0]["part"])'''),
    M("""## 3. A·B 두 조건으로 같은 질문을 보내고 측정한다
각 질문을 조건 A(자료 전부)·B(관련 부분만)로 각각 한 번씩 보내, 정답 여부 · 응답 시간 · 입력 토큰 · 비용을 표에 기록합니다."""),
    C('''def measure(context, q):
    prompt = f"<자료>\\n{context}\\n</자료>\\n\\n<질문>{q}</질문>"
    r = llm.call(prompt, max_tokens=300)
    return r

table = []
for item in QUESTIONS:
    for name, ctx in [("A 전부", ALL), ("B 골라서", item["part"])]:
        r = measure(ctx, item["q"])
        ok = item["answer"] in r.text
        table.append((item["q"][:18], name, "○" if ok else "×", r.seconds, r.input_tokens, llm.fmt_cost(r.cost)))
        print(f"[{name}] {r.text.strip()[:80]}")
    print()

print(f"{'질문':<20}{'조건':<10}{'정답':<5}{'시간':>7}{'입력 토큰':>10}  비용")
for q, name, ok, sec, tin, c in table:
    print(f"{q:<20}{name:<10}{ok:<5}{sec:>6.1f}초{tin:>10,}  {c}")'''),
    M("""## 4. 세 번씩 돌려 본다
한 번은 우연일 수 있습니다 — 어제 배운 것. A 조건을 세 번 더 돌려 매번 맞는지 봅니다."""),
    C('''for item in QUESTIONS:
    hits = sum(item["answer"] in measure(ALL, item["q"]).text for _ in range(3))
    print(f"A 전부 · {item['q'][:20]} → 3번 중 {hits}번 정답")'''),
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
    C('''history = []
questions = ["연차 신청 절차를 알려줘", "반차는 어떻게 나뉘어?", "경조휴가 기준은?", "병가는 며칠까지야?", "방금 말한 것들을 표로 정리해줘"]
for q in questions:
    r = llm.call(q, history=history, max_tokens=300)
    history += [{"role": "user", "content": q}, {"role": "assistant", "content": r.text}]
    print(f"{q:<22} 입력 {r.input_tokens:>5} 토큰")'''),
    M("""**줄이기**: 직전 몇 턴은 그대로 두고, 그 이전은 요약 한 덩어리로 바꿉니다."""),
    C('''old, recent = history[:-4], history[-4:]
old_text = "\\n".join(f"{m['role']}: {m['content']}" for m in old)
summary = llm.call("다음 대화에서 나중에 필요할 사실만 다섯 줄 이내로 요약해 주세요.\\n\\n" + old_text, max_tokens=300).text

short = [{"role": "user", "content": "<이전 대화 요약>\\n" + summary + "\\n</이전 대화 요약>"},
         {"role": "assistant", "content": "네, 요약을 참고하겠습니다."}] + recent
q = "지금까지 이야기한 휴가 종류를 한 줄씩 다시 말해줘"
a = llm.call(q, history=history, max_tokens=300)
b = llm.call(q, history=short, max_tokens=300)
print(f"전체 이력  입력 {a.input_tokens} 토큰\\n요약 + 최근  입력 {b.input_tokens} 토큰\\n")
print(b.text)'''),
    M("""## 2. 쓰기 — 창 밖에 적어 두고 필요할 때 읽는다
작업 중 알게 된 것을 파일에 써 두면, 다음 호출(또는 다음 날)에 그 파일만 창에 넣으면 됩니다.
내일 Claude Code의 `CLAUDE.md`가 바로 이 전략입니다."""),
    C('''notes = Path("results/notes.md")
notes.write_text("# 작업 메모\\n- 사용자는 생산관리팀 소속\\n- 답은 표로 받기를 원함\\n- 연차 규정은 일반 업무 규칙 제13~15조\\n", encoding="utf-8")

r = llm.call("반차 규정을 알려줘", system="<메모>\\n" + notes.read_text(encoding="utf-8") + "</메모>", max_tokens=300)
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
    M("""# 03a · 임베딩 · 청킹 · 색인 · 검색 비교
**3세션 · 고르기 · RAG (오전)** — 실습 30분

RAG의 다섯 단계 — 자르기 → 벡터로 바꾸기 → 저장 → **검색** → 주입해서 묻기.
새로 배우는 것은 검색 하나이고, 나머지는 어제 배운 프롬프트입니다.

> 임베딩 모델은 처음 실행할 때 내려받습니다(약 470MB). 강의장에서 막히면 `.env`에 `EMBED=hash`를 넣고 커널을 다시 시작합니다."""),
    C(SETUP_RAG + '''
import numpy as np'''),
    M("""## 1. 임베딩 — 뜻이 비슷하면 숫자도 가깝다"""),
    C('''docs = ["연차는 사용 3일 전까지 팀장 승인을 받는다",
        "출장비는 귀임 후 7일 이내 정산한다",
        "비밀번호는 90일마다 바꾼다"]
doc_vecs = rag.embed(docs)
print("벡터 모양:", doc_vecs.shape)

for q in ["휴가 신청은 어떻게 해요?", "교통비 돌려받는 법", "암호 변경 주기"]:
    sims = doc_vecs @ rag.embed(q)          # 정규화했으므로 내적 = 코사인 유사도
    best = int(np.argmax(sims))
    print(f"{q:<16} → {docs[best][:20]:<22} " + "  ".join(f"{s:.2f}" for s in sims))'''),
    M("""## 2. 청킹 — 어떻게 자를 것인가
검색되는 단위가 곧 모델이 보는 단위입니다. **제목 · 조항 앞에서 먼저 자르고**, 긴 것만 다시 나눕니다."""),
    C('''import inspect
print(inspect.getsource(rag.chunk).split('"""')[0] + "...")

chunks = rag.chunk_folder("data/kb", max_len=800, overlap=100)
print(f"\\n20편 → 조각 {len(chunks)}개 · 가장 긴 조각 {max(len(c['text']) for c in chunks)}자")'''),
    M("""### 조각 10개를 무작위로 뽑아 사람이 읽는다
- 혼자 읽어도 뜻이 통하는가
- 어느 문서 어느 절인지 알 수 있는가"""),
    C('''import random
random.seed(7)                     # ✏️ 숫자를 바꾸면 다른 조각이 나온다
for c in random.sample(chunks, 10):
    print(f"── {c['source']} · {c['title'][:30]}")
    print(c["text"][:150].replace("\\n", " "), "\\n")'''),
    M("""## 3. 색인 — 벡터 DB에 넣는다
조각 · 벡터 · 출처를 함께 저장합니다. 출처가 있어야 나중에 각주를 달 수 있습니다."""),
    C('''idx = rag.Index.build(chunks)
print("저장한 조각:", idx.col.count())

for h in idx.search("연차는 언제까지 신청해요?", k=3):
    print(h)                       # 거리 · 작을수록 가깝다'''),
    M("""메타데이터 필터 — "이 문서 안에서만" 같은 조건을 겁니다."""),
    C('''for h in idx.search("기준 금액", k=3, where={"파일": "10_구매_절차.txt"}):
    print(h)'''),
    M("""## 4. 실습 · 키워드 검색과 의미 검색 비교
네 종류의 질문을 두 방식으로 검색하고 1위를 비교합니다. ✏️ 질문을 내 것으로 바꿔 봅니다."""),
    C('''kw = rag.Keyword(chunks)

TRIALS = [
    ("뜻은 같고 단어가 다른 질문",  "휴가 쓰려면 며칠 전에 말해야 해요?"),
    ("문서에 쓰인 단어 그대로",     "연차 사용 절차"),
    ("코드 · 번호가 들어간 질문",   "AX-2041 정격 토크"),
    ("문서에 답이 없는 질문",       "사내 헬스장 운영 시간"),
]
for kind, q in TRIALS:
    k1, s1 = kw.search(q, 1)[0], idx.search(q, 1)[0]
    print(f"[{kind}] {q}")
    print(f"   키워드 1위  {k1.source:<26} {k1.text[:40].replace(chr(10), ' ')}")
    print(f"   의미   1위  {s1.source:<26} {s1.text[:40].replace(chr(10), ' ')}\\n")'''),
    M("""| 질문 | 키워드 1위 | 의미 1위 | 맞은 쪽 |
|---|---|---|---|
| 뜻은 같고 단어가 다른 질문 | | | |
| 문서에 쓰인 단어 그대로 | | | |
| 코드 · 번호가 들어간 질문 | | | |
| 문서에 답이 없는 질문 | | | |

**꼭 볼 것** — 마지막 줄. 답이 없는데도 검색은 무언가를 1위로 내놓습니다. **검색은 "없다"고 말하지 않습니다.**
이 성질 때문에 RAG 프롬프트에 거절 지시가 반드시 필요합니다 → 03b_rag_qa 노트북."""),
    C('''# 거리로 "없음"을 가려낼 수 있을까? 답이 있는 질문과 없는 질문의 1위 거리를 나란히 본다
for q in ["연차 사용 절차", "AX-2041 정격 토크", "사내 헬스장 운영 시간", "올해 성과급 지급률"]:
    print(f"{idx.search(q, 1)[0].value:.3f}  {q}")
print("\\n→ 경계가 깔끔하게 나뉘나요? 대개는 아닙니다. 그래서 판단은 모델에게 '거절 지시'로 맡깁니다.")'''),
]

# ============================================================== 04 · 3세션 오후
nb04 = [
    M("""# 03b · 근거를 달고 답하는 질의응답 · 진단 · 다시 측정하기
**3세션 · 고르기 · RAG (오후)** — 실습 30분 + 고장 내기 20분 + 다시 측정하기

| 순서 | 할 일 |
|---|---|
| 1 청킹 · 2 색인 | 03a_rag_index 노트북에서 한 것 — 여기서 다시 만든다 |
| 3 ask() | 검색 → 주입 → 호출, 출처 각주 포함 |
| 4 거절 확인 | 답이 없는 질문 3개에 "자료에 없음"이 나오는가 — **건너뛰지 않는다** |
| 5 10문항 채점 | 답있음 5 · 답없음 3 · 바꿔쓴 2 |
| 6 고장 내기 | 짝끼리 — debug 출력만 보고 몇 번 단계 고장인지 말하기 |
| 8 창만 바꿔 다시 측정하기 | 자료 없음 · RAG · 자료 전부 |"""),
    C(SETUP_RAG + '''
from src import qa

chunks = rag.chunk_folder("data/kb")
idx = rag.Index.build(chunks)
print("조각", len(chunks))'''),
    M("""## 3. ask() — 검색 · 주입 · 호출
자료마다 번호와 출처를 달아 지시와 분리합니다. 규칙은 맨 앞, 질문은 맨 끝 — 어제 배운 위치."""),
    C('''print(rag.RULES)
answer, hits = rag.ask("휴가 신청은 어떻게 해요?", idx, k=3)
print("\\n" + answer)
print("\\n각주:", rag.cited(answer), "→", [hits[n - 1].source for n in rag.cited(answer) if n <= len(hits)])'''),
    M("""최종 프롬프트를 눈으로 봅니다. 모델이 본 것은 이것이 전부입니다."""),
    C('''print(rag.LAST_PROMPT)'''),
    M("""## 4. 거절 확인
지어낸 금액을 말하지 않는 것이 이 시스템의 **가장 중요한 동작**입니다."""),
    C('''for q in ["올해 성과급 지급률은 몇 퍼센트인가요?", "사내 헬스장은 몇 시까지 운영하나요?", "육아휴직 기간에 급여는 얼마나 나오나요?"]:
    a, _ = rag.ask(q, idx)
    print(f"Q {q}\\nA {a.strip()}\\n")'''),
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
    C('''passed, fails, rows = qa.run_qa(idx, k=3)'''),
    M("## 6. 진단 — 답만 보지 말고 중간을 찍는다"),
    C('''FAIL_Q = rows[[r["ok"] for r in rows].index(False)]["q"] if fails else "휴가 쓰려면 며칠 전에 말해야 해요?"
rag.debug(FAIL_Q, idx, k=3);'''),
    M("""## 7. 실습 · 일부러 고장 내기 (20분)
짝끼리 한 사람이 아래 고장 중 하나를 **몰래** 고르고, 다른 사람이 `debug` 출력만 보고 몇 번 단계 고장인지 맞힙니다.

| 고장 내는 법 | 기대 증상 | 진단한 단계 |
|---|---|---|
| ① `k=1`로 줄이고 단어를 바꾼 질문 | 답이 엉뚱함 | |
| ② `max_len=80`으로 잘게 자르기 | 문장이 끊김 | |
| ③ 자료를 프롬프트에서 빼먹는 버그 | 있는데 못 씀 | |
| ④ 규칙에서 "자료에 없음" 줄 지우기 | 지어냄 | |"""),
    C('''BREAK = 4      # ✏️ 1 · 2 · 3 · 4 중 하나 — 짝에게 보여 주지 않는다

broken_idx, kw = idx, {}
if BREAK == 1:
    kw = {"k": 1}
elif BREAK == 2:
    broken_idx = rag.Index.build(rag.chunk_folder("data/kb", max_len=80, overlap=0, pattern=None), name="broken")
elif BREAK == 3:
    kw = {"drop_context": True}
elif BREAK == 4:
    kw = {"rules": rag.RULES_NO_REFUSAL}

k = kw.pop("k", 3)
print("10문항 다시 채점")
_ = qa.run_qa(broken_idx, k=k, **kw)'''),
    C('''# 짝이 진단할 질문 하나 — debug 출력만 보고 몇 번 단계인지 말한다
rag.debug("사내 헬스장은 몇 시까지 운영하나요?" if BREAK == 4 else "휴가 쓰려면 며칠 전에 말해야 해요?",
          broken_idx, k=k, **kw);'''),
    M("""**마지막 줄(④)을 꼭 해 봅니다.** 거절 지시 한 줄이 빠졌을 때 무엇이 나오는지 직접 보는 것이 가장 오래 남습니다.

고친 뒤에는 10문항을 다시 돌립니다 — 하나를 고치다 다른 하나가 깨지는 것은 RAG에서도 똑같이 일어납니다."""),
    M("""## 8. 창만 바꿔 다시 측정한다
같은 10문항, 같은 채점 기준으로 **창에 넣는 것만** 세 가지로 바꿉니다.

| 조건 | 창에 들어가는 것 |
|---|---|
| 창에 자료 없음 | 질문만 — 모델은 한빛정밀 규정을 모른다 |
| RAG | 검색한 조각 3개 + 거절 규칙 |
| 자료 전부 | 사내 자료 20편 전체 + 같은 규칙 (01 노트북의 A 조건) |

차이가 곧 **컨텍스트의 효과**이고, RAG와 *자료 전부*의 토큰 차이가 곧 **고르기의 값**입니다."""),
    C('''ALL = "\\n\\n".join(f"<자료 출처=\\"{name}\\">\\n{text}\\n</자료>" for name, text in rag.load_folder("data/kb"))

def judge(answer, t):
    """답 문항은 정답 문자열, 답없음 문항은 "자료에 없음"이 있으면 통과 (출처는 보지 않는다)"""
    return qa.REFUSAL in answer if t.get("refuse") else any(e in answer for e in t["expect"])

def no_context(q):
    return llm.call(q, max_tokens=400)

def with_rag(q):
    hits = idx.search(q, 3)
    return llm.call(rag.make_prompt(q, hits), max_tokens=400)

def with_all(q):
    return llm.call(f"{rag.RULES}\\n\\n{ALL}\\n\\n<질문>{q}</질문>", max_tokens=400)

tests = qa.load_qa()
print(f"{'조건':<14}{'통과':>8}{'답없음 거절':>12}{'평균 입력 토큰':>16}{'평균 초':>9}  1건 비용")
for name, fn in [("창에 자료 없음", no_context), ("RAG", with_rag), ("자료 전부", with_all)]:
    rs = [(t, fn(t["q"])) for t in tests]
    ok = sum(judge(r.text, t) for t, r in rs)
    refused = sum(judge(r.text, t) for t, r in rs if t.get("refuse"))
    tin = sum(r.input_tokens for _, r in rs) / len(rs)
    sec = sum(r.seconds for _, r in rs) / len(rs)
    c = llm.cost(llm.MODEL, int(tin), int(sum(r.output_tokens for _, r in rs) / len(rs)))
    print(f"{name:<14}{ok:>5} / {len(rs)}{refused:>9} / 3{tin:>16,.0f}{sec:>9.1f}  {llm.fmt_cost(c)}")'''),
    M("""| 조건 | 통과 | 답없음 거절 | 평균 입력 토큰 | 평균 초 |
|---|---|---|---|---|
| 창에 자료 없음 | | | | |
| RAG | | | | |
| 자료 전부 | | | | |

- *창에 자료 없음*의 답을 몇 개 열어 봅니다 — 모르면 그럴듯하게 채웁니다
- RAG가 *자료 전부*보다 낮은 문항이 있다면, 그 문항은 검색이 놓친 것입니다 → `rag.debug(...)`
- 하루 1,000건이면 RAG와 *자료 전부*의 비용 차이는 얼마인가"""),
]

# ============================================================== 05 · 4세션
nb05 = [
    M("""# 04 · 계산기와 검색을 붙인 단일 루프
**4세션 · 도구 결과도 컨텍스트다** — 실습 40분

모델은 *이 도구를 이 값으로 불러 달라*고 말할 뿐이고, **실행은 우리 코드가 합니다.**
매 바퀴 `tool_result`가 messages에 쌓입니다 — 그것이 다음 바퀴의 컨텍스트입니다.

에이전트 = **모델 + 도구 + 루프**"""),
    C(SETUP_RAG + '''
import json, inspect
from src import loop

loop.SEARCH_INDEX = rag.Index.build(rag.chunk_folder("data/kb"))'''),
    M("""## 1. 함수 정의의 실물
이름 · 설명 · 입력 스키마 세 가지가 전부입니다. **설명은 모델이 도구를 고르는 유일한 근거**입니다."""),
    C('''print(json.dumps(loop.TOOLS, ensure_ascii=False, indent=2))'''),
    M("""> 문자열 수식을 받아 `eval`로 계산하는 도구는 만들지 않습니다. 모델이 무엇을 넘길지 우리가 통제할 수 없기 때문입니다. `enum`으로 고를 수 있는 값을 제한합니다."""),
    M("## 2. 루프 코드"),
    C('''print(inspect.getsource(loop.run))'''),
    M("""## 3. 1단계 · 붙이기
질문 세 개로 돌려 **매 바퀴 출력**을 봅니다. 셋째 질문 — 두 도구를 차례로 부르는가?"""),
    C('''Q1 = "AX-2041의 무게는 얼마인가요?"
Q2 = "1,234,500원을 3명이 똑같이 나누면 1명당 얼마인가요?"
Q3 = "서울로 3박 출장을 가면 숙박비 한도는 모두 얼마인가요?"

for q in [Q1, Q2, Q3]:
    print("=" * 70, "\\nQ", q)
    answer, trace = loop.run(q)
    print("→ 쓴 도구:", loop.tools_used(trace), "\\n")'''),
    M("""## 4. 2단계 · 일부러 틀리게
도구 설명을 *"검색한다"* / *"계산한다"*로 줄입니다. 코드는 그대로입니다.
모델이 **도구를 안 부르거나, 잘못된 도구를 고르는** 질문을 찾습니다."""),
    C('''print(json.dumps([{t["name"]: t["description"]} for t in loop.TOOLS_VAGUE], ensure_ascii=False))

TRY = [
    Q3,
    "법인카드 사용 한도는 얼마인가요?",              # 자료에 없는 질문 — 지어내는가
    "자기계발비 한도를 12개월로 나누면 한 달에 얼마인가요?",
    "회의실은 하루에 몇 번 예약할 수 있나요?",
]
for q in TRY:
    print("=" * 70, "\\nQ", q)
    _, trace = loop.run(q, tools=loop.TOOLS_VAGUE, system=None)
    print("→ 쓴 도구:", loop.tools_used(trace), "\\n")'''),
    M("""## 5. 설명 문장만 고쳐 바로잡는다
잘못 고른 질문을 하나 정하고, **description만** 고쳐 다시 돌립니다. 코드는 건드리지 않습니다."""),
    C('''MY_TOOLS = [
    {**loop.TOOLS_VAGUE[0], "description": "계산한다."},      # ✏️ 이 문장만 고친다
    {**loop.TOOLS_VAGUE[1], "description": "검색한다."},      # ✏️ 이 문장만 고친다
]
Q = TRY[2]                                                    # ✏️ 잘못 골랐던 질문

for name, tools in [("고치기 전", loop.TOOLS_VAGUE), ("고친 뒤", MY_TOOLS)]:
    print("=" * 70, f"\\n[{name}]")
    _, trace = loop.run(Q, tools=tools, system=None)
    print("→ 쓴 도구:", loop.tools_used(trace))'''),
    M("""| 질문 | 고치기 전 고른 도구 | 고친 설명 문장 | 고친 뒤 고른 도구 |
|---|---|---|---|
| | | | |

## 6. 창에 무엇이 쌓였나
마지막 실행의 messages를 열어 봅니다. 도구 결과가 그대로 창에 들어가 있습니다 — 그래서 **도구 결과도 컨텍스트**입니다."""),
    C('''# loop.run 안의 msgs를 보려면 한 바퀴씩 직접 돌려 본다
msgs = [{"role": "user", "content": Q3}]
r = loop._create(model=llm.MODEL, max_tokens=800, tools=loop.TOOLS, messages=msgs, system=loop.SYSTEM)
for b in r.content:
    print(b.type, getattr(b, "name", ""), getattr(b, "input", getattr(b, "text", ""))) '''),
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
    for name, cells in [("01_window", nb01), ("02_strategies", nb02), ("03a_rag_index", nb03),
                        ("03b_rag_qa", nb04), ("04_tool_loop", nb05)]:
        nbf.write(nb(cells), NB / f"{name}.ipynb")
        print("작성:", f"notebooks/{name}.ipynb", len(cells), "셀")

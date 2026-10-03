"""notebooks/*.ipynb 를 만든다 (강사용 — 수강생은 만들어진 노트북만 쓰면 된다).

    python tools/make_notebooks.py
"""
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

# ============================================================== 02
nb01 = [
    M("""# 01 · API와 메시지
**블록 2 · API와 메시지** — 실습 25분

1. 첫 호출 — SDK를 그대로 써 본다
2. 응답 읽기 — `stop_reason` · `usage`
3. system과 user
4. 모델은 기억하지 않는다 — 대화 이력
5. 같은 질문 다섯 번 — 그리고 temperature
6. 토큰과 비용"""),
    C(SETUP),
    M("""## 1. 첫 호출
`src/llm.py`의 `call()`은 아래 코드를 감싼 것입니다. 한 번은 SDK를 그대로 써 봅니다.
(모의 모드에서는 이 셀을 건너뜁니다.)"""),
    C('''if not llm.MOCK:
    import anthropic
    client = anthropic.Anthropic()          # .env의 ANTHROPIC_API_KEY를 읽는다
    r = client.messages.create(
        model=llm.MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": "연차 신청 절차를 세 단계로 알려줘"}],
    )
    print(r.content[0].text)
else:
    print("모의 모드 — 건너뜀")'''),
    M("""## 2. 응답 읽기
응답에는 글 말고도 **왜 멈췄는지**(`stop_reason`)와 **토큰을 얼마나 썼는지**(`usage`)가 들어 있습니다."""),
    C('''r = llm.call("연차 신청 절차를 세 단계로 알려줘", max_tokens=300)
print(r.text)
print("---")
print("stop_reason :", r.stop_reason)
print("입력 토큰   :", r.input_tokens)
print("출력 토큰   :", r.output_tokens)
print("걸린 시간   :", f"{r.seconds:.2f}초")'''),
    M("""### max_tokens에서 잘리면
`max_tokens`를 작게 주면 글이 중간에 끊기고 `stop_reason`이 `max_tokens`가 됩니다.
**프로그램은 글을 쓰기 전에 `stop_reason`부터 확인합니다** — 잘린 JSON은 파싱이 깨집니다."""),
    C('''r = llm.call("연차 신청 절차를 세 단계로 자세히 알려줘", max_tokens=20)
print(repr(r.text))
print("stop_reason :", r.stop_reason)
if r.stop_reason == "max_tokens":
    print("→ 잘렸습니다. max_tokens를 늘리거나 더 짧게 쓰라고 지시합니다.")'''),
    M("""## 3. system과 user
매번 같은 **역할 · 규칙 · 형식**은 `system`에, 매번 바뀌는 **자료와 질문**은 `user`에 둡니다.
같은 질문에 system만 바꿔 봅니다."""),
    C('''question = "다음 주 화요일 오후 2시에 전 직원 소방 훈련이 있습니다. 이 내용을 안내해 주세요."

for system in [
    None,
    "당신은 신입 사원에게 친절하게 설명하는 인사팀 담당자입니다. 두 문장 이내로 씁니다.",
    "당신은 사내 메신저 공지 봇입니다. 이모지 없이 한 줄로, '[공지]'로 시작합니다.",
]:
    r = llm.call(question, system=system, max_tokens=200)
    print(f"[system] {system}\\n{r.text.strip()}\\n")'''),
    M("""## 4. 모델은 기억하지 않는다
API는 매 호출이 처음입니다. 이어서 대화하려면 **앞서 주고받은 메시지를 직접 다시 보냅니다.**"""),
    C('''r1 = llm.call("제 이름은 김민수이고, 생산관리팀에서 일합니다.", max_tokens=100)
print("1:", r1.text.strip())

r2 = llm.call("제 이름과 부서가 뭐였죠?", max_tokens=100)      # 이력 없이
print("2 (이력 없음):", r2.text.strip())

history = [
    {"role": "user", "content": "제 이름은 김민수이고, 생산관리팀에서 일합니다."},
    {"role": "assistant", "content": r1.text},
]
r3 = llm.call("제 이름과 부서가 뭐였죠?", history=history, max_tokens=100)
print("3 (이력 있음):", r3.text.strip())
print("\\n이력을 보낸 호출의 입력 토큰:", r3.input_tokens, "— 대화가 길어질수록 매번 더 냅니다")'''),
    M("""## 5. 같은 질문 다섯 번
같은 질문을 두 가지로 각각 5회 보내고 결과를 나란히 놓습니다.

**관찰할 것**
- 다섯 개 중 몇 개가 서로 같은가
- 달라지는 곳은 문장의 어디인가
- 정답이 거의 정해진 질문(절차)과 열린 질문(슬로건)은 차이가 어떻게 다른가
- 출력 토큰 수는 매번 같은가"""),
    C('''QUESTIONS = {
    "절차": "회사 연차 신청 절차를 세 단계로 알려줘",
    "슬로건": "신제품 무선 청소기 슬로건 하나만 지어줘",
}

runs = {}
for name, q in QUESTIONS.items():
    runs[name] = []
    for i in range(5):
        r = llm.call(q, max_tokens=200)
        runs[name].append({"text": r.text, "output_tokens": r.output_tokens})
        print(name, i + 1, r.output_tokens, "|", r.text.strip().replace("\\n", " ")[:60])
    print()

for name, rs in runs.items():
    print(f"{name}: 서로 다른 답 {len({x['text'] for x in rs})}개 / 5")'''),
    M("""### temperature — 흔들림을 조절하는 손잡이
`temperature`는 다음 토큰을 얼마나 고르게 뽑을지 정합니다. **0 = 가장 확률 높은 토큰 위주(덜 흔들림)**, **1 = 더 고르게(더 다양함)**.
- **SDK 1.x**: `messages.create()`에서 `temperature` 인자가 빠졌습니다. (`llm.call`은 `extra_body`로 우회해 보냅니다.)
- **API**: 모델마다 다릅니다. 이전 세대(Haiku 4.5)는 받지만, **최신 모델(Sonnet 5.5 · Opus 5.5)은 거부합니다** — 400 오류.

아래 셀은 ① Haiku로 같은 질문을 온도 0과 1에서 세 번씩 보내 비교하고, ② Sonnet 5.5에 보내 거부되는 것을 봅니다.

**관찰할 것**
- 온도 1에서 답이 얼마나 다양해지는가
- 온도 0이면 세 번 모두 똑같은가 — *0이어도 완전히 같다는 보장은 없습니다*
- 최신 모델에서는 이 손잡이 자체가 없다 → 그래서 **여러 번 돌려 재는 습관(블록 4)**이 필요하다"""),
    C('''Q = "신제품 무선 청소기 슬로건 하나만 지어줘. 슬로건만 답해."

# ① temperature를 받는 모델(Haiku 4.5) — 온도를 바꿔 가며 세 번씩
print("모델:", llm.MODEL)
for t in [0.0, 1.0]:
    answers = [llm.call(Q, temperature=t, max_tokens=60).text.strip() for _ in range(3)]
    print(f"\\ntemperature={t} → 서로 다른 답 {len(set(answers))}개 / 3")
    for a in answers:
        print("   ", a.replace("\\n", " ")[:60])

# ② 최신 모델(Sonnet 5.5)은 temperature 자체를 거부한다
print("\\n모델:", llm.MODEL_ADVANCED)
try:
    llm.call(Q, model=llm.MODEL_ADVANCED, temperature=0.0, max_tokens=20)
    print("받아들였습니다")
except Exception as e:
    print(type(e).__name__, "—", str(e)[:200])'''),
    M("""> 대신 생길 수 있는 조절 손잡이는 `effort`("low"~"max")처럼 *얼마나 생각할지*입니다. 지원 여부는 모델마다 다르므로 강의 당일 문서로 확인합니다."""),
    M("결과는 지우지 말고 저장해 둡니다. 오후 블록 4에서 *한 번 돌려 보고 판단하면 안 되는 이유*의 근거로 다시 씁니다."),
    C('''import json
Path("results").mkdir(exist_ok=True)
Path("results/repeat5.json").write_text(
    json.dumps({"questions": QUESTIONS, "runs": runs}, ensure_ascii=False, indent=2),
    encoding="utf-8")
print("저장: results/repeat5.json")'''),
    M("""## 6. 토큰과 비용
비용 = 입력 토큰 × 입력 단가 + 출력 토큰 × 출력 단가. **단가는 강의 당일 요금표로 `src/llm.py`의 `PRICES`를 채웁니다.**
(채우지 않은 모델은 "단가 미입력"으로 나옵니다.)"""),
    C('''doc = Path("data/docs/11_정보보호지침_개정_긴문서.txt").read_text(encoding="utf-8")
r = llm.call(f"다음 문서를 세 줄로 요약해 주세요.\\n\\n{doc}", max_tokens=300)
print(r.text.strip(), "\\n")
print(f"입력 {r.input_tokens} 토큰 · 출력 {r.output_tokens} 토큰 · 1건 {llm.fmt_cost(r.cost)}")
if r.cost is not None:
    print(f"하루 1,000건이면 약 ${r.cost * 1000:.2f}")'''),
]

# ============================================================== 03
nb02 = [
    M("""# 02 · 프롬프트 설계
**블록 3 · 프롬프트 설계** — 실습 60분

여기서 만드는 v1이 오후 블록 4에서 20문항으로 채점받는 **1차**의 재료입니다. 지금은 그 전에 "쓸 만한 프롬프트 하나"를 준비하는 단계입니다.

사내 문서 한 편에서 **「제목 · 항목 3개 · 단위」**를 뽑아내는 프롬프트를 씁니다.

```json
{"제목": "2026년 4분기 사무용품 구매 계획",
 "항목": [{"이름": "복사용지", "값": 120, "단위": "박스"},
          {"이름": "토너", "값": 8, "단위": "개"},
          {"이름": "예산", "값": 340, "단위": "만원"}]}
```

**통과 기준** — 10번 돌려 10번 모두 `json.loads` 통과 · 항목이 정확히 3개 · 값은 숫자, 단위는 문자열 · 문서에 없는 값은 지어내지 않음

| 순서 | 할 일 | 시간 |
|---|---|---|
| 1 | 문서 고르기 — 업무 문서 한 편과 뽑을 항목 세 개 (없으면 `data/docs/`) | 10분 |
| 2 | v0 — 한 줄짜리 지시로 먼저 돌려 보고 무엇이 부족한지 적는다 | 10분 |
| 3 | v1 — 프롬프트 파일을 한 줄씩 채우고, 채울 때마다 돌려 본다 | 25분 |
| 4 | 짝 점검 — 체크리스트로 서로의 v1을 보고, 10번 돌려 형식 확인 | 15분 |"""),
    C(SETUP + '''
import json
from src.grade import build, parse, check'''),
    M("## 1. 문서 고르기"),
    C('''DOC_PATH = "data/docs/01_사무용품_구매계획.txt"   # ✏️ 내 업무 문서로 바꿔도 됩니다
doc = Path(DOC_PATH).read_text(encoding="utf-8")
print(doc)'''),
    M("""## 2. v0 — 한 줄짜리 지시
`prompts/prompt_v0.txt`를 그대로 돌립니다. 결과를 보고 **무엇이 부족한지** 적습니다."""),
    C('''def try_prompt(prompt_text, document, n=1, show=True):
    """프롬프트를 n번 돌려 JSON 파싱 성공 횟수를 센다."""
    system, user = build(prompt_text, document)
    if show:
        print(f"=== system에 들어간 것 ===\\n{system}\\n")
        print(f"=== user에 들어간 것 ===\\n{user}\\n")
    ok = 0
    for i in range(n):
        r = llm.call(user, system=system, max_tokens=1000)
        try:
            out = parse(r.text); ok += 1; note = f"JSON OK · 항목 {len(out.get('항목', []))}개"
        except ValueError as e:
            note = f"JSON 실패 — {e}"
        if show:
            print(f"--- {i+1}회 · {note} · 출력 {r.output_tokens} 토큰")
            print(r.text.strip()[:600])
    print(f"\\n파싱 성공 {ok} / {n}")
    return ok

v0 = llm.load_prompt("prompts/prompt_v0.txt")
print(v0, "\\n========")
try_prompt(v0, doc)'''),
    M("""**v0에서 부족했던 것** (한 줄씩):
-
-
- """),
    M("""## 3. v1 — 아래 표를 한 줄씩 채우고 바로 돌려본다
`prompts/prompt_v1.txt`를 엽니다. 표의 항목을 **위에서부터 한 줄씩** 채우고, 한 줄 채울 때마다 바로 아래 셀을 다시 실행해 뭐가 달라지는지 봅니다. 다 채운 뒤에 한꺼번에 실행하지 않습니다 — 그러면 뭐가 효과 있었는지 알 수 없습니다.

| 채울 내용 | 넣는 곳 |
|---|---|
| 역할을 구체적으로 — 누가, 무엇을 위해 | `<역할>` |
| 할 일을 구체적으로 — 몇 개를, 어떤 기준으로 뽑는지 | `<할 일>` |
| "~하지 마" 대신 "~해라"로 쓰기 | `<역할>` `<할 일>` 전체 |
| 예시 하나 — 짧은 문서와 정답 JSON | `<예시>` |
| 원하는 JSON 모양을 그대로 보여주기 | `<출력 형식>` |

파일 맨 위 `=== system ===` 아래는 system으로, `=== user ===` 아래는 user로 보냅니다. `{document}` 자리에 문서가 들어갑니다."""),
    C('''v1 = llm.load_prompt("prompts/prompt_v1.txt")      # 파일을 고친 뒤 이 셀을 다시 실행
try_prompt(v1, doc)'''),
    M("""> 막히면 `solutions/prompts/prompt_v1.txt`를 열어 봅니다. 그대로 베끼기보다, 내 v1과 **무엇이 다른지** 비교합니다."""),
    M("""## 4. 짝 점검 체크리스트
v1을 짝과 바꿔 보고, 아래 다섯 가지를 하나씩 확인합니다. 하나라도 "아니오"면 3절로 돌아가 고칩니다.

- [ ] **형식** — 10번 돌려 10번 다 `json.loads`로 읽히는가? (코드블록·설명 없이)
- [ ] **개수** — 항목이 항상 정확히 3개인가? (많지도 적지도 않게)
- [ ] **타입** — 값은 숫자, 단위는 문자열인가?
- [ ] **지어냄 금지** — 문서에 없는 수치를 채워 넣지 않는가?
- [ ] **구조** — `=== system ===`에는 역할·규칙·형식만, `=== user ===`에는 문서만 들어가 있는가?

아래 셀은 이 중 **첫 번째(형식)만 자동으로** 확인합니다. 나머지 네 개는 사람이 눈으로 봐야 합니다 — 9번 셀에서 연 원문을 같이 보면서 짝과 확인하세요."""),
    C('''ok = try_prompt(v1, doc, n=10, show=False)
print("통과" if ok == 10 else "아직 — 형식 지시 · 예시를 다시 봅니다")'''),
    M("""## 5. 생각할 자리를 준다
**방금 만든 v1에, 한 가지를 더합니다.** 바로 `<json>`을 쓰게 하지 말고, **근거를 먼저 옮겨 적게** 합니다. 출력 형식은 v1 것을 그대로 쓰고, 규칙만 하나 추가합니다.

코드는 `<json>` 안만 꺼내 쓰고(v1과 같은 `parse()`), `<근거>`는 사람이 디버깅할 때 엽니다."""),
    C('''import re

system, user = build(v1, doc)      # v1의 <출력 형식>을 그대로 쓴다
EVIDENCE = ("\\n\\n<근거 규칙>\\n<json>을 쓰기 전에 <근거>에 문서에서 실제로 찾은 문장을 그대로 "
            "옮겨 적어라. 문서에 없으면 그 항목은 <json>에 넣지 않는다.\\n</근거 규칙>")

r = llm.call(user, system=(system or "") + EVIDENCE, max_tokens=800)
print(r.text.strip())

m = re.search(r"<근거>(.*?)</근거>", r.text, re.S)
print("\\n→ 코드가 디버깅용으로 꺼낸 <근거>:", (m.group(1).strip() if m else "(없음)"))
print("→ parse() 결과(<json>만 읽음):", parse(r.text))'''),
    M("""## 6. 한 덩어리 일을 세 단계로 나눈다 — 뽑기(모델) → 검사(코드) → 쓰기(모델)
이 절은 프롬프트를 잘 쓰는 기술이 아니라 **작업을 어떻게 나눌지**에 대한 얘기입니다. 프롬프트로 해결하려 하지 말고 코드로 해야 하는 부분이 있다는 것을 봅니다.

"문서에서 수치를 뽑고, 3개가 맞는지 확인하고, 직원용 안내문으로 써 줘"를 한 번에 시킬 수도 있습니다. 그러면 셋 중 어디서 틀렸는지 알 수 없고, 모델이 개수를 잘못 세도 그냥 넘어갑니다.

아래 셀은 이 일을 셋으로 나눕니다.
- **① 뽑기** — v1으로 JSON을 뽑습니다 (모델)
- **② 검사** — 항목이 3개인지, 값이 숫자인지 셉니다 (**코드** — 세는 일은 모델이 자주 틀립니다)
- **③ 쓰기** — ②를 통과한 JSON만 보고 안내문을 씁니다 (모델). ②에서 걸리면 ③은 건너뛰고 ①로 돌아갑니다."""),
    C('''# ① 추출 — 지금까지 쓴 v1을 그대로 쓴다
system, user = build(v1, doc)
r1 = llm.call(user, system=system)
try:
    data = parse(r1.text)
except ValueError as e:
    data = None
    print("① 추출 실패:", e)
print("① 추출:", json.dumps(data, ensure_ascii=False))

# ② 검증 — 모델이 아니라 코드가 센다
problems = []
if data is None:
    problems.append("JSON 아님")
else:
    if len(data.get("항목", [])) != 3:
        problems.append(f"항목 {len(data.get('항목', []))}개")
    for it in data.get("항목", []):
        if not isinstance(it.get("값"), (int, float)):
            problems.append(f"{it.get('이름')} 값이 숫자가 아님")
print("② 검증:", problems or "통과")

# ③ 작성 — 검증을 통과한 JSON만 안내문으로
if not problems:
    r3 = llm.call(
        "아래 JSON만 보고 직원용 메신저 안내문을 세 줄로 쓰세요. JSON에 없는 내용은 쓰지 않습니다.\\n\\n"
        + json.dumps(data, ensure_ascii=False),
        max_tokens=300)
    print("③ 작성:\\n" + r3.text.strip())
else:
    print("③ 작성: 건너뜀 — ①로 돌아가 고칩니다")'''),
    M("""## 7. 일반화된 프롬프트를 여러 다른 문서에 적용한다
v1은 문서 한 편에 맞춘 프롬프트가 아닙니다. 역할 · 할 일 · 출력 형식 · 예시는 고정하고 `{document}` 자리만 비워 둔 **일반화된 프롬프트**입니다.

아래 셀은 그 v1을 `data/docs/`의 문서 5개에 차례로 적용해, **프롬프트를 고치지 않고도 다른 문서에서 같은 모양의 결과가 나오는지** 확인합니다. 오후 블록 4는 같은 방법으로 문서 20개에 적용합니다. (이 셀은 아무것도 새로 저장하지 않습니다.)"""),
    C('''for p in sorted(Path("data/docs").glob("*.txt"))[:5]:
    system, user = build(v1, p.read_text(encoding="utf-8"))
    r = llm.call(user, system=system)
    try:
        out = parse(r.text)
        print(f"{p.name:<28} OK  ", [(i.get("이름"), i.get("값")) for i in out.get("항목", [])])
    except ValueError as e:
        print(f"{p.name:<28} 실패 {e}")'''),
    M("""## 제출할 것
- `prompts/prompt_v0.txt` · `prompts/prompt_v1.txt` — 두 버전을 모두 남긴다
- v0에서 v1로 넘어오며 추가한 것과 그 이유 세 줄:
  1.
  2.
  3. """),
]

# ============================================================== 04
nb03 = [
    M("""# 03 · 평가
**블록 4 · 평가** — 실습 50분

고쳤다는 느낌은 증거가 아닙니다. **같은 문항, 같은 기준, 같은 방법으로** 다시 재야 고친 것입니다.

| 순서 | 할 일 | 시간 |
|---|---|---|
| 1 | 20문항 — 구성표대로 만들고 통과 조건을 적는다 | 15분 |
| 2 | v1 채점 — 통과 수와 실패 유형을 결과표에 | 10분 |
| 3 | v2 · v3 — 한 유형씩 고치고 다시 채점 | 15분 |
| 4 | 모델 비교 — v3를 모델 셋에 돌린다 | 10분 |"""),
    C(SETUP + '''
import json
from collections import Counter
from src.grade import load_tests, run, check, summarize, save, print_table, print_fails, KINDS'''),
    M("""## 1. 고정 테스트 20문항
`data/tests.jsonl` — 한 줄에 한 문항. **프롬프트를 고치기 전에 만들고, 고치는 동안 바꾸지 않습니다** (고치는 중간에 문항이 바뀌면 전후 비교가 안 됩니다).

20문항은 4종류로 나뉘어 있고, 종류마다 보려는 게 다릅니다.

| 구성 | 문항 수 | 이 실습의 문항 | 뭘 보려고 넣었나 |
|---|---|---|---|
| 평범한 입력 | 10 | 1–10 공지 · 보고서 | 가장 흔한 문서에서 기본으로 되는지 |
| 경계에 있는 입력 | 5 | 11 긴 문서 · 12 단위 없음 · 13 항목 둘 · 14 한글 숫자 · 15 표 | 까다로운 형태에서도 버티는지 |
| 답이 자료에 없는 입력 | 3 | 16 · 17 수치 없음 · 18 예산 미정 | 없는 값을 지어내지 않고 거절하는지 |
| 실제로 틀렸던 입력 | 2 | 19 날짜 많음 · 20 영문 혼용 | 아래 설명 |

**"실제로 틀렸던 입력"이 뭔지:** 앞의 세 종류는 미리 설계해 둔 문제지만, 이 둘은 **"내 v1을 돌려봤더니 실제로 틀렸던 문서"**를 넣는 자리입니다. 지금은 강사가 미리 겪은 흔한 실패 예시(날짜 많은 문서, 영어 섞인 발주서)가 채워져 있을 뿐입니다.

**내 것으로 바꾸는 법:**
1. 02 노트북에서 v1이 실제로 틀렸던 문서를 `data/docs/`에 저장한다
2. `tests.jsonl`의 19·20번 줄에서 `doc`과 `check`를 그 문서에 맞게 고친다
3. **그다음부터는 문항을 바꾸지 않는다** — 고치는 동안 문항이 바뀌면 비교할 수 없다

| check 필드 | 뜻 |
|---|---|
| `items` | 값이 있는 항목이 정확히 이 개수여야 통과 |
| `values` | 이름에 이 말이 들어간 항목의 값이 이 숫자여야 통과 (340만원 = 340 또는 3,400,000) |
| `absent` | 이 이름의 항목은 값이 없어야(null) 통과 — 지어냄을 잡는다 |
| `has` | 답 어딘가에 이 말이 있어야 통과 |"""),
    C('''tests = load_tests()
print(Counter(t["group"] for t in tests))
for t in tests[:3] + tests[15:18]:
    print(t["id"], t["group"], t["doc"].split("/")[-1], t["check"])'''),
    M("""## 2. check — 판정 규칙
`check(출력, 통과 조건)` → `(통과 여부, 실패 유형, 설명)`. 가짜 출력으로 먼저 확인합니다.
판정 순서: **형식 위반 → 지어냄 → 지시 일부 누락 → 사실 오류**"""),
    C('''spec = tests[0]["check"]
samples = {
    "정상": '{"제목": "사무용품 구매 계획", "항목": [{"이름": "복사용지", "값": 120, "단위": "박스"}, {"이름": "토너", "값": 8, "단위": "개"}, {"이름": "예산", "값": 340, "단위": "만원"}]}',
    "코드 블록": '```json\\n{"제목": "x", "항목": []}\\n```',
    "앞에 설명": '다음과 같습니다.\\n{"제목": "x", "항목": []}',
    "두 개만": '{"제목": "x", "항목": [{"이름": "복사용지", "값": 120, "단위": "박스"}, {"이름": "토너", "값": 8, "단위": "개"}]}',
    "숫자 틀림": '{"제목": "x", "항목": [{"이름": "복사용지", "값": 100, "단위": "박스"}, {"이름": "토너", "값": 8, "단위": "개"}, {"이름": "예산", "값": 340, "단위": "만원"}]}',
}
for name, text in samples.items():
    print(f"{name:<6}", check(text, spec))

print("지어냄 ", check('{"제목": "x", "항목": [{"이름": "참석자", "값": 7, "단위": "명"}, {"이름": "회의 시간", "값": 60, "단위": "분"}, {"이름": "예산", "값": 500, "단위": "만원"}]}', tests[17]["check"]))'''),
    M("""## 3. 1차 · v1 채점
**여러분의 `prompts/prompt_v1.txt`**를 20문항에 돌립니다. 아직 비어 있다면 풀이본으로 바꿉니다."""),
    C('''V1 = "prompts/prompt_v1.txt"          # ✏️ 비어 있으면 "solutions/prompts/prompt_v1.txt"

passed, fails, rows = run(V1, detail=True)
s1 = summarize(rows, llm.MODEL)
save(V1, llm.MODEL, rows, s1, note="v1")
print(f"통과 {passed} / {len(rows)}")
print(Counter(kind for _, kind in fails))
print_fails(rows)'''),
    M("""### 실패 문항을 직접 연다
통과 수만 보면 **새로 생긴 실패**를 놓칩니다. 실패 문항의 출력을 열어 유형이 맞는지 사람이 확인합니다.
(사실 오류는 코드가 숫자만 보고 판정합니다 — 이름을 다르게 붙였을 뿐인지 눈으로 봅니다.)"""),
    C('''FAIL_ID = fails[0][0] if fails else 1      # ✏️ 보고 싶은 문항 번호
row = next(r for r in rows if r["id"] == FAIL_ID)
print(f"#{row['id']} [{row['group']}] {row['kind']} — {row['why']}\\n")
print(row["text"][:1200])'''),
    M("""## 4. 2차 · 한 유형씩 고친다
1. 가장 많은 실패 유형 **하나**를 고른다
2. 그 유형에 맞는 기법 **하나**만 넣어 `prompts/prompt_v2.txt`로 저장한다
3. 같은 20문항으로 v1과 v2를 비교한다
4. 나빠졌으면 되돌린다

| 유형 | 고치는 곳 |
|---|---|
| 형식 위반 | 출력 형식 지시 · 예시 · `<json>` 태그로 감싸게 하기 |
| 지시 일부 누락 | 지시를 구조로 나누기 · 개수 규칙을 분명히 |
| 지어냄 | 거절 지시 + "대신 이렇게(null · 빈 목록)" · 근거 요구 |
| 사실 오류 | 프롬프트가 아니라 참조 문서 — **Day 2** |"""),
    C('''V2 = "solutions/prompts/prompt_v2.txt"   # ✏️ 내 v2: "prompts/prompt_v2.txt"
NOTE = "형식: <json> 태그로 감싸게 함"      # ✏️ 무엇을 바꿨는지 한 줄

p2, f2, rows2 = run(V2, detail=True)
s2 = summarize(rows2, llm.MODEL)
save(V2, llm.MODEL, rows2, s2, note=NOTE)
print_table([("v1", llm.MODEL, s1), ("v2", llm.MODEL, s2)])

before = {r["id"] for r in rows if r["ok"]}
after = {r["id"] for r in rows2 if r["ok"]}
print("\\n새로 통과:", sorted(after - before), " 새로 실패:", sorted(before - after))'''),
    M("""### 2차 · 한 번 더 → v3
v2의 실패 중 가장 많은 유형 하나를 골라 v3를 만듭니다. 풀이본 v3는 **지어냄 · 누락**을 겨냥해 `<근거>`와 null 규칙을 넣었습니다."""),
    C('''V3 = "solutions/prompts/prompt_v3.txt"   # ✏️ 내 v3: "prompts/prompt_v3.txt"
NOTE = "지어냄: 근거 먼저 + 없으면 null/빈 목록"

p3, f3, rows3 = run(V3, detail=True)
s3 = summarize(rows3, llm.MODEL)
save(V3, llm.MODEL, rows3, s3, note=NOTE)
print_table([("v1", llm.MODEL, s1), ("v2", llm.MODEL, s2), ("v3", llm.MODEL, s3)])
print_fails(rows3)'''),
    M("""**발표 — 한 문장으로**
> "___ 유형을 줄이려고 ___를 바꿨더니 통과가 __ → __ 가 됐고, 대신 ___ 가 생겼다(또는 생기지 않았다)."
"""),
    M("""## 5. 3차 · 모델을 바꿔 잰다
같은 v3, 같은 20문항 — **모델만** 바꿉니다. 모델 이름은 `src/llm.py`의 `MODELS`에서 강의 당일 쓸 수 있는 것으로 확인합니다.

고르는 기준 — 통과 기준을 넘는 모델 중에서 가장 싸고 빠른 것. **가격은 통과 수를 본 다음에 봅니다.**"""),
    C('''compare = []
for m in llm.MODELS:
    pm, fm, rm = run(V3, model=m, detail=True)
    sm = summarize(rm, m)
    save(V3, m, rm, sm, note="모델 비교")
    compare.append(("v3", m, sm))
print_table(compare)'''),
    M("""## 6. 결과표
`results/scoreboard.csv`에 실행할 때마다 한 줄씩 쌓입니다. 엑셀로 열어도 됩니다."""),
    C('''import csv
with open("results/scoreboard.csv", encoding="utf-8-sig") as f:
    for row in list(csv.reader(f))[-8:]:
        print(" | ".join(row[:11]))'''),
    M("""## 내일 가지고 올 것
- `prompt_v3.txt` · `tests.jsonl` · `grade.py` · 결과표(`results/scoreboard.csv`)
- 생각해 올 것 — 오늘 남은 실패 중, **"모델이 몰라서"** 틀린 것은 무엇인가 (→ Day 2 컨텍스트)"""),
]

if __name__ == "__main__":
    NB.mkdir(exist_ok=True)
    for name, cells in [("01_api_basics", nb01), ("02_prompt_design", nb02),
                        ("03_evaluation", nb03)]:
        nbf.write(nb(cells), NB / f"{name}.ipynb")
        print("작성:", f"notebooks/{name}.ipynb", len(cells), "셀")

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

# ============================================================== 01
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
    print("\\n--- r에 저장된 것 전체 (글은 그중 하나일 뿐) ---")
    print(r)
else:
    print("모의 모드 — 건너뜀")'''),
    M("""`r`은 글 하나가 아니라 `id`·`role`·`type`·`content`(블록 리스트)·`stop_reason`·`stop_sequence`·`model`·`usage`(입력/출력 토큰 · 캐시 사용량 · 처리 등급 등)·`container`·`diagnostics`·`stop_details`까지 다 들어있는 객체입니다. `r.content[0].text`는 그중 **글자만** 꺼낸 것이고, 나머지는 뒤에서(2·4절) 하나씩 다룹니다."""),
    M("""## 2. 응답 읽기
응답에는 글 말고도 **왜 멈췄는지**(`stop_reason`)와 **토큰을 얼마나 썼는지**(`usage`)가 들어 있습니다."""),
    C('''r = llm.call("연차 신청 절차를 세 단계로 알려줘", max_tokens=300)
print(r.text)
print("---")
print("stop_reason :", r.stop_reason)
print("입력 토큰   :", r.input_tokens)
print("출력 토큰   :", r.output_tokens)
print("걸린 시간   :", f"{r.seconds:.2f}초")'''),
    M("""### 입력은 두 번 모양이 바뀐다 — 내 코드 → 서버 → 모델
"안녕"이 모델에 닿기까지 **두 단계**를 거치고, 단계마다 모양이 다릅니다. 이 둘을 섞으면 토큰 수가 이해가 안 됩니다.

```
내 코드 ──(JSON)──▶ Anthropic 서버 ──(토큰 열)──▶ 모델
```

**1단계 — 내 코드가 서버로 보내는 것 (JSON).** 이건 모델이 받는 모양이 **아닙니다.**"""),
    C('''import json as _json

request = {
    "model": llm.MODEL,
    "max_tokens": 20,
    "messages": [{"role": "user", "content": "안녕"}],
}
print("내가 입력한 건: '안녕' (2글자)")
print("\\n내 코드가 서버로 보내는 요청 (JSON) — 모델이 받는 모양은 아님:")
print(_json.dumps(request, ensure_ascii=False, indent=2))'''),
    M("""**2단계 — 서버가 이 JSON을 읽고 모델용으로 다시 쓴 것.** 서버는 JSON 글자를 모델에 넘기지 않습니다.
- `model` → 어느 모델에 보낼지 **고르는 데만** 쓰고 버림. 모델 입력에 안 들어감
- `max_tokens` → 생성을 몇 토큰에서 **끊을지**에만 쓰고 버림. 모델 입력에 안 들어감
- `messages` → **이것만** 모델에 들어감. 단, `"role": "user"` 같은 글자가 아니라 **특수 토큰**(구조 표식)으로 바뀜

모델이 실제로 받는 토큰 열은 이런 모양입니다 (`[ ]`는 글자가 아닌 특수 토큰):
```
[대화 시작] [user 차례] 안녕 [내용 끝] [assistant 차례] ← 모델은 여기서부터 이어 쓴다
```"""),
    C('''r = llm.call("안녕", max_tokens=20)
print("모델이 받은 입력 토큰 수:", r.input_tokens, " — '안녕' 2글자가 11토큰")
print("\\n돌아온 응답 전체:")
print(r.raw)'''),
    M("""응답엔 `id`(요청 번호) · `stop_reason`(멈춘 이유) · `usage`(토큰 수뿐 아니라 캐시 사용량 · 처리 등급 · 추론 지역까지) 같은 게 글 말고도 같이 옵니다. `r.text`만 보면 이 중 대부분을 놓치는 겁니다 — `llm.py`의 `Result`는 지금 당장 필요한 몇 개(`text`·`stop_reason`·토큰 수)만 추려서 보여주는 것뿐입니다.

### 그 11토큰은 뭔가 — JSON 글자가 아니다
"JSON에서 안녕을 뺀 나머지가 토큰 아니냐"고 생각하기 쉽습니다. 아닙니다. 내용을 바꿔 가며 세어 보면 알 수 있습니다."""),
    C('''for t in ["a", "hello", "안", "안녕"]:
    print(f"{t!r:34} → {llm.count_tokens(t):>2} 토큰")
j = '{"role": "user", "content": ""}'
print(f"{j!r:34} → {llm.count_tokens(j):>2} 토큰   ← JSON 글자를 내용으로 보내 보면")'''),
    M("""- 영어는 `a`든 `hello`든 **단어 하나 = 1토큰**이라 전부 8 → 내용을 뺀 **틀이 정확히 7개**
- 한글은 **한 글자 ≈ 2토큰** → `안` 7+2=9, `안녕` 7+4=11
- JSON 글자 `{"role": "user", "content": ""}`를 **내용으로** 보내면 틀 7을 빼고도 10개가 넘습니다. JSON 글자가 틀이었다면 7이 나올 수 없습니다 → **틀 7개는 JSON 글자가 아닙니다**

그러니 11개 = **구조 표식 7개 + "안녕" 4개**입니다.

### 틀 7개는 "내 메시지 포장 3 + 대화 틀 4"
`role`·`user`·`content`에 해당하는 표식이라면 3개면 될 텐데 왜 7인가 — 메시지 수를 바꿔 가며 재면 갈립니다."""),
    C('''import anthropic
_c = anthropic.Anthropic()
def _n(msgs):
    return _c.messages.count_tokens(model=llm.MODEL, messages=msgs).input_tokens
u = lambda s: {"role": "user", "content": s}
a = lambda s: {"role": "assistant", "content": s}
for name, msgs in [("1턴 [a]", [u("a")]),
                   ("3턴 [a|b|a]", [u("a"), a("b"), u("a")]),
                   ("5턴 [a|b|a|b|a]", [u("a"), a("b"), u("a"), a("b"), u("a")])]:
    total = _n(msgs); content = len(msgs)      # 내용은 메시지당 1토큰
    print(f"{name:18} → {total:>2} 토큰 = 내용 {content} + 틀 {total - content}")'''),
    M("""메시지가 하나 늘 때마다 틀이 **정확히 3**씩 늡니다 → `틀 = 4 + 3 × 메시지 수`.

| 개수 | 정체 | 언제 붙나 |
|---|---|---|
| **3** | 내 메시지 하나의 포장 — 턴 시작 · 누구 차례(user/assistant) · 턴 끝. `"role": "user", "content":`가 뜻하는 바로 그것 | 메시지 1개마다 |
| **4** | 대화 틀 — 토큰 열 **시작** 표시 + 맨 끝의 **"이제 assistant 차례"** 표시. 후자는 내 JSON에 없습니다 — 응답이 assistant 턴이라 서버가 "여기서부터 네가 써"라고 열어 주는 것 | 대화 전체에 1번 |

```
[대화 시작] [user 차례] 안녕 [내용 끝] [assistant 차례] ← 모델이 이어 쓴다
```

내가 쓴 글자(2개)보다 이 표식(7개)이 더 크고, 한글은 영어보다 글자당 비쌉니다 — 글자 수로 토큰 수를 어림잡으면 안 되는 이유입니다. 그리고 4절에서 보겠지만, 턴이 쌓이면 이 "메시지당 3개"가 매번 전부 다시 들어갑니다."""),
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
API는 매 호출이 처음입니다. 이어서 대화하려면 **앞서 주고받은 메시지를 직접 다시 보냅니다** — 그래서 턴이 늘어날수록 **매번 보내는 요청 자체가 커집니다.**

아래 셀은 2턴짜리 대화를 돌리면서, **매 턴마다 서버로 나가는 요청(JSON) 전체와 돌아오는 응답 전체**를 빠짐없이 찍습니다. (2절에서 봤듯 모델은 이 JSON의 `messages`만 특수 토큰으로 바꿔 받습니다.)"""),
    C('''import json

history = []
sent = []          # 턴마다 (보낸 messages, 응답) 을 남겨 둔다 — 아래에서 토큰 수를 검산한다
turns = [
    "제 이름은 김민수이고, 생산관리팀에서 일합니다.",
    "제 이름과 부서가 뭐였죠?",
]
for i, user_text in enumerate(turns, 1):
    messages = history + [{"role": "user", "content": user_text}]
    request = {"model": llm.MODEL, "max_tokens": 100, "messages": messages}
    print(f"===== {i}번째 턴 =====")
    print("--- 서버로 나가는 요청 (JSON) ---")
    print(json.dumps(request, ensure_ascii=False, indent=2))

    r = llm.call(user_text, history=history, max_tokens=100)
    sent.append((messages, r))

    print("\\n--- 돌아온 응답 전체 ---")
    print(r.raw)
    print()

    history = messages + [{"role": "assistant", "content": r.text}]'''),
    M("""**1턴**은 `messages`에 내가 보낸 말 하나뿐이지만, **2턴**은 1턴의 내 말 + 모델의 답 + 이번 내 말, **세 개**가 들어갑니다. 이력 없이 "제 이름과 부서가 뭐였죠?"만 물으면 모델은 모릅니다 — 매번 **지금까지 오간 것 전부**를 다시 보내야 기억하는 것처럼 보입니다.

### 멀티턴 입력 토큰은 이 식으로 정확히 맞는다
2절에서 메시지 하나의 포장이 **3**, 대화 틀이 **4**였습니다. 턴이 쌓이면:

```
input_tokens = 4 + Σ (3 + 메시지 내용 토큰)     ← 지금까지 쌓인 모든 메시지에 대해
```

아래 셀이 방금 돌린 두 턴의 실제 `usage.input_tokens`와 이 식을 대조합니다. (메시지 하나의 내용 토큰 = 그것만 따로 센 값 − 7)"""),
    C('''content = lambda s: llm.count_tokens(s) - 7      # 메시지 1개 측정값 − 틀 7 = 순수 내용 토큰

for i, (messages, r) in enumerate(sent, 1):
    pieces = [content(m["content"]) for m in messages]
    pred = 4 + sum(3 + p for p in pieces)
    ok = "✓" if pred == r.input_tokens else "✗"
    print(f"{i}턴: 메시지 {len(messages)}개, 내용 토큰 {pieces}")
    print(f"     4 + Σ(3+내용) = {pred}   실제 input_tokens = {r.input_tokens}   {ok}")'''),
    M("""2턴째 내용 토큰 가운데 가장 큰 덩어리는 **1턴에서 모델이 출력한 답**입니다. 1턴엔 `output_tokens`로 냈던 것을 2턴엔 `input_tokens`로 **다시** 냅니다 — 멀티턴에서 비용이 빨리 불어나는 진짜 이유입니다. 메시지당 틀 3개도 매번 전부 다시 들어갑니다.

**요청보다 응답에 훨씬 많은 게 따라옵니다.** 요청은 `model`·`max_tokens`·`messages`, 딱 3가지뿐이었습니다. 방금 받은 마지막 응답(`r`) 하나를 열어서, 거기 뭐가 더 들어있는지 하나씩 짚어 봅니다."""),
    C('''u = r.raw.usage
block = r.raw.content[0]      # 우리가 r.text로 쓰는 게 바로 이 블록의 .text
print("요청에는 모델 이름 · max_tokens · messages, 이 3가지만 넣었습니다.")
print("마지막 턴의 응답(r.raw)에는 그보다 훨씬 많은 게 같이 옵니다:\\n")
print(f"  content                           : (길이 {len(r.raw.content)}인 리스트)")
print(f"      답이 블록 하나가 아니라 **리스트**인 이유 — 도구를 쓰면 블록이 여러 개(생각 ·")
print(f"      도구 호출 · 텍스트)로 늘어납니다. 지금은 글만 와서 블록이 하나뿐입니다.")
print(f"  content[0].type                  : {block.type}")
print(f"      이 블록이 글(text)인지 · 생각(thinking)인지 · 도구 호출(tool_use)인지")
print(f"  content[0].text                  : {block.text[:40]!r}...")
print(f"      우리가 r.text로 꺼내 쓰는 바로 이 값 — content[0].text")
print(f"  content[0].citations              : {block.citations}")
print(f"      문서를 인용하며 답했을 때만 출처가 들어감 (지금은 없음)")
print(f"  role                              : {r.raw.role}")
print(f"      누가 말했는지 — 응답은 항상 'assistant'")
print(f"  type                              : {r.raw.type}")
print(f"      이 객체 자체가 무엇인지 — 'message'")
print(f"  container                         : {r.raw.container}")
print(f"      코드 실행 도구를 쓸 때만 생기는 실행 환경 정보 (안 쓰면 None)")
print(f"  diagnostics                       : {r.raw.diagnostics}")
print(f"      캐시 진단(베타 기능)을 켰을 때만 옴 (안 켜면 None)")
print(f"  stop_details                      : {r.raw.stop_details}")
print(f"      거절(refusal)당했을 때만 이유가 들어감 (지금처럼 정상 답이면 None)")
print(f"  id                                : {r.raw.id}")
print(f"      내가 보낸 적 없음 — 이 응답 하나를 가리키는 고유 번호")
print(f"  stop_reason                       : {r.raw.stop_reason}")
print(f"      내가 물은 적 없음 — 왜 멈췄는지(end_turn · max_tokens · tool_use · ...)")
print(f"  stop_sequence                     : {r.raw.stop_sequence}")
print(f"      어떤 중단 문자열에 걸렸는지 (안 걸리면 None)")
print(f"  model                             : {r.raw.model}")
print(f"      실제로 처리한 모델 — 요청에 쓴 이름과 같아야 정상")
print(f"  usage.input_tokens / output_tokens: {u.input_tokens} / {u.output_tokens}")
print(f"      우리가 Result로 뽑아 쓰는 바로 그 숫자")
print(f"  usage.cache_creation_input_tokens : {u.cache_creation_input_tokens}")
print(f"      프롬프트 캐시에 이번에 새로 쓴 토큰 수 (지금은 캐시를 안 써서 0)")
print(f"  usage.cache_read_input_tokens     : {u.cache_read_input_tokens}")
print(f"      캐시에서 그냥 읽어서 싸게 처리한 토큰 수")
print(f"  usage.service_tier                : {u.service_tier}")
print(f"      이번 요청이 처리된 등급")
print(f"  usage.inference_geo               : {u.inference_geo}")
print(f"      추론이 실제로 일어난 지역")'''),
    M("""요청 쪽은 3가지뿐인데, 응답 쪽은 이렇게 **15가지가 넘는 부가 정보**가 따라옵니다. `content`조차 글 하나가 아니라 **블록 리스트**이고, 우리가 늘 쓰는 `r.text`는 사실 그 리스트의 첫 블록(`content[0]`)의 `.text`일 뿐입니다. `r.text`만 보면 이 중 거의 전부를 놓치는 겁니다 — `llm.py`의 `Result`는 당장 쓸모 있는 몇 개(`text`·`stop_reason`·토큰 수)만 추려 둔 것뿐이고, 나머지는 `r.raw`를 직접 열어야 보입니다."""),
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

# ============================================================== 02
nb02 = [
    M("""# 02 · 프롬프트 설계
**블록 3 · 프롬프트 설계** — 실습 60분

사내 문의 메시지 하나를 받아 **카테고리 · 긴급도 · 요약**으로 분류하는 프롬프트를 만듭니다. 한 줄짜리 지시(v0)에서 시작해, 요소를 **하나씩 더할 때마다 새 프롬프트 파일**(`prompt_1` → `prompt_4`)을 만들고 그때마다 뭐가 달라졌는지 봅니다. `prompt_4.txt`가 최종이고, 오후 블록 4에서 20문항으로 채점받는 **1차**의 재료입니다.

```json
{"카테고리": "IT", "긴급도": "보통", "요약": "비밀번호 재설정 요청"}
```

- 카테고리 — 비품 · 시설 · 인사 · IT · 기타 중 하나
- 긴급도 — 높음 · 보통 · 낮음 중 하나

**통과 기준** — 돌릴 때마다 ① JSON으로 읽히고 ② 카테고리·긴급도가 위 보기 안에 있고 ③ 요약이 비어 있지 않음. `try_prompt()`가 이 세 가지를 세어 "통과 x / n"으로 보여줍니다.

| 순서 | 할 일 | 시간 |
|---|---|---|
| 1 | 문의 고르기 | 5분 |
| 2 | v0 — 한 줄짜리 지시를 돌려 보고 무엇이 부족한지 적는다 | 10분 |
| 3 | prompt_1 → prompt_4 — 요소를 하나씩 더하며 효과를 본다 | 30분 |
| 4 | 근거를 먼저 적게 하고, 그 근거를 어떻게 쓰는지 | 15분 |"""),
    C(SETUP + '''
import json, re
from pathlib import Path
from src.grade import build, parse, schema_errors, CATEGORIES, URGENCY'''),
    M("""## 1. 문의 고르기
이 노트북은 **문의 하나**를 끝까지 씁니다. 프롬프트를 바꿀 때 입력까지 같이 바뀌면 뭐 때문에 결과가 달라졌는지 알 수 없기 때문입니다. 그리고 매번 **같은 문의를 3번** 보냅니다 — 모델 답은 조금씩 흔들리므로(01 노트북 "같은 질문 다섯 번"), 1번으로는 운인지 실력인지 모릅니다. 다른 문의로 시험하는 건 4절(헷갈리는 문의 둘)과 오후 03 노트북(정답 있는 20문항)입니다."""),
    C('''doc = "탕비실 정수기가 고장나서 물이 안 나옵니다. 교체 부탁드립니다."   # ✏️ 내 업무 문의로 바꿔도 됩니다
print(doc)'''),
    M("""## 2. v0 — 한 줄짜리 지시
`prompts/prompt_v0.txt`를 그대로 돌립니다. 결과를 보고 **무엇이 부족한지** 적습니다."""),
    C('''def try_prompt(prompt_text, document, n=1, show=True):
    """프롬프트를 n번 돌려, 통과 기준 세 가지를 모두 만족한 횟수를 센다.
    ① JSON으로 읽히는가  ② 카테고리·긴급도가 보기 안인가  ③ 요약이 비어 있지 않은가
    돌려주는 값: (통과 수, 모델이 낸 (카테고리, 긴급도) 목록)"""
    system, user = build(prompt_text, document)
    if show:
        print(f"=== system에 들어간 것 ===\\n{system}\\n")
        print(f"=== user에 들어간 것 ===\\n{user}\\n")
    c1 = c2 = c3 = ok = 0            # ①파싱  ②보기 안  ③요약 있음  통과=셋 다
    vals = []
    for i in range(n):
        r = llm.call(user, system=system, max_tokens=500)
        try:
            out = parse(r.text)                                                       # ①
            c1 += 1
            in_range = out.get("카테고리") in CATEGORIES and out.get("긴급도") in URGENCY   # ②
            has_sum  = isinstance(out.get("요약"), str) and out["요약"].strip() != ""    # ③
            c2 += in_range; c3 += has_sum
            if in_range and has_sum:
                ok += 1
                note = f"통과 · 카테고리={out['카테고리']} · 긴급도={out['긴급도']}"
            else:
                why = "보기 밖" if not in_range else "요약 없음"
                note = f"JSON은 읽힘 · {why} — 카테고리={out.get('카테고리')!r} 긴급도={out.get('긴급도')!r}"
            vals.append((out.get("카테고리"), out.get("긴급도")))
        except ValueError as e:
            note = f"JSON 실패 — {e}"
            vals.append("파싱 실패")
        if show:
            print(f"--- {i+1}회 · {note} · 출력 {r.output_tokens} 토큰")
            print(r.text.strip()[:600])
    print(f"\\n①JSON {c1}/{n}   ②보기 안 {c2}/{n}   ③요약 있음 {c3}/{n}   →   통과 {ok}/{n} (셋 다 만족)")
    return ok, vals

v0 = llm.load_prompt("prompts/prompt_v0.txt")
print(v0, "\\n========")
ok_v0, vals_v0 = try_prompt(v0, doc, n=3)      # 같은 문의(doc)를 3번 — 이후 모든 비교도 같은 방식'''),
    M("""**v0에서 부족했던 것** (한 줄씩). 위 출력에서 이 세 가지를 확인해 적습니다:
- 형식 — `<json>` 태그 안에 들어 있나, 아니면 코드블록(```)이나 설명이 붙어 있나? →
- 키 이름 — `카테고리`·`긴급도`·`요약` 세 개인가, 아니면 모델이 다른 이름을 지어냈나? →
- 값 — 카테고리가 다섯 보기 중 하나인가, 긴급도가 세 보기 중 하나인가? → """),
    M("""## 3. prompt_1 → prompt_4 — 요소를 하나씩 더하며 효과를 본다
빈 틀에서 출발해 네 요소를 **하나씩** 넣습니다. 요소를 하나 넣을 때마다 **새 파일** `prompts/prompt_N.txt`로 저장하고, **같은 문의(`doc`)를 3번** 돌려 통과 수와 모델이 낸 (카테고리, 긴급도) 값을 봅니다. 그래서 "이 요소를 넣으니 뭐가 바뀌었다"가 **파일 단위로** 남습니다.

| 단계 | 넣는 것 | 파일 |
|---|---|---|
| 1 | `<출력 형식>` — JSON 모양과 "코드블록 없이 `<json>` 안에만" | `prompt_1.txt` |
| 2 | `<역할>` — 누가, 무엇을 위해 | `prompt_2.txt` |
| 3 | `<할 일>` — 카테고리 다섯 개·긴급도 세 개를 각각 뭘 기준으로 고르는지 | `prompt_3.txt` |
| 4 | `<예시>` — 짧은 문의 하나와 정답 JSON | `prompt_4.txt` (최종) |

출력 형식을 **먼저** 넣는 이유: 이게 없으면 파싱이 막혀서 나머지 셋이 뭘 바꾸는지 볼 수 없기 때문입니다. 각 단계의 문장은 ✏️ 표시된 변수에 들어 있으니 **직접 고쳐 가며** 돌려 봐도 됩니다."""),
    C('''TEMPLATE = """=== system ===
<역할>
</역할>

<할 일>
</할 일>

<출력 형식>
</출력 형식>

<예시>
</예시>

=== user ===
<문의>
{document}
</문의>"""

# ✏️ 단계 목록 — 위에서부터 하나씩 더해진다. 문장을 고치고 아래 셀을 다시 실행해 보세요.
STEPS = [
    # (채울 태그,  넣을 문장)
    ("출력 형식", "설명이나 코드블록(```) 없이, 아래처럼 <json></json> 태그 안에만 써라. 그 외에는 아무것도 쓰지 않는다.\\n"
                  '<json>{"카테고리": "…", "긴급도": "…", "요약": "…"}</json>'),

    ("역할",      "너는 총무팀 헬프데스크 담당자다. 직원이 보낸 문의 메시지를 읽고 분류한다."),

    ("할 일",     "<문의>를 아래 기준으로 분류하라.\\n"
                  "- 카테고리: 비품(소모품·책상·의자 등 구매 요청) · 시설(냉난방·조명·주차장·건물 설비) · "
                  "인사(연차·급여·휴가) · IT(컴퓨터·네트워크·계정·장비 고장) · 기타(위 네 가지에 뚜렷이 안 맞을 때)\\n"
                  "- 긴급도: 높음 · 보통 · 낮음\\n"
                  "- 요약: 한 줄"),

    ("예시",      '문의: "에어컨 필터 청소가 필요합니다."\\n'
                  '정답: <json>{"카테고리": "시설", "긴급도": "낮음", "요약": "에어컨 필터 청소 요청"}</json>'),
]'''),
    C('''Path("prompts").mkdir(exist_ok=True)
results = []                      # (단계, 태그, 통과 수, 값들) — 마지막 비교표에 쓴다

print("0) 빈 틀 (아무 요소도 없음)")
_, vals0 = try_prompt(TEMPLATE, doc, n=3, show=False)
print("   모델이 낸 값:", vals0, "\\n")

cur = TEMPLATE
for n, (tag, body) in enumerate(STEPS, 1):
    cur = re.sub(rf"<{tag}>.*?</{tag}>", f"<{tag}>\\n{body}\\n</{tag}>", cur, flags=re.S)   # <tag> 안쪽을 채운다
    path = Path(f"prompts/prompt_{n}.txt")
    path.write_text(cur, encoding="utf-8")                                                   # 단계마다 파일로 저장
    print(f"===== prompt_{n}: <{tag}> 추가 → {path} =====")
    ok, vals = try_prompt(cur, doc, n=3, show=False)
    print("   모델이 낸 값:", vals, "\\n")
    results.append((n, tag, ok, vals))

final = cur                        # 마지막 단계 = 최종 프롬프트 (prompts/prompt_4.txt)'''),
    M("""### 최종 프롬프트(prompt_4)는 v0에서 뭐가 좋아졌나
네 단계의 결과를 한 표로 놓고, 최종 프롬프트 전문을 봅니다."""),
    C('''print(f"{'단계':<6}{'추가한 요소':<10}{'통과':<8}모델이 낸 값")
print("-" * 70)
print(f"{'v0':<6}{'(한 줄 지시)':<10}{str(ok_v0)+' / 3':<8}{vals_v0}   ← 2절 결과")
print(f"{'빈 틀':<6}{'(태그만)':<10}{'0 / 3':<8}{vals0}")
for n, tag, ok, vals in results:
    print(f"{'prompt_'+str(n):<6}{'<'+tag+'>':<10}{str(ok)+' / 3':<8}{vals}")

print("\\n===== 최종 프롬프트 prompts/prompt_4.txt =====")
print(final)'''),
    M("""읽는 법 — 단계마다 **다른 것**이 고쳐집니다:
- **빈 틀 → `prompt_1` (출력 형식):** 파싱 실패가 사라집니다. 모델이 ` ``` ` 대신 `<json>` 안에 씁니다. 그런데 통과는 여전히 0 — 값이 `'시설관리'`, `'중'`처럼 **보기에 없는 말**이기 때문입니다. 형식은 잡혔는데 **어휘**가 안 잡힌 상태입니다.
- **`prompt_2` (역할):** 거의 아무것도 안 바뀝니다. 역할 한 줄은 이 과제에서 효과가 작습니다 — 그걸 아는 것도 결과입니다.
- **`prompt_3` (할 일 — 보기 다섯 개·세 개를 정의):** 값이 `'시설'`, `'보통'`으로 **보기 안에 들어오면서 3/3 통과.** 통과를 결정한 건 이 단계입니다. 모델은 보기를 **말해 줘야** 그 안에서 고릅니다.
- **`prompt_4` (예시):** 통과는 그대로, 긴급도 값이 움직입니다(보통 ↔ 높음). 문의 한 건으로는 그 움직임이 **맞는 방향인지 알 수 없습니다.**

그래서 **최종(prompt_4)이 v0보다 좋아진 점**은 둘로 나뉩니다. 확실한 것: 코드가 읽을 수 있고(1단계), 정해진 보기 안에서만 답한다(3단계). 아직 모르는 것: 카테고리·긴급도를 **맞게** 고르는가 — 이건 정답이 있는 20문항으로 재야 하고, 그게 오후 03 노트북입니다. 거기서 효과가 없는 요소(예: 역할)는 빼도 됩니다.

> 위 숫자는 돌릴 때마다 조금씩 다를 수 있습니다. 바뀌지 않는 건 **어느 단계에서 파싱이 되고, 어느 단계에서 보기 안으로 들어오는가**입니다.

### 최종 프롬프트 확인
아래 셀은 `prompts/prompt_4.txt`를 **파일에서 다시 읽어** 빈 자리나 `TODO`가 남지 않았는지 확인하고 한 번 돌립니다. 위 단계의 ✏️ 문장을 고쳤다면 그 셀을 다시 실행한 뒤 이 셀을 실행합니다."""),
    C('''FINAL_PATH = "prompts/prompt_4.txt"      # ✏️ 풀이본과 비교하려면 "solutions/prompts/prompt_4.txt"
v1 = llm.load_prompt(FINAL_PATH)

empty = [t for t in ["역할", "할 일", "출력 형식", "예시"] if re.search(rf"<{t}>\\s*</{t}>", v1)]
if "TODO" in v1 or empty:
    print("=" * 70)
    print("⚠️  최종 프롬프트가 아직 비어 있는 곳이 있습니다:", empty or "TODO 남음")
    print("    3절의 해당 단계 셀을 채우고 다시 실행하세요.")
    print("=" * 70, "\\n")

try_prompt(v1, doc, n=3)'''),
    M("""## 4. 근거를 먼저 적게 한다 — 그리고 그 근거를 어떻게 쓰나
최종 프롬프트에 규칙 하나를 더합니다: **`<json>`을 쓰기 전에 `<근거>`에 왜 그렇게 분류했는지 한 문장을 적어라.** 출력 형식은 그대로입니다 — `parse()`는 `<json>` 안만 읽으므로 `<근거>`가 앞에 붙어도 코드는 안 깨집니다.

근거는 **코드가 아니라 사람이 쓰는 것**입니다. 쉬운 문의 하나(위의 `doc`)와, 사람도 헷갈리는 문의 둘을 `data/tests.jsonl`에서 가져와 돌려 봅니다 — 12번(차분한 말투지만 안전 문제 → 시설·높음)과 11번(전자기기지만 구매 요청 → 비품·낮음).

여기서 **"정답"은 `tests.jsonl`에 적어 둔 판단 기준**이지 객관적 사실이 아닙니다. 다른 회사라면 모니터 추가 요청을 IT 소관으로 둘 수도 있습니다. 그래서 모델이 정답과 다르게 답했을 때 할 일은 둘 중 하나입니다 — 근거를 읽고 **프롬프트의 기준을 고치거나**, 그 근거가 더 타당하면 **`tests.jsonl`의 정답을 고치거나.** 어느 쪽이든 근거가 있어야 결정할 수 있습니다."""),
    C('''EVIDENCE = ("\\n\\n<근거 규칙>\\n<json>을 쓰기 전에 <근거>에 이 문의를 그렇게 분류한 이유를 "
            "한 문장으로 적어라.\\n</근거 규칙>")

from src.grade import load_tests
T = {t["id"]: t for t in load_tests()}                         # 정답은 data/tests.jsonl 에 정의된 것을 그대로 쓴다
cases = [(doc, None)] + [
    (T[i]["input"], (T[i]["check"]["category"], T[i]["check"]["urgency"]))
    for i in (12, 11)                                         # 12: 차분한 말투의 안전 문제 · 11: 전자기기지만 구매 요청
]
for text, answer in cases:
    system, user = build(final, text)
    r = llm.call(user, system=(system or "") + EVIDENCE, max_tokens=400)
    m = re.search(r"<근거>(.*?)</근거>", r.text, re.S)
    try:
        out = parse(r.text); got = (out.get("카테고리"), out.get("긴급도"))
    except ValueError as e:
        out, got = None, f"파싱 실패: {e}"
    print("문의 :", text)
    print("근거 :", m.group(1).strip() if m else "(없음)")
    print("분류 :", got, "" if answer is None else f"   정답 {answer}  {'✓' if got == answer else '✗'}")
    print()'''),
    M("""근거를 이렇게 씁니다:

1. **틀린 답의 원인을 진단한다.** 분류가 ✗인데 근거에 "말투가 차분해서 급하지 않다고 봤다"거나 "모니터는 IT 장비라서"라고 적혀 있으면, 모델이 **무엇을 기준으로** 틀렸는지가 보입니다. 그러면 고칠 곳이 정해집니다 — `<할 일>`에 "말투가 아니라 안전·업무 중단 여부로 판단하라", "전자기기라도 구매 요청이면 비품"을 추가하는 식으로. 이것이 오후 03에서 v1 → v2 → v3로 고쳐 가는 방법입니다.
2. **맞았어도 이유가 엉뚱하면 믿지 않는다.** 분류는 ✓인데 근거가 문의와 상관없는 소리면 운으로 맞은 것이고, 다른 문의에서는 틀립니다.
3. **코드는 근거를 버립니다.** `parse()`는 `<json>`만 읽습니다. 근거는 사람이 디버깅할 때만 열어 보는 것이라, 출력 형식은 그대로 유지됩니다.

최종 프롬프트에 이 규칙을 넣을지는 선택입니다 — 근거를 쓰게 하면 출력 토큰(비용)이 늘고, 그 대신 틀렸을 때 왜 틀렸는지 알 수 있습니다."""),
]

# ============================================================== 03
nb03 = [
    M("""# 03 · 평가
**블록 4 · 평가** — 실습 50분

고쳤다는 느낌은 증거가 아닙니다. **같은 문항, 같은 기준, 같은 방법으로** 다시 재야 고친 것입니다.

02에서 만든 최종 프롬프트 **`prompt_4`**를 정답이 있는 20문항에 돌려 점수를 내고(1차), 가장 많이 틀리는 유형 하나를 고쳐 **`prompt_5`**로 저장해 다시 재고(2차), 한 번 더 고쳐 **`prompt_6`**(2차 반복), 마지막으로 같은 `prompt_6`를 모델만 바꿔 잽니다(3차). 번호는 02에서 이어집니다.

| 순서 | 할 일 | 시간 |
|---|---|---|
| 1 | 20문항 — 구성표와 통과 조건을 읽는다 | 10분 |
| 2 | 1차 — `prompt_4` 채점, 실패 문항을 직접 연다 | 10분 |
| 3 | 2차 — 한 유형씩 고쳐 `prompt_5` · `prompt_6`, 같은 20문항으로 다시 채점 | 20분 |
| 4 | 3차 — `prompt_6`를 모델 셋에 돌린다 | 10분 |"""),
    C(SETUP + '''
import json
from pathlib import Path
from collections import Counter
from src.grade import load_tests, run, check, summarize, save, print_table, print_fails'''),
    M("""## 1. 고정 테스트 20문항
`data/tests.jsonl` — 한 줄에 한 문항. **프롬프트를 고치기 전에 만들고, 고치는 동안 바꾸지 않습니다** (고치는 중간에 문항이 바뀌면 전후 비교가 안 됩니다).

20문항은 4종류로 나뉘어 있고, 종류마다 보려는 게 다릅니다.

| 구성 | 문항 수 | 이 실습의 문항 | 뭘 보려고 넣었나 |
|---|---|---|---|
| 평범한 입력 | 10 | 1–10 | 가장 흔한 문의에서 기본으로 되는지 |
| 경계에 있는 입력 | 5 | 11 구매 요청 · 12 차분한 어투의 위험 신호 · 13 장비 고장 · 14 격한 어투 · 15 휴가 중 급여 | 말투·단어에 속지 않고 내용으로 판단하는지 |
| 어느 카테고리에도 안 맞는 입력 | 3 | 16 · 17 · 18 | 억지로 짜맞추지 않고 "기타"로 분류하는지 |
| 실제로 틀렸던 입력 | 2 | 19 "노트북"이라는 단어 · 20 영문 혼용 | 아래 설명 |

**"실제로 틀렸던 입력"이 뭔지:** 앞의 세 종류는 미리 설계해 둔 문제지만, 이 둘은 **"내 프롬프트를 돌려봤더니 실제로 틀렸던 문의"**를 넣는 자리입니다. 지금은 강사가 미리 겪은 흔한 실패 예시가 채워져 있을 뿐입니다.

**내 것으로 바꾸는 법:**
1. 02의 4절(근거)이나 아래 1차 채점에서 `prompt_4`가 실제로 틀린 문의를 적어둔다
2. `tests.jsonl`의 19·20번 줄에서 `input`과 `check`를 그 문의에 맞게 고친다
3. **그다음부터는 문항을 바꾸지 않는다** — 고치는 동안 문항이 바뀌면 비교할 수 없다

여기 적힌 **정답(`check`)은 설계자가 정한 판단 기준**이지 객관적 사실이 아닙니다(02의 4절). 모델이 다르게 답했을 때 프롬프트를 고칠지 정답을 고칠지는 근거를 보고 사람이 정합니다.

| check 필드 | 뜻 |
|---|---|
| `category` | 이 값과 같은 카테고리여야 통과 |
| `urgency` | 이 값과 같은 긴급도여야 통과 |
| `has` | 요약 어딘가에 이 말이 있어야 통과 (없으면 생략) |"""),
    C('''tests = load_tests()
print("종류별 문항 수:", dict(Counter(t["group"] for t in tests)), "\\n")

# 종류마다 첫 문항 하나씩 — 문의 본문과 통과 조건(check)이 어떻게 적혀 있는지 본다
for group in ["평범", "경계", "기타", "틀렸던"]:
    t = next(t for t in tests if t["group"] == group)
    print(f"[{group}] #{t['id']:>2}  {t['input']}")
    print(f"        check = {t['check']}\\n")'''),
    M("""## 2. check — 판정 규칙
`check(출력, 통과 조건)` → `(통과 여부, 실패 유형, 설명)`. 모델 없이 **가짜 출력**으로 먼저 돌려, 판정기가 네 유형을 어떻게 가르는지 봅니다.
판정 순서: **형식 위반 → 지어냄 → 지시 일부 누락 → 사실 오류** — 앞에서 걸리면 거기서 멈춥니다."""),
    C('''# 채점기를 먼저 시험한다 — 모델 없이, 일부러 틀리게 만든 가짜 답으로.
# (라벨, 어느 문항의 정답 조건으로 채점할지, 가짜 답, 나와야 할 판정)
spec1  = tests[0]["check"]     # 1번:  {"category": "IT", "urgency": "보통", "has": "비밀번호"}
spec16 = tests[15]["check"]    # 16번: {"category": "기타", "urgency": "낮음"}  ← 정답이 "기타"

fakes = [
    ("정상",            spec1,  \'{"카테고리": "IT", "긴급도": "보통", "요약": "비밀번호 재설정 요청"}\',               None),
    ("코드 블록으로 감쌈", spec1,  \'```json\\n{"카테고리": "IT", "긴급도": "보통", "요약": "비밀번호 재설정 요청"}\\n```\', "형식 위반"),
    ("보기에 없는 카테고리", spec1, \'{"카테고리": "기술지원", "긴급도": "보통", "요약": "비밀번호 재설정 요청"}\',           "형식 위반"),
    ("요약에 필수 단어 없음", spec1, \'{"카테고리": "IT", "긴급도": "보통", "요약": "로그인 문제 접수"}\',                  "지시 일부 누락"),
    ("카테고리가 정답과 다름", spec1, \'{"카테고리": "비품", "긴급도": "보통", "요약": "비밀번호 재설정 요청"}\',             "사실 오류"),
    ("기타여야 하는데 지어냄", spec16, \'{"카테고리": "인사", "긴급도": "낮음", "요약": "워크숍 일정 문의"}\',               "지어냄"),
]

print(f"{\'가짜 답\':<14}{\'기대 판정\':<10}{\'실제 판정\':<10} 설명")
print("-" * 70)
for label, spec, text, expected in fakes:
    ok, kind, why = check(text, spec)
    mark = "✓" if kind == expected else "✗"
    print(f"{label:<14}{str(expected or \'통과\'):<10}{str(kind or \'통과\'):<10} {mark}  {why}")'''),
    M("""## 3. 1차 · `prompt_4` 채점
02에서 만든 최종 프롬프트 `prompts/prompt_4.txt`를 20문항에 돌립니다. 02를 아직 안 돌려 파일이 없으면 아래 셀이 **풀이본으로 대신 돌리고 그렇다고 알려 줍니다** — 흐름을 먼저 보고, 02를 돌린 뒤 다시 오면 됩니다."""),
    C('''P4 = Path("prompts/prompt_4.txt")
if not P4.exists():
    print("※ prompts/prompt_4.txt 가 없습니다 (02 노트북을 아직 안 돌림). 풀이본 solutions/prompts/prompt_4.txt 로 대신 돌립니다.\\n")
    P4 = Path("solutions/prompts/prompt_4.txt")

passed, fails, rows = run(str(P4), detail=True)
s1 = summarize(rows, llm.MODEL)
save(str(P4), llm.MODEL, rows, s1, note="1차 · prompt_4")
print(f"통과 {passed} / {len(rows)}")
print(Counter(kind for _, kind in fails))
print_fails(rows)'''),
    M("""### 실패 문항을 직접 연다
통과 수만 보면 **새로 생긴 실패**를 놓칩니다. 실패 문항의 출력을 열어 유형이 맞는지 사람이 확인합니다.
(사실 오류는 코드가 카테고리·긴급도 문자열만 비교해 판정합니다 — 애매한 경우엔 사람이 다시 봅니다.)"""),
    C('''FAIL_ID = fails[0][0] if fails else 1      # ✏️ 보고 싶은 문항 번호
row = next(r for r in rows if r["id"] == FAIL_ID)
print(f"#{row[\'id\']} [{row[\'group\']}] {row[\'kind\']} — {row[\'why\']}\\n")
print(row["text"][:1200])'''),
    M("""## 4. 2차 · 한 유형씩 고쳐 `prompt_5`
1. 위 실패 중 **가장 많은 유형 하나**를 고른다
2. `prompt_4.txt`를 복사해 `prompts/prompt_5.txt`로 만들고, **그 유형에 맞는 것 하나만** 고친다 (아래 표)
3. 같은 20문항으로 `prompt_4`와 `prompt_5`를 나란히 비교한다 — 통과 수만이 아니라 **어느 문항이 새로 통과하고 어느 문항이 새로 실패했는지**
4. 나빠졌으면 되돌린다

| 유형 | 고치는 곳 |
|---|---|
| 형식 위반 | 출력 형식 지시 · 예시 · `<json>` 태그로 감싸게 하기 |
| 지시 일부 누락 | 요약에 꼭 들어가야 할 말을 지시에 명시 |
| 지어냄 | "기타" 기준을 분명히 — 뚜렷이 안 맞으면 억지로 짜맞추지 말라고 지시 |
| 사실 오류 | 카테고리 · 긴급도 판단 기준을 더 구체적으로 — 02의 4절에서 본 **근거**가 어디를 고칠지 알려 준다 |

아래 셀은 기본값으로 **풀이본 `prompt_5`**(긴급도를 말투가 아니라 정해진 기준으로 판단하게 함)를 돌립니다. 내 `prompt_5`를 만들었으면 경로와 NOTE를 바꾸세요."""),
    C('''P5 = "solutions/prompts/prompt_5.txt"      # ✏️ 내 것: "prompts/prompt_5.txt"
NOTE = "긴급도: 말투가 아니라 정해진 기준으로"   # ✏️ 무엇을 바꿨는지 한 줄 — 결과표에 남는다

p2, f2, rows2 = run(P5, detail=True)
s2 = summarize(rows2, llm.MODEL)
save(P5, llm.MODEL, rows2, s2, note=NOTE)
print_table([("prompt_4", llm.MODEL, s1), ("prompt_5", llm.MODEL, s2)])

before = {r["id"] for r in rows  if r["ok"]}
after  = {r["id"] for r in rows2 if r["ok"]}
print("\\n새로 통과:", sorted(after - before), "  새로 실패:", sorted(before - after))'''),
    M("""### 2차를 한 번 더 → `prompt_6`
`prompt_5`의 실패 중 가장 많은 유형 하나를 골라 `prompt_6`을 만듭니다. 풀이본 `prompt_6`은 **카테고리 판단 기준(전자기기라도 구매 요청이면 비품, 고장 신고만 IT)**을 더 분명히 했습니다 — 02의 4절에서 모니터 건이 "IT 장비라서"라는 근거로 틀렸던 바로 그 지점입니다."""),
    C('''P6 = "solutions/prompts/prompt_6.txt"      # ✏️ 내 것: "prompts/prompt_6.txt"
NOTE = "카테고리: 구매 요청과 고장 신고를 구분하는 기준 추가"

p3, f3, rows3 = run(P6, detail=True)
s3 = summarize(rows3, llm.MODEL)
save(P6, llm.MODEL, rows3, s3, note=NOTE)
print_table([("prompt_4", llm.MODEL, s1), ("prompt_5", llm.MODEL, s2), ("prompt_6", llm.MODEL, s3)])
print_fails(rows3)'''),
    M("""**발표 — 한 문장으로**
> "___ 유형을 줄이려고 ___를 바꿨더니 통과가 __ → __ 가 됐고, 대신 ___ 가 생겼다(또는 생기지 않았다)."
"""),
    M("""## 5. 3차 · 모델을 바꿔 잰다
같은 `prompt_6`, 같은 20문항 — **모델만** 바꿉니다. 모델 이름은 `common/llm.py`의 `MODELS`에서 강의 당일 쓸 수 있는 것으로 확인합니다.

고르는 기준 — 통과 기준을 넘는 모델 중에서 가장 싸고 빠른 것. **가격은 통과 수를 본 다음에 봅니다.**"""),
    C('''compare, fails_by_model = [], {}
for m in llm.MODELS:
    pm, fm, rm = run(P6, model=m, detail=True)
    sm = summarize(rm, m)
    save(P6, m, rm, sm, note="3차 · 모델 비교")
    compare.append(("prompt_6", m, sm))
    fails_by_model[m] = {r["id"]: r["why"] for r in rm if not r["ok"]}
print_table(compare)'''),
    M("""### 모델을 올려도 남는 실패는 어떤 것인가
비싼 모델로 바꿔도 통과 수가 거의 안 움직인다면, 남은 실패는 모델 능력 문제가 아닐 가능성이 큽니다. 모델별로 **어느 문항**에서 틀렸는지 모아 보면 갈립니다."""),
    C('''by_id = {}
for m, f in fails_by_model.items():
    for i, why in f.items():
        by_id.setdefault(i, []).append((m.replace("claude-", ""), why))

common = [i for i, lst in by_id.items() if len(lst) == len(llm.MODELS)]
print("세 모델 모두 틀린 문항:", sorted(common) or "없음")
print()
for i in sorted(by_id):
    t = next(t for t in tests if t["id"] == i)
    print(f"#{i:>2} [{t[\'group\']}] {t[\'input\']}")
    print(f"     정답 {t[\'check\'][\'category\']} · {t[\'check\'][\'urgency\']}")
    for m, why in by_id[i]:
        print(f"     {m:<22} {why}")
    print()'''),
    M("""읽는 법:
- **세 모델이 같은 문항에서 틀린다** → 그 문항은 프롬프트 기준이 애매하거나 `tests.jsonl`의 정답이 이상한 것입니다. 모델을 바꿔 봐야 소용없고, 기준을 고쳐야 합니다.
- **모델마다 다른 문항에서, 긴급도만 한 단계씩 어긋난다** → 긴급도 경계(낮음↔보통, 보통↔높음)가 `prompt_6`의 기준에도 정답에도 느슨하게 남아 있다는 뜻입니다. 사람도 "에어컨 소리는 보통인가 낮음인가"에서 갈립니다. 이런 문항은 기준을 더 구체적으로 적거나, 경계 사례로 인정하고 넘어갑니다.
- 표에서 Opus·Sonnet의 **평균 초와 1건 비용이 몇 배 큰 것**도 보세요. 최신 모델은 답하기 전에 생각(thinking)을 하고 그 토큰도 과금됩니다 — 그런데 통과 수는 Haiku와 같습니다. 이 과제에선 그 비용이 아무것도 사 주지 않은 겁니다.
- **어느 쪽이든 결론은 같습니다** — 모델 교체는 **마지막** 수단입니다. 기준(프롬프트·정답)으로 풀 수 있는 실패를 비싼 모델로 덮으려 하면 돈만 들고 그대로 남습니다. 그래서 3차에서 고르는 기준이 "통과 기준을 넘는 것 중 **가장 싸고 빠른 것**"인 겁니다."""),
    M("""## 6. 결과표
`results/scoreboard.csv`에 실행할 때마다 한 줄씩 쌓입니다. 엑셀로 열어도 됩니다. "바꾼 것" 칸에 NOTE가 들어가므로, 나중에 봐도 **어느 줄이 어떤 수정의 결과인지** 알 수 있습니다."""),
    C('''import csv
with open("results/scoreboard.csv", encoding="utf-8-sig") as f:
    for row in list(csv.reader(f))[-8:]:
        print(" | ".join(row[:11]))'''),
    M("""## 내일 가지고 올 것
- `prompt_6.txt` · `tests.jsonl` · `grade.py` · 결과표(`results/scoreboard.csv`)
- 생각해 올 것 — 오늘 남은 실패 중, **"모델이 몰라서"** 틀린 것은 무엇인가 (→ Day 2 컨텍스트)"""),
]

if __name__ == "__main__":
    NB.mkdir(exist_ok=True)
    for name, cells in [("01_api_basics", nb01), ("02_prompt_design", nb02),
                        ("03_evaluation", nb03)]:
        nbf.write(nb(cells), NB / f"{name}.ipynb")
        print("작성:", f"notebooks/{name}.ipynb", len(cells), "셀")

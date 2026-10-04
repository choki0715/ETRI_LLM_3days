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

여기서 만드는 v1이 오후 블록 4에서 20문항으로 채점받는 **1차**의 재료입니다. 지금은 그 전에 "쓸 만한 프롬프트 하나"를 준비하는 단계입니다.

사내 문의 메시지 하나를 받아 **카테고리 · 긴급도 · 요약**으로 분류하는 프롬프트를 씁니다.

```json
{"카테고리": "IT", "긴급도": "보통", "요약": "비밀번호 재설정 요청"}
```

- 카테고리 — 비품 · 시설 · 인사 · IT · 기타 중 하나
- 긴급도 — 높음 · 보통 · 낮음 중 하나

**통과 기준** — 10번 돌려 10번 모두 ① JSON으로 읽히고 ② 카테고리·긴급도가 위 보기 안에 있고 ③ 요약이 비어 있지 않음. 아래 `try_prompt()`가 이 세 가지를 그대로 세어 "통과 x / n"으로 보여줍니다.

| 순서 | 할 일 | 시간 |
|---|---|---|
| 1 | 문의 고르기 — 짧은 문의 하나 준비 | 5분 |
| 2 | v0 — 한 줄짜리 지시로 먼저 돌려 보고 무엇이 부족한지 적는다 | 10분 |
| 3 | v1 — 프롬프트 파일을 한 줄씩 채우고, 채울 때마다 돌려 본다 | 30분 |
| 4 | 짝 점검 체크리스트 | 15분 |"""),
    C(SETUP + '''
import json
from src.grade import build, parse, schema_errors'''),
    M("## 1. 문의 고르기"),
    C('''doc = "탕비실 정수기가 고장나서 물이 안 나옵니다. 교체 부탁드립니다."   # ✏️ 내 업무 문의로 바꿔도 됩니다
print(doc)'''),
    M("""## 2. v0 — 한 줄짜리 지시
`prompts/prompt_v0.txt`를 그대로 돌립니다. 결과를 보고 **무엇이 부족한지** 적습니다."""),
    C('''def try_prompt(prompt_text, document, n=1, show=True):
    """프롬프트를 n번 돌려, 도입부의 통과 기준 세 가지를 모두 만족한 횟수를 센다.
    ① JSON으로 읽히는가  ② 카테고리·긴급도가 보기 안인가  ③ 요약이 비어 있지 않은가"""
    system, user = build(prompt_text, document)
    if show:
        print(f"=== system에 들어간 것 ===\\n{system}\\n")
        print(f"=== user에 들어간 것 ===\\n{user}\\n")
    ok = 0
    for i in range(n):
        r = llm.call(user, system=system, max_tokens=500)
        try:
            out = parse(r.text)                                   # ①
            errs = schema_errors(out)                             # ② ③
            if errs:
                note = "JSON은 읽힘 · 보기 밖 — " + errs[0]
            else:
                ok += 1
                note = f"통과 · 카테고리={out['카테고리']} · 긴급도={out['긴급도']}"
        except ValueError as e:
            note = f"JSON 실패 — {e}"
        if show:
            print(f"--- {i+1}회 · {note} · 출력 {r.output_tokens} 토큰")
            print(r.text.strip()[:600])
    print(f"\\n통과 {ok} / {n}   (①JSON ②보기 안 ③요약 있음 — 셋 다 만족한 횟수)")
    return ok

v0 = llm.load_prompt("prompts/prompt_v0.txt")
print(v0, "\\n========")
try_prompt(v0, doc)'''),
    M("""**v0에서 부족했던 것** (한 줄씩). 위 출력에서 이 세 가지를 확인해 적습니다:
- 형식 — `<json>` 태그 안에 들어 있나, 아니면 코드블록(```)이나 설명이 붙어 있나? →
- 키 이름 — `카테고리`·`긴급도`·`요약` 세 개인가, 아니면 모델이 다른 이름을 지어냈나? →
- 값 — 카테고리가 다섯 보기 중 하나인가, 긴급도가 세 보기 중 하나인가? → """),
    M("""## 3. v1 — 아래 표를 한 줄씩 채우고 바로 돌려본다
`prompts/prompt_v1.txt`를 엽니다. 파일 안에 **`TODO:`로 시작하는 줄이 네 개** 있습니다. `TODO`는 "여기는 네가 써야 할 자리"라는 표시일 뿐이고, 할 일은 **그 줄을 통째로 지우고 그 자리에 내 문장을 쓰는 것**입니다. 다 채우면 파일에 `TODO`라는 글자가 하나도 남지 않아야 합니다 — 아래 셀이 그걸로 "아직 안 채웠다"를 판단합니다.

예를 들어 `<역할>`은 이렇게 바뀝니다:
```
전:  <역할>
     TODO: 누가, 무엇을 위해 이 일을 하는지 한두 줄 (예: 총무팀 헬프데스크 담당자)
     </역할>

후:  <역할>
     너는 총무팀 헬프데스크 담당자다. 직원이 보낸 문의를 읽고 분류한다.
     </역할>
```

표의 항목을 **위에서부터 한 줄씩** 채우고, 한 줄 채울 때마다 바로 아래 셀을 다시 실행해 뭐가 달라지는지 봅니다. 다 채운 뒤에 한꺼번에 실행하지 않습니다 — 그러면 뭐가 효과 있었는지 알 수 없습니다.

| 채울 내용 | 넣는 곳 |
|---|---|
| 역할을 구체적으로 — 누가, 무엇을 위해 | `<역할>` |
| 할 일을 구체적으로 — 카테고리 다섯 개 · 긴급도 세 개를 각각 뭘 기준으로 고르는지 | `<할 일>` |
| "~하지 마" 대신 "~해라"로 쓰기 | `<역할>` `<할 일>` 전체 |
| 예시 하나 — 짧은 문의와 정답 JSON | `<예시>` |
| 원하는 JSON 모양을 그대로 보여주기 | `<출력 형식>` |

파일 맨 위 `=== system ===` 아래는 system으로, `=== user ===` 아래는 user로 보냅니다. `{document}` 자리에 문의가 들어갑니다.

### 먼저 전체 과정을 한 번 구경한다 — TODO를 하나씩 채우면 뭐가 바뀌나
내 파일을 고치기 전에, 아래 셀이 **TODO 템플릿에서 출발해 TODO 네 개를 하나씩 채우면서 매번 3번씩 돌려** 봅니다. 파일은 건드리지 않고 메모리에서만 채웁니다. 어느 TODO를 채웠을 때 파싱이 통과하는지 보세요."""),
    C('''import re

def fill(text, tag, body):
    """<tag>…</tag> 안쪽을 body로 바꾼다 (TODO 줄을 지우고 내 문장을 쓰는 것과 같다)"""
    return re.sub(rf"<{tag}>.*?</{tag}>", f"<{tag}>\\n{body}\\n</{tag}>", text, flags=re.S)

steps = [
    ("역할",      "너는 총무팀 헬프데스크 담당자다. 직원이 보낸 문의 메시지를 읽고 분류한다."),
    ("할 일",     "<문의>를 아래 기준으로 분류하라.\\n"
                  "- 카테고리: 비품(소모품·책상·의자 등 구매 요청) · 시설(냉난방·조명·주차장·건물 설비) · "
                  "인사(연차·급여·휴가) · IT(컴퓨터·네트워크·계정·장비 고장) · 기타(위 네 가지에 뚜렷이 안 맞을 때)\\n"
                  "- 긴급도: 높음 · 보통 · 낮음\\n- 요약: 한 줄"),
    ("예시",      "문의: \\"에어컨 필터 청소가 필요합니다.\\"\\n"
                  "정답: <json>{\\"카테고리\\": \\"시설\\", \\"긴급도\\": \\"낮음\\", \\"요약\\": \\"에어컨 필터 청소 요청\\"}</json>"),
    ("출력 형식", "설명이나 코드블록(```) 없이, 아래처럼 <json></json> 태그 안에만 써라. 그 외에는 아무것도 쓰지 않는다.\\n"
                  "<json>{\\"카테고리\\": \\"…\\", \\"긴급도\\": \\"…\\", \\"요약\\": \\"…\\"}</json>"),
]

cur = llm.load_prompt("prompts/prompt_v1.txt")      # TODO 템플릿 (파일은 안 바꾼다)
print("0) TODO 템플릿 그대로"); try_prompt(cur, doc, n=3, show=False); print()
for i, (tag, body) in enumerate(steps, 1):
    cur = fill(cur, tag, body)
    print(f"{i}) <{tag}> 채움  (남은 TODO {cur.count('TODO')}개)")
    try_prompt(cur, doc, n=3, show=False)
    print()'''),
    M("""`<역할>`·`<할 일>`·`<예시>`를 채워도 파싱은 계속 0입니다. **`<출력 형식>`을 채운 순간 통과**합니다 — "`<json></json>` 안에만, 코드블록 없이"라는 지시가 파싱을 결정하기 때문입니다. 나머지 셋은 파싱이 아니라 **답의 내용**(카테고리·긴급도를 맞게 고르는지)을 좌우하고, 그 차이는 오후 채점에서 드러납니다.

이제 **내 파일**로 같은 일을 합니다."""),
    C('''V1_PATH = "prompts/prompt_v1.txt"      # ✏️ 내 것 대신 풀이본을 보려면 "solutions/prompts/prompt_v1.txt"
v1 = llm.load_prompt(V1_PATH)           # 파일을 고친 뒤 이 셀을 다시 실행

if "TODO" in v1:
    print("=" * 70)
    print("⚠️  prompt_v1.txt 에 'TODO:' 로 시작하는 줄이 아직 남아 있습니다.")
    print("    그 줄은 자리 표시입니다 — 줄을 지우고 그 자리에 내 문장을 쓰세요 (3절의 전/후 예시 참고).")
    print("    채우기 전까지는 이 셀부터 아래 셀 전부가 '실패'로 나옵니다 — 그게 정상입니다.")
    print("=" * 70, "\\n")

try_prompt(v1, doc)'''),
    M("""> 막히면 `solutions/prompts/prompt_v1.txt`를 열어 봅니다. 그대로 베끼기보다, 내 v1과 **무엇이 다른지** 비교합니다."""),
    M("""## 4. 짝 점검 체크리스트
v1을 짝과 바꿔 보고, 아래 다섯 가지를 하나씩 확인합니다. 하나라도 "아니오"면 3절로 돌아가 고칩니다.

- [ ] **형식** — 10번 돌려 10번 다 `json.loads`로 읽히는가? (코드블록·설명 없이)
- [ ] **보기 안** — 카테고리가 항상 다섯 보기(비품·시설·인사·IT·기타) 중 하나인가?
- [ ] **보기 안** — 긴급도가 항상 세 보기(높음·보통·낮음) 중 하나인가?
- [ ] **요약 있음** — 요약이 비어 있지 않은가?
- [ ] **구조** — `=== system ===`에는 역할·규칙·형식만, `=== user ===`에는 문의만 들어가 있는가?

아래 셀이 위 **네 개를 자동으로** 셉니다(`try_prompt`가 세는 통과 기준이 바로 이것). 다섯 번째(구조)만 파일을 열어 눈으로 봅니다."""),
    C('''ok = try_prompt(v1, doc, n=10, show=False)
print("통과" if ok == 10 else "아직 — 형식 지시 · 예시를 다시 봅니다")'''),
    M("""## 5. 생각할 자리를 준다
**방금 만든 v1에, 한 가지를 더합니다.** 바로 분류하게 하지 말고, **판단 근거를 먼저 한 줄 적게** 합니다. 출력 형식은 v1 것을 그대로 쓰고, 규칙만 하나 추가합니다."""),
    C('''import re

system, user = build(v1, doc)      # v1의 <출력 형식>을 그대로 쓴다
EVIDENCE = ("\\n\\n<근거 규칙>\\n<json>을 쓰기 전에 <근거>에 이 문의를 그렇게 분류한 이유를 "
            "한 문장으로 적어라.\\n</근거 규칙>")

r = llm.call(user, system=(system or "") + EVIDENCE, max_tokens=500)
print(r.text.strip())

m = re.search(r"<근거>(.*?)</근거>", r.text, re.S)
print("\\n→ 코드가 디버깅용으로 꺼낸 <근거>:", (m.group(1).strip() if m else "(없음)"))
try:
    print("→ parse() 결과(<json>만 읽음):", parse(r.text))
except ValueError as e:
    print("→ parse() 실패:", e)
    print("   v1의 <출력 형식>에 '<json></json> 안에만 써라'가 들어 있는지 확인하세요 — 3절로 돌아갑니다.")'''),
    M("""## 6. 한 덩어리 일을 세 단계로 나눈다 — 분류하기(모델) → 검사하기(코드) → 답장 쓰기(모델)
이 절은 프롬프트를 잘 쓰는 기술이 아니라 **작업을 어떻게 나눌지**에 대한 얘기입니다. 프롬프트로 해결하려 하지 말고 코드로 해야 하는 부분이 있다는 것을 봅니다.

"문의를 분류하고, 분류가 정해진 보기 안에 있는지 확인하고, 직원에게 보낼 접수 답장을 써 줘"를 한 번에 시킬 수도 있습니다. 그러면 모델이 보기에 없는 카테고리를 만들어내도 그냥 넘어갈 수 있습니다.

아래 셀은 이 일을 셋으로 나눕니다.
- **① 분류** — v1으로 카테고리·긴급도·요약을 뽑습니다 (모델)
- **② 검사** — 카테고리·긴급도가 정해진 보기 안에 있는지 봅니다 (**코드** — 정해진 보기 밖의 말을 걸러내는 건 모델보다 코드가 확실합니다)
- **③ 답장** — ②를 통과한 분류만 보고 접수 답장을 씁니다 (모델). ②에서 걸리면 ③은 건너뛰고 ①로 돌아갑니다."""),
    C('''# ① 분류 — 지금까지 쓴 v1을 그대로 쓴다
system, user = build(v1, doc)
r1 = llm.call(user, system=system)
try:
    data = parse(r1.text)
except ValueError as e:
    data = None
    print("① 분류 실패:", e)
print("① 분류:", json.dumps(data, ensure_ascii=False))

# ② 검사 — 모델이 아니라 코드가 본다
from src.grade import CATEGORIES, URGENCY
problems = []
if data is None:
    problems.append("JSON 아님")
else:
    if data.get("카테고리") not in CATEGORIES:
        problems.append(f"카테고리 '{data.get('카테고리')}'가 보기 밖")
    if data.get("긴급도") not in URGENCY:
        problems.append(f"긴급도 '{data.get('긴급도')}'가 보기 밖")
    if not data.get("요약"):
        problems.append("요약 없음")
print("② 검사:", problems or "통과")

# ③ 답장 — 검사를 통과한 분류만 보고 접수 답장 작성
if not problems:
    r3 = llm.call(
        "아래 분류 결과만 보고 문의자에게 보낼 접수 답장을 두 줄로 쓰세요. 분류에 없는 내용은 쓰지 않습니다.\\n\\n"
        + json.dumps(data, ensure_ascii=False),
        max_tokens=300)
    print("③ 답장:\\n" + r3.text.strip())
else:
    print("③ 답장: 건너뜀 — ①로 돌아가 고칩니다")'''),
    M("""## 7. 일반화된 프롬프트를 여러 다른 문의에 적용한다
v1은 문의 한 건에 맞춘 프롬프트가 아닙니다. 역할 · 할 일 · 출력 형식 · 예시는 고정하고 `{document}` 자리만 비워 둔 **일반화된 프롬프트**입니다.

아래 셀은 그 v1을 `data/tests.jsonl`에 있는 문의 5건에 차례로 적용해, **프롬프트를 고치지 않고도 다른 문의에서 같은 모양의 결과가 나오는지** 확인합니다. 오후 블록 4는 같은 방법으로 문의 20건에 적용합니다. (이 셀은 아무것도 새로 저장하지 않습니다.)"""),
    C('''from src.grade import load_tests

for t in load_tests()[:5]:
    system, user = build(v1, t["input"])
    r = llm.call(user, system=system)
    try:
        out = parse(r.text)
        print(f"#{t['id']:>2}  {t['input'][:24]:<24} → {out.get('카테고리')} · {out.get('긴급도')}")
    except ValueError as e:
        print(f"#{t['id']:>2}  실패 {e}")'''),
    M("""## 제출할 것
- `prompts/prompt_v0.txt` · `prompts/prompt_v1.txt` — 두 버전을 모두 남긴다
- v0에서 v1로 넘어오며 추가한 것과 그 이유 세 줄:
  1.
  2.
  3. """),
]

# ============================================================== 03
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

**"실제로 틀렸던 입력"이 뭔지:** 앞의 세 종류는 미리 설계해 둔 문제지만, 이 둘은 **"내 v1을 돌려봤더니 실제로 틀렸던 문의"**를 넣는 자리입니다. 지금은 강사가 미리 겪은 흔한 실패 예시가 채워져 있을 뿐입니다.

**내 것으로 바꾸는 법:**
1. 02 노트북에서 v1이 실제로 틀렸던 문의를 적어둔다
2. `tests.jsonl`의 19·20번 줄에서 `input`과 `check`를 그 문의에 맞게 고친다
3. **그다음부터는 문항을 바꾸지 않는다** — 고치는 동안 문항이 바뀌면 비교할 수 없다

| check 필드 | 뜻 |
|---|---|
| `category` | 이 값과 같은 카테고리여야 통과 |
| `urgency` | 이 값과 같은 긴급도여야 통과 |
| `has` | 요약 어딘가에 이 말이 있어야 통과 (없으면 생략) |"""),
    C('''tests = load_tests()
print(Counter(t["group"] for t in tests))
for t in tests[:3] + tests[15:18]:
    print(t["id"], t["group"], t["input"][:30], t["check"])'''),
    M("""## 2. check — 판정 규칙
`check(출력, 통과 조건)` → `(통과 여부, 실패 유형, 설명)`. 가짜 출력으로 먼저 확인합니다.
판정 순서: **형식 위반 → 지어냄 → 지시 일부 누락 → 사실 오류**"""),
    C('''spec = tests[0]["check"]                 # {"category": "IT", "urgency": "보통", "has": "비밀번호"}
samples = {
    "정상":          \'{"카테고리": "IT", "긴급도": "보통", "요약": "비밀번호 재설정 요청"}\',
    "코드 블록":      \'```json\\n{"카테고리": "IT", "긴급도": "보통", "요약": "비밀번호 재설정 요청"}\\n```\',
    "보기 밖 카테고리": \'{"카테고리": "기술지원", "긴급도": "보통", "요약": "비밀번호 재설정 요청"}\',
    "요약에 키워드 없음": \'{"카테고리": "IT", "긴급도": "보통", "요약": "로그인 문제 접수"}\',
    "카테고리 틀림":   \'{"카테고리": "비품", "긴급도": "보통", "요약": "비밀번호 재설정 요청"}\',
}
for name, text in samples.items():
    print(f"{name:<10}", check(text, spec))

spec16 = tests[15]["check"]              # 정답이 "기타"인 문항
print("지어냄     ", check(\'{"카테고리": "인사", "긴급도": "낮음", "요약": "워크숍 일정 문의"}\', spec16))'''),
    M("""## 3. 1차 · v1 채점
**여러분의 `prompts/prompt_v1.txt`**를 20문항에 돌립니다. 아직 TODO 그대로라면 20문항 전부 "형식 위반"으로 나옵니다 — 그때는 아래 경로를 풀이본으로 바꿔 흐름을 먼저 봅니다."""),
    C('''V1 = "prompts/prompt_v1.txt"          # ✏️ 아직 TODO 그대로면 "solutions/prompts/prompt_v1.txt"

passed, fails, rows = run(V1, detail=True)
s1 = summarize(rows, llm.MODEL)
save(V1, llm.MODEL, rows, s1, note="v1")
print(f"통과 {passed} / {len(rows)}")
print(Counter(kind for _, kind in fails))
print_fails(rows)'''),
    M("""### 실패 문항을 직접 연다
통과 수만 보면 **새로 생긴 실패**를 놓칩니다. 실패 문항의 출력을 열어 유형이 맞는지 사람이 확인합니다.
(사실 오류는 코드가 카테고리·긴급도 문자열만 비교해 판정합니다 — 애매한 경우엔 사람이 다시 봅니다.)"""),
    C('''FAIL_ID = fails[0][0] if fails else 1      # ✏️ 보고 싶은 문항 번호
row = next(r for r in rows if r["id"] == FAIL_ID)
print(f"#{row['id']} [{row['group']}] {row['kind']} — {row['why']}\\n")
print(row["text"][:1200])'''),
    M("""## 4. 2차 · 한 유형씩 고친다
1. 가장 많은 실패 유형 **하나**를 고른다
2. 그 유형에 맞는 걸 고쳐서 `prompts/prompt_v2.txt`로 저장한다
3. 같은 20문항으로 v1과 v2를 비교한다
4. 나빠졌으면 되돌린다

| 유형 | 고치는 곳 |
|---|---|
| 형식 위반 | 출력 형식 지시 · 예시 · `<json>` 태그로 감싸게 하기 |
| 지시 일부 누락 | 요약에 꼭 들어가야 할 말을 지시에 명시 |
| 지어냄 | "기타" 기준을 분명히 — 뚜렷이 안 맞으면 억지로 짜맞추지 말라고 지시 |
| 사실 오류 | 카테고리 · 긴급도 판단 기준을 더 구체적으로 — **Day 2에서 더 다룬다** |"""),
    C('''V2 = "solutions/prompts/prompt_v2.txt"   # ✏️ 내 v2: "prompts/prompt_v2.txt"
NOTE = "긴급도: 말투가 아니라 정해진 기준으로"      # ✏️ 무엇을 바꿨는지 한 줄

p2, f2, rows2 = run(V2, detail=True)
s2 = summarize(rows2, llm.MODEL)
save(V2, llm.MODEL, rows2, s2, note=NOTE)
print_table([("v1", llm.MODEL, s1), ("v2", llm.MODEL, s2)])

before = {r["id"] for r in rows if r["ok"]}
after = {r["id"] for r in rows2 if r["ok"]}
print("\\n새로 통과:", sorted(after - before), " 새로 실패:", sorted(before - after))'''),
    M("""### 2차 · 한 번 더 → v3
v2의 실패 중 가장 많은 유형 하나를 골라 v3를 만듭니다. 풀이본 v3는 **카테고리 판단 기준(구매 요청 vs 고장 신고)**을 더 분명히 했습니다."""),
    C('''V3 = "solutions/prompts/prompt_v3.txt"   # ✏️ 내 v3: "prompts/prompt_v3.txt"
NOTE = "카테고리: 구매 요청과 고장 신고를 구분하는 기준 추가"

p3, f3, rows3 = run(V3, detail=True)
s3 = summarize(rows3, llm.MODEL)
save(V3, llm.MODEL, rows3, s3, note=NOTE)
print_table([("v1", llm.MODEL, s1), ("v2", llm.MODEL, s2), ("v3", llm.MODEL, s3)])
print_fails(rows3)'''),
    M("""**발표 — 한 문장으로**
> "___ 유형을 줄이려고 ___를 바꿨더니 통과가 __ → __ 가 됐고, 대신 ___ 가 생겼다(또는 생기지 않았다)."
"""),
    M("""## 5. 3차 · 모델을 바꿔 잰다
같은 v3, 같은 20문항 — **모델만** 바꿉니다. 모델 이름은 `common/llm.py`의 `MODELS`에서 강의 당일 쓸 수 있는 것으로 확인합니다.

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

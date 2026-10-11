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
if llm.MOCK:
    print("모델:", llm.MODEL, "| 모의 모드")
else:
    print("모델:", llm.MODEL, "| 실제 호출")'''


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
**2세션 · API와 메시지** — 실습 25분

1. 첫 호출 — SDK를 그대로 써 본다
2. 응답 읽기 — `stop_reason` · `usage`
3. system과 user
4. 모델은 기억하지 않는다 — 대화 이력
5. 같은 질문 다섯 번 — 그리고 temperature
6. 토큰과 비용

**읽는 법** — 실습 셀마다 바로 앞에 **▶ 이 셀에서 할 것**, 바로 뒤에 **✔ 이 셀의 시사점**이 있습니다. 셀을 돌리기 전에 ▶를, 돌린 뒤에 출력과 ✔를 같이 읽습니다."""),
    M("""**▶ 이 셀에서 할 것** — 준비. 공용 도구 `llm`(`ETRI_LLM_3days/common/llm.py`)을 불러오고, 어떤 모델로 부르는지 · 실제 호출인지 모의 모드인지 확인합니다."""),
    C(SETUP),
    M("""**✔ 이 셀의 시사점**
- 출력의 모델 이름이 오늘 쓸 모델인지 확인합니다. 다르면 `.env`의 `MODEL`을 고칩니다.
- `실제 호출`이어야 이 노트북의 숫자(토큰 수 · 비용)가 의미가 있습니다. `모의 모드`면 답이 가짜 문장으로 나옵니다."""),
    M("""## 1. 첫 호출
`llm.call()`은 아래 SDK 코드를 감싼 것입니다. 감싸기 전 모습을 한 번은 그대로 봐 둡니다.

**▶ 이 셀에서 할 것** — `llm` 도구 없이 anthropic SDK로 직접 한 번 호출합니다. 답 글을 찍고, 이어서 돌아온 `r`을 **통째로** 찍어 글 말고 무엇이 들어 있는지 봅니다. (모의 모드에서는 건너뜁니다.)"""),
    C('''if not llm.MOCK:
    import anthropic
    client = anthropic.Anthropic()          # .env의 ANTHROPIC_API_KEY를 읽는다
    r = client.messages.create(
        model=llm.MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": "연차 신청 절차를 세 단계로 알려줘"}],
    )
    for block in r.content:                 # 답은 블록 여러 개로 올 수 있다
        if block.type == "text":
            print(block.text)
        else:
            print(f"[{block.type} 블록]")
    print("\\n--- r에 저장된 것 전체 (글은 그중 하나일 뿐) ---")
    print(r)
else:
    print("모의 모드 — 건너뜀")'''),
    M("""**✔ 이 셀의 시사점**
- `r`은 글 하나가 아니라 `id`·`role`·`type`·`content`(블록 리스트)·`stop_reason`·`stop_sequence`·`model`·`usage`(입력/출력 토큰 · 캐시 사용량 · 처리 등급 등)·`container`·`diagnostics`·`stop_details`까지 다 들어 있는 객체입니다.
- 답 글은 `content` 리스트 안의 **text 블록**에 들어 있습니다. 위 셀은 그 글만 꺼내 찍었습니다. text 블록 앞에 `[thinking 블록]`이 찍혔다면 그게 무엇인지는 2절에서 봅니다. 나머지 항목은 2·4절에서 하나씩 다룹니다.
- 앞으로는 이 호출을 `llm.call()` 한 줄로 씁니다. 하는 일은 같고, 자주 보는 값(글 · 멈춘 이유 · 토큰 수 · 걸린 시간)을 바로 꺼내 쓰게 해 둔 것입니다."""),
    M("""## 2. 응답 읽기
응답에는 글 말고도 **왜 멈췄는지**(`stop_reason`)와 **토큰을 얼마나 썼는지**(`usage`)가 들어 있습니다.

**▶ 이 셀에서 할 것** — 1절과 같은 질문을 이번엔 `llm.call()`로 보내고, 답 글과 함께 받은 블록의 종류 · `stop_reason` · 입력 토큰 · 출력 토큰 · 걸린 시간을 찍습니다."""),
    C('''r = llm.call("연차 신청 절차를 세 단계로 알려줘", max_tokens=1500)
print(r.text)
print("---")
print("받은 블록   :", [block.type for block in r.raw.content])
print("stop_reason :", r.stop_reason)
print("입력 토큰   :", r.input_tokens)
print("출력 토큰   :", r.output_tokens)
print("걸린 시간   :", f"{r.seconds:.2f}초")'''),
    M("""**✔ 이 셀의 시사점**
- `stop_reason`이 `end_turn`이면 모델이 스스로 답을 끝낸 것입니다. (끝내지 못하고 잘린 경우는 2절 끝에서 봅니다.)
- 비용은 **입력 토큰과 출력 토큰** 두 숫자로 계산됩니다(6절). 그래서 이 두 숫자를 늘 같이 봅니다.
- **받은 블록에 `thinking`이 있으면**, 모델이 답 글을 쓰기 전에 **보이지 않는 생각**을 먼저 한 것입니다. Haiku 5.5는 생각할지 말지를 스스로 정해서, 같은 질문이라도 생각할 때가 있고 안 할 때가 있습니다. 위 출력에 `thinking`이 없었다면 2절 끝 "max_tokens에서 잘리면" 셀에서 보게 될 수 있습니다.
  - 생각한 내용은 우리에게 빈 칸으로 옵니다. 하지만 **생각에 쓴 토큰도 출력 토큰에 들어가서 돈을 냅니다.** 그래서 출력 토큰이 답 글보다 커집니다. 얼마나 커지는지는 아래 "출력 토큰 중 생각에 쓴 몫"에서 재 봅니다.
  - 생각도 `max_tokens` 안에서 합니다. 그래서 이 노트북은 `max_tokens`를 넉넉히(1500) 줍니다.
- 그런데 입력 토큰 수는 질문 글자 수와 맞지 않습니다. 왜 그런지 아래에서 "안녕" 두 글자로 따져 봅니다."""),
    M("""### 입력은 두 번 모양이 바뀐다 — 내 코드 → 서버 → 모델
"안녕"이 모델에 닿기까지 **두 단계**를 거치고, 단계마다 모양이 다릅니다. 이 둘을 섞으면 토큰 수가 이해가 안 됩니다.

```
내 코드 ──(JSON)──▶ Anthropic 서버 ──(토큰 열)──▶ 모델
```

**1단계 — 내 코드가 서버로 보내는 것 (JSON).** 내가 입력한 건 "안녕" 두 글자지만, 실제로 나가는 건 JSON 덩어리입니다.
이 JSON을 받는 쪽은 **모델이 아니라 Anthropic 서버**입니다. 모델은 `{` · `"role"` · `"user"` 같은 JSON 글자를 하나도 보지 않습니다 — 서버가 JSON을 풀어서 모델용 입력으로 다시 만들어 넘기기 때문입니다(2단계).

**▶ 이 셀에서 할 것** — 실제로 보내지는 않고, "안녕"을 보낼 때 서버로 나가는 요청(JSON)의 모양만 찍어 봅니다."""),
    C('''import json

# 보내지는 않고, 보낼 요청의 모양만 찍어 본다
request = {
    "model": llm.MODEL,
    "max_tokens": 20,
    "messages": [{"role": "user", "content": "안녕"}],
}
print("내가 입력한 건: '안녕' (2글자)")
print("\\n실제로 서버에 보내는 요청 (JSON):")
print(json.dumps(request, ensure_ascii=False, indent=2))'''),
    M("""**✔ 이 셀의 시사점**
- 내가 쓴 건 2글자인데, 나가는 건 `model` · `max_tokens` · `messages` 세 항목짜리 JSON입니다.
- 그럼 이 JSON 글자가 전부 토큰으로 세어질까요? 아닙니다 — 아래 2단계에서 서버가 이걸 어떻게 바꾸는지 봅니다."""),
    M("""**2단계 — 서버가 JSON을 풀어서 모델 입력으로 바꾼다.** 세 항목이 각각 이렇게 쓰입니다.
- `model` → 어느 모델에 보낼지 **고르는 데만** 쓰고 버림. 모델 입력에 안 들어감
- `max_tokens` → 생성을 몇 토큰에서 **끊을지**에만 쓰고 버림. 모델 입력에 안 들어감
- `messages` → **이것만** 모델 입력이 됨. 단, `"role": "user"` 같은 글자 그대로가 아니라 "여기서부터 user의 말" 같은 뜻의 **특수 토큰**(구조 표식)으로 바뀜

그래서 모델이 읽는 것은 JSON이 아니라 대략 이런 토큰 열입니다 (`[ ]`는 글자가 아닌 특수 토큰):
```
[대화 시작] [user 차례] 안녕 [내용 끝] [assistant 차례] ← 모델은 여기서부터 이어 쓴다
```

> **어디까지가 확인된 것인가.** 이 토큰 열의 정확한 모양은 공개된 문서에 없어서 우리가 직접 볼 수 없습니다. 아래에서 직접 재서 확인하는 것은 두 가지입니다 — ① JSON 글자는 토큰으로 세어지지 않는다 ② 내용 말고 붙는 표식의 **개수**와, 메시지가 늘 때 몇 개씩 느는지. 표식 하나하나의 이름(`[대화 시작]` 등)은 그 개수에 맞춰 그린 **그림**입니다.

**▶ 이 셀에서 할 것** — "안녕"을 실제로 보내서 입력 토큰이 몇 개로 세어지는지 보고, 돌아온 응답 원본(`r.raw`)을 통째로 찍습니다."""),
    C('''r = llm.call("안녕", max_tokens=20)
print("모델이 받은 입력 토큰 수:", r.input_tokens, " — 내가 쓴 건 '안녕' 2글자")
print("\\n돌아온 응답 전체:")
print(r.raw)'''),
    M("""**✔ 이 셀의 시사점**
- 2글자를 보냈는데 입력 토큰은 11개입니다. 내가 쓴 글자 말고도 뭔가가 붙어서 세어진다는 뜻입니다.
- 응답에는 글 말고도 `id`(요청 번호) · `stop_reason`(멈춘 이유) · `usage`(토큰 수뿐 아니라 캐시 사용량 · 처리 등급 · 추론 지역까지)가 같이 옵니다. `llm.call()`의 결과는 그중 당장 필요한 몇 개(`text`·`stop_reason`·토큰 수)만 추려 둔 것이고, 전부 보려면 `r.raw`를 엽니다."""),
    M("""### 그 11토큰은 뭔가 — JSON 글자가 아니다
"JSON에서 안녕을 뺀 나머지가 토큰 아니냐"고 생각하기 쉽습니다. 아닙니다. 내용을 바꿔 가며 세어 보면 알 수 있습니다.

**▶ 이 셀에서 할 것** — 모델을 부르지 않고 토큰 수만 세는 `llm.count_tokens()`로, 메시지 내용을 `a` · `hello` · `안` · `안녕`으로 바꿔 가며 셉니다. 마지막엔 JSON 글자 `{"role": "user", "content": ""}` 자체를 내용으로 넣어 셉니다."""),
    C('''for t in ["a", "hello", "안", "안녕"]:
    print(f"{t!r:34} → {llm.count_tokens(t):>2} 토큰")
j = '{"role": "user", "content": ""}'
print(f"{j!r:34} → {llm.count_tokens(j):>2} 토큰   ← JSON 글자를 내용으로 보내 보면")'''),
    M("""**✔ 이 셀의 시사점**
- 한 글자짜리 `a`도 **9토큰**입니다. 내용은 적어도 1토큰이니, 내용과 상관없이 **8개 안팎이 늘 붙는다**는 뜻입니다.
- `hello`는 10, `안`은 9, `안녕`은 11입니다. 글자 수나 단어 수로는 토큰 수를 맞힐 수 없습니다 — 직접 세어 봐야 압니다.
- JSON 글자 `{"role": "user", "content": ""}`를 **내용으로** 넣으면 21토큰, `a`보다 12개나 많습니다. JSON 글자는 그 자체로 토큰을 이만큼 먹습니다. 그런데 `a` 하나를 보낼 때 붙는 건 8개 안팎뿐이니, **늘 붙는 그 8개는 JSON 글자가 아닙니다.**

그러니 "안녕"의 11개는 **"안녕" 내용 + 구조 표식**입니다. `count_tokens`는 합계만 알려 주므로 둘을 몇 대 몇으로 딱 가를 수는 없고, 표식이 정확히 무엇인지도 공개돼 있지 않습니다. 확인되는 것은 **내용과 상관없이 늘 일정한 개수가 붙는다**는 것까지입니다."""),
    M("""### 늘 붙는 개수는 메시지 수에 따라 어떻게 늘어나나
메시지 하나를 감싸는 표식이라면 메시지가 늘 때 같이 늘어야 합니다. 메시지 수를 바꿔 가며 재 봅니다.

**▶ 이 셀에서 할 것** — 메시지를 1개 · 3개 · 5개로 늘려 가며(내용은 모두 한 글자짜리 `a`, `b`) 전체 토큰을 셉니다. 내용을 메시지마다 1토큰으로 보고 뺀 나머지(틀)가 몇 개인지 보고, 마지막에 **틀이 메시지 수에 따라 어떻게 느는지** 식으로 정리합니다."""),
    C('''import anthropic
client = anthropic.Anthropic()

def count_messages(messages):
    """messages 전체의 입력 토큰 수를 센다 (모델은 부르지 않는다)."""
    result = client.messages.count_tokens(model=llm.MODEL, messages=messages)
    return result.input_tokens

user_a = {"role": "user", "content": "a"}
assistant_b = {"role": "assistant", "content": "b"}

cases = [
    ("메시지 1개 [a]", [user_a]),
    ("메시지 3개 [a|b|a]", [user_a, assistant_b, user_a]),
    ("메시지 5개 [a|b|a|b|a]", [user_a, assistant_b, user_a, assistant_b, user_a]),
]
frames = []                          # 경우마다 틀(전체 − 내용)을 모은다
for name, messages in cases:
    total = count_messages(messages)
    content = len(messages)          # 내용 a · b는 메시지마다 1토큰으로 본다
    frame = total - content
    frames.append(frame)
    print(f"{name:22} → {total:>2} 토큰 = 내용 {content} + 틀 {frame}")

PER_MESSAGE = (frames[1] - frames[0]) // 2    # 메시지가 2개 늘 때 늘어난 틀 ÷ 2 = 메시지 하나마다 붙는 틀
BASE = frames[0] - PER_MESSAGE                 # 메시지 1개일 때 틀에서 그 메시지 몫을 뺀 나머지 = 대화 전체에 한 번 붙는 틀
print(f"\\n→ 틀 = {BASE} + {PER_MESSAGE} × 메시지 수")'''),
    M("""**✔ 이 셀의 시사점**
- 메시지가 하나 늘 때마다 틀이 **똑같은 개수만큼** 늡니다. 그래서 틀은 `대화 전체에 한 번 붙는 몫 + 메시지마다 붙는 몫 × 메시지 수`로 나뉩니다. 이 모델(Haiku 5.5)에서는 `6 + 2 × 메시지 수`입니다. 이 두 숫자(`BASE` · `PER_MESSAGE`)는 4절에서 다시 씁니다.
- 이 숫자는 **모델마다 다릅니다.** 같은 실험을 이전 모델 Haiku 4.5에서 하면 `4 + 3 × 메시지 수`가 나왔습니다. 공개된 값이 아니어서 이렇게 직접 재서 알아냅니다.
- 이 실험은 `a`·`b`가 각각 1토큰이라고 보고 계산했습니다. 그 가정이 맞는지는 4절에서 실제 대화의 토큰 수와 맞춰 보며 확인합니다.
- 실무에서 기억할 것: 내가 쓴 글자(2개)보다 붙는 표식이 더 크고, 글자 수로는 토큰 수를 어림잡을 수 없습니다. 그리고 4절에서 보겠지만, 턴이 쌓이면 **메시지마다 붙는 몫**도 매번 전부 다시 들어갑니다."""),
    M("""### 출력 토큰 중 생각에 쓴 몫
2절 앞에서 본 것처럼 Haiku 5.5는 답 전에 보이지 않는 생각을 할 수 있고, 그 토큰도 출력 토큰에 들어갑니다. 생각은 `llm.call(..., thinking=...)`으로 끌 수 있습니다. 끄는 값은 모델마다 다르고, 이 모델(Haiku 5.5)은 `{"type": "disabled"}`입니다.

**▶ 이 셀에서 할 것** — 같은 질문을 thinking **기본(켜짐)**과 **끄기**로 두 번씩 보냅니다. 답 글만 따로 센 토큰(바로 위에서 잰 틀을 빼서 구함)을 출력 토큰에서 빼서, 나머지 — 생각에 쓴 몫 — 를 봅니다."""),
    C('''question = "연차 신청 절차를 세 단계로 자세히 알려줘"
FRAME_ONE = BASE + PER_MESSAGE      # 메시지 1개짜리 틀 (바로 위에서 잰 값) — 글만 셀 때 뺀다

cases = [
    ("기본 (켜짐)", None),
    ("끄기", {"type": "disabled"}),  # 끄는 값은 모델마다 다르다 — 이 값은 Haiku 5.5용
]
for label, thinking in cases:
    for i in range(2):
        r = llm.call(question, max_tokens=1500, thinking=thinking)
        kinds = [block.type for block in r.raw.content]
        text_tokens = llm.count_tokens(r.text) - FRAME_ONE      # 답 글만 따로 센 토큰
        rest = r.output_tokens - text_tokens                    # 출력 토큰 중 글이 아닌 나머지
        print(f"{label:9} {i+1}회 | 블록 {kinds} | 출력 {r.output_tokens:>5} = 글 {text_tokens:>5} + 나머지 {rest:>4}")'''),
    M("""**✔ 이 셀의 시사점**
- **끄면** 받은 블록이 `text`뿐이고, 나머지는 2개 안팎입니다. 생각을 안 했는데도 2개쯤 남는 이유는 이 자료로는 알 수 없어서, 그만큼은 오차로 봅니다.
- **켜면** 나머지가 그보다 훨씬 큽니다 — 그것이 **생각에 쓴 토큰**이고, 출력 단가로 돈을 냅니다. 강사가 돌렸을 때 이 질문에서는 약 70~80토큰이었고, 6절의 긴 문서 요약에서는 출력 500토큰 안팎 중 220~360토큰이 생각이었습니다. **얼마나 생각하는지는 질문마다 다릅니다.**
- 강사가 여러 번 돌렸을 때는 켰을 때 **답 글 자체도 300~500토큰쯤 더 길었습니다**(켜면 글 약 1,050~1,320토큰, 끄면 약 740~850토큰). 그래서 켜고 끈 출력 토큰 차이가 전부 생각은 아닙니다 — 글을 따로 세어 봐야 생각의 몫이 보입니다.
- 이 과정은 기본(켜짐) 그대로 씁니다. 끄면 출력 토큰은 줄지만, 생각이 필요한 어려운 질문에서 답이 어떻게 달라지는지는 이 셀로는 알 수 없습니다."""),
    M("""### max_tokens에서 잘리면
`max_tokens`를 작게 주면 답이 중간에 끊기고 `stop_reason`이 `max_tokens`가 됩니다. 생각하는 모델은 생각에 토큰을 먼저 쓰기 때문에, **글은 시작도 못 하고** 끊길 수도 있습니다.

**▶ 이 셀에서 할 것** — "자세히 알려 달라"는 질문을 `max_tokens=20`으로 짧게 묶어 보내고, 받은 블록 · 글 · `stop_reason` · 출력 토큰을 봅니다."""),
    C('''r = llm.call("연차 신청 절차를 세 단계로 자세히 알려줘", max_tokens=20)
print("받은 블록   :", [block.type for block in r.raw.content])
print("글          :", repr(r.text))
print("stop_reason :", r.stop_reason, "| 출력 토큰:", r.output_tokens)
if r.stop_reason == "max_tokens":
    print("→ 잘렸습니다. max_tokens를 늘리거나 더 짧게 쓰라고 지시합니다.")'''),
    M("""**✔ 이 셀의 시사점**
- `stop_reason`이 `max_tokens`이고, 출력 토큰을 20개 다 썼습니다. 글은 쓰다 만 채로 끊기거나, 받은 블록이 `thinking`뿐이고 글이 `''`(빈 문자열)일 수 있습니다 — 20토큰을 **생각하는 데 다 써서** 글을 쓸 차례가 오지 않은 것입니다.
- 어느 쪽이든 **오류는 나지 않습니다** — 그래서 `stop_reason`을 안 보면 잘린 줄 모릅니다.
- 그래서 **프로그램은 답을 쓰기 전에 `stop_reason`부터 확인합니다.** 예를 들어 JSON으로 답하게 했는데 잘리면 파싱이 깨집니다."""),
    M("""## 3. system과 user
매번 같은 **역할 · 규칙 · 형식**은 `system`에, 매번 바뀌는 **자료와 질문**은 `user`에 둡니다.

**▶ 이 셀에서 할 것** — 같은 질문(소방 훈련 안내)을 system 없이 · 인사팀 담당자 · 사내 공지 봇, 세 가지 system으로 보내 답을 나란히 봅니다. 질문은 한 글자도 바꾸지 않습니다."""),
    C('''question = "다음 주 화요일 오후 2시에 전 직원 소방 훈련이 있습니다. 이 내용을 안내해 주세요."

for system in [
    None,
    "당신은 신입 사원에게 친절하게 설명하는 인사팀 담당자입니다. 두 문장 이내로 씁니다.",
    "당신은 사내 메신저 공지 봇입니다. 이모지 없이 한 줄로, '[공지]'로 시작합니다.",
]:
    r = llm.call(question, system=system, max_tokens=1500)
    print(f"[system] {system}\\n{r.text.strip()}\\n")'''),
    M("""**✔ 이 셀의 시사점**
- 질문은 그대로인데 말투 · 길이 · 형식이 system을 따라 바뀝니다. system에 적은 규칙(두 문장 이내, '[공지]'로 시작 등)이 지켜졌는지 출력에서 직접 확인합니다.
- 그러니 매번 같은 역할 · 규칙 · 형식은 system에 한 번 정해 두고, user에는 그때그때 바뀌는 자료와 질문만 넣습니다."""),
    M("""## 4. 모델은 기억하지 않는다
API는 매 호출이 처음입니다. 이어서 대화하려면 **앞서 주고받은 메시지를 직접 다시 보냅니다** — 그래서 턴이 늘어날수록 **매번 보내는 요청 자체가 커집니다.**

**▶ 이 셀에서 할 것** — 2턴짜리 대화를 돌립니다. 1턴에 이름과 부서를 알려 주고, 2턴에 그걸 다시 묻습니다. 매 턴 **서버로 나가는 요청(JSON) 전체와 돌아오는 응답 전체**를 빠짐없이 찍습니다. (2절에서 봤듯 모델은 이 JSON의 `messages`만 특수 토큰으로 바꿔 받습니다.)"""),
    C('''import json

history = []
sent = []          # 턴마다 (보낸 messages, 응답) 을 남겨 둔다 — 아래에서 토큰 수를 검산한다
turns = [
    "제 이름은 김민수이고, 생산관리팀에서 일합니다.",
    "제 이름과 부서가 뭐였죠?",
]
for i, user_text in enumerate(turns, 1):
    messages = history + [{"role": "user", "content": user_text}]
    request = {"model": llm.MODEL, "max_tokens": 1500, "messages": messages}
    print(f"===== {i}번째 턴 =====")
    print("--- 서버로 나가는 요청 (JSON) ---")
    print(json.dumps(request, ensure_ascii=False, indent=2))

    r = llm.call(user_text, history=history, max_tokens=1500)
    sent.append((messages, r))

    print("\\n--- 돌아온 응답 전체 ---")
    print(r.raw)
    print()

    history = messages + [{"role": "assistant", "content": r.text}]'''),
    M("""**✔ 이 셀의 시사점**
- **1턴**은 `messages`에 내가 보낸 말 하나뿐이지만, **2턴**은 1턴의 내 말 + 모델의 답 + 이번 내 말, **세 개**가 들어갑니다.
- 2턴에서 모델이 이름과 부서를 답할 수 있는 건 기억해서가 아니라 **1턴 내용을 내가 다시 보냈기 때문**입니다. 이력 없이 "제 이름과 부서가 뭐였죠?"만 보내면 모델은 모릅니다."""),
    M("""### 멀티턴 입력 토큰은 이 식으로 정확히 맞는다
2절 끝에서 잰 틀은 `BASE + PER_MESSAGE × 메시지 수`였습니다(이 모델: `6 + 2 × 메시지 수`). 턴이 쌓이면:

```
input_tokens = BASE + Σ (PER_MESSAGE + 메시지 내용 토큰)     ← 지금까지 쌓인 모든 메시지에 대해
```

**▶ 이 셀에서 할 것** — 방금 돌린 두 턴의 실제 `usage.input_tokens`를 이 식으로 계산한 값과 맞춰 봅니다. 메시지 하나의 내용 토큰은 그 메시지만 따로 센 값에서 메시지 1개짜리 틀(`BASE + PER_MESSAGE`)을 빼서 구합니다."""),
    C('''FRAME_ONE = BASE + PER_MESSAGE      # 메시지 1개짜리를 셀 때 붙는 틀 (2절에서 잰 값)

for i, (messages, r) in enumerate(sent, 1):
    pieces = []                                                 # 메시지마다 내용 토큰
    for m in messages:
        pieces.append(llm.count_tokens(m["content"]) - FRAME_ONE)   # 그 메시지만 센 값 − 틀 = 내용 토큰
    pred = BASE
    for p in pieces:
        pred = pred + PER_MESSAGE + p
    if pred == r.input_tokens:
        ok = "✓"
    else:
        ok = "✗"
    print(f"{i}턴: 메시지 {len(messages)}개, 내용 토큰 {pieces}")
    print(f"     {BASE} + Σ({PER_MESSAGE}+내용) = {pred}   실제 input_tokens = {r.input_tokens}   {ok}")'''),
    M("""**✔ 이 셀의 시사점**
- 두 턴 모두 ✓ — 입력 토큰은 "지금까지 쌓인 메시지 전부의 내용 + 메시지마다 붙는 틀 + 대화 전체에 한 번 붙는 틀"로 정확히 계산됩니다. 2절에서 `a`·`b`를 1토큰으로 본 가정도 맞았다는 뜻입니다.
- 2턴째 내용 토큰 가운데 가장 큰 덩어리는 **1턴에서 모델이 쓴 답 글**입니다. 1턴엔 `output_tokens`로 냈던 것을 2턴엔 `input_tokens`로 **다시** 냅니다 (생각에 쓴 토큰은 이력에 넣지 않으므로 다시 내지 않습니다) — 멀티턴에서 비용이 빨리 불어나는 이유입니다. 메시지마다 붙는 틀도 매번 전부 다시 들어갑니다."""),
    M("""### 요청보다 응답에 훨씬 많은 게 따라온다
요청은 `model` · `max_tokens` · `messages`, 딱 3가지뿐이었습니다.

**▶ 이 셀에서 할 것** — 방금 받은 마지막 응답 원본(`r.raw`)을 항목별로 열어, 각 값과 그 뜻을 한 줄씩 찍어 봅니다."""),
    C('''u = r.raw.usage
types = [b.type for b in r.raw.content]
block = None
for b in r.raw.content:       # text 블록을 찾는다 — 앞에 thinking 블록이 있을 수 있다
    if b.type == "text":
        block = b
print("요청에는 모델 이름 · max_tokens · messages, 이 3가지만 넣었습니다.")
print("마지막 턴의 응답(r.raw)에는 그보다 훨씬 많은 게 같이 옵니다:\\n")
print(f"  content                           : {types}")
print(f"      답이 블록 하나가 아니라 **리스트**인 이유 — 생각(thinking) · 도구 호출(tool_use) ·")
print(f"      글(text)처럼 종류가 다른 블록이 여러 개 올 수 있습니다.")
print(f"  text 블록의 .text                 : {block.text[:40]!r}...")
print(f"      우리가 r.text로 꺼내 쓰는 바로 이 값")
print(f"  text 블록의 .citations            : {block.citations}")
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
    M("""**✔ 이 셀의 시사점**
- 요청 쪽은 3가지뿐인데, 응답 쪽은 **15가지가 넘는 부가 정보**가 따라옵니다.
- `content`조차 글 하나가 아니라 **블록 리스트**이고, 우리가 늘 쓰는 `r.text`는 그 리스트에서 **text 블록의 글만** 꺼낸 것입니다. thinking 블록은 빠집니다.
- `r.text`만 보면 이 중 거의 전부를 놓칩니다. `llm.call()`의 결과는 당장 쓸모 있는 몇 개만 추려 둔 것이고, 나머지는 `r.raw`를 직접 열어야 보입니다."""),
    M("""## 5. 같은 질문 다섯 번
같은 질문을 두 가지로 각각 5회 보내고 결과를 나란히 놓습니다.

**▶ 이 셀에서 할 것** — 정답이 거의 정해진 질문(연차 신청 절차)과 열린 질문(슬로건)을 각각 5번씩 보냅니다. 매번 출력 토큰 수와 답 앞부분을 찍고, 마지막에 서로 다른 답이 몇 개인지 셉니다.

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
        r = llm.call(q, max_tokens=1500)
        runs[name].append({"text": r.text, "output_tokens": r.output_tokens})
        print(name, i + 1, r.output_tokens, "|", r.text.strip().replace("\\n", " ")[:60])
    print()

for name, rs in runs.items():
    print(f"{name}: 서로 다른 답 {len({x['text'] for x in rs})}개 / 5")'''),
    M("""**✔ 이 셀의 시사점**
- 같은 질문을 같은 설정으로 보내도 답이 **매번 같다는 보장이 없습니다.** 위의 "서로 다른 답 ○개 / 5"가 그 결과입니다. 글자 하나만 달라도 다른 답으로 세므로, 답을 눈으로 비교해 **어디가 달라졌는지**도 봅니다.
- 출력 토큰 수도 매번 달라질 수 있으니, 길이 · 비용도 한 번 잰 값으로 단정하지 않습니다.
- 출력 토큰에는 보이지 않는 생각(2절)도 들어 있습니다. 그래서 답 글 길이가 비슷해도 출력 토큰은 크게 다를 수 있습니다.
- 그래서 **한 번 돌려 본 결과로 "이 프롬프트는 된다/안 된다"를 판단하면 안 됩니다** — 4세션(평가)의 출발점입니다."""),
    M("""### temperature — 흔들림을 조절하는 손잡이였던 것
`temperature`는 다음 토큰을 얼마나 고르게 뽑을지 정하는 값입니다. **0 = 가장 확률 높은 토큰 위주(덜 흔들림)**, **1 = 더 고르게(더 다양함)**. 위에서 본 흔들림을 줄이려고 예전에는 이 값을 0으로 낮췄습니다.
- **SDK 1.x**: `messages.create()`에서 `temperature` 인자가 빠졌습니다. (`llm.call`은 `extra_body`로 우회해 보냅니다.)
- **API**: 이 과정에서 쓰는 모델(Haiku 5.5 · Sonnet 5.5)은 **1이 아닌 값을 거부합니다** — 400 오류. 1은 받지만 기본값과 같아서 아무것도 바뀌지 않습니다. (이전 세대 Haiku 4.5는 0~1 사이 값을 받았습니다.)

**▶ 이 셀에서 할 것** — 기본 모델(`llm.MODEL`)과 고급 모델(`llm.MODEL_ADVANCED`)에 같은 슬로건 질문을 temperature **0**과 **1**로 각각 보내, 어느 쪽이 받아들여지고 어느 쪽이 거부되는지 봅니다."""),
    C('''Q = "신제품 무선 청소기 슬로건 하나만 지어줘. 슬로건만 답해."

for model in [llm.MODEL, llm.MODEL_ADVANCED]:
    print("모델:", model)
    for t in [0.0, 1.0]:
        try:
            r = llm.call(Q, model=model, temperature=t, max_tokens=500)
            print(f"   temperature={t}: 받아들였습니다 → {r.text.strip()[:40]}")
        except Exception as e:
            print(f"   temperature={t}: 거부 — {type(e).__name__}: {str(e)[:120]}")
    print()'''),
    M("""**✔ 이 셀의 시사점**
- 두 모델 모두 **0은 거부**(400 오류)하고 **1만 받습니다.** 1은 기본값이라, 흔들림을 줄이는 데는 아무 도움이 안 됩니다.
- 즉 지금 모델에서는 흔들림을 손잡이로 줄일 수 없습니다. 그래서 **여러 번 돌려 측정하는 습관(4세션)**이 필요합니다.

> 대신 생긴 조절 손잡이는 `effort`("low"~"max")처럼 *얼마나 생각할지*입니다. 흔들림을 줄이는 손잡이는 아닙니다. 지원 여부는 모델마다 다르므로 강의 당일 문서로 확인합니다."""),
    M("""## 6. 토큰과 비용
비용 = 입력 토큰 × 입력 단가 + 출력 토큰 × 출력 단가. **단가는 강의 당일 요금표로 `common/llm.py`의 `PRICES`를 채웁니다.**
(채우지 않은 모델은 "단가 미입력"으로 나옵니다.)

**▶ 이 셀에서 할 것** — 긴 사내 문서(`11_정보보호지침_개정_긴문서.txt`) 한 편을 세 줄로 요약시킵니다. 받은 블록 종류를 보고, 입력 비용과 출력 비용을 **따로** 계산해 어느 쪽이 큰지 비교한 뒤, 1건 비용과 하루 1,000건일 때의 비용을 봅니다."""),
    C('''doc = Path("data/docs/11_정보보호지침_개정_긴문서.txt").read_text(encoding="utf-8")
r = llm.call(f"다음 문서를 세 줄로 요약해 주세요.\\n\\n{doc}", max_tokens=2000)
print(r.text.strip(), "\\n")
print("받은 블록:", [block.type for block in r.raw.content])

price = llm.PRICES.get(llm.MODEL)              # (입력 단가, 출력 단가) — 100만 토큰당 달러
if price is None:
    print("단가 미입력 — common/llm.py의 PRICES를 채웁니다")
else:
    cost_in = r.input_tokens * price[0] / 1_000_000
    cost_out = r.output_tokens * price[1] / 1_000_000
    print(f"입력 {r.input_tokens:>5} 토큰 × ${price[0]} → {llm.fmt_cost(cost_in)}")
    print(f"출력 {r.output_tokens:>5} 토큰 × ${price[1]} → {llm.fmt_cost(cost_out)}")
    print(f"1건 합계 {llm.fmt_cost(r.cost)} · 하루 1,000건이면 약 ${r.cost * 1000:.2f}")'''),
    M("""**✔ 이 셀의 시사점**
- 긴 문서를 넣으면 **입력 토큰이 출력 토큰보다 몇 배 많습니다.** 그런데 출력 단가가 입력의 5배라서, 입력 비용과 출력 비용은 **비슷해지거나 출력 쪽이 더 클 수도** 있습니다. 위 두 줄을 비교해 봅니다.
- 출력 토큰에는 보이지 않는 생각(2절)도 들어갑니다. 받은 블록에 `thinking`이 있었다면, 세 줄 요약치고 출력 토큰이 큰 이유가 그것입니다.
- 1건은 작아 보여도 건수를 곱하면 커집니다. 그래서 비용을 줄이려면 **넣는 양(입력)과 쓰게 하는 양(출력)을 둘 다** 봐야 합니다. 넣는 양은 내일 1세션(전부 넣기 vs 골라 넣기)에서 이어서 봅니다."""),
]

# ============================================================== 02
nb02 = [
    M("""# 02 · 프롬프트 설계
**3세션 · 프롬프트 설계** — 실습 60분

사내 문의 메시지 하나를 받아 **카테고리 · 긴급도 · 요약**으로 분류하는 프롬프트를 만듭니다. 한 줄짜리 지시(v0)에서 시작해, 요소를 **하나씩 더할 때마다 새 프롬프트 파일**(`prompt_1` → `prompt_4`)을 만들고 그때마다 뭐가 달라졌는지 봅니다. `prompt_4.txt`가 최종이고, 오후 4세션에서 20문항으로 채점받는 **1차**의 재료입니다.

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
| 4 | 근거를 먼저 적게 하고, 그 근거를 어떻게 쓰는지 | 15분 |

**읽는 법** — 실습 셀마다 바로 앞에 **▶ 이 셀에서 할 것**, 바로 뒤에 **✔ 이 셀의 시사점**이 있습니다. 셀을 돌리기 전에 ▶를, 돌린 뒤에 출력과 ✔를 같이 읽습니다."""),
    M("""**▶ 이 셀에서 할 것** — 준비. 공용 도구 `llm`과, 채점 코드 `src/grade.py`에서 이 노트북이 쓰는 함수들을 불러옵니다.
- `build` — 프롬프트 파일을 system과 user로 나누고 `{document}` 자리에 문의를 넣는다
- `parse` — 모델 답에서 JSON을 꺼낸다 (못 꺼내면 오류)
- `CATEGORIES` · `URGENCY` — 카테고리 다섯 개 · 긴급도 세 개 보기"""),
    C(SETUP + '''
import json, re
from pathlib import Path
from src.grade import build, parse, schema_errors, CATEGORIES, URGENCY'''),
    M("""**✔ 이 셀의 시사점**
- 출력의 모델 이름과 `실제 호출`을 확인합니다. 오류 없이 끝나면 `src/grade.py`도 제대로 불러온 것입니다."""),
    M("""## 1. 문의 고르기
이 노트북은 **문의 하나**를 끝까지 씁니다. 프롬프트를 바꿀 때 입력까지 같이 바뀌면 뭐 때문에 결과가 달라졌는지 알 수 없기 때문입니다. 그리고 매번 **같은 문의를 3번** 보냅니다 — 모델 답은 조금씩 흔들리므로(01 노트북 "같은 질문 다섯 번"), 1번으로는 운인지 실력인지 모릅니다. 다른 문의로 시험하는 건 4절(헷갈리는 문의 둘)과 오후 03 노트북(정답 있는 20문항)입니다.

**▶ 이 셀에서 할 것** — 이 노트북 내내 쓸 문의 하나를 `doc`에 정하고 찍습니다. ✏️ 내 업무 문의로 바꿔도 되지만, 한 번 정하면 끝까지 바꾸지 않습니다."""),
    C('''doc = "출입카드가 인식이 안 돼서 사무실에 못 들어가고 있어요."   # ✏️ 내 업무 문의로 바꿔도 됩니다
print(doc)'''),
    M("""**✔ 이 셀의 시사점**
- 이 문의가 2~4절 모든 비교의 **공통 입력**입니다. 입력은 그대로 두고 프롬프트만 바꿔야, 결과가 달라졌을 때 프롬프트 때문이라고 말할 수 있습니다."""),
    M("""## 2. v0 — 한 줄짜리 지시
`prompts/prompt_v0.txt`를 그대로 돌립니다. 결과를 보고 **무엇이 부족한지** 적습니다.

**▶ 이 셀에서 할 것** — 이 노트북에서 계속 쓸 시험 함수 `try_prompt()`를 정의하고, 한 줄짜리 `prompt_v0.txt`로 같은 문의를 3번 보냅니다. 출력 순서는 이렇습니다.
1. 프롬프트 파일 내용
2. system과 user에 **실제로 들어간 것**
3. 회마다 판정(통과 / JSON 실패 / 보기 밖 …)과 모델 답
4. 마지막 줄 — 통과 기준 세 가지를 각각 몇 번 만족했는지와 최종 통과 수"""),
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
        r = llm.call(user, system=system, max_tokens=1500)
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
    M("""**✔ 이 셀의 시사점**
- `prompt_v0.txt`에는 `=== system ===` 칸이 없어서 system은 `None`이고, 지시와 문의가 전부 user로 들어갑니다.
- 한 줄 지시만 주면 **형식 · 키 이름 · 값을 모델이 제멋대로 정합니다.** 코드블록(```)으로 감싸거나, 보기에 없는 말을 쓰거나, 키 이름을 새로 지어내서 코드가 읽지 못합니다.

**v0에서 부족했던 것** (한 줄씩). 위 출력에서 이 세 가지를 확인해 적습니다:
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

출력 형식을 **먼저** 넣는 이유: 이게 없으면 파싱이 막혀서 나머지 셋이 뭘 바꾸는지 볼 수 없기 때문입니다. 각 단계의 문장은 ✏️ 표시된 변수에 들어 있으니 **직접 고쳐 가며** 돌려 봐도 됩니다.

**▶ 이 셀에서 할 것** — 네 태그가 비어 있는 프롬프트 틀(`TEMPLATE`)과, 단계마다 채울 문장(`STEPS`)을 **정의만** 합니다. 모델은 아직 부르지 않습니다."""),
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
    M("""**✔ 이 셀의 시사점**
- 출력이 없는 게 정상입니다. 정의만 했습니다.
- `TEMPLATE`의 `=== system ===` 아래가 system, `=== user ===` 아래가 user로 들어갑니다. `{document}` 자리에 문의가 들어갑니다.
- `STEPS`는 출력 형식 → 역할 → 할 일 → 예시 순서로, 다음 셀에서 위에서부터 하나씩 채워집니다."""),
    M("""**▶ 이 셀에서 할 것** — 빈 틀부터 시작해 `STEPS`를 하나씩 채웁니다. 채울 때마다 `prompts/prompt_1.txt` ~ `prompt_4.txt`로 저장하고, 같은 문의를 3번 돌려 통과 집계와 모델이 낸 (카테고리, 긴급도)를 찍습니다. (`show=False`라 답 전문은 찍지 않고 집계만 찍습니다.)"""),
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
    M("""**✔ 이 셀의 시사점**
- `prompts/` 폴더에 `prompt_1.txt` ~ `prompt_4.txt` 네 파일이 생겼습니다. 단계마다 무엇을 넣었는지가 파일로 남습니다.
- 단계마다 ① JSON · ② 보기 안 · ③ 요약 중 **어느 칸이 바뀌는지** 봅니다. 단계별 차이는 바로 아래 표에서 한눈에 비교합니다."""),
    M("""### 최종 프롬프트(prompt_4)는 v0에서 뭐가 좋아졌나

**▶ 이 셀에서 할 것** — v0 · 빈 틀 · `prompt_1` ~ `prompt_4`의 결과를 한 표로 놓고, 최종 프롬프트 `prompts/prompt_4.txt` 전문을 찍습니다."""),
    C('''print(f"{'단계':<6}{'추가한 요소':<10}{'통과':<8}모델이 낸 값")
print("-" * 70)
print(f"{'v0':<6}{'(한 줄 지시)':<10}{str(ok_v0)+' / 3':<8}{vals_v0}   ← 2절 결과")
print(f"{'빈 틀':<6}{'(태그만)':<10}{'0 / 3':<8}{vals0}")
for n, tag, ok, vals in results:
    print(f"{'prompt_'+str(n):<6}{'<'+tag+'>':<10}{str(ok)+' / 3':<8}{vals}")

print("\\n===== 최종 프롬프트 prompts/prompt_4.txt =====")
print(final)'''),
    M("""**✔ 이 셀의 시사점** — 단계마다 **다른 것**이 고쳐집니다:
- **빈 틀 → `prompt_1` (출력 형식):** 파싱 실패가 사라집니다. 모델이 ` ``` ` 대신 `<json>` 안에 씁니다. 그런데 통과는 여전히 0 — 카테고리가 `'출입통제'`, `'출입/보안'`처럼 **보기에 없는 말**이기 때문입니다. 형식은 잡혔는데 **어휘**가 안 잡힌 상태입니다.
- **`prompt_2` (역할):** 카테고리 말이 조금 바뀔 수는 있어도(`'출입/보안'` 등) 여전히 보기 밖이라 통과는 그대로 0입니다. 역할 한 줄은 이 과제의 통과를 바꾸지 못합니다 — 그걸 아는 것도 결과입니다.
- **`prompt_3` (할 일 — 보기 다섯 개·세 개를 정의):** 값이 `'시설'`, `'높음'`으로 **보기 안에 들어오면서 3/3 통과.** 통과를 결정한 건 이 단계입니다. 모델은 보기를 **말해 줘야** 그 안에서 고릅니다.
- **`prompt_4` (예시):** 통과는 그대로입니다. 예시가 값을 바꾸는지는 문의 한 건으로는 알 수 없습니다 — 바뀌더라도 그게 **맞는 방향인지** 판단할 정답이 없기 때문입니다.

그래서 **최종(prompt_4)이 v0보다 좋아진 점**은 둘로 나뉩니다. 확실한 것: 코드가 읽을 수 있고(1단계), 정해진 보기 안에서만 답한다(3단계). 아직 모르는 것: 카테고리·긴급도를 **맞게** 고르는가 — 이건 정답이 있는 20문항으로 재야 하고, 그게 오후 03 노트북입니다. 거기서 효과가 없는 요소(예: 역할)는 빼도 됩니다.

> 위 숫자는 돌릴 때마다 조금씩 다를 수 있습니다. 바뀌지 않는 건 **어느 단계에서 파싱이 되고, 어느 단계에서 보기 안으로 들어오는가**입니다."""),
    M("""### 최종 프롬프트 확인

**▶ 이 셀에서 할 것** — `prompts/prompt_4.txt`를 **파일에서 다시 읽어** 빈 태그나 `TODO`가 남지 않았는지 확인하고, 같은 문의로 3번 돌려 답 전문까지 봅니다. 위 단계의 ✏️ 문장을 고쳤다면 그 셀을 다시 실행한 뒤 이 셀을 실행합니다."""),
    C('''FINAL_PATH = "prompts/prompt_4.txt"      # ✏️ 풀이본과 비교하려면 "solutions/prompts/prompt_4.txt"
v1 = llm.load_prompt(FINAL_PATH)

empty = [t for t in ["역할", "할 일", "출력 형식", "예시"] if re.search(rf"<{t}>\\s*</{t}>", v1)]
if "TODO" in v1 or empty:
    print("=" * 70)
    print("⚠️  최종 프롬프트가 아직 비어 있는 곳이 있습니다:", empty or "TODO 남음")
    print("    3절의 해당 단계 셀을 채우고 다시 실행하세요.")
    print("=" * 70, "\\n")

ok_final, vals_final = try_prompt(v1, doc, n=3)'''),
    M("""**✔ 이 셀의 시사점**
- ⚠️ 경고 없이 바로 system/user가 찍혔다면, 파일에 빈 태그가 없다는 뜻입니다.
- 모델 답이 `<json>{...}</json>` 한 줄로만 나오는지 봅니다. v0의 출력과 비교하면 형식이 얼마나 정리됐는지 보입니다.
- 통과 3/3이어도 긴급도는 회마다 다를 수 있습니다. **형식과 보기를 지키는 것**과 **맞게 고르는 것**은 다른 문제입니다 — 후자는 03에서 정답과 대조해 잽니다."""),
    M("""## 4. 근거를 먼저 적게 한다 — 그리고 그 근거를 어떻게 쓰나
최종 프롬프트에 규칙 하나를 더합니다: **`<json>`을 쓰기 전에 `<근거>`에 왜 그렇게 분류했는지 한 문장을 적어라.** 출력 형식은 그대로입니다 — `parse()`는 `<json>` 안만 읽으므로 `<근거>`가 앞에 붙어도 코드는 안 깨집니다.

근거는 **코드가 아니라 사람이 쓰는 것**입니다. 위의 `doc`과, 정답이 정해진 문의 둘을 `data/tests.jsonl`에서 가져와 돌려 봅니다 — 12번(차분한 말투지만 안전 문제 → 시설·높음)과 8번(급여명세서가 안 옴 → 이 회사 기준으로 인사·**높음**).

여기서 **"정답"은 `tests.jsonl`에 적어 둔 판단 기준**이지 객관적 사실이 아닙니다. 8번의 "높음"은 이 회사가 "급여처럼 돈이 걸린 인사 문제는 높음"으로 정해 둔 것이고, 다른 회사라면 "보통"으로 둘 수도 있습니다. 그래서 모델이 정답과 다르게 답했을 때 할 일은 둘 중 하나입니다 — 근거를 읽고 **프롬프트의 기준을 고치거나**, 그 근거가 더 타당하면 **`tests.jsonl`의 정답을 고치거나.** 어느 쪽이든 근거가 있어야 결정할 수 있습니다.

**▶ 이 셀에서 할 것** — 최종 프롬프트의 system 끝에 근거 규칙(`EVIDENCE`)을 붙여, 세 문의(`doc` · 12번 · 8번)를 한 번씩 보냅니다. 문의마다 **문의 · 근거 · 분류**를 찍고, 정답이 있는 두 문의는 정답과 맞았는지(✓/✗)도 찍습니다."""),
    C('''EVIDENCE = ("\\n\\n<근거 규칙>\\n<json>을 쓰기 전에 <근거>에 이 문의를 그렇게 분류한 이유를 "
            "한 문장으로 적어라.\\n</근거 규칙>")

from src.grade import load_tests
T = {t["id"]: t for t in load_tests()}                         # 정답은 data/tests.jsonl 에 정의된 것을 그대로 쓴다
cases = [(doc, None)] + [
    (T[i]["input"], (T[i]["check"]["category"], T[i]["check"]["urgency"]))
    for i in (12, 8)                                          # 12: 차분한 말투의 안전 문제 · 8: 급여 문제 (이 회사 기준: 높음)
]
for text, answer in cases:
    system, user = build(final, text)
    r = llm.call(user, system=(system or "") + EVIDENCE, max_tokens=1500)
    m = re.search(r"<근거>(.*?)</근거>", r.text, re.S)
    try:
        out = parse(r.text); got = (out.get("카테고리"), out.get("긴급도"))
    except ValueError as e:
        out, got = None, f"파싱 실패: {e}"
    print("문의 :", text)
    print("근거 :", m.group(1).strip() if m else "(없음)")
    print("분류 :", got, "" if answer is None else f"   정답 {answer}  {'✓' if got == answer else '✗'}")
    print()'''),
    M("""**✔ 이 셀의 시사점** — 근거를 이렇게 씁니다:

1. **틀린 답의 원인을 진단한다.** 8번이 ✗이고 근거에 "업무에 즉각적 장애가 되는 긴급 상황은 아니다"라고 적혀 있으면, 모델이 **업무 지장 여부**를 기준으로 판단했고 이 회사의 규칙("돈이 걸린 인사 문제는 높음")은 몰랐다는 게 보입니다. 그러면 고칠 곳이 정해집니다 — `<할 일>`의 긴급도 기준에 그 규칙을 적어 주는 식으로. 이것이 오후 03에서 `prompt_5` → `prompt_6`으로 고쳐 가는 방법입니다.
2. **맞았어도 이유가 엉뚱하면 믿지 않는다.** 분류는 ✓인데 근거가 문의와 상관없는 소리면 운으로 맞은 것이고, 다른 문의에서는 틀립니다.
3. **코드는 근거를 버립니다.** `parse()`는 `<json>`만 읽습니다. 근거는 사람이 디버깅할 때만 열어 보는 것이라, 출력 형식은 그대로 유지됩니다.

최종 프롬프트에 이 규칙을 넣을지는 선택입니다 — 근거를 쓰게 하면 출력 토큰(비용)이 늘고, 그 대신 틀렸을 때 왜 틀렸는지 알 수 있습니다."""),
]

# ============================================================== 03
nb03 = [
    M("""# 03 · 평가
**4세션 · 평가** — 실습 50분

고쳤다는 느낌은 증거가 아닙니다. **같은 문항, 같은 기준, 같은 방법으로** 다시 재야 고친 것입니다.

02에서 만든 최종 프롬프트 **`prompt_4`**를 정답이 있는 20문항에 돌려 점수를 내고(1차), 가장 많이 틀리는 유형 하나를 고쳐 **`prompt_5`**로 저장해 다시 측정하고(2차), 한 번 더 고쳐 **`prompt_6`**(2차 반복)으로 다시 측정합니다. 번호는 02에서 이어집니다.

| 순서 | 할 일 | 시간 |
|---|---|---|
| 1 | 20문항 — 구성표와 통과 조건을 읽는다 | 10분 |
| 2 | 1차 — `prompt_4` 채점, 실패 문항을 직접 연다 | 10분 |
| 3 | 2차 — 한 유형씩 고쳐 `prompt_5` · `prompt_6`, 같은 20문항으로 다시 채점 | 30분 |

**읽는 법** — 실습 셀마다 바로 앞에 **▶ 이 셀에서 할 것**, 바로 뒤에 **✔ 이 셀의 시사점**이 있습니다. 셀을 돌리기 전에 ▶를, 돌린 뒤에 출력과 ✔를 같이 읽습니다."""),
    M("""**▶ 이 셀에서 할 것** — 준비. 공용 도구 `llm`과, 채점 코드 `src/grade.py`에서 이 노트북이 쓰는 함수들을 불러옵니다.
- `load_tests` — 20문항(`data/tests.jsonl`)을 읽는다
- `check` — 모델 답 하나를 통과 조건 하나로 판정한다
- `run` — 프롬프트 하나로 20문항을 전부 돌려 채점한다
- `summarize` · `save` · `print_table` · `print_fails` — 결과를 요약하고, 결과표에 저장하고, 표와 실패 목록을 찍는다"""),
    C(SETUP + '''
from src.grade import load_tests, run, check, summarize, save, print_table, print_fails'''),
    M("""**✔ 이 셀의 시사점**
- 출력의 모델 이름과 `실제 호출`을 확인합니다. 02와 같은 모델이어야 02의 결과와 이어서 비교할 수 있습니다."""),
    M("""## 1. 고정 테스트 20문항
`data/tests.jsonl` — 한 줄에 한 문항. **프롬프트를 고치기 전에 만들고, 고치는 동안 바꾸지 않습니다** (고치는 중간에 문항이 바뀌면 전후 비교가 안 됩니다).

20문항은 3종류로 나뉘어 있고, 종류마다 보려는 게 다릅니다.

| 구성 | 문항 수 | 이 실습의 문항 | 뭘 보려고 넣었나 |
|---|---|---|---|
| 평범한 입력 | 10 | 1–10 | 가장 흔한 문의에서 기본으로 되는지 |
| 경계에 있는 입력 | 7 | 11 구매 요청 · 12 차분한 어투의 위험 신호 · 13 장비 고장 · 14 격한 어투의 예약 시스템 문의 · 15 휴가 중 급여 · 19 영어로 쓴 급여 문의 · 20 사라진 회의실 예약 | 말투·단어·언어에 속지 않고 이 회사 기준대로 판단하는지 |
| 어느 카테고리에도 안 맞는 입력 | 3 | 16 · 17 · 18 | 억지로 짜맞추지 않고 "기타"로 분류하는지 |

여기 적힌 **정답(`check`)은 설계자가 정한 판단 기준**이지 객관적 사실이 아닙니다(02의 4절). 모델이 다르게 답했을 때 프롬프트를 고칠지 정답을 고칠지는 근거를 보고 사람이 정합니다.

| check 필드 | 뜻 |
|---|---|
| `category` | 이 값과 같은 카테고리여야 통과 |
| `urgency` | 이 값과 같은 긴급도여야 통과 |
| `has` | 요약 어딘가에 이 말이 있어야 통과 (없으면 생략) |

**▶ 이 셀에서 할 것** — 20문항을 읽어 종류별 문항 수를 세고, 종류마다 첫 문항 하나씩 **문의 본문과 통과 조건(`check`)**을 찍습니다. 모델은 부르지 않습니다."""),
    C('''tests = load_tests()

# 종류별로 문항이 몇 개인지 센다
group_counts = {}
for test in tests:
    group = test["group"]
    if group not in group_counts:
        group_counts[group] = 0
    group_counts[group] = group_counts[group] + 1
print("종류별 문항 수:", group_counts)
print()

# 종류마다 첫 문항 하나씩 — 문의 본문과 정답 조건(check)이 어떻게 적혀 있는지 본다
for group in ["평범", "경계", "기타"]:
    for test in tests:
        if test["group"] == group:
            print(f"[{group}] #{test['id']}  {test['input']}")
            print(f"        check = {test['check']}")
            print()
            break                  # 이 종류의 첫 문항만 보고 다음 종류로'''),
    M("""**✔ 이 셀의 시사점**
- 종류별 문항 수가 위 표대로 10 · 7 · 3인지 확인합니다.
- `check`에 적힌 `category` · `urgency` (· `has`)가 곧 **채점 기준**입니다. 위 표의 설명이 실제 파일에서는 이런 모양으로 적혀 있습니다."""),
    M("""## 2. check — 판정 규칙
`check(출력, 통과 조건)` → `(통과 여부, 실패 유형, 설명)`. 판정 순서: **형식 위반 → 지어냄 → 지시 일부 누락 → 사실 오류** — 앞에서 걸리면 거기서 멈춥니다.

**▶ 이 셀에서 할 것** — 여기서 시험받는 것은 **모델이 아니라 채점 코드 `check()`**입니다. 모델은 부르지 않습니다. 사람이 일부러 틀리게 써 둔 **가짜 답 6개**를 `check()`에 하나씩 넣고, 가짜 답마다 "나와야 할 판정"과 "`check()`가 실제로 낸 판정"을 나란히 찍습니다. 둘이 같으면 ✓, 다르면 ✗입니다."""),
    C('''# 채점 코드 check()를 먼저 시험한다 — 모델은 부르지 않는다.
# 사람이 일부러 틀리게 써 둔 가짜 답을 넣어, check()가 맞는 판정을 내는지 본다.

spec_1 = tests[0]["check"]      # 1번 문항의 정답 조건 — IT · 보통 · 요약에 "비밀번호"가 있어야 함
spec_16 = tests[15]["check"]    # 16번 문항의 정답 조건 — 기타 · 낮음

# 가짜 답 하나에 네 가지를 적는다: 이름 · 어느 문항 기준으로 채점할지 · 가짜 답 글자 · 나와야 할 판정
fake_answers = [
    {"name": "정상",
     "spec": spec_1,
     "answer": '{"카테고리": "IT", "긴급도": "보통", "요약": "비밀번호 재설정 요청"}',
     "should_be": "통과"},
    {"name": "코드 블록으로 감쌈",
     "spec": spec_1,
     "answer": '```json\\n{"카테고리": "IT", "긴급도": "보통", "요약": "비밀번호 재설정 요청"}\\n```',
     "should_be": "형식 위반"},
    {"name": "보기에 없는 카테고리",
     "spec": spec_1,
     "answer": '{"카테고리": "기술지원", "긴급도": "보통", "요약": "비밀번호 재설정 요청"}',
     "should_be": "형식 위반"},
    {"name": "요약에 필수 단어 없음",
     "spec": spec_1,
     "answer": '{"카테고리": "IT", "긴급도": "보통", "요약": "로그인 문제 접수"}',
     "should_be": "지시 일부 누락"},
    {"name": "카테고리가 정답과 다름",
     "spec": spec_1,
     "answer": '{"카테고리": "비품", "긴급도": "보통", "요약": "비밀번호 재설정 요청"}',
     "should_be": "사실 오류"},
    {"name": "기타여야 하는데 지어냄",
     "spec": spec_16,
     "answer": '{"카테고리": "인사", "긴급도": "낮음", "요약": "워크숍 일정 문의"}',
     "should_be": "지어냄"},
]

number = 1
for fake in fake_answers:
    ok, kind, why = check(fake["answer"], fake["spec"])   # ← 여기서 check()가 실행된다
    if ok:
        judged = "통과"
    else:
        judged = kind

    if judged == fake["should_be"]:
        mark = "✓ check()가 맞게 채점함"
    else:
        mark = "✗ check()가 틀리게 채점함 — 채점 코드를 고쳐야 한다"

    print(f"[{number}] {fake['name']}")
    print(f"    가짜 답          : {fake['answer']}")
    print(f"    나와야 할 판정   : {fake['should_be']}")
    print(f"    check()가 낸 판정: {judged}  {why}")
    print(f"    → {mark}")
    print()
    number = number + 1'''),
    M("""**✔ 이 셀의 시사점**
- 여섯 개 모두 ✓면, 채점 코드가 네 가지 실패(형식 위반 · 지어냄 · 지시 일부 누락 · 사실 오류)를 의도대로 가른다는 뜻입니다.
- 모델을 채점하기 **전에** 채점 코드부터 시험하는 이유: 채점 코드가 틀리면 그 뒤에 나오는 모델 점수가 전부 틀립니다. 시험지를 채점하기 전에 정답지부터 검사하는 것과 같습니다.
- "check()가 낸 판정" 뒤에 붙은 설명을 봅니다. 실제 채점에서도 실패 문항마다 이런 설명이 붙어, 왜 실패로 판정했는지 알 수 있습니다."""),
    M("""## 3. 1차 · `prompt_4` 채점
02에서 만든 최종 프롬프트 `prompts/prompt_4.txt`를 20문항에 돌립니다. 02를 아직 안 돌려 파일이 없으면 아래 셀이 **풀이본으로 대신 돌리고 그렇다고 알려 줍니다** — 흐름을 먼저 보고, 02를 돌린 뒤 다시 오면 됩니다.

**▶ 이 셀에서 할 것** — `prompt_4`로 20문항을 한 번씩 돌려 채점하고, 결과를 `results/scoreboard.csv`에 한 줄 저장합니다. 이어서 통과 수 · 실패 유형별 개수 · 실패 문항 목록을 찍습니다."""),
    C('''P4 = Path("prompts/prompt_4.txt")
if not P4.exists():
    print("※ prompts/prompt_4.txt 가 없습니다 (02 노트북을 아직 안 돌림). 풀이본 solutions/prompts/prompt_4.txt 로 대신 돌립니다.\\n")
    P4 = Path("solutions/prompts/prompt_4.txt")

# run()은 세 가지를 돌려준다 — 통과 수 · 실패 목록 [(문항 번호, 실패 유형), …] · 문항별 상세 결과
passed_4, fails_4, rows_4 = run(str(P4), detail=True)
summary_4 = summarize(rows_4, llm.MODEL)
save(str(P4), llm.MODEL, rows_4, summary_4, note="1차 · prompt_4")
print(f"통과 {passed_4} / {len(rows_4)}")

# 실패를 유형별로 센다
kind_counts = {}
for fail in fails_4:
    kind = fail[1]                 # fail = (문항 번호, 실패 유형)
    if kind not in kind_counts:
        kind_counts[kind] = 0
    kind_counts[kind] = kind_counts[kind] + 1
print("실패 유형별 개수:", kind_counts)

print_fails(rows_4)'''),
    M("""**✔ 이 셀의 시사점**
- 02에서 문의 하나로 3/3 통과하던 프롬프트도, 정답이 있는 20문항에서는 틀리는 문항이 나올 수 있습니다. 02의 "통과"는 형식과 보기만 확인한 것이고, **맞게 골랐는지**는 여기서 처음 잽니다.
- "실패 유형별 개수" 줄에서 실패가 **어느 유형에 몰리는지** 봅니다. 4절에서 고칠 대상이 이 유형입니다.
- 실패 문항의 **정답**을 보면 이 회사만의 기준이 드러납니다. 강사가 네 번 돌렸을 때 통과는 13~14 / 20이었고, 매번 #2(토너 부족 → 낮음) · #8 · #15 · #19(급여 문제 → 높음)의 긴급도와 #14 · #20(예약 시스템 → 시설)의 카테고리가 틀렸습니다. (한 번은 #9도 틀렸습니다 — 매번 틀리는 문항과 가끔 틀리는 문항은 구분해서 봅니다.) 모델이 일반 상식으로 판단해서 틀린 것이라, 이 회사의 기준을 프롬프트에 **적어 줘야** 고쳐집니다.
- 실패 목록에서 실패가 어느 **종류**(평범 · 경계 · 기타)에 몰리는지도 봅니다."""),
    M("""### 실패 문항을 직접 연다
통과 수만 보면 **새로 생긴 실패**를 놓칩니다. 실패 문항의 출력을 열어 유형이 맞는지 사람이 확인합니다.
(사실 오류는 코드가 카테고리·긴급도 문자열만 비교해 판정합니다 — 애매한 경우엔 사람이 다시 봅니다.)

**▶ 이 셀에서 할 것** — 실패 문항 하나(기본값: 첫 번째 실패)를 골라 **문의 · 정답 조건 · 판정 · 모델이 쓴 답 원문**을 찍습니다. ✏️ `FAIL_ID`를 바꿔 다른 문항도 열어 봅니다."""),
    C('''ROWS_TO_OPEN = rows_4           # ✏️ 어느 채점 결과에서 열지 — 4절 뒤에는 rows_5 · rows_6도 된다

# ✏️ 보고 싶은 문항 번호 — 기본값은 첫 번째로 실패한 문항
if len(fails_4) > 0:
    first_fail = fails_4[0]       # (문항 번호, 실패 유형)
    FAIL_ID = first_fail[0]
else:
    FAIL_ID = 1

# 문항 번호로 문항(문의 · 정답 조건)과 채점 결과(판정 · 모델 답)를 찾는다
for test in tests:
    if test["id"] == FAIL_ID:
        chosen_test = test
for row in ROWS_TO_OPEN:
    if row["id"] == FAIL_ID:
        chosen_row = row

if chosen_row["ok"]:
    verdict = "통과"
else:
    verdict = f"{chosen_row['kind']} — {chosen_row['why']}"

print(f"#{FAIL_ID} [{chosen_row['group']}]")
print("문의      :", chosen_test["input"])
print("정답 조건 :", chosen_test["check"])
print("판정      :", verdict)
print()
print("모델이 쓴 답 원문:")
print(chosen_row["text"])'''),
    M("""**✔ 이 셀의 시사점**
- 판정 설명(예: "긴급도 기대 '낮음', 출력 '보통'")과 모델 출력 원문을 대조해, **판정이 맞는지 사람이 확인합니다.**
- 모델이 틀린 것인지, 정답(`check`)이 애매한 것인지도 여기서 가립니다. 정답이 애매하면 `tests.jsonl`을 고칠 일이지 프롬프트를 고칠 일이 아닙니다(02의 4절)."""),
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
| 사실 오류 | 카테고리 · 긴급도 판단 기준을 더 구체적으로 — 02의 4절에서 본 **근거**가 어디를 고칠지 알려 준다 |"""),
    M("""### 1차에서 무엇이 틀렸나 — 진단
강사가 돌렸을 때 1차(`prompt_4`)의 실패 6개는 모두 **사실 오류**였습니다. 실패 문항을 하나씩 열어 보고, 02의 4절처럼 근거를 쓰게 해서 모델이 **왜** 그렇게 답했는지도 받아 봤습니다.

| 문항 | 문의 | 정답 | 모델 답 | 모델이 댄 근거 (요약) |
|---|---|---|---|---|
| #2 | 프린터 토너가 다 떨어졌습니다 | 비품 · **낮음** | 비품 · 보통 | 긴급 장애가 아니라 주문 요청이라 보통 |
| #8 | 급여명세서가 메일로 안 왔습니다 | 인사 · **높음** | 인사 · 보통 | 업무에 즉각적 지장이 크지 않아 보통 |
| #15 | 출산휴가 중 급여가 적게 들어온 것 같아요 | 인사 · **높음** | 인사 · 보통 | 급여 관련이라 인사 (긴급도 이유는 적지 않음) |
| #19 | Overtime pay … missing from my payslip | 인사 · **높음** | 인사 · 보통 | 금전 손해가 있지만 보통 |
| #14 | 회의실 예약 시스템이 너무 느려서… | **시설** · 보통 | IT · 보통 | 예약 시스템은 소프트웨어라 IT |
| #20 | 회의실 예약해 둔 게 시스템에서 사라졌어요 | **시설** · 보통 | IT · 높음 | 예약 시스템 장애라 IT |

**공통 원인 — 모델은 이 회사의 기준을 모른 채 일반 상식으로 판단했습니다.**
- 긴급도: `prompt_4`의 지시는 `- 긴급도: 높음 · 보통 · 낮음` 한 줄뿐입니다. 보기 이름만 있고 **무엇을 높음 · 낮음으로 볼지 기준이 없습니다.** 그래서 모델은 근거에 적힌 대로 "업무가 당장 멈췄나"라는 상식으로 골랐고, 이 회사가 정해 둔 "급여 문제는 높음 · 소모품 부족은 낮음"과 어긋났습니다.
- 카테고리: "회의실 예약 시스템은 총무팀(시설) 소관"이라는 이 회사의 규칙이 프롬프트에 없습니다. 그래서 "시스템"이 들어간 문의를 상식대로 IT로 봤습니다.

**고칠 순서:** 실패 6개 중 4개가 긴급도이므로 **긴급도부터** 고칩니다(`prompt_5`). 카테고리는 그다음입니다(`prompt_6`). 한 번에 하나만 고쳐야, 결과가 바뀌었을 때 무엇 때문인지 압니다.

> 위 표는 강사 실행 결과입니다. 내 1차 결과의 실패 목록과 비교해 봅니다 — 대부분 같고, 가끔 흔들리는 문항(#9 등)이 더 끼어 있을 수 있습니다.

**▶ 이 셀에서 할 것** — 풀이본 `prompt_4`와 `prompt_5` 파일을 줄 단위로 비교해, **빠진 줄(-)과 새로 생긴 줄(+)만** 찍습니다. 비교하는 함수 `show_changes()`는 아래 `prompt_6`에서도 다시 씁니다."""),
    C('''def show_changes(old_path, new_path):
    """두 프롬프트 파일을 줄 단위로 비교해, 빠진 줄(-)과 새로 생긴 줄(+)만 찍는다."""
    old_lines = llm.load_prompt(old_path).splitlines()
    new_lines = llm.load_prompt(new_path).splitlines()
    print(old_path, "→", new_path)
    print()
    print("빠진 줄 (-)")
    for line in old_lines:
        if line not in new_lines:
            print("  -", line)
    print()
    print("새로 생긴 줄 (+)")
    for line in new_lines:
        if line not in old_lines:
            print("  +", line)


show_changes("solutions/prompts/prompt_4.txt", "solutions/prompts/prompt_5.txt")'''),
    M("""**✔ 이 셀의 시사점** — 바꾼 곳은 `<할 일>`의 **긴급도 한 줄**뿐입니다. 보기 이름만 있던 그 한 줄을, 이 회사의 기준을 적은 네 줄로 바꿨습니다. 각 줄이 무엇을 겨냥하는지는 이렇습니다.

| 새로 생긴 줄 | 겨냥한 문항 |
|---|---|
| 이 회사의 기준으로 판단한다. 말투나 일반적인 느낌과 다를 수 있다. | 전체 — 모델이 상식 대신 아래 기준을 따르게 한다 |
| 높음: … **급여(명세서 포함)처럼 돈이 걸린 인사 문제** | #8 · #15 · #19 |
| 낮음: **소모품이 떨어진 것**(토너 · 마카 · 종이 등) | #2 (#6 마카도 같은 기준) |
| 낮음: 조명 깜빡임처럼 당장 지장 없는 사소한 불편 | #3 — 1차에서는 통과했지만, 강사가 이 문구 없이 시험했을 때 #3이 보통으로 틀려서 함께 넣었다 |
| 낮음: "급한 건 아니다"라고 직접 말한 것, 방법 · 일정을 묻는 단순 문의 | #11 · #4 — 1차에서도 맞았지만, 긴급도 기준을 새로 쓰면서 이미 맞던 문항이 깨지지 않게 적었다 |
| 보통: 위 둘에 해당하지 않는 것 | 기준에 없는 나머지 |

카테고리 줄은 건드리지 않았습니다. 그래서 `prompt_5`로 채점해도 **#14 · #20(카테고리)은 그대로 틀릴 것**으로 예상합니다. 아래 셀에서 확인합니다."""),
    M("""아래 셀은 기본값으로 **풀이본 `prompt_5`**(긴급도에 이 회사의 기준을 적음 — 급여 문제는 높음, 소모품 부족·사소한 불편은 낮음)를 돌립니다. 내 `prompt_5`를 만들었으면 경로와 NOTE를 바꾸세요.

**▶ 이 셀에서 할 것** — `prompt_5`로 같은 20문항을 다시 채점해 결과표에 한 줄 저장하고, `prompt_4`와 나란히 놓은 표를 찍습니다. 마지막 줄에 **새로 통과한 문항 번호와 새로 실패한 문항 번호**를 찍습니다."""),
    C('''P5 = "solutions/prompts/prompt_5.txt"      # ✏️ 내 것: "prompts/prompt_5.txt"
NOTE = "긴급도: 이 회사 기준(급여는 높음 · 소모품 부족은 낮음)을 적음"   # ✏️ 무엇을 바꿨는지 한 줄 — 결과표에 남는다

passed_5, fails_5, rows_5 = run(P5, detail=True)
summary_5 = summarize(rows_5, llm.MODEL)
save(P5, llm.MODEL, rows_5, summary_5, note=NOTE)
print_table([("prompt_4", llm.MODEL, summary_4), ("prompt_5", llm.MODEL, summary_5)])

# 문항마다 prompt_4와 prompt_5의 결과를 나란히 비교한다 (두 결과 모두 1번부터 20번 순서)
newly_passed = []
newly_failed = []
for index in range(len(rows_4)):
    before = rows_4[index]
    after = rows_5[index]
    if not before["ok"] and after["ok"]:
        newly_passed.append(after["id"])
    if before["ok"] and not after["ok"]:
        newly_failed.append(after["id"])
print()
print("새로 통과:", newly_passed, "  새로 실패:", newly_failed)'''),
    M("""**✔ 이 셀의 시사점**
- 고치려던 유형(여기서는 긴급도의 사실 오류)이 줄었는지 표에서 봅니다. 강사가 돌렸을 때는 세 번 모두 18 / 20 — 긴급도 실패가 모두 사라지고 #14 · #20(카테고리)만 남았습니다.
- 통과 수만 보지 말고 **"새로 실패"**를 봅니다. 하나를 고치면 전에 맞던 문항이 깨질 수 있습니다. 새로 실패한 문항이 있으면 위 "실패 문항을 직접 연다" 셀에서 `ROWS_TO_OPEN = rows_5`, `FAIL_ID = 그 번호`로 바꿔 다시 실행해 원인을 봅니다.
- 통과 수 차이가 1~2개뿐이면 프롬프트 효과가 아니라 흔들림일 수도 있습니다(01 "같은 질문 다섯 번"). 같은 프롬프트를 한 번 더 돌려 보면 가릴 수 있습니다."""),
    M("""### 2차를 한 번 더 → `prompt_6`
**2차에서 남은 문제:** 강사가 돌렸을 때 `prompt_5`는 18 / 20이었습니다. 긴급도 실패는 모두 사라지고, 예상대로 **#14 · #20(정답 시설, 모델 답 IT)**만 남았습니다. `prompt_5`에서도 모델은 #14에 "회의실 예약 시스템의 속도 저하는 IT 시스템 문제"라는 근거를 댔습니다.

원인은 카테고리 정의에 있습니다. `prompt_4`부터 그대로인 정의는 `IT(컴퓨터·네트워크·계정·장비 고장)`, `시설(냉난방·조명·주차장·건물 설비)`뿐이라, "시스템"이 들어간 문의를 IT로 보는 것이 상식적으로 자연스럽습니다. 하지만 이 회사에서는 회의실 예약 시스템을 총무팀이 관리하므로 **시설**입니다 — 이 규칙이 프롬프트에 없습니다.

**고친 것:** 카테고리 줄 바로 아래에 이 회사의 규칙을 한 줄 더했습니다. 02에서 쓴 출입카드 문의도 같은 규칙에 해당합니다.

**▶ 이 셀에서 할 것** — 위에서 만든 `show_changes()`로 `prompt_5`와 `prompt_6`을 비교해, 새로 생긴 줄을 찍습니다."""),
    C('''show_changes("solutions/prompts/prompt_5.txt", "solutions/prompts/prompt_6.txt")'''),
    M("""**✔ 이 셀의 시사점**
- 빠진 줄은 없고, 새로 생긴 줄은 하나입니다 — "회의실·주차 예약 시스템, 출입카드처럼 **총무팀이 관리하는 건물 시스템**은 IT가 아니라 시설이다." #14 · #20을 겨냥합니다.
- 긴급도 기준은 `prompt_5` 그대로 두었습니다. 그래서 아래 결과에서 긴급도 쪽 문항이 다시 틀리면, 이번에 넣은 한 줄이 원인일 수 있다고 좁혀 볼 수 있습니다."""),
    M("""**▶ 이 셀에서 할 것** — `prompt_6`으로 같은 20문항을 다시 채점해 결과표에 저장하고, `prompt_4` · `prompt_5` · `prompt_6` 세 줄을 나란히 찍은 뒤 남은 실패 문항을 찍습니다."""),
    C('''P6 = "solutions/prompts/prompt_6.txt"      # ✏️ 내 것: "prompts/prompt_6.txt"
NOTE = "카테고리: 총무팀이 관리하는 건물 시스템(예약·출입카드)은 시설"

passed_6, fails_6, rows_6 = run(P6, detail=True)
summary_6 = summarize(rows_6, llm.MODEL)
save(P6, llm.MODEL, rows_6, summary_6, note=NOTE)
print_table([("prompt_4", llm.MODEL, summary_4), ("prompt_5", llm.MODEL, summary_5), ("prompt_6", llm.MODEL, summary_6)])
print_fails(rows_6)'''),
    M("""**✔ 이 셀의 시사점**
- 세 줄을 비교해 **어느 수정이 어느 유형을 줄였는지** 봅니다. 한 번에 하나씩 고쳤기 때문에 이렇게 나눠 볼 수 있습니다.
- 표 아래에 실패 목록이 찍히지 않았다면 20문항을 모두 통과한 것입니다.
- **1건 비용** 칸도 봅니다. 기준을 덧붙이면 프롬프트가 길어져 입력 토큰이 늘고, 1건 비용이 오를 수 있습니다. 통과가 늘어난 만큼의 값어치가 있는지가 판단 거리입니다."""),
    M("""**발표 — 한 문장으로**
> "___ 유형을 줄이려고 ___를 바꿨더니 통과가 __ → __ 가 됐고, 대신 ___ 가 생겼다(또는 생기지 않았다)."
"""),
    M("""## 5. 결과표
`results/scoreboard.csv`에 실행할 때마다 한 줄씩 쌓입니다. 엑셀로 열어도 됩니다. "바꾼 것" 칸에 NOTE가 들어가므로, 나중에 봐도 **어느 줄이 어떤 수정의 결과인지** 알 수 있습니다.

**▶ 이 셀에서 할 것** — `results/scoreboard.csv`의 마지막 8줄을 찍습니다. 줄이 아직 적으면 맨 앞에 칸 이름 줄도 함께 보입니다."""),
    C('''import csv
with open("results/scoreboard.csv", encoding="utf-8-sig") as scoreboard_file:
    all_lines = list(csv.reader(scoreboard_file))   # 파일의 모든 줄 — 한 줄이 칸들의 목록

last_lines = all_lines[-8:]                          # 뒤에서 8줄
for line in last_lines:
    print(" | ".join(line))'''),
    M("""**✔ 이 셀의 시사점**
- 방금 돌린 1차(`prompt_4`) · 2차(`prompt_5` · `prompt_6`)가 한 줄씩 쌓여 있습니다. 노트북을 다시 돌리면 그 줄이 또 쌓입니다.
- 맨 끝 "바꾼 것" 칸에 NOTE가 남아 있어, 숫자만 봐도 어떤 수정의 결과인지 알 수 있습니다. 이 표가 "고쳤다"는 주장의 증거입니다."""),
    M("""## 내일 가지고 올 것
- `prompt_6.txt` · `tests.jsonl` · `grade.py` · 결과표(`results/scoreboard.csv`)"""),
]

if __name__ == "__main__":
    NB.mkdir(exist_ok=True)
    for name, cells in [("01_api_basics", nb01), ("02_prompt_design", nb02),
                        ("03_evaluation", nb03)]:
        nbf.write(nb(cells), NB / f"{name}.ipynb")
        print("작성:", f"notebooks/{name}.ipynb", len(cells), "셀")

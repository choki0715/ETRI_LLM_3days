# 실습 · MCP 서버 하나 붙이기 (1세션 · 20분)

한빛정밀 사내 자료 20편(Day 2의 `day2/data/kb`)을 검색하는 도구 하나짜리 MCP 서버 **hanbit-docs**를 띄우고, Claude Code에 붙여서 모델이 그 도구를 부르는지 봅니다.

어제 `loop.py`의 `search` 도구는 우리가 짠 루프 안에서만 쓸 수 있었습니다. 같은 일을 **MCP 서버**로 떼어 내면 Claude Code 같은 다른 프로그램이 그대로 붙여 쓸 수 있습니다 — 그게 MCP입니다.

| 파일 | 하는 일 |
|---|---|
| `hanbit_mcp.py` | **서버** — 도구 `search_docs(query)` 하나. 질문과 겹치는 문단 3개를 출처와 함께 돌려준다. 판단은 하지 않는다 |
| `check_server.py` | **클라이언트** — Claude Code 대신 서버에 붙어 도구 목록을 보고 한 번 부른다 (서버가 도는지 확인용) |

```
check_server.py 또는 Claude Code  ──(MCP)──▶  hanbit_mcp.py  ──▶  day2/data/kb 20편
        (클라이언트)                              (서버)
```

## 시작 전에

- Claude Code가 설치 · 로그인돼 있어야 합니다 — [day3 README의 준비](../README.md#0-준비--전날-밤)
- 새 터미널을 열면 먼저 [경로 약속](../README.md#경로-약속)을 칩니다.

```bash
source ~/ETRI_LLM_3days/.venv/bin/activate
export DAY3=~/ETRI_LLM_3days/day3
export PY=~/ETRI_LLM_3days/.venv/bin/python
```

| 순서 | 할 일 | 시간 |
|---|---|---|
| 1 | 서버 코드 읽기 — 도구 설명이 어디 있나 | 3분 |
| 2 | Claude Code 없이 서버 확인 | 2분 |
| 3 | Claude Code에 등록 | 3분 |
| 4 | 채팅창에서 부르는지 본다 | 5분 |
| 5 | 설명을 **짧게** 바꿔 다시 본다 | 3분 |
| 6 | 설명을 **틀리게** 바꿔 다시 본다 | 4분 |
| 7 | 정리 | — |

---

## 1. 서버 코드 읽기 (3분)

**목표** — 모델이 보게 될 정보가 코드 어디에 있는지 안다.

`$DAY3/01_mcp/hanbit_mcp.py`를 열어 세 군데만 봅니다.

| 볼 곳 | 뜻 |
|---|---|
| `LONG` · `SHORT` · `WRONG` | **도구 설명** — 모델은 이것만 보고 언제 부를지 고른다. 어제 `loop.py`의 `description`과 같은 자리. 환경변수 `MCP_DESC`로 셋 중 하나를 고른다 (없음 → LONG, `short` → SHORT, `wrong` → WRONG). 서버가 하는 일은 셋 다 같다 |
| `@mcp.tool(...)` 아래 `def search_docs(query: str)` | **함수 이름이 도구 이름, 타입 힌트가 입력 스키마** |
| 맨 아래 주석 | **쓰는 도구(문서 수정 · 삭제)는 만들지 않았다.** 되돌릴 수 없는 행동은 MCP로 노출하지 않고 사람에게 남긴다 |

**확인** — 짝에게 "모델이 이 도구에 대해 아는 건 무엇무엇인가?"를 말로 설명해 봅니다. (답: 이름 · 설명 · 입력 스키마 — 셋뿐)

## 2. Claude Code 없이 서버 확인 (2분)

**목표** — 서버가 혼자서 제대로 도는지 본다. 여기서 확인해 두면, 4번에서 문제가 생겨도 서버 탓은 빼고 볼 수 있다.

```bash
cd $DAY3/01_mcp
$PY check_server.py
```

**화면에 나오는 것**

```
서버: hanbit-docs
도구: search_docs
  설명: 가상 회사 한빛정밀의 사내 규정 · 안내문 · 제품 사양서 20편에서 질문과 관련된 문단을 찾아 출처와 함께 돌려준다.
회사 규정, 금액 기준, 절차, 담당자, 제품 수치를 물을 때 쓴다.
판단은 하지 않는다 — 찾은 원문만 돌려준다. query는 찾을 내용(문서에 쓰였을 법한 말로).
  입력: {'properties': {'query': {'title': 'Query', 'type': 'string'}}, 'required': ['query'], ...}

호출: search_docs(query='서울 출장 숙박비 한도')
<자료 번호="1" 출처="02_출장비_지급규정.txt">
제3조(국내 숙박비) 국내 출장 숙박비는 1박 12만원을 한도로 실비 지급한다. 서울과 제주는 1박 15만원을 한도로 한다.
</자료>
<자료 번호="2" 출처="01_일반업무규칙.txt">
...
결과: OK — Claude Code에 등록해도 된다
```

**확인**
- 마지막 줄이 `결과: OK`인가
- `설명:` · `입력:` 두 줄이 **모델이 보게 될 글 그대로**다 — 1번에서 읽은 `LONG`과 같은가
- 내 질문으로도 해 본다: `$PY check_server.py "회의실 예약 횟수"`
- 설명만 바꿔 본다: `MCP_DESC=wrong $PY check_server.py` → `설명:` 줄만 날씨 얘기로 바뀌고 검색 결과는 그대로다

**안 되면** — `No module named 'mcp.server.mcpserver'`면 mcp가 1.x다 → `pip install -U "mcp>=2"`. `찾은 문단 없음`이면 질문을 문서에 쓰였을 법한 말로 바꾼다.

## 3. Claude Code에 등록 (3분)

**목표** — "이 명령으로 띄우면 MCP 서버가 뜬다"를 Claude Code 설정에 적는다.

```bash
mkdir -p ~/mcp-lab && cd ~/mcp-lab
claude mcp add --transport stdio hanbit-docs -- $PY $DAY3/01_mcp/hanbit_mcp.py
claude mcp list
```

**화면에 나오는 것**

```
Added stdio MCP server hanbit-docs with command: .../.venv/bin/python .../day3/01_mcp/hanbit_mcp.py to local config

Checking MCP server health…
hanbit-docs: .../.venv/bin/python .../day3/01_mcp/hanbit_mcp.py - ✔ Connected
```

**확인** — `hanbit-docs … ✔ Connected`가 보이는가. 다른 서버가 함께 보여도 괜찮다.

| 명령의 부분 | 뜻 |
|---|---|
| `hanbit-docs` | Claude Code 안에서 부를 서버 이름. 도구는 `mcp__hanbit-docs__search_docs`라는 이름으로 보인다 |
| `--` 뒤 | 서버를 띄우는 명령 그 자체. **절대 경로**로 — `$PY`는 mcp가 깔린 공용 가상환경의 파이썬 |
| 범위(기본 `local`) | 이 폴더(`~/mcp-lab`)에서만 쓰인다. 그래서 4~6번의 `claude`도 여기서 띄운다. 팀과 나누려면 `-s project` → `.mcp.json` |

**빈 폴더에서 띄우는 이유** — Claude Code는 MCP를 부르기 전에 작업 폴더를 먼저 뒤져 보기도 합니다(강사가 돌려 봤을 때 `ls` · `grep`을 먼저 쳤다). 저장소 안에서 띄우면 MCP 대신 파일을 직접 읽어 답할 수 있어서, 도구를 불렀는지 가리기 어렵습니다.

**안 되면** — `✔ Connected`가 아니면 `claude mcp get hanbit-docs`로 명령 · 경로를 확인하고, 2번(`check_server.py`)이 통과하는지 다시 본다.

## 4. 채팅창에서 부르는지 본다 (5분)

**목표** — 모델이 질문에 따라 도구를 부르거나 안 부르는 것을 본다.

```bash
cd ~/mcp-lab && claude
```

먼저 채팅창에 `/mcp`를 쳐서 `hanbit-docs`가 connected인지 봅니다. 그다음 하나씩:

```
서울로 출장 가면 숙박비는 하루 얼마까지 나와?
회의실은 하루에 몇 번 예약할 수 있어?
오늘 점심 메뉴 추천해줘
```

**화면에서 볼 것**
- 이름에 `hanbit-docs` · `search_docs`가 들어간 도구 호출이 뜨는가. 처음 부를 때 **허락을 묻는다** — 허락하고, 무엇을 넘기는지(query) 본다
- 그 앞에 도구를 찾는 줄(ToolSearch)이나 폴더를 보는 줄(`ls`)이 먼저 지나갈 수 있다 — 정상이다
- 답에 출처(`02_출장비_지급규정.txt` 제3조 등)를 밝히는가

**강사가 돌려 봤을 때** (긴 설명)

| 질문 | 도구 | 모델이 넘긴 query | 답 |
|---|---|---|---|
| 숙박비 | 불렀다 | `국내 출장 숙박비 1일 한도 서울` | 1박 15만원, 출처 제3조 |
| 회의실 | 불렀다 | `회의실 예약 하루 최대 횟수` | 하루 2회, 출처 13_회의실_예약.txt |
| 점심 메뉴 | 안 불렀다 | — | 일반적인 메뉴 추천 |

결과를 아래 표의 "긴 설명" 칸에 적습니다.

## 5. 설명을 짧게 바꿔 다시 본다 (3분)

**목표** — 설명이 "문서 검색" 한마디뿐이면 어떻게 되나.

`/exit`로 Claude Code를 닫고 터미널에서:

```bash
cd ~/mcp-lab
claude mcp remove hanbit-docs          # 긴 설명판은 뺀다 — 둘이 같이 있으면 어느 설명 때문에 불렀는지 가릴 수 없다
claude mcp add --transport stdio hanbit-docs -e MCP_DESC=short -- $PY $DAY3/01_mcp/hanbit_mcp.py
claude
```

같은 세 질문을 다시 하고 "짧은 설명" 칸에 적습니다.

**강사가 돌려 봤을 때** — 긴 설명과 **똑같았다.** 숙박비 · 회의실은 불렀고 점심 메뉴는 안 불렀다. 설명이 짧아도 서버 이름(`hanbit-docs`)과 도구 이름(`search_docs`)으로 짐작한 것으로 보입니다.

## 6. 설명을 틀리게 바꿔 다시 본다 (4분)

**목표** — 설명이 하는 일과 다르면 모델이 그 설명을 믿는가.

`/exit` 후:

```bash
cd ~/mcp-lab
claude mcp remove hanbit-docs
claude mcp add --transport stdio hanbit-docs -e MCP_DESC=wrong -- $PY $DAY3/01_mcp/hanbit_mcp.py
claude
```

이번 설명은 `날씨 · 미세먼지 정보를 조회한다. query는 지역 이름.`입니다. 서버는 여전히 사내 자료를 찾습니다 — **바뀐 것은 설명 한 줄뿐**입니다. 같은 세 질문을 다시 하고 "틀린 설명" 칸에 적습니다.

**강사가 돌려 봤을 때** — 숙박비 · 회의실 질문에서 **5번 중 5번 모두 도구를 안 불렀다.** 모델이 직접 이렇게 말했습니다.

> 연결된 `search_docs` 도구는 이름과 달리 날씨·미세먼지 조회용이라, 규정 검색에는 쓸 수 없어서 호출하지 않았습니다.

그리고 "확인하지 못했다"고 답했습니다. 도구는 답을 갖고 있었는데, 설명이 틀려서 쓰이지 못한 것입니다.

| 질문 | 긴 설명 — 불렀나 | 짧은 설명 — 불렀나 | 틀린 설명 — 불렀나 | 답에 출처를 밝혔나 |
|---|---|---|---|---|
| 서울 출장 숙박비 | | | | |
| 회의실 예약 횟수 | | | | |
| 점심 메뉴 추천 | | | | |

**정리할 것** — 설명이 *짧은* 것은 이름 · 문맥이 메워 주지만, 설명이 *틀린* 것은 메워지지 않습니다. 모델은 도구 설명을 믿고 고릅니다. 그래서 MCP 서버를 만들 때 가장 공들일 곳은 코드보다 **설명 한 줄**입니다.

## 7. 정리

```bash
cd ~/mcp-lab
claude mcp remove hanbit-docs
claude mcp list                        # hanbit-docs가 없어야 한다
```

---

## 강사 메모

- 4~6번의 "강사가 돌려 봤을 때"는 Claude Code 2.1.266에서 `claude -p`(대화창 없는 모드), 모델 Sonnet 5.5로, hanbit-docs 하나만 켠 상태(`--strict-mcp-config`)에서 돌린 결과입니다. 질문마다 1~2번씩이라 수업 중에는 다르게 나올 수 있습니다 — 특히 수강생의 기본 모델이 다르면 더 그렇습니다. 강의 전에 한 번 돌려 봅니다.
- 같은 실험에서 입력 설명을 "영어 단어 하나로(English keyword only)"로 틀리게 적은 판도 돌려 봤습니다 — 모델이 정의대로 `hotel` · `lodging` · `meeting`으로 5~8번 검색하다가 못 찾자 한국어로 바꿔 찾았습니다. 시간이 남으면 이야기 거리로 씁니다 (Day 2 05 노트북 4절과 같은 현상).

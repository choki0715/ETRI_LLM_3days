# 실습 · MCP 서버 하나 붙이기 (1세션 · 20분)

한빛정밀 사내 자료 20편(Day 2의 `day2/data/kb`)을 검색하는 도구 하나짜리 MCP 서버 **hanbit-docs**를 띄우고, Claude Code에 붙여서 모델이 그 도구를 부르는지 봅니다.

어제 `loop.py`의 `search` 도구는 우리가 짠 루프 안에서만 쓸 수 있었습니다. 같은 일을 **MCP 서버**로 떼어 내면 Claude Code 같은 다른 프로그램이 그대로 붙여 쓸 수 있습니다 — 그게 MCP입니다.

| 파일 | 하는 일 |
|---|---|
| `hanbit_mcp.py` | MCP 서버 — 도구 `search_docs(query)` 하나. 질문과 겹치는 문단 3개를 출처와 함께 돌려준다. 판단은 하지 않는다 |
| `check_server.py` | Claude Code 없이 서버가 도는지 확인 — MCP 클라이언트로 붙어 도구 목록을 보고 한 번 부른다 |

명령은 [day3 README의 경로 약속](../README.md#경로-약속)(`$DAY3` · `$PY`)을 먼저 쳐 둔 터미널에서 실행합니다. Claude Code가 설치 · 로그인돼 있어야 합니다(같은 README의 준비).

| 순서 | 할 일 | 시간 |
|---|---|---|
| 1 | `hanbit_mcp.py` 읽기 — 도구 설명이 어디 있나 | 3분 |
| 2 | `check_server.py`로 서버 확인 | 2분 |
| 3 | Claude Code에 등록 | 3분 |
| 4 | 채팅창에서 부르는지 본다 | 6분 |
| 5 | 설명을 줄여 다시 본다 | 6분 |
| 6 | 정리 | — |

## 1. 서버 코드 읽기 — `hanbit_mcp.py` (3분)

세 군데만 봅니다.

- **`description`이 곧 도구 설명**입니다. 모델은 이것만 보고 언제 부를지 고릅니다 — 어제 `loop.py`의 `description`과 같은 자리. 파일 안에 긴 설명(`LONG`)과 한마디 설명(`SHORT` = "문서 검색")이 있고, 환경변수 `MCP_DESC=short`로 고릅니다 → 5번 실험
- **함수 이름이 도구 이름, 타입 힌트가 입력 스키마**입니다 (`def search_docs(query: str)`).
- **쓰는 도구(문서 수정 · 삭제)는 만들지 않았습니다.** 되돌릴 수 없는 행동은 MCP로 노출하지 않고 사람에게 남깁니다.

## 2. 서버 확인 — Claude Code 없이 (2분)

```bash
cd $DAY3/01_mcp
$PY check_server.py                          # 기본 질문 "서울 출장 숙박비 한도"
$PY check_server.py "회의실 예약 횟수"        # 내 질문으로도
```

서버 이름 · 도구 설명 · 입력 스키마가 찍히고, 찾은 문단 3개가 출처와 함께 나온 뒤 마지막 줄이 `결과: OK`면 다음으로 넘어갑니다. 여기서 찍힌 도구 설명이 **모델이 보게 될 글 그대로**입니다.

이 단계는 등록에 꼭 필요한 것은 아니지만, 여기서 서버가 도는 것을 보고 가야 4번에서 문제가 생겼을 때 서버 탓인지 아닌지 가릴 수 있습니다.

## 3. Claude Code에 등록 (3분)

```bash
mkdir -p ~/mcp-lab && cd ~/mcp-lab
claude mcp add --transport stdio hanbit-docs -- $PY $DAY3/01_mcp/hanbit_mcp.py
claude mcp list                        # hanbit-docs … ✔ Connected
```

- `--` 뒤가 서버를 띄우는 명령입니다. **절대 경로**로 씁니다 — `$PY`는 mcp가 깔린 공용 가상환경의 파이썬입니다.
- 범위는 기본 `local`(이 폴더 `~/mcp-lab`에서 나만)입니다. 그래서 4 · 5번의 `claude`도 이 폴더에서 띄웁니다. 팀과 나누려면 `-s project` → `.mcp.json`이 생깁니다.
- 빈 폴더(`~/mcp-lab`)에서 띄우는 이유 — 저장소 안에서 띄우면 Claude Code가 MCP 대신 파일을 직접 읽어 답할 수 있어서, 도구를 불렀는지 보기 어렵습니다.

## 4. 부르는지 본다 (6분)

```bash
cd ~/mcp-lab && claude
```

먼저 `/mcp`를 쳐서 `hanbit-docs`가 연결됐는지 봅니다. 그다음 채팅창에서 하나씩:

```
서울로 출장 가면 숙박비는 하루 얼마까지 나와?
회의실은 하루에 몇 번 예약할 수 있어?
오늘 점심 메뉴 추천해줘
```

`mcp__hanbit-docs__search_docs`가 불리는지, 처음 부를 때 허락을 묻는지, 답에 출처(파일 이름)를 밝히는지 봅니다. 결과를 아래 표의 "긴 설명" 칸에 적습니다.

## 5. 설명을 줄여 다시 본다 (6분)

`/exit`로 Claude Code를 닫고 터미널에서:

```bash
cd ~/mcp-lab
claude mcp add --transport stdio hanbit-docs-short -e MCP_DESC=short -- $PY $DAY3/01_mcp/hanbit_mcp.py
claude mcp remove hanbit-docs          # 긴 설명판은 뺀다 — 둘이 같이 있으면 어느 설명 때문에 불렀는지 가릴 수 없다
claude
```

같은 세 질문을 다시 합니다. 서버 코드는 그대로이고 **모델이 읽는 설명 글자만** "문서 검색" 한마디로 바뀌었습니다. 언제 부르는지가 달라지나요?

| 질문 | 긴 설명 — 불렀나 | 짧은 설명 — 불렀나 | 답에 출처를 밝혔나 |
|---|---|---|---|
| 서울 출장 숙박비 | | | |
| 회의실 예약 횟수 | | | |
| 점심 메뉴 추천 | | | |

> "문서 검색"만 보고는 *무슨* 문서인지 모릅니다. 한빛정밀 규정을 묻는데도 안 부르거나, 점심 메뉴에도 부를 수 있습니다. 다만 결과는 실행마다 다를 수 있으니, 질문마다 한두 번 더 해 봅니다.

## 6. 정리

```bash
cd ~/mcp-lab
claude mcp remove hanbit-docs-short    # hanbit-docs는 5번에서 이미 뺐다
```

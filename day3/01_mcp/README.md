# 실습 · MCP 서버 하나 붙이기 (1세션 · 20분)

sf-harness의 `sf-signals`를 MCP 도구 하나로 감싼 **sf-plant** 서버를 Claude Code에 붙이고, 모델이 그 도구를 부르는지 봅니다.

| 파일 | 하는 일 |
|---|---|
| `sf_mcp.py` | MCP 서버 — 도구 `signals(plant)` 하나. 판단은 하지 않고 KEY: value를 그대로 돌려준다 |
| `check_server.py` | Claude Code 없이 서버가 도는지 확인 — MCP 클라이언트로 붙어 도구 목록을 보고 한 번 부른다 |

명령은 [day3 README의 경로 약속](../README.md#경로-약속)(`$DAY3` · `$PY`)을 먼저 쳐 둔 터미널에서 실행합니다.

| 순서 | 할 일 | 시간 |
|---|---|---|
| 1 | 가상 플랜트 준비 | 3분 |
| 2 | `sf_mcp.py` 읽기 — 도구 설명이 어디 있나 | 2분 |
| 3 | `check_server.py`로 서버 확인 | 2분 |
| 4 | Claude Code에 등록 | 3분 |
| 5 | 채팅창에서 부르는지 본다 | 5분 |
| 6 | 설명을 줄여 다시 본다 | 5분 |
| 7 | 정리 | — |

## 1. 가상 플랜트 준비 (3분)

sf-harness를 clone해서 **스크립트만** 씁니다. 플러그인 설치는 오후(3세션)에 합니다.

```bash
git clone https://github.com/choki0715/sf-harness ~/sf-harness
~/sf-harness/sf-harness/bin/sf-demo-data          # /tmp/sf-demo 생성
```

mcp 패키지는 `setup.sh`가 공용 가상환경에 이미 깔았습니다(2.x). `check_env.sh`에서 "mcp 2.x 패키지"가 ○였으면 됩니다.

## 2. 서버 코드 읽기 — `sf_mcp.py` (2분)

실험 전에 세 군데만 봅니다.

- **`description`이 곧 도구 설명**입니다. 모델은 이것만 보고 언제 부를지 고릅니다 — 어제 `loop.py`의 `description`과 같은 자리. 파일 안에 긴 설명(`LONG`)과 한마디 설명(`SHORT`)이 있고, 환경변수 `SF_MCP_DESC=short`로 고릅니다 → 6번 실험
- **타입 힌트가 곧 입력 스키마**입니다 (`plant: str = "/tmp/sf-demo"`).
- **쓰는 도구(승인 · 정지)는 만들지 않았습니다.** 되돌릴 수 없는 행동은 MCP로 노출하지 않고 사람에게 남깁니다.

## 3. 서버 확인 — Claude Code 없이 (2분)

```bash
cd $DAY3/01_mcp
$PY check_server.py
```

마지막 줄이 `결과: OK`면 다음으로 넘어갑니다. `sf-signals를 찾지 못했다`가 나오면 `export SF_BIN=~/sf-harness/sf-harness/bin` 후 다시 돌립니다.

이 단계는 등록에 꼭 필요한 것은 아니지만, 여기서 서버가 도는 것을 보고 가야 5번에서 문제가 생겼을 때 서버 탓인지 아닌지 가릴 수 있습니다.

## 4. Claude Code에 등록 (3분)

```bash
mkdir -p ~/mcp-lab && cd ~/mcp-lab
claude mcp add --transport stdio sf-plant -- $PY $DAY3/01_mcp/sf_mcp.py
claude mcp list                        # sf-plant … ✔ Connected
```

- `--` 뒤가 서버를 띄우는 명령입니다. **절대 경로**로 씁니다 — `$PY`는 mcp가 깔린 공용 가상환경의 파이썬입니다.
- 범위는 기본 `local`(이 폴더 `~/mcp-lab`에서 나만)입니다. 그래서 5 · 6번의 `claude`도 이 폴더에서 띄웁니다. 팀과 나누려면 `-s project` → `.mcp.json`이 생깁니다.
- `sf-signals`를 못 찾는다고 나오면 `-e SF_BIN=$HOME/sf-harness/sf-harness/bin`을 `--` 앞에 붙여 다시 등록합니다.

## 5. 부르는지 본다 (5분)

```bash
cd ~/mcp-lab && claude
```

먼저 `/mcp`를 쳐서 `sf-plant`가 연결됐는지 봅니다. 그다음 채팅창에서:

```
CNC-02 상태 알려줘
지금 데이터가 끊긴 설비가 있어?
오늘 점심 메뉴 추천해줘
```

`mcp__sf-plant__signals`가 불리는지, 처음 부를 때 허락을 묻는지 봅니다. 결과를 아래 표의 "긴 설명" 칸에 적습니다.

## 6. 설명을 줄여 다시 본다 (5분)

`/exit`로 Claude Code를 닫고 터미널에서:

```bash
cd ~/mcp-lab
claude mcp add --transport stdio sf-plant-short -e SF_MCP_DESC=short -- $PY $DAY3/01_mcp/sf_mcp.py
claude mcp remove sf-plant             # 긴 설명판은 뺀다 — 둘이 같이 있으면 어느 설명 때문에 불렀는지 가릴 수 없다
claude
```

같은 세 질문을 다시 합니다. 설명이 "설비 정보" 한마디뿐일 때 언제 부르는지가 어떻게 바뀌나요?

| 질문 | 긴 설명 — 불렀나 | 짧은 설명 — 불렀나 | 모델이 결과를 그대로 인용했나 |
|---|---|---|---|
| CNC-02 상태 알려줘 | | | |
| 데이터가 끊긴 설비가 있어? | | | |
| 점심 메뉴 추천 | | | |

## 7. 정리

```bash
cd ~/mcp-lab
claude mcp remove sf-plant-short       # sf-plant는 6번에서 이미 뺐다
```

`~/sf-harness`와 `/tmp/sf-demo`는 그대로 둬도 됩니다. 3세션에서는 플러그인으로 새로 설치하고, 가상 플랜트도 `--fresh`로 다시 만듭니다.

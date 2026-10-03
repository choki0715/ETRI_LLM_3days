# 실습 · MCP 서버 하나 붙이기 (블록 1 · 20분)

sf-harness의 `sf-signals`를 MCP 도구 하나로 감싼 **sf-plant** 서버를 Claude Code에 붙이고, 모델이 그 도구를 부르는지 봅니다.

| 파일 | 하는 일 |
|---|---|
| `sf_mcp.py` | MCP 서버 — 도구 `signals(plant)` 하나. 판단은 하지 않고 KEY: value를 그대로 돌려준다 |
| `check_server.py` | Claude Code 없이 서버가 도는지 확인 — MCP 클라이언트로 붙어 도구 목록을 보고 한 번 부른다 |

## 1. 준비 (3분)

```bash
pip install mcp                       # Ubuntu 시스템 파이썬이면 --break-system-packages 또는 venv

# 가상 플랜트 — sf-harness를 clone해서 스크립트만 쓴다 (플러그인 설치는 오후에)
git clone https://github.com/choki0715/sf-harness ~/sf-harness
~/sf-harness/sf-harness/bin/sf-demo-data          # /tmp/sf-demo 생성
```

## 2. 서버 확인 (2분)

```bash
python3 check_server.py
```

마지막 줄이 `결과: OK`면 다음으로 넘어갑니다. `sf-signals를 찾지 못했다`가 나오면 `export SF_BIN=~/sf-harness/sf-harness/bin` 후 다시 돌립니다.

## 3. Claude Code에 등록 (5분)

```bash
mkdir -p ~/mcp-lab && cd ~/mcp-lab
claude mcp add --transport stdio sf-plant -- python3 $HOME/day3/01_mcp/sf_mcp.py    # 경로는 내 위치로
claude mcp list                        # sf-plant … ✓ Connected
claude
```

Claude Code 안에서 `/mcp`를 쳐서 `sf-plant`가 연결됐는지 봅니다.

- `--` 뒤가 서버를 띄우는 명령입니다. **절대 경로**로 씁니다.
- 범위는 기본 `local`(이 폴더에서 나만)입니다. 팀과 나누려면 `-s project` → `.mcp.json`이 생깁니다.
- `sf-signals`가 PATH에 없으면 `-e SF_BIN=$HOME/sf-harness/sf-harness/bin`을 `--` 앞에 붙입니다.

## 4. 부르는지 본다 (10분)

Claude Code 채팅창에서:

```
CNC-02 상태 알려줘
지금 데이터가 끊긴 설비가 있어?
오늘 점심 메뉴 추천해줘
```

`mcp__sf-plant__signals`가 불리는지, 처음 부를 때 허락을 묻는지 봅니다.

### 관찰 실험 · 설명을 줄이면

```bash
claude mcp add --transport stdio sf-plant-short -e SF_MCP_DESC=short -- python3 $HOME/day3/01_mcp/sf_mcp.py
claude mcp remove sf-plant             # 긴 설명판은 잠시 빼 둔다
```

같은 세 질문을 다시 합니다. 설명이 "설비 정보" 한마디뿐일 때 언제 부르는지가 어떻게 바뀌나요?

| 질문 | 긴 설명 — 불렀나 | 짧은 설명 — 불렀나 | 모델이 결과를 그대로 인용했나 |
|---|---|---|---|
| CNC-02 상태 알려줘 | | | |
| 데이터가 끊긴 설비가 있어? | | | |
| 점심 메뉴 추천 | | | |

## 읽을 거리 — `sf_mcp.py`

- **docstring · description이 곧 도구 설명**입니다. 모델은 이것만 보고 고릅니다 — 어제 `loop.py`의 description과 같은 자리.
- **타입 힌트가 곧 입력 스키마**입니다 (`plant: str = "/tmp/sf-demo"`).
- **쓰는 도구(승인 · 정지)는 만들지 않았습니다.** 되돌릴 수 없는 행동은 MCP로 노출하지 않고 사람에게 남깁니다.

## 정리

```bash
claude mcp remove sf-plant-short
claude mcp remove sf-plant
```

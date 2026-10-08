#!/usr/bin/env python3
"""PreToolUse 훅 — 에이전트가 넘으면 안 되는 선 두 가지만 막는다 (sf-harness guard.py를 줄인 뼈대).

  1. 최종 결정 (my-decide approve / reject) — 에이전트는 제안까지. 결정은 사람이 터미널에서
  2. 기준(rules.csv) 수정 · 청구 원본(claims.csv) 삭제 — 기준을 바꾸면 모든 위반이 사라진다

범위: 1은 우리 명령이라 어디서든 막는다. 2는 흔한 파일 이름이라 .my-harness 마커 아래에서만 막는다.
한계: 정규식이지 셸 파서가 아니다. 과속방지턱이지 보안 경계가 아니다.
내 업무로 바꿀 때: ALWAYS · IN_SCOPE 목록과 PROTECTED 패턴만 고치고, test/run-tests.sh에 막을 것 · 막지 말 것을 함께 더한다.

훅이 하는 일
    Claude Code가 도구를 쓰기 직전에 이 프로그램을 실행하고, 표준 입력으로 JSON을 넘긴다.
        {"tool_name": "Bash", "tool_input": {"command": "rm claims.csv"}, "cwd": "/tmp/my-demo", ...}
    막을 때는 표준 출력에 "deny" JSON을 찍는다. 아무것도 안 찍으면 통과다.
"""
import json
import os
import re
import sys

MARKER = ".my-harness"          # 연습 폴더 표시 파일 — my-demo-data가 만든다

# 명령의 시작 위치: 맨 앞, 또는 ; & | 줄바꿈 뒤 (sudo가 붙어도 된다)
CMD_START = r"(?:\A|[;&|]|\n)\s*(?:sudo\s+)?"

# 1. 어디서든 막는 명령 — (정규식, 에이전트에게 돌려줄 이유 문장)
ALWAYS = [
    (re.compile(CMD_START + r"(?:\S*/)?my-decide\s+(?:-\S+\s+\S+\s+)*(?:approve|reject)\b"),
     "승인 · 반려는 사람이 한다. 에이전트는 제안(reports/review.md)까지다.\n"
     "결정이 필요한 청구와 근거를 보고하고, 담당자가 터미널에서 my-decide 를 친다."),
]

# 2. 연습 폴더(.my-harness 마커 아래)에서만 막는 명령
IN_SCOPE = [
    (re.compile(CMD_START + r"(?:sed\s+-i|tee|cp|mv|rm|truncate)\b[^;&|\n]*rules\.csv"),
     "지급 기준(rules.csv)은 바꾸지 않는다. 기준을 올리면 위반이 사라질 뿐이다. 기준 변경은 담당 부서가 한다."),
    (re.compile(r"(?<!\d)>{1,2}\s*\S*rules\.csv"),
     "지급 기준(rules.csv)에 덮어쓰지 않는다."),
    (re.compile(CMD_START + r"(?:rm|mv|truncate|shred)\b[^;&|\n]*claims\.csv"),
     "청구 원본(claims.csv)은 증빙이다. 지우거나 옮기지 않는다."),
]

# Write · Edit 도구로 편집하면 안 되는 파일 이름
PROTECTED = re.compile(r"(?:^|/)(?:rules\.csv|claims\.csv)$")

# 명령 안에서 rules.csv · claims.csv 경로를 뽑아내는 패턴 (범위 판단용)
PATH_TOKEN = re.compile(r"[\"']?([^\s\"';&|<>]*(?:rules|claims)\.csv)")


def deny(reason):
    """막는다 — Claude Code가 읽는 형식으로 이유를 찍고 끝낸다."""
    answer = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(answer, ensure_ascii=False))
    sys.exit(0)


def under_marker(path):
    """path 또는 그 위 폴더 어딘가에 .my-harness 마커가 있으면 True."""
    current = os.path.abspath(path)
    while True:
        if os.path.exists(os.path.join(current, MARKER)):
            return True
        parent = os.path.dirname(current)
        if parent == current:          # 맨 위(/)까지 올라왔다
            return False
        current = parent


def in_scope(data, command):
    """이 명령이 연습 폴더를 건드리는가 — 지금 폴더가 마커 아래이거나, 명령 속 경로가 마커 아래이면 True."""
    cwd = data.get("cwd")
    if not cwd:
        cwd = os.getcwd()
    if under_marker(cwd):
        return True

    for token in PATH_TOKEN.findall(command):
        path = os.path.expanduser(token)
        if not os.path.isabs(path):
            path = os.path.join(cwd, path)
        if under_marker(os.path.dirname(path)):
            return True
    return False


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0                                    # 깨진 입력은 통과 (fail-open)

    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input")
    if not tool_input:
        tool_input = {}

    if tool == "Bash":
        command = tool_input.get("command", "")
        # 1. 어디서든 막는 명령
        for pattern, reason in ALWAYS:
            if pattern.search(command):
                deny(reason)
        # 2. 연습 폴더를 건드릴 때만 막는 명령
        if in_scope(data, command):
            for pattern, reason in IN_SCOPE:
                if pattern.search(command):
                    deny(reason)

    elif tool in ("Write", "Edit", "MultiEdit"):
        file_path = tool_input.get("file_path", "")
        folder = os.path.dirname(os.path.abspath(file_path))
        if PROTECTED.search(file_path) and under_marker(folder):
            deny("지급 기준 · 청구 원본은 편집하지 않는다. 검토 결과는 reports/ 에 쓴다.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

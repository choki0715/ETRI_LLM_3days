#!/usr/bin/env python3
"""PreToolUse 훅 — 에이전트가 넘으면 안 되는 선 두 가지만 막는다 (sf-harness guard.py를 줄인 뼈대).

  1. 최종 결정 (my-decide approve / reject) — 에이전트는 제안까지. 결정은 사람이 터미널에서
  2. 기준(rules.csv) 수정 · 청구 원본(claims.csv) 삭제 — 기준을 바꾸면 모든 위반이 사라진다

범위: 1은 우리 명령이라 어디서든 막는다. 2는 흔한 파일 이름이라 .my-harness 마커 아래에서만 막는다.
한계: 정규식이지 셸 파서가 아니다. 과속방지턱이지 보안 경계가 아니다.
내 업무로 바꿀 때: RULES 목록과 PROTECTED 패턴만 고치고, test/run-tests.sh에 막을 것 · 막지 말 것을 함께 더한다.
"""
import json
import os
import re
import sys

MARKER = ".my-harness"
CMD_START = r"(?:\A|[;&|]|\n)\s*(?:sudo\s+)?"

ALWAYS = [
    (re.compile(CMD_START + r"(?:\S*/)?my-decide\s+(?:-\S+\s+\S+\s+)*(?:approve|reject)\b"),
     "승인 · 반려는 사람이 한다. 에이전트는 제안(reports/review.md)까지다.\n"
     "결정이 필요한 청구와 근거를 보고하고, 담당자가 터미널에서 my-decide 를 친다."),
]
IN_SCOPE = [
    (re.compile(CMD_START + r"(?:sed\s+-i|tee|cp|mv|rm|truncate)\b[^;&|\n]*rules\.csv"),
     "지급 기준(rules.csv)은 바꾸지 않는다. 기준을 올리면 위반이 사라질 뿐이다. 기준 변경은 담당 부서가 한다."),
    (re.compile(r"(?<!\d)>{1,2}\s*\S*rules\.csv"),
     "지급 기준(rules.csv)에 덮어쓰지 않는다."),
    (re.compile(CMD_START + r"(?:rm|mv|truncate|shred)\b[^;&|\n]*claims\.csv"),
     "청구 원본(claims.csv)은 증빙이다. 지우거나 옮기지 않는다."),
]
PROTECTED = re.compile(r"(?:^|/)(?:rules\.csv|claims\.csv)$")
PATH_TOKEN = re.compile(r"[\"']?([^\s\"';&|<>]*(?:rules|claims)\.csv)")


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}, ensure_ascii=False))
    sys.exit(0)


def under_marker(path):
    cur = os.path.abspath(path)
    while True:
        if os.path.exists(os.path.join(cur, MARKER)):
            return True
        parent = os.path.dirname(cur)
        if parent == cur:
            return False
        cur = parent


def in_scope(data, command):
    cwd = data.get("cwd") or os.getcwd()
    if under_marker(cwd):
        return True
    for tok in PATH_TOKEN.findall(command):
        p = os.path.expanduser(tok)
        p = p if os.path.isabs(p) else os.path.join(cwd, p)
        if under_marker(os.path.dirname(p)):
            return True
    return False


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0                                    # 깨진 입력은 통과 (fail-open)
    tool, inp = data.get("tool_name", ""), data.get("tool_input", {}) or {}
    if tool == "Bash":
        cmd = inp.get("command", "")
        for rx, why in ALWAYS:
            if rx.search(cmd):
                deny(why)
        if in_scope(data, cmd):
            for rx, why in IN_SCOPE:
                if rx.search(cmd):
                    deny(why)
    elif tool in ("Write", "Edit", "MultiEdit"):
        fp = inp.get("file_path", "")
        if PROTECTED.search(fp) and under_marker(os.path.dirname(os.path.abspath(fp))):
            deny("지급 기준 · 청구 원본은 편집하지 않는다. 검토 결과는 reports/ 에 쓴다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

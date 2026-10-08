"""벽돌깨기 자동 플레이 테스트 — 체크리스트 여덟 개 중 코드로 볼 수 있는 것을 대신 본다.

    pip install playwright && python -m playwright install chromium   # 처음 한 번
    python playtest.py ~/breakout/index.html

- 누구의 게임이든: 콘솔 에러 · 캔버스 · 키 입력 · 창 크기 변경 (체크 1 · 8 일부)
- 게임이 상태를 window.game 에 노출하면 (CLAUDE.md에 한 줄 — README 참고) 체크 1~7까지 본다
  window.game = { paddle:{x}, ball:{x,y,vx,vy}, bricks:[{alive}], score, lives, state }

자동 테스트가 통과해도 사람이 직접 한 판은 한다. 손맛(속도 · 각도)은 코드가 못 본다.

읽는 법: page.evaluate("...") 안의 따옴표 부분은 브라우저에서 도는 자바스크립트다.
         그 결과(숫자 · 참거짓 · 글자)가 파이썬으로 돌아온다.
"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

PASS = "○"
FAIL = "×"
SKIP = "–"          # 코드로 볼 수 없어 사람이 확인

results = []        # [(표시, 항목 이름, 설명), ...]
errors = []         # 브라우저 콘솔에 찍힌 에러


def record(mark, name, detail=""):
    """검사 결과 한 줄을 기록하고 화면에 찍는다."""
    results.append((mark, name, detail))
    if detail:
        print(f"  {mark} {name} — {detail}")
    else:
        print(f"  {mark} {name}")


def check(passed, name, detail=""):
    """passed가 참이면 ○, 거짓이면 ×로 기록한다."""
    if passed:
        record(PASS, name, detail)
    else:
        record(FAIL, name, detail)


def on_console(message):
    """브라우저 콘솔 메시지 중 에러만 모은다."""
    if message.type == "error":
        errors.append(message.text)


def on_page_error(error):
    """잡히지 않은 자바스크립트 예외를 모은다."""
    errors.append(str(error))


def hold_key(page, key, milliseconds):
    """키를 일정 시간 누르고 있다가 뗀다."""
    page.keyboard.down(key)
    page.wait_for_timeout(milliseconds)
    page.keyboard.up(key)


def js(page, body):
    """자바스크립트 함수 본문을 실행하고 return 값을 돌려준다. 예: js(page, "return game.lives")"""
    return page.evaluate("(() => {" + body + "})()")


def main(path):
    url = Path(path).resolve().as_uri()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1000, "height": 760})
        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page.goto(url)
        page.wait_for_timeout(800)

        print("기본 점검")
        check(page.locator("canvas").count() > 0, "캔버스가 있다")
        check(len(errors) == 0, "열자마자 콘솔 에러 없음", "; ".join(errors[:2]))

        hold_key(page, "ArrowLeft", 1500)
        hold_key(page, "ArrowRight", 1500)
        page.screenshot(path="playtest_1.png")
        check(len(errors) == 0, "← → 를 눌러도 에러 없음 (화면: playtest_1.png)")

        has_state = page.evaluate("typeof window.game === 'object' && window.game && 'paddle' in window.game")
        if has_state:
            check_game_state(page)
        else:
            record(SKIP, "window.game 이 없어 체크 1~7은 사람이 확인")

        # 8. 창을 좁혀도 캔버스가 화면 안에 보이는가
        page.set_viewport_size({"width": 480, "height": 700})
        page.wait_for_timeout(500)
        page.screenshot(path="playtest_8.png")
        visible = page.evaluate("(() => { const r = document.querySelector('canvas').getBoundingClientRect();"
                                " return r.width > 0 && r.right <= innerWidth + 1; })()")
        check(visible and len(errors) == 0, "8 창 크기를 바꿔도 깨지지 않는다 (화면: playtest_8.png)")
        browser.close()

    n_pass = 0
    n_fail = 0
    n_skip = 0
    for mark, name, detail in results:
        if mark == PASS:
            n_pass += 1
        elif mark == FAIL:
            n_fail += 1
        else:
            n_skip += 1
    print(f"\n통과 {n_pass} · 실패 {n_fail} · 사람 확인 {n_skip}")
    if errors:
        print("콘솔 에러 맨 윗줄:", errors[0])

    if n_fail > 0:
        return 1
    return 0


def check_game_state(page):
    """window.game 을 읽어 체크 1~7을 본다."""
    W = page.evaluate("document.querySelector('canvas').width")       # 캔버스 너비
    H = page.evaluate("document.querySelector('canvas').height")      # 캔버스 높이
    print("상태 점검 (window.game)")

    # 1. 패들이 화면 밖으로 안 나간다 — 왼쪽 끝까지, 오른쪽 끝까지 밀어 본다
    hold_key(page, "ArrowLeft", 2500)
    left = js(page, "return game.paddle.x")
    hold_key(page, "ArrowRight", 3500)
    right = js(page, "return game.paddle.x")
    paddle_w = js(page, "return (typeof PADDLE_W !== 'undefined') ? PADDLE_W : (game.paddle.w || 0)")
    check(left >= 0 and right + paddle_w <= W + 0.5, "1 패들이 양 끝에서 멈춘다", f"x={left:.0f} → {right:.0f}")

    # 2·4. 자동 조종으로 오래 친다 — 공이 화면 밖으로 새거나 패들 안에 박히지 않는가
    #      8ms마다 패들을 공 밑으로 옮기고, 공이 벽 · 천장 밖으로 나가면 window.__bad 에 적는다
    page.keyboard.press("Space")
    pilot = """window.__pilot = setInterval(() => {
        const pw = (typeof PADDLE_W !== 'undefined') ? PADDLE_W : (game.paddle.w || 100);
        const off = [-0.45, 0.45, 0, -0.3, 0.3][Math.floor(performance.now() / 3000) % 5];  // 끝으로도 받는다
        game.paddle.x = Math.max(0, Math.min(__W__ - pw, game.ball.x - pw / 2 - off * pw));
        if (game.ball.stuck) { const e = new KeyboardEvent('keydown', {key: ' '}); dispatchEvent(e); }
        const b = game.ball; window.__bad = window.__bad || [];
        if (b.x < -1 || b.x > __W__ + 1 || b.y < -1) window.__bad.push([b.x, b.y]);
    }, 8);"""
    page.evaluate(pilot.replace("__W__", str(W)))

    lives_before = js(page, "return game.lives")
    start = time.time()
    # 최소 2초, 최대 20초 — 그 사이에 게임이 play 상태를 벗어나면(클리어 · 게임오버) 멈춘다
    while True:
        elapsed = time.time() - start
        still_playing = js(page, "return game.state") == "play"
        if elapsed >= 2 and not (elapsed < 20 and still_playing):
            break
        page.wait_for_timeout(500)

    bad = js(page, "return (window.__bad || []).length")
    broken = js(page, "return game.bricks.filter(b => !b.alive).length")
    check(bad == 0, "2·4 오래 쳐도 공이 벽 · 천장을 뚫지 않는다", f"깬 벽돌 {broken}개")

    lives_after = js(page, "return game.lives")
    state = js(page, "return game.state")
    check(lives_after == lives_before or state == "clear", "2 패들 끝으로 받아도 놓치지 않는다 (자동 조종)")

    score = js(page, "return game.score")
    check(score >= broken * 1 and broken > 0, "벽돌을 깨면 점수가 오른다", f"점수 {score}")
    page.evaluate("clearInterval(window.__pilot)")

    # 5. 일부러 놓친다 — 패들은 왼쪽 끝, 공은 오른쪽 아래로 떨어뜨린다 (최대 5번)
    miss = """if (game.ball.stuck) { dispatchEvent(new KeyboardEvent('keydown', {key: ' '})); }
             game.paddle.x = 0; game.ball.x = __W__ - 20; game.ball.y = __Y__; game.ball.vx = 0; game.ball.vy = 6;"""
    miss = miss.replace("__W__", str(W)).replace("__Y__", str(H - 30))
    for _ in range(5):
        if js(page, "return game.state") == "over":
            break
        js(page, miss)
        page.wait_for_timeout(400)
    lives = js(page, "return game.lives")
    state = js(page, "return game.state")
    check(lives == 0 and state == "over", "5 세 번 놓치면 목숨 0 · 게임오버", f"lives={lives} state={state}")

    # 6. 다시 시작
    page.keyboard.press("Space")
    page.wait_for_timeout(300)
    reset_ok = js(page, "return game.score === 0 && game.lives >= 3 && game.bricks.every(b => b.alive)")
    check(reset_ok, "6 다시 시작하면 점수 · 목숨 · 벽돌이 처음 상태로")

    # 3. 모서리 — 맨 아래 줄 벽돌 두 개 사이 틈으로 공을 올려 보낸다. 튕겨 내려올 때까지 몇 개가 사라지나
    js(page, """if (game.ball.stuck) dispatchEvent(new KeyboardEvent('keydown', {key: ' '}));
         const live = game.bricks.filter(b => b.alive); const yMax = Math.max(...live.map(b => b.y));
         const row = live.filter(b => b.y === yMax).sort((p, q) => p.x - q.x);
         const a = row[0], c = row[1]; const gx = (a.x + a.w + c.x) / 2;
         game.ball.x = gx; game.ball.y = a.y + a.h + 40; game.ball.vx = 0.01; game.ball.vy = -4;
         window.__before = game.bricks.filter(b => b.alive).length;""")
    for _ in range(40):                       # 최대 2초 — 공이 내려오기 시작하면(vy > 0) 멈춘다
        page.wait_for_timeout(50)
        if js(page, "return game.ball.vy > 0"):
            break
    gone = js(page, "return window.__before - game.bricks.filter(b => b.alive).length")
    check(gone <= 1, "3 벽돌 사이 모서리에 맞아도 한 번에 하나만 사라진다", f"{gone}개 사라짐")

    # 7. 다 깬다 — 벽돌 하나만 남기고 공을 그 밑에서 쏘아 올린다
    js(page, "game.bricks.forEach((b, i) => { if (i) b.alive = false; }); const a = game.bricks[0];"
             "if (game.ball.stuck) dispatchEvent(new KeyboardEvent('keydown', {key: ' '}));"
             "game.ball.x = a.x + a.w / 2; game.ball.y = a.y + a.h + 30; game.ball.vx = 0; game.ball.vy = -5;")
    page.wait_for_timeout(600)
    state = js(page, "return game.state")
    check(state == "clear", "7 벽돌을 다 깨면 클리어", f"state={state}")
    page.screenshot(path="playtest_7.png")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python playtest.py <index.html 경로>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))

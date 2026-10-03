"""벽돌깨기 자동 플레이 테스트 — 체크리스트 여덟 개 중 코드로 볼 수 있는 것을 대신 본다.

    pip install playwright && python -m playwright install chromium   # 처음 한 번
    python playtest.py ~/breakout/index.html

- 누구의 게임이든: 콘솔 에러 · 캔버스 · 키 입력 · 창 크기 변경 (체크 1 · 8 일부)
- 게임이 상태를 window.game 에 노출하면 (CLAUDE.md에 한 줄 — README 참고) 체크 1~7까지 본다
  window.game = { paddle:{x}, ball:{x,y,vx,vy}, bricks:[{alive}], score, lives, state }

자동 테스트가 통과해도 사람이 직접 한 판은 한다. 손맛(속도 · 각도)은 코드가 못 본다.
"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

PASS, FAIL, SKIP = "○", "×", "–"
results = []


def rec(mark, name, detail=""):
    results.append((mark, name, detail))
    print(f"  {mark} {name}" + (f" — {detail}" if detail else ""))


def main(path: str):
    url = Path(path).resolve().as_uri()
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1000, "height": 760})
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url)
        page.wait_for_timeout(800)

        print("기본 점검")
        rec(PASS if page.locator("canvas").count() else FAIL, "캔버스가 있다")
        rec(PASS if not errors else FAIL, "열자마자 콘솔 에러 없음", "; ".join(errors[:2]))

        page.keyboard.down("ArrowLeft"); page.wait_for_timeout(1500); page.keyboard.up("ArrowLeft")
        page.keyboard.down("ArrowRight"); page.wait_for_timeout(1500); page.keyboard.up("ArrowRight")
        page.screenshot(path="playtest_1.png")
        rec(PASS if not errors else FAIL, "← → 를 눌러도 에러 없음 (화면: playtest_1.png)")

        has_state = page.evaluate("typeof window.game === 'object' && window.game && 'paddle' in window.game")
        if not has_state:
            rec(SKIP, "window.game 이 없어 체크 1~7은 사람이 확인")
        else:
            deep(page)

        page.set_viewport_size({"width": 480, "height": 700})
        page.wait_for_timeout(500)
        page.screenshot(path="playtest_8.png")
        visible = page.evaluate("(() => { const r = document.querySelector('canvas').getBoundingClientRect();"
                                " return r.width > 0 && r.right <= innerWidth + 1; })()")
        rec(PASS if visible and not errors else FAIL, "8 창 크기를 바꿔도 깨지지 않는다 (화면: playtest_8.png)")
        browser.close()

    n_fail = sum(m == FAIL for m, _, _ in results)
    print(f"\n통과 {sum(m == PASS for m, _, _ in results)} · 실패 {n_fail} · 사람 확인 {sum(m == SKIP for m, _, _ in results)}")
    if errors:
        print("콘솔 에러 맨 윗줄:", errors[0])
    return 1 if n_fail else 0


def deep(page):
    g = lambda expr: page.evaluate("(() => {" + expr + "})()")
    W = page.evaluate("document.querySelector('canvas').width")
    print("상태 점검 (window.game)")

    # 1. 패들이 화면 밖으로 안 나간다
    page.keyboard.down("ArrowLeft"); page.wait_for_timeout(2500); page.keyboard.up("ArrowLeft")
    left = g("return game.paddle.x")
    page.keyboard.down("ArrowRight"); page.wait_for_timeout(3500); page.keyboard.up("ArrowRight")
    right = g("return game.paddle.x")
    pw_ = g("return (typeof PADDLE_W !== 'undefined') ? PADDLE_W : (game.paddle.w || 0)")
    rec(PASS if left >= 0 and right + pw_ <= W + 0.5 else FAIL, "1 패들이 양 끝에서 멈춘다", f"x={left:.0f} → {right:.0f}")

    # 2·4. 자동 조종으로 오래 친다 — 공이 화면 밖으로 새거나 패들 안에 박히지 않는가
    page.keyboard.press("Space")
    page.evaluate("""window.__pilot = setInterval(() => {
        const pw = (typeof PADDLE_W !== 'undefined') ? PADDLE_W : (game.paddle.w || 100);
        const off = [-0.45, 0.45, 0, -0.3, 0.3][Math.floor(performance.now() / 3000) % 5];  // 끝으로도 받는다
        game.paddle.x = Math.max(0, Math.min(__W__ - pw, game.ball.x - pw / 2 - off * pw));
        if (game.ball.stuck) { const e = new KeyboardEvent('keydown', {key: ' '}); dispatchEvent(e); }
        const b = game.ball; window.__bad = window.__bad || [];
        if (b.x < -1 || b.x > __W__ + 1 || b.y < -1) window.__bad.push([b.x, b.y]);
    }, 8);""".replace("__W__", str(W)))
    lives0 = g("return game.lives")
    t0 = time.time()
    while time.time() - t0 < 20 and g("return game.state") == "play" or time.time() - t0 < 2:
        page.wait_for_timeout(500)
    bad = g("return (window.__bad || []).length")
    broke = g("return game.bricks.filter(b => !b.alive).length")
    rec(PASS if bad == 0 else FAIL, "2·4 오래 쳐도 공이 벽 · 천장을 뚫지 않는다", f"깬 벽돌 {broke}개")
    rec(PASS if g("return game.lives") == lives0 or g("return game.state") == "clear" else FAIL,
        "2 패들 끝으로 받아도 놓치지 않는다 (자동 조종)")
    rec(PASS if g("return game.score") >= broke * 1 and broke > 0 else FAIL, "벽돌을 깨면 점수가 오른다",
        f"점수 {g('return game.score')}")
    page.evaluate("clearInterval(window.__pilot)")

    # 5. 일부러 세 번 놓친다
    for _ in range(5):
        if g("return game.state") == "over":
            break
        g("""if (game.ball.stuck) { dispatchEvent(new KeyboardEvent('keydown', {key: ' '})); }
             game.paddle.x = 0; game.ball.x = __W__ - 20; game.ball.y = __Y__; game.ball.vx = 0; game.ball.vy = 6;"""
          .replace("__W__", str(W)).replace("__Y__", str(page.evaluate("document.querySelector('canvas').height") - 30)))
        page.wait_for_timeout(400)
    rec(PASS if g("return game.lives") == 0 and g("return game.state") == "over" else FAIL,
        "5 세 번 놓치면 목숨 0 · 게임오버", f"lives={g('return game.lives')} state={g('return game.state')}")

    # 6. 다시 시작
    page.keyboard.press("Space"); page.wait_for_timeout(300)
    ok6 = g("return game.score === 0 && game.lives >= 3 && game.bricks.every(b => b.alive)")
    rec(PASS if ok6 else FAIL, "6 다시 시작하면 점수 · 목숨 · 벽돌이 처음 상태로")

    # 3. 모서리 — 맨 아래 줄 벽돌 두 개 사이 틈으로 공을 올려 보낸다. 튕겨 내려올 때까지 몇 개가 사라지나
    g("""if (game.ball.stuck) dispatchEvent(new KeyboardEvent('keydown', {key: ' '}));
         const live = game.bricks.filter(b => b.alive); const yMax = Math.max(...live.map(b => b.y));
         const row = live.filter(b => b.y === yMax).sort((p, q) => p.x - q.x);
         const a = row[0], c = row[1]; const gx = (a.x + a.w + c.x) / 2;
         game.ball.x = gx; game.ball.y = a.y + a.h + 40; game.ball.vx = 0.01; game.ball.vy = -4;
         window.__before = game.bricks.filter(b => b.alive).length;""")
    for _ in range(40):
        page.wait_for_timeout(50)
        if g("return game.ball.vy > 0"):
            break
    gone = g("return window.__before - game.bricks.filter(b => b.alive).length")
    rec(PASS if gone <= 1 else FAIL, "3 벽돌 사이 모서리에 맞아도 한 번에 하나만 사라진다", f"{gone}개 사라짐")

    # 7. 다 깬다
    g("game.bricks.forEach((b, i) => { if (i) b.alive = false; }); const a = game.bricks[0];"
      "if (game.ball.stuck) dispatchEvent(new KeyboardEvent('keydown', {key: ' '}));"
      "game.ball.x = a.x + a.w / 2; game.ball.y = a.y + a.h + 30; game.ball.vx = 0; game.ball.vy = -5;")
    page.wait_for_timeout(600)
    rec(PASS if g("return game.state") == "clear" else FAIL, "7 벽돌을 다 깨면 클리어", f"state={g('return game.state')}")
    page.screenshot(path="playtest_7.png")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python playtest.py <index.html 경로>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))

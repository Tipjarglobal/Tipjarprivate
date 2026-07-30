import os
from playwright.sync_api import sync_playwright

URL = "https://ai-credit-saver.preview.emergentagent.com"
OUT = "/app/frontend/public/broll"
os.makedirs(OUT, exist_ok=True)

def new_page(b):
    ctx = b.new_context(viewport={"width": 412, "height": 900}, device_scale_factor=2)
    pg = ctx.new_page()
    pg.goto(URL, wait_until="domcontentloaded")
    pg.wait_for_timeout(4300)
    pg.evaluate("() => { const s=document.querySelector('[data-testid=\"splash-screen\"]'); if(s) s.remove(); }")
    return ctx, pg

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])

    # 1. Language switcher open
    ctx, pg = new_page(b)
    try:
        pg.click('[data-testid="language-switcher"]', timeout=5000)
        pg.wait_for_timeout(1200)
    except Exception as e: print("lang", e)
    pg.screenshot(path=f"{OUT}/01_language.png")
    ctx.close()

    # 2. Notification prompt
    ctx, pg = new_page(b)
    try:
        pg.evaluate("() => window.dispatchEvent(new Event('tj-viewed-pick'))")
        pg.wait_for_timeout(4000)
    except Exception as e: print("notif", e)
    pg.screenshot(path=f"{OUT}/02_notification.png")
    ctx.close()

    # 3. Submit tip modal
    ctx, pg = new_page(b)
    try:
        pg.click('[data-testid="hero-submit-btn"]', timeout=5000)
        pg.wait_for_timeout(2500)
    except Exception as e: print("submit", e)
    pg.screenshot(path=f"{OUT}/03_submit.png")
    ctx.close()

    # 4/5/6 views
    for name, view in [("04_ai_picks","ai"),("05_master","master"),("06_live","live")]:
        ctx, pg = new_page(b)
        try:
            pg.evaluate(f"() => window.dispatchEvent(new CustomEvent('tj-open-view', {{detail:'{view}'}}))")
            pg.wait_for_timeout(5500)
            pg.evaluate("() => { const w=document.querySelector('[data-testid=\"tips-window\"]'); if(w) w.scrollTo(0,0); }")
            pg.wait_for_timeout(800)
        except Exception as e: print(name, e)
        pg.screenshot(path=f"{OUT}/{name}.png")
        ctx.close()

    # 7 settled won
    ctx, pg = new_page(b)
    try:
        pg.evaluate("() => window.dispatchEvent(new CustomEvent('tj-open-view', {detail:'settled'}))")
        pg.wait_for_timeout(4500)
        pg.click('[data-testid="settled-won-toggle"]', timeout=6000)
        pg.wait_for_timeout(5000)
        pg.evaluate("() => { const w=document.querySelector('[data-testid=\"tips-window\"]'); if(w) w.scrollTo(0,0); }")
        pg.wait_for_timeout(800)
    except Exception as e: print("won", e)
    pg.screenshot(path=f"{OUT}/07_settled_won.png")
    ctx.close()

    b.close()
print("DONE")

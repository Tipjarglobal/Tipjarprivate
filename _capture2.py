import os
from playwright.sync_api import sync_playwright

URL = "https://ai-credit-saver.preview.emergentagent.com"
OUT = "/app/frontend/public/broll"
os.makedirs(OUT, exist_ok=True)

def fresh(p):
    ctx = p.chromium.launch(args=["--no-sandbox"]).new_context(
        viewport={"width": 412, "height": 900}, device_scale_factor=2)
    return ctx

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    # --- SETTLED (won) view ---
    ctx = b.new_context(viewport={"width": 412, "height": 900}, device_scale_factor=2)
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(4200)
    page.evaluate("() => { const s=document.querySelector('[data-testid=\"splash-screen\"]'); if(s) s.remove(); }")
    page.evaluate("() => window.dispatchEvent(new CustomEvent('tj-open-view', {detail:'settled'}))")
    page.wait_for_timeout(6500)
    page.evaluate("() => { const w=document.querySelector('[data-testid=\"tips-window\"]'); if(w) w.scrollTo(0,0); }")
    page.wait_for_timeout(1000)
    page.screenshot(path=f"{OUT}/settled.png")
    page.evaluate("() => { const w=document.querySelector('[data-testid=\"tips-window\"]'); if(w) w.scrollTo(0,700); }")
    page.wait_for_timeout(1200)
    page.screenshot(path=f"{OUT}/settled_2.png")
    print("SETTLED:", page.inner_text("[data-testid='tips-window']")[:500])
    ctx.close()

    # --- Hall of Fame on landing ---
    ctx2 = b.new_context(viewport={"width": 412, "height": 900}, device_scale_factor=2)
    pg = ctx2.new_page()
    pg.goto(URL, wait_until="domcontentloaded")
    pg.wait_for_timeout(4200)
    pg.evaluate("() => { const s=document.querySelector('[data-testid=\"splash-screen\"]'); if(s) s.remove(); }")
    pg.evaluate("() => document.getElementById('best-wins')?.scrollIntoView()")
    pg.wait_for_timeout(2500)
    pg.screenshot(path=f"{OUT}/halloffame.png")
    pg.evaluate("() => window.scrollBy(0, 800)")
    pg.wait_for_timeout(1500)
    pg.screenshot(path=f"{OUT}/halloffame_2.png")
    print("HOF:", pg.inner_text("#best-wins")[:400])
    ctx2.close()
    b.close()
print("DONE")

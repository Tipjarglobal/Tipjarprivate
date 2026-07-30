import os
from playwright.sync_api import sync_playwright

URL = "https://ai-credit-saver.preview.emergentagent.com"
OUT = "/app/frontend/public/broll"

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])

    # SETTLED -> WON
    ctx = b.new_context(viewport={"width": 412, "height": 900}, device_scale_factor=2)
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(4200)
    page.evaluate("() => { const s=document.querySelector('[data-testid=\"splash-screen\"]'); if(s) s.remove(); }")
    page.evaluate("() => window.dispatchEvent(new CustomEvent('tj-open-view', {detail:'settled'}))")
    page.wait_for_timeout(5000)
    try:
        page.get_by_text("Won", exact=False).first.click(timeout=5000)
    except Exception as e:
        print("won click err", e)
    page.wait_for_timeout(5000)
    page.evaluate("() => { const w=document.querySelector('[data-testid=\"tips-window\"]'); if(w) w.scrollTo(0,320); }")
    page.wait_for_timeout(1500)
    page.screenshot(path=f"{OUT}/won.png")
    page.evaluate("() => { const w=document.querySelector('[data-testid=\"tips-window\"]'); if(w) w.scrollTo(0,1000); }")
    page.wait_for_timeout(1500)
    page.screenshot(path=f"{OUT}/won_2.png")
    ctx.close()

    # HALL OF FAME
    ctx2 = b.new_context(viewport={"width": 412, "height": 900}, device_scale_factor=2)
    pg = ctx2.new_page()
    pg.goto(URL, wait_until="domcontentloaded")
    pg.wait_for_timeout(4200)
    pg.evaluate("() => { const s=document.querySelector('[data-testid=\"splash-screen\"]'); if(s) s.remove(); }")
    pg.evaluate("() => document.getElementById('best-wins')?.scrollIntoView()")
    pg.wait_for_timeout(3000)
    pg.screenshot(path=f"{OUT}/halloffame.png")
    pg.evaluate("() => window.scrollBy(0, 750)")
    pg.wait_for_timeout(2000)
    pg.screenshot(path=f"{OUT}/halloffame_2.png")
    ctx2.close()
    b.close()
print("DONE")

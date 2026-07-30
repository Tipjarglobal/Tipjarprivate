import os, time
from playwright.sync_api import sync_playwright

URL = "https://ai-credit-saver.preview.emergentagent.com"
OUT = "/app/frontend/public/broll"
os.makedirs(OUT, exist_ok=True)

VIEWS = ["master", "ai", "members", "settled", "live"]

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 412, "height": 900}, device_scale_factor=2)
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)  # let splash (2.5s) finish
    # remove splash if lingering
    page.evaluate("() => { const s=document.querySelector('[data-testid=\"splash-screen\"]'); if(s) s.remove(); }")
    for v in VIEWS:
        try:
            page.evaluate(f"() => window.dispatchEvent(new CustomEvent('tj-open-view', {{detail:'{v}'}}))")
            page.wait_for_timeout(6000)
            # scroll modal to top
            page.evaluate("() => { const w=document.querySelector('[data-testid=\"tips-window\"]'); if(w) w.scrollTo(0,0); }")
            page.wait_for_timeout(1000)
            page.screenshot(path=f"{OUT}/{v}.png")
            # capture a scrolled view too
            page.evaluate("() => { const w=document.querySelector('[data-testid=\"tips-window\"]'); if(w) w.scrollTo(0,600); }")
            page.wait_for_timeout(1200)
            page.screenshot(path=f"{OUT}/{v}_2.png")
            # body text snippet
            txt = page.inner_text("[data-testid='tips-window']")[:600] if page.query_selector("[data-testid='tips-window']") else "NO WINDOW"
            print(f"=== {v} ===")
            print(txt)
            print()
        except Exception as e:
            print(v, "ERR", e)
    b.close()
print("DONE")

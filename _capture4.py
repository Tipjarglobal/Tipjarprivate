import os
from playwright.sync_api import sync_playwright

URL = "https://ai-credit-saver.preview.emergentagent.com"
OUT = "/app/frontend/public/broll"

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 412, "height": 900}, device_scale_factor=2)
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(4200)
    page.evaluate("() => { const s=document.querySelector('[data-testid=\"splash-screen\"]'); if(s) s.remove(); }")
    page.evaluate("() => window.dispatchEvent(new CustomEvent('tj-open-view', {detail:'settled'}))")
    page.wait_for_timeout(5000)
    page.click('[data-testid="settled-won-toggle"]', timeout=6000)
    page.wait_for_timeout(5500)
    for i, y in enumerate([300, 850, 1450, 2050]):
        page.evaluate(f"() => {{ const w=document.querySelector('[data-testid=\"tips-window\"]'); if(w) w.scrollTo(0,{y}); }}")
        page.wait_for_timeout(1400)
        page.screenshot(path=f"{OUT}/won_{i}.png")
    b.close()
print("DONE")

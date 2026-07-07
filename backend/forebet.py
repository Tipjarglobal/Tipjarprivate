"""Forebet scraper — renders the Cloudflare-protected page with Playwright and
extracts today's football predictions (1X2, predicted score, probabilities)."""
import logging

logger = logging.getLogger("forebet")

FOREBET_URL = "https://www.forebet.com/en/football-tips-and-predictions-for-today"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


async def scrape_forebet_today(limit: int = 40) -> list[dict]:
    from playwright.async_api import async_playwright
    rows = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            ctx = await browser.new_context(user_agent=UA, locale="en-US")
            page = await ctx.new_page()
            await page.goto(FOREBET_URL, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(4000)
            rows = await page.evaluate("""(limit) => {
                const out = [];
                const rowsEl = Array.from(document.querySelectorAll('div.rcnt')).slice(0, limit);
                for (const r of rowsEl) {
                    const q = (s) => { const e = r.querySelector(s); return e ? e.textContent.trim() : null; };
                    const link = r.querySelector('a[href*="/football/matches/"]');
                    const href = link ? link.getAttribute('href') : null;
                    let matchid = null;
                    if (href) { const m = href.match(/-(\\d+)$/); if (m) matchid = m[1]; }
                    let cc = null;
                    const flag = r.querySelector('img[src*="/images/fc/"]');
                    if (flag) { const fm = (flag.getAttribute('src')||'').match(/\\/images\\/fc\\/([^\\/.]+)\\.png/); if (fm) cc = fm[1].toLowerCase(); }
                    const probs = Array.from(r.querySelectorAll('.fprc span')).map(e => parseInt(e.textContent.trim(), 10)).filter(n => !isNaN(n));
                    const fulltext = r.textContent || '';
                    const dm = fulltext.match(/(\\d{2}\\/\\d{2}\\/\\d{4}\\s+\\d{1,2}:\\d{2}\\s*[AP]M)/);
                    const homeName = q('span.homeTeam') || q('.homeTeam');
                    let lcode = null;
                    if (homeName) { const idx = fulltext.indexOf(homeName); if (idx > 0) lcode = fulltext.slice(0, idx).trim().split(/\\s+/)[0]; }
                    out.push({
                        home: q('span.homeTeam') || q('.homeTeam'),
                        away: q('span.awayTeam') || q('.awayTeam'),
                        probs: probs,
                        pred: q('.forepr'),
                        score: q('.ex_sc') || q('.tnmscr'),
                        avg: q('.avg_sc'),
                        matchid: matchid,
                        cc: cc,
                        lcode: lcode,
                        datetime: dm ? dm[1] : null
                    });
                }
                return out;
            }""", limit)
        finally:
            await browser.close()
    clean = []
    for r in rows:
        if not r.get("home") or not r.get("away") or len(r.get("probs") or []) < 3:
            continue
        clean.append(r)
    logger.info(f"Forebet: scraped {len(clean)} valid rows")
    return clean

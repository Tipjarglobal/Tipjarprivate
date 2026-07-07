"""Predictz.com scraper — renders the (bot-protected) predictions pages with
Playwright and extracts upcoming matches with a predicted score, plus the
Over/Under 2.5 and BTTS tips. Used to derive safe "10-star" goals-market
bankers (Über 0.5 / Über 1.5 / Über 2.5 / BTTS) up to ~50h before kickoff."""
import logging
import re

logger = logging.getLogger("predictz")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

BASE = "https://www.predictz.com"

# JS that reads every match row's prediction box + match id on any predictz page.
_ROW_JS = """() => {
    const out = [];
    for (const r of Array.from(document.querySelectorAll('.pttr'))) {
        const home = (r.querySelector('.ptmobh')?.textContent || '').trim();
        const away = (r.querySelector('.ptmoba')?.textContent || '').trim();
        const predEl = r.querySelector('.ptprd .ptpredboxsml');
        const pred = (predEl?.textContent || '').trim();
        let conf = 'nyellow';
        if (predEl) {
            if (predEl.classList.contains('ngreen')) conf = 'ngreen';
            else if (predEl.classList.contains('nred')) conf = 'nred';
        }
        const link = r.querySelector('a[href*="/predictions/"]');
        const href = link ? link.getAttribute('href') : '';
        let matchid = null, league = '';
        if (href) {
            const m = href.match(/\\/(\\d+)\\/?$/);
            if (m) matchid = m[1];
            const parts = href.replace(/^https?:\\/\\/[^/]+/, '').split('/').filter(Boolean);
            if (parts.length >= 3) league = parts.slice(1, -1).join(' ').replace(/-/g, ' ');
        }
        if (matchid) out.push({ home, away, pred, conf, matchid, league });
    }
    return out;
}"""


async def _rows(page, url: str) -> list[dict]:
    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(3200)
    return await page.evaluate(_ROW_JS)


async def scrape_predictz(date_paths: list[str]) -> list[dict]:
    """For each date page, also read its Over/Under 2.5 and BTTS sub-pages and
    merge the tips onto each match (keyed by matchid). date_paths e.g.
    ['/predictions/tomorrow/', '/predictions/20260710/']."""
    from playwright.async_api import async_playwright
    all_rows = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            ctx = await browser.new_context(user_agent=UA, locale="en-US")
            page = await ctx.new_page()
            for i, path in enumerate(date_paths):
                try:
                    main = await _rows(page, BASE + path)
                    ou = {r["matchid"]: r["pred"] for r in await _rows(page, BASE + path + "over-under-25-goals/")}
                    btts = {r["matchid"]: r["pred"] for r in await _rows(page, BASE + path + "both-teams-to-score/")}
                    for r in main:
                        r["ou_tip"] = ou.get(r["matchid"], "")
                        r["btts_tip"] = btts.get(r["matchid"], "")
                        r["date_path"] = path
                        r["day_offset"] = i + 1  # 1 = tomorrow, 2 = day after
                    all_rows.extend(main)
                except Exception as e:
                    logger.error(f"Predictz page {path} failed: {e}")
        finally:
            await browser.close()
    logger.info(f"Predictz: scraped {len(all_rows)} rows across {len(date_paths)} days")
    return all_rows


def parse_pred_score(pred: str):
    """'Home 1-0' / 'Away 1-2' / 'Draw 2-2' -> (home_goals, away_goals) or None."""
    m = re.search(r"(\d+)\s*-\s*(\d+)", pred or "")
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))

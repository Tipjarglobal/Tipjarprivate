"""Statarea scraper — renders old.statarea.com/predictions with Playwright and
extracts today's matches grouped by league: 1X2 probabilities, Over 1.5/2.5/3.5
probabilities and (when shown) the predicted score. A third, independent data
source that widens match coverage beyond Forebet/Predictz."""
import logging

logger = logging.getLogger("statarea")

STATAREA_URL = "https://old.statarea.com/predictions"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# Ordered walk over the predictions table: emit league headers and match rows so
# the caller can attach each match to its league. Percentages come in fixed groups
# (1X2 / halftime / Over 1.5-2.5-3.5 / handicap); we only keep 1X2 + Over lines.
_JS = r"""() => {
    const trs = Array.from(document.querySelectorAll('tr'));
    const out = [];
    for (const tr of trs) {
        const teamLinks = tr.querySelectorAll('a[href*="results_t.php"]');
        const txt = (tr.textContent || '').trim().replace(/\s+/g, ' ');
        if (teamLinks.length >= 2) {
            const home = (teamLinks[0].textContent || '').trim();
            const away = (teamLinks[1].textContent || '').trim();
            const href = teamLinks[0].getAttribute('href') || '';
            const cm = href.match(/\(([^)]+)\)/);
            const country = cm ? cm[1].trim() : '';
            const tds = Array.from(tr.querySelectorAll('td'));
            const time = (tds[0] ? tds[0].textContent : '').trim();
            let score = null;
            const sm = txt.match(/(\d+)\s*:\s*(\d+)\s*Half\s*time/i);
            if (sm) score = [parseInt(sm[1], 10), parseInt(sm[2], 10)];
            const pcts = tds.map(td => (td.textContent || '').trim())
                            .filter(t => /^\d+%$/.test(t))
                            .map(t => parseInt(t, 10));
            if (home && away) out.push({ type: 'match', home, away, country, time, score, pcts });
        } else if (txt && txt.length < 60 && /^[A-Za-z].*,.+/.test(txt)) {
            out.push({ type: 'league', text: txt });
        }
    }
    return out;
}"""


async def scrape_statarea() -> list[dict]:
    from playwright.async_api import async_playwright
    items = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            ctx = await browser.new_context(user_agent=UA, locale="en-US")
            page = await ctx.new_page()
            await page.goto(STATAREA_URL, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(3500)
            items = await page.evaluate(_JS)
        finally:
            await browser.close()

    rows, country, league = [], "", ""
    for it in items:
        if it.get("type") == "league":
            parts = it["text"].split(",", 1)
            country = parts[0].strip()
            league = parts[1].strip() if len(parts) > 1 else ""
            continue
        pcts = it.get("pcts") or []
        if len(pcts) < 3:
            continue
        p1, px, p2 = pcts[0], pcts[1], pcts[2]
        # Over 1.5/2.5/3.5 group is the 3rd triple (after 1X2 and halftime) when present.
        over15 = pcts[6] if len(pcts) >= 9 else None
        over25 = pcts[7] if len(pcts) >= 9 else None
        over35 = pcts[8] if len(pcts) >= 9 else None
        rows.append({
            "home": it["home"], "away": it["away"],
            "country": it.get("country") or country, "league": league,
            "time": it.get("time") or "", "score": it.get("score"),
            "p1": p1, "px": px, "p2": p2,
            "over15": over15, "over25": over25, "over35": over35,
        })
    logger.info(f"Statarea: scraped {len(rows)} match rows")
    return rows

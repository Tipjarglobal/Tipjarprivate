"""FootballPredictions.com scraper — a static (no-JS) source that publishes a
predicted scoreline per match. Fetched with plain requests (no Chromium needed).
Clean team names + league come from each match's JSON-LD SportsEvent block; the
predicted score and kickoff datetime come from the visible prediction card. Rows
are joined by the match URL. Widens pre-match coverage like Statarea."""
import re
import logging
import requests

logger = logging.getLogger("footballpredictions")

FP_URL = "https://footballpredictions.com/footballpredictions/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

_EVENT_RE = re.compile(
    r'"@type":\s*"SportsEvent".*?"name":\s*"([^"]+)".*?"description":\s*"([^"]+)"'
    r'.*?"url":\s*"([^"]+)".*?"startDate":\s*"([^"]+)"',
    re.DOTALL)

_CARD_RE = re.compile(
    r'Prediction:\s*<br>\s*<strong>\s*(\d+)\s*-\s*(\d+)\s*</strong>'
    r'.*?data-datetime="([^"]+)"'
    r'.*?<a href="([^"]+prediction-\d{2}-\d{2}-\d{4}/)"',
    re.DOTALL)


async def scrape_footballpredictions() -> list[dict]:
    import asyncio

    def _fetch():
        r = requests.get(FP_URL, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        return r.text

    try:
        html = await asyncio.to_thread(_fetch)
    except Exception as e:
        logger.error(f"FootballPredictions fetch failed: {e}")
        return []

    # url -> {home, away, league, date}
    events = {}
    for name, desc, url, start in _EVENT_RE.findall(html):
        if " vs " not in name:
            continue
        home, away = [s.strip() for s in name.split(" vs ", 1)]
        league = re.sub(r'^' + re.escape(name) + r'\s+', '', desc.strip())
        league = re.sub(r'\s+Match$', '', league).strip()
        if not league or league == "Match":
            league = "Club Friendly"
        events[url.strip()] = {"home": home, "away": away,
                               "league": league, "date": start.strip()}

    rows = []
    for gh, ga, dt_iso, url in _CARD_RE.findall(html):
        ev = events.get(url.strip())
        if not ev:
            continue
        rows.append({
            "home": ev["home"], "away": ev["away"], "league": ev["league"],
            "country": "", "kickoff": dt_iso.strip(),
            "ph": int(gh), "pa": int(ga),
        })
    logger.info(f"FootballPredictions: scraped {len(rows)} predicted-score rows")
    return rows

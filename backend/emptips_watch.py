"""Free X/Twitter timeline reader for the EMP Tips account (no paid API).

Reads a public profile timeline through live Nitter mirrors (rotating fallback)
and parses each tweet's text, date, permalink id and attached media images. Used
by the emptips auto-poster to turn EMP's betslip tweets into TipJar picks.
No login/keys required; best-effort (skips gracefully if all mirrors are down)."""
import re
import logging
import requests

logger = logging.getLogger("emptips_watch")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# Rotating free Nitter mirrors (order = preference). Add/remove as they live/die.
MIRRORS = [
    "https://lightbrd.com",
    "https://xcancel.com",
    "https://nitter.poast.org",
    "https://nitter.net",
]

_ITEM_RE = re.compile(
    r'<div class="timeline-item[ "].*?(?=<div class="timeline-item[ "]|<div class="show-more|</body)',
    re.DOTALL)


def _abs(mirror, src):
    if src.startswith("http"):
        return src
    if src.startswith("/"):
        return mirror + src
    return src


def _parse_items(html, mirror, handle):
    out = []
    for it in _ITEM_RE.findall(html or ""):
        if 'class="retweet-header"' in it or 'class="replying-to"' in it:
            continue  # skip retweets / replies → only EMP's own tips
        cm = re.search(r'<div class="tweet-content[^"]*"[^>]*>(.*?)</div>', it, re.DOTALL)
        text = re.sub(r'<[^>]+>', '', cm.group(1)).strip() if cm else ""
        text = re.sub(r'\s+\n', '\n', text)
        dm = re.search(r'<span class="tweet-date"><a[^>]*title="([^"]+)"', it)
        date = dm.group(1) if dm else ""
        lm = re.search(r'href="/[^"]*/status/(\d+)', it)
        tid = lm.group(1) if lm else None
        # attachment media images only (exclude avatars/emoji/profile images)
        imgs = []
        for src in re.findall(r'<img[^>]+src="([^"]+)"', it):
            if "profile_images" in src or "/emoji/" in src or "avatar" in src:
                continue
            if "media" in src or "/pic/" in src:
                imgs.append(_abs(mirror, src))
        if tid:
            out.append({"id": tid, "text": text, "date": date, "images": imgs,
                        "url": f"https://x.com/{handle}/status/{tid}"})
    return out


def fetch_timeline(handle):
    """Return a list of recent tweets [{id,text,date,images,url}] for @handle, or []
    if every mirror is unreachable."""
    handle = (handle or "").lstrip("@").strip()
    if not handle:
        return []
    for mirror in MIRRORS:
        try:
            r = requests.get(f"{mirror}/{handle}", headers={"User-Agent": UA}, timeout=12)
            if r.status_code != 200 or "timeline-item" not in r.text:
                continue
            items = _parse_items(r.text, mirror, handle)
            if items:
                logger.info(f"EMP timeline via {mirror}: {len(items)} tweets")
                return items
        except Exception as e:
            logger.info(f"EMP mirror {mirror} failed: {type(e).__name__}")
            continue
    logger.warning("EMP timeline: all mirrors unavailable")
    return []


def fetch_image(url):
    """Download a media image (via the mirror proxy or pbs.twimg). Returns bytes or None."""
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=15)
        if r.status_code == 200 and r.content:
            return r.content
    except Exception as e:
        logger.info(f"EMP image fetch failed: {type(e).__name__}")
    return None


def fetch_telegram(channel):
    """Read EMP's PUBLIC Telegram channel via the free t.me/s/ web preview (no API/keys,
    reliable). Returns [{id,text,images,url}] newest-last, or [] if unavailable. Each tip
    post carries a betslip screenshot (telesco.pe) which vision-AI turns into the legs."""
    import html as _html
    channel = (channel or "").lstrip("@").strip()
    if not channel:
        return []
    try:
        r = requests.get(f"https://t.me/s/{channel}", headers={"User-Agent": UA}, timeout=15)
        if r.status_code != 200 or "tgme_widget_message" not in r.text:
            return []
    except Exception as e:
        logger.warning(f"EMP Telegram fetch failed: {type(e).__name__}")
        return []
    out = []
    for w in re.split(r'(?=<div class="tgme_widget_message[ "])', r.text):
        mid = re.search(r'data-post="' + re.escape(channel) + r'/(\d+)"', w)
        if not mid:
            continue
        tm = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', w, re.DOTALL)
        txt = ""
        if tm:
            txt = re.sub(r'<[^>]+>', '', _html.unescape(re.sub(r'<br ?/?>', '\n', tm.group(1)))).strip()
        photos = [p for p in re.findall(r"background-image:url\('([^']+)'\)", w)
                  if "telesco" in p or "/file/" in p or "cdn" in p]
        out.append({"id": f"tg-{mid.group(1)}", "text": txt, "images": photos,
                    "url": f"https://t.me/{channel}/{mid.group(1)}"})
    logger.info(f"EMP Telegram {channel}: {len(out)} messages")
    return out


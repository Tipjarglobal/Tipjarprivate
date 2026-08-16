"""
TipJar - Universal Ticket Collector
Nimmt Scheine von Überall: Instagram, Experten, Capella Scraper etc.
Und überträgt sie direkt in Real_odds.py

Struktur:
1. Instagram (deine eigenen Posts / Stories)
2. Experten (Telegram, Discord, WhatsApp Gruppen)
3. Scraper (Capella, Tipico, Bet365 Tracker etc.)
"""

import re
from real_odds import add_real_ticket_any_language, get_real_quote_multilang, REAL_QUOTES_DB

# =================================================================
# 1. UNIVERSELLER PARSER - Egal welches Format
# =================================================================

# Regex für fast alle Schein-Formate: "PSG Über 0.5 @1.46 Wazamba" / "Lens vs PSG - Over 0.5 - 1.44 - bet365"
TICKET_PATTERNS = [
    # Format: Team Markt @Quote Anbieter  ->  "PSG Über 0.5 @1.46 Wazamba"
    r"(?P<market>[\w\s\.\-\/üÜöÖäÄéÉàáùúÜşğıİ]+?)\s*[@]\s*(?P<quote>\d+[.,]\d+)\s*(?:bei\s*)?(?P<anbieter>\w+)",
    # Format: Match - Markt @Quote  -> "Lens vs PSG - PSG Over 0.5 @1.44"
    r"(?P<match>[\w\s]+vs\.?\s+[\w\s]+)[\s\-:]+(?P<market>[\w\s\.\-\/üÜöÖäÄéÉàáùúÜşğıİ]+?)\s*[@]?\s*(?P<quote>\d+[.,]\d+)",
    # Capella Style: oft "PSG - Über 0.5 Tore - 1.50"
    r"(?P<market>[\w\s]+Über[\s\w\.]+|[\w\s]+Over[\s\w\.]+|BTTS|GG|1X|X2|12)\s*[-:]\s*(?P<quote>\d+[.,]\d+)",
]

BOOKIES = ["bet365", "wazamba", "bwin", "tipico", "unibet", "betano", "neobet", "betway", "1xbet", "pinnacle", "wettarena", "bet-at-home", "interwetten"]
SPRACHEN = {
    "de": ["über", "unter", "beide treffen", "doppelte chance"],
    "en": ["over", "under", "both to score", "double chance", "btts"],
    "es": ["mas de", "menos de", "ambas marcan", "doble oportunidad"],
    "tr": ["üst", "alt", "kg var", "her iki", "cifte sans"],
    "it": ["piu di", "meno di", "gol", "doppia chance"],
    "pl": ["powyzej", "ponizej", "obie strzela"],
}

def detect_language(text: str) -> str:
    text_low = text.lower()
    for lang, keywords in SPRACHEN.items():
        if any(k in text_low for k in keywords):
            return lang
    return "de"

def detect_anbieter(text: str, default="Unbekannt") -> str:
    text_low = text.lower()
    for b in BOOKIES:
        if b in text_low:
            return b
    return default

def extract_quote(text: str) -> float:
    """Findet die ECHTE Quote (Odds), nicht die Markt-Linie (0.5/1.5/2.5).
    Bevorzugt @1.46, sonst die letzte plausible Quote > 1.05."""
    m = re.search(r"[@]\s*(\d+[.,]\d+)", text)
    if m:
        return float(m.group(1).replace(",", "."))
    nums = [float(x.replace(",", ".")) for x in re.findall(r"\d+[.,]\d+", text)]
    if not nums:
        return 0.0
    lines = {0.5, 1.5, 2.5, 3.5, 4.5, 5.5}
    odds = [n for n in nums if n > 1.05 and n not in lines]
    return odds[-1] if odds else nums[-1]


def universal_ticket_parser(raw_text: str, default_match: str = None):
    """
    Nimmt irgendeinen Text-Schein und gibt Match, Markt, Quote, Anbieter zurück
    Egal ob Instagram Caption, Capella Scraper oder Experten-Text
    """
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return None

    quote = extract_quote(raw_text)

    # Match: expliziter Hint gewinnt (Instagram/Experten), sonst aus dem Text lesen
    match_found = default_match
    if not match_found:
        mm = re.search(r"([\w\s]{3,}?\s+vs\.?\s+[\w\s]{3,}?)(?=[\s\-:@]|$)", raw_text, re.IGNORECASE)
        if mm:
            match_found = re.sub(r"\s*-\s*", " vs ", mm.group(1)).strip()
    if not match_found:
        match_found = "Unbekanntes Match"

    # Markt = alles vor der Quote (Linie wie 0.5 bleibt drin), ohne Match/Anbieter
    market_text = re.sub(r"\s*[@]\s*\d+[.,]\d+.*$", "", raw_text)
    market_text = re.sub(r"\s*[-:]\s*\d+[.,]\d+.*$", "", market_text).strip()
    if match_found and match_found in market_text:
        market_text = market_text.replace(match_found, "").strip(" -:|")
    market_text = re.sub(r"^[\w\s]{3,}\s+vs\.?\s+[\w\s]{3,}?[\s\-:]+", "", market_text, flags=re.IGNORECASE).strip()
    if len(market_text) < 2:
        market_text = raw_text.split("@")[0].strip()

    anbieter = detect_anbieter(raw_text)
    sprache = detect_language(raw_text)

    return {
        "match": match_found,
        "market_raw": market_text,
        "quote": quote,
        "anbieter": anbieter,
        "sprache": sprache,
        "original": raw_text
    }

# =================================================================
# 2. COLLECTORS - Hier kommen deine Quellen rein
# =================================================================

def ingest_instagram(caption: str, image_ocr_text: str = "", match_hint: str = None):
    """Deine eigenen TipJar Insta Scheine"""
    # Kombiniere Caption + OCR Text aus dem Schein-Bild
    full_text = f"{caption} {image_ocr_text}".strip()
    parsed = universal_ticket_parser(full_text, default_match=match_hint)
    if parsed and parsed["quote"] > 1.0:
        add_real_ticket_any_language(
            match=parsed["match"],
            market_raw=parsed["market_raw"],
            anbieter=parsed["anbieter"],
            quote=parsed["quote"],
            sprache=parsed["sprache"]
        )
        return parsed
    return None

def ingest_experten(name: str, nachricht: str, match_hint: str = None):
    """Experten aus Telegram / Discord / WhatsApp"""
    # Experten schreiben oft: "🔥 Lens vs PSG - PSG Over 0.5 @1.44"
    parsed = universal_ticket_parser(nachricht, default_match=match_hint)
    if parsed and parsed["quote"] > 1.0:
        # Anbieter = Experten-Name als Quelle, wenn kein Bookie dabei steht
        anbieter = parsed["anbieter"] if parsed["anbieter"] != "Unbekannt" else f"experte_{name}"
        add_real_ticket_any_language(
            match=parsed["match"],
            market_raw=parsed["market_raw"],
            anbieter=anbieter,
            quote=parsed["quote"],
            sprache=parsed["sprache"]
        )
        return parsed
    return None

def ingest_capella_scraper(scraper_data: dict):
    """
    Capella oder andere Scraper liefern meist JSON:
    {"match": "RC Lens - Paris SG", "market": "PSG Over 0.5", "odd": 1.45, "bookmaker": "bet365"}
    """
    match = scraper_data.get("match", "Unbekannt")
    market_raw = scraper_data.get("market") or scraper_data.get("selection") or ""
    quote = float(str(scraper_data.get("odd") or scraper_data.get("quote") or 0).replace(",", "."))
    anbieter = scraper_data.get("bookmaker") or scraper_data.get("anbieter") or "capella"
    sprache = scraper_data.get("lang") or detect_language(market_raw)

    if quote > 1.0:
        add_real_ticket_any_language(
            match=match,
            market_raw=market_raw,
            anbieter=anbieter,
            quote=quote,
            sprache=sprache
        )
        return True
    return False

# =================================================================
# 3. BATCH IMPORT - Für viele Scheine auf einmal
# =================================================================

def batch_import(file_pfad: str):
    """
    Liest eine .txt Datei mit einem Schein pro Zeile
    Ideal für Exporte aus Insta / Telegram
    """
    try:
        with open(file_pfad, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    parsed = universal_ticket_parser(line)
                    if parsed:
                        print(f"-> Import: {parsed}")

                        add_real_ticket_any_language(
                            parsed["match"], parsed["market_raw"],
                            parsed["anbieter"], parsed["quote"], parsed["sprache"]
                        )
        print(f"\n✅ Batch Import fertig. DB hat jetzt {len(REAL_QUOTES_DB)} Matches")
    except FileNotFoundError:
        print(f"Datei {file_pfad} nicht gefunden")

# =================================================================
# 4. TEST - Zeigt dir wie es läuft
# =================================================================

if __name__ == "__main__":
    print("=== TIPJAR COLLECTOR TEST ===\n")

    # 1. Dein Instagram Post
    print("1. Instagram:")
    ingest_instagram(
        caption="PSG Über 0.5 @1.46 bei Wazamba 🔥 #tipjar",
        image_ocr_text="Lens vs PSG - PSG Über 0.5",
        match_hint="Lens vs PSG"
    )

    # 2. Experte aus Telegram
    print("\n2. Experte:")
    ingest_experten(
        name="brazino_experte",
        nachricht="Lens vs PSG - PSG Over 0.5 @1.44 bet365 - sicher!",
        match_hint="Lens vs PSG"
    )

    # 3. Capella Scraper JSON
    print("\n3. Capella Scraper:")
    ingest_capella_scraper({
        "match": "Lens vs PSG",
        "market": "PSG Más de 0.5",
        "odd": 1.48,
        "bookmaker": "bet365",
        "lang": "es"
    })
    ingest_capella_scraper({
        "match": "Lens vs PSG",
        "market": "PSG Üst 0.5",
        "odd": 1.50,
        "bookmaker": "bwin",
        "lang": "tr"
    })

    print("\n=== FINALE ECHTE QUOTE ===")
    quote, count, details = get_real_quote_multilang("Lens vs PSG", "Über 0.5")
    print(f"Match: Lens vs PSG | Markt: PSG Über 0.5")
    print(f"Echte Durchschnittsquote: {quote} aus {count} Quellen")
    print(f"Details: {details}")


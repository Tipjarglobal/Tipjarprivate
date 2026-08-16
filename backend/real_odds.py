"""
TipJar - Echte Quoten von ALLEN Anbietern + ALLEN Sprachen
V2 - Produktions-ready mit Sprach-Normalisierung
"""

from collections import defaultdict
import re
import unicodedata

def clean_text(text: str) -> str:
    """Entfernt Akzente und normalisiert: Más de 0.5 -> mas de 0.5"""
    text = text.lower().strip()
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = re.sub(r'\s+', ' ', text)
    return text

# Zentrales Übersetzungs-Mapping - Keys immer schon gecleant!
MARKET_TRANSLATION = {
    # PSG Team Tore
    "psg uber 0.5": "PSG Über 0.5",
    "psg over 0.5": "PSG Über 0.5",
    "psg mas de 0.5": "PSG Über 0.5",
    "psg ust 0.5": "PSG Über 0.5",
    "psg piu di 0.5": "PSG Über 0.5",
    "psg boven 0.5": "PSG Über 0.5",
    "psg powyzej 0.5": "PSG Über 0.5",

    # Generisch Über/Under
    "uber 0.5": "Über 0.5",
    "over 0.5": "Über 0.5",
    "mas de 0.5": "Über 0.5",
    "ust 0.5": "Über 0.5",
    "powyzej 0.5": "Über 0.5",
    "boven 0.5": "Über 0.5",

    "uber 1.5": "Über 1.5",
    "over 1.5": "Über 1.5",
    "mas de 1.5": "Über 1.5",

    "uber 2.0": "Über 2.0",
    "over 2.0": "Über 2.0",
    "asian over 2.0": "Über 2.0",
    "asian uber 2.0": "Über 2.0",

    "uber 2.5": "Über 2.5",
    "over 2.5": "Über 2.5",

    "unter 2.5": "Unter 2.5",
    "under 2.5": "Unter 2.5",
    "menos de 2.5": "Unter 2.5",
    "alt 2.5": "Unter 2.5",

    # BTTS
    "btts": "Beide treffen",
    "both to score": "Beide treffen",
    "gg": "Beide treffen",
    "both teams to score": "Beide treffen",
    "beide treffen": "Beide treffen",
    "ambas marcan": "Beide treffen",
    "gol gol": "Beide treffen",
    "her iki takim gol atar": "Beide treffen",

    # Doppelte Chance
    "1x": "1X",
    "double chance 1x": "1X",
    "doppelte chance 1x": "1X",
    "doble oportunidad 1x": "1X",
    "x2": "X2",
    "double chance x2": "X2",
    "12": "12",
}

# DB Struktur: { match: { market: { anbieter: {quote, sprache, raw} } } }
REAL_QUOTES_DB = defaultdict(lambda: defaultdict(dict))

def normalize_market(market_text: str) -> str:
    """Macht aus jeder Sprache den gleichen Standard Key"""
    key = clean_text(market_text)
    return MARKET_TRANSLATION.get(key, market_text.strip())

def add_real_ticket_any_language(match: str, market_raw: str, anbieter: str, quote: float, sprache="de"):
    """
    Egal welche Sprache im Schein steht - wird erkannt
    z.B.:
    - Deutsch: "PSG Über 0.5 @1.46 bei Wazamba"
    - Englisch: "PSG Over 0.5 @1.44 Bet365"
    - Spanisch: "PSG Más de 0.5 @1.48"
    - Türkisch: "PSG Üst 0.5 @1.50"
    """
    market = normalize_market(market_raw)
    anbieter_key = anbieter.lower().strip()

    REAL_QUOTES_DB[match][market][anbieter_key] = {
        "quote": float(quote),
        "sprache": sprache.lower(),
        "raw": market_raw
    }

    alle_quoten = [v["quote"] for v in REAL_QUOTES_DB[match][market].values()]
    durchschnitt = round(sum(alle_quoten) / len(alle_quoten), 3) if alle_quoten else 0

    print(f"✅ [{sprache.upper()}|{anbieter}] {match} | '{market_raw}' -> '{market}' = {quote} | Ø {durchschnitt} ({len(alle_quoten)} Anbieter)")
    return durchschnitt

def get_real_quote_multilang(match: str, market_in_any_language: str):
    """Egal welche Sprache du abfragst, bekommst echte Quote + Anzahl"""
    market = normalize_market(market_in_any_language)
    if match in REAL_QUOTES_DB and market in REAL_QUOTES_DB[match]:
        alle = [v["quote"] for v in REAL_QUOTES_DB[match][market].values()]
        avg = round(sum(alle)/len(alle), 3) if alle else None
        return avg, len(alle), REAL_QUOTES_DB[match][market]
    return None, 0, {}

def get_all_quotes_for_match(match: str):
    """Gibt alle Märkte für ein Match zurück"""
    return dict(REAL_QUOTES_DB.get(match, {}))


# ── Persistenz-Helfer (für MongoDB in der App) ───────────────────────
def snapshot_providers(match: str, market: str) -> dict:
    """Anbieter-Dict eines (Match, Markt) für die Persistenz."""
    return dict(REAL_QUOTES_DB.get(match, {}).get(market, {}))


def hydrate(docs) -> int:
    """Lädt gespeicherte Dokumente {match, market, providers} in die In-Memory-DB."""
    n = 0
    for d in docs or []:
        match, market = d.get("match"), d.get("market")
        providers = d.get("providers") or {}
        if not match or not market:
            continue
        for anbieter_key, v in providers.items():
            REAL_QUOTES_DB[match][market][anbieter_key] = v
            n += 1
    return n

# BEISPIEL - Alle Sprachen lernen
if __name__ == "__main__":
    # Deutscher Schein
    add_real_ticket_any_language("Lens vs PSG", "PSG Über 0.5", "wazamba", 1.46, "de")
    # Englischer Schein - gleicher Markt!
    add_real_ticket_any_language("Lens vs PSG", "PSG Over 0.5", "bet365", 1.44, "en")
    # Spanischer Schein - gleicher Markt! Überschreibt bet365
    add_real_ticket_any_language("Lens vs PSG", "PSG Más de 0.5", "bet365", 1.48, "es")
    # Türkischer Schein
    add_real_ticket_any_language("Lens vs PSG", "PSG Üst 0.5", "bwin", 1.50, "tr")
    # Italienisch
    add_real_ticket_any_language("Lens vs PSG", "PSG Più di 0.5", "unibet", 1.45, "it")

    print("\n--- DB Inhalt ---")
    import json
    # defaultdict zu normalem dict für print
    print(json.dumps({k: dict(v) for k,v in REAL_QUOTES_DB.items()}, indent=2, ensure_ascii=False))

    print(f"\n--- TipJar zeigt jetzt egal welche Sprache ---")
    for abfrage in ["Über 0.5", "Over 0.5", "Más de 0.5", "Üst 0.5"]:
        q, count, _ = get_real_quote_multilang("Lens vs PSG", f"PSG {abfrage}")
        print(f"{abfrage:15} -> Ø {q} aus {count} Bookies")

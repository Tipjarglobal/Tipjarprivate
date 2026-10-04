"""TipJar owner's Money-Glitch Lexikon - IMPROVED GENERELL

Central knowledge base + GENERELLER Safety Glitch Melder für TipJarMaster
Jede Master Pille hat IMMER einen Safe drin
Speech Blase meldet Safety Glitches für ALLE Teams generisch

Beispiele die du genannt hast:
- Ludogorets trifft und verliert nicht
- Antwerp trifft  
- Porto wird 1 bis 4 mal treffen
-> Aber gilt jetzt für JEDES Team generisch
"""

FLAGS = {
    "Bulgarien": "🇧🇬", "Niederlande": "🇳🇱", "Belgien": "🇧🇪", "Norwegen": "🇳🇴",
    "Portugal": "🇵🇹", "Türkei": "🇹🇷", "Frankreich": "🇫🇷", "Serbien": "🇷🇸",
    "Dänemark": "🇩🇰", "Schweiz": "🇨🇭", "Spanien": "🇪🇸",
    "Deutschland": "🇩🇪", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Italien": "🇮🇹", "Österreich": "🇦🇹",
    "Polen": "🇵🇱", "Kroatien": "🇭🇷", "Griechenland": "🇬🇷", "Schweden": "🇸🇪",
    "Schottland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Irland": "🇮🇪", "Ungarn": "🇭🇺", "Rumänien": "🇷🇴",
    "Tschechien": "🇨🇿", "Slowakei": "🇸🇰", "Ukraine": "🇺🇦", "Russland": "🇷🇺",
    "Island": "🇮🇸", "Finnland": "🇫🇮", "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿", "Albanien": "🇦🇱",
    "Bosnien": "🇧🇦", "Mazedonien": "🇲🇰", "Slowenien": "🇸🇮", "Zypern": "🇨🇾",
    "Malta": "🇲🇹", "Luxemburg": "🇱🇺", "Andorra": "🇦🇩", "Liechtenstein": "🇱🇮",
    "Aserbaidschan": "🇦🇿", "Armenien": "🇦🇲", "Georgien": "🇬🇪", "Kasachstan": "🇰🇿",
    "Israel": "🇮🇱", "Saudi-Arabien": "🇸🇦", "VAE": "🇦🇪", "Katar": "🇶🇦",
    "Japan": "🇯🇵", "Südkorea": "🇰🇷", "China": "🇨🇳", "Australien": "🇦🇺",
    "Brasilien": "🇧🇷", "Argentinien": "🇦🇷", "USA": "🇺🇸", "Mexiko": "🇲🇽",
    "Ägypten": "🇪🇬", "Marokko": "🇲🇦", "Nigeria": "🇳🇬", "Südafrika": "🇿🇦",
    "Chile": "🇨🇱", "Kolumbien": "🇨🇴", "Peru": "🇵🇪", "Uruguay": "🇺🇾",
    "Ecuador": "🇪🇨", "Paraguay": "🇵🇾",
}

GLITCH_LEXIKON = {
    "TYP1_HINSPIEL": {
        "beschreibung": "2. KO-Runde – Hinspiel gewonnen, Qualifikation in regulärer Zeit kaufen 1.05-1.06",
        "logik": "Hinspiel schon gewonnen. Wettanbieter denkt: schon durch. Wahrheit: Gegner muss aufmachen, gibt Konter. 'Quali in reg. Zeit' ist sicherer als der reine Sieg.",
        "quote_range": "1.02 - 1.15",
        "markt": "Winning method / To qualify in regular time",
    },
    "TYP2_BUILDER_KORRELATION": {
        "beschreibung": "X2 + Über 0.5 + Unter 5.5 auf defensiv stabiles Team = 1-5 Tore, kein 0:0",
        "logik": "Defensiv starkes Team (z.B. Porto) kassiert nicht leicht → Unter 5.5 safe + X2 safe = Glitch. 0:1, 0:2, 1:1, 1:2, 2:2 wahrscheinlich.",
        "quote_range": "1.23 - 1.81",
        "markt": "Double Chance + Over 0.5 + Under 5.5 / Bet-Builder",
    },
    "TYP3_LIVE_OVER": {
        "beschreibung": "Live Over wenn beide noch drücken, Quote noch zu hoch",
        "logik": "Live-Quote denkt: schon viele Tore, unwahrscheinlich noch eins. Du siehst: beide drücken, hoher xG, noch ~20 Min.",
        "quote_range": "1.40 - 1.70",
        "markt": "Live Total Over",
    },
    "TYP4_IMMER_LIEFERANTEN": {
        "beschreibung": "Spieler die IMMER ihre Schüsse liefern – aber Line-Minimum beachten",
        "logik": "Salah-Line startet erst bei 1.5 (kein 0.5) → nur als Starter nehmen. Karetsas/Zafeiris haben 0.5 = echter Glitch. Dembélé 0.5 SOT, Antwerp Team Über 0.5.",
        "quote_range": "1.30 - 1.50",
        "markt": "Spieler-Schüsse / Team Über 0.5",
        "immer_liste": ["Salah (nur Starter, Line ab 1.5)", "Karetsas 0.5", "Zafeiris 0.5", "Dembélé 0.5 SOT", "Antwerp Team 0.5"],
    },
    "TYP5_DNB_SICHERHEIT": {
        "beschreibung": "Draw No Bet statt 1X2 für Kombi-Sicherheit",
        "logik": "Statt Sieg 1.80 → DNB 1.27. Bei Unentschieden Push statt Verlust. Perfekt für Kombis.",
        "quote_range": "1.25 - 1.35",
        "markt": "Draw No Bet",
    },
    "TYP6_SHOTS_DOMINANZ": {
        "beschreibung": "Team hinten auf aggregate dominiert Schüsse, trifft aber spät",
        "logik": "Hinspiel verloren, Rückspiel muss das Team → Schuss-Dominanz kommt, Tore aber spät (0:0 bis 70', dann Damm bricht). Für Live: Over ab 70' bei 0:0.",
        "quote_range": "1.35 - 1.50",
        "markt": "1X2 Total Shots / Live Over spät",
    },
    "TYP7_MASTER_TOR_ASSIST": {
        "beschreibung": "Flügelspieler die 'trifft oder Assist' liefern – doppelte Chance",
        "logik": "Wettanbieter multipliziert Tor × Assist, aber Korrelation ist hoch. 'Trifft oder Assist' = doppelte Chance, Quote noch zu hoch. Tzolis/Karetsas immer an Toren beteiligt.",
        "quote_range": "1.40 - 2.20",
        "markt": "Player to score or assist",
        "spieler": ["Tzolis", "Karetsas", "Salah", "Dembélé"],
    },
    "TYP8_LUCAS_1HZ_TOR": {
        "beschreibung": "LUCAS LIVE: frühe 1.-Halbzeit-Tore, Over 0.5/1.5 1.Ht in Min 5-15",
        "logik": "Live 0-15 Min scannen: hoher xG, viele Schüsse/Ecken/Dangerous Attacks. Quote noch 1.7+ für Over 0.5/1.5 1.Ht bei 0:0 → Glitch, Druck erzwingt Tor.",
        "quote_range": "1.70 - 1.82",
        "markt": "Total Over (0.5/1.5) 1st half LIVE",
    },
    "TYP9_SIEG_BTTS": {
        "beschreibung": "Top-Team Sieg + BTTS vs offensiver Gegner @~2.40",
        "logik": "Top-Team zu Hause: Anbieter denkt 3:0/4:0. Realität: gewinnt, kassiert aber 1 Tor (hoch verteidigt + Gegner-Konter). Sieg+BTTS (3:1, 2:1, 4:1) viel wahrscheinlicher.",
        "quote_range": "2.20 - 2.80",
        "markt": "Win + Both Teams To Score",
        "teams": ["Bayern", "Man City", "PSG", "Real", "Barca vs Top 6"],
    },
}

# === NEU: GENERELLER Safety Speech für TipJarMaster Bubble ===
SAFETY_SPEECH_TEMPLATES = {
    "TYP5_DNB_SICHERHEIT": "🛡️ {team} trifft und verliert nicht",
    "TYP1_HINSPIEL": "🛡️ {team} trifft und verliert nicht",
    "TYP4_IMMER_LIEFERANTEN": "⚽ {team} trifft",
    "TYP2_BUILDER_KORRELATION": "🔒 {team} wird 1 bis 4 mal treffen",
    "TYP7_MASTER_TOR_ASSIST": "🎯 {team} trifft oder bereitet vor",
    "TYP9_SIEG_BTTS": "🎯 {team} trifft und gewinnt mit Gegentor",
    "TYP8_LUCAS_1HZ_TOR": "⏰ {team} trifft vor Pause",
    "TYP6_SHOTS_DOMINANZ": "📈 {team} Chancen-Überhang - trifft",
    "TYP3_LIVE_OVER": "⏱️ {team} Over spät - beide brauchen Tor",
}

def get_safety_speech(team: str, glitch_key: str) -> str:
    """GENERELL für JEDES Team - z.B. Ludogorets, Antwerp, Porto oder irgendein Team"""
    # Normalisiere Key
    key = glitch_key.replace("🎁 ","").replace("🔒 ","").strip()
    # Suche passenden Template Key
    for k in SAFETY_SPEECH_TEMPLATES:
        if k in key or key in k:
            return SAFETY_SPEECH_TEMPLATES[k].format(team=team)
    # Fallback nach detect
    if "TYP5" in key or "TYP1" in key or "DNB" in key or "X2" in key:
        return f"🛡️ {team} trifft und verliert nicht"
    if "TYP2" in key and "PORTO" in key:
        return f"🔒 {team} wird 1 bis 4 mal treffen"
    if "TYP4" in key or "TYP2" in key:
        return f"⚽ {team} trifft"
    return f"✅ {team} Safety Call"

def detect_glitch(market, quote, first_leg=None, minute=None, notes=""):
    """Auto-tag a bet with the matching glitch type. Returns '' if none matches."""
    m = (market or "").lower()
    try:
        q = float(quote) if quote not in (None, "") else None
    except (TypeError, ValueError):
        q = None
    try:
        mi = int(minute) if minute not in (None, "") else None
    except (TypeError, ValueError):
        mi = None

    if any(x in m for x in ["1st half", "1. ht", "1.ht", "1.hz", "1. halbzeit"]):
        if q and q >= 1.70:
            return "🎁 TYP8 LUCAS 1HZ"
        return "📈 1HZ TOR"
    if any(x in m for x in ["trifft oder", "score or assist", "tor oder assist", "goal or assist"]):
        return "🎁 TYP7 MASTER TOR+ASSIST"
    if "tzolis" in m and any(x in m for x in ["assist", "trifft", "score"]):
        return "🎁 TYP7 MASTER TZOLIS"
    if first_leg and ("regular time" in m or "winning method" in m) and q and q <= 1.15:
        return "🎁 TYP1 HINSPIEL"
    if "over 1" in m and first_leg and q and q <= 1.10:
        return "🎁 TYP1 HINSPIEL"
    if "total shots" in m or "1x2 total" in m:
        return "🎁 TYP6 SHOTS"
    if ("über 0.5" in m or "over 0.5" in m) and "unter 5.5" in m:
        return "🎁 TYP2 PORTO 1-5"
    if "+" in (market or "") and ("shot" in m or "schuss" in m) and ("over 0.5" in m or "über 0.5" in m):
        return "🎁 TYP2 BUILDER"
    if "1x" in m and ("über 0.5" in m or "over 0.5" in m):
        return "🎁 TYP2 BUILDER"
    if mi and mi >= 70 and ("über" in m or "over" in m) and q and q >= 1.40:
        return "🎁 TYP3 LIVE"
    if any(name in m for name in ["salah", "karetsas", "zafeiris", "dembele", "dembélé"]) and ("schuss" in m or "shot" in m):
        return "🎁 TYP4 IMMER"
    if "antwerp" in m and ("über 0.5" in m or "over 0.5" in m):
        return "🎁 TYP4 IMMER"
    if any(x in m for x in ["draw no bet", "dnb", "unentschieden keine wette"]):
        return "🔒 TYP5 DNB"
    if any(x in m for x in ["sieg", "win", "gewinnt"]) and any(x in m for x in ["btts", "both to score", "beide treffen"]):
        return "🎁 TYP9 SIEG+BTTS"
    return ""

def build_avatar_speech_for_tip(tip: dict) -> str:
    """
    Baut Safety Speech für einen Tip - GENERELL für alle Teams
    Input: tip dict mit home_team, away_team, market
    Output: "Ludogorets trifft und verliert nicht" etc. generisch
    """
    home = tip.get("home_team","Team")
    away = tip.get("away_team","")
    market = tip.get("market","")
    glitch = detect_glitch(market, tip.get("odds"))
    # Team raten
    team = home
    if away and away.lower() in market.lower():
        team = away
    # Wenn Market enthält "Team XY" nimm das
    if "team" in market.lower():
        # Versuche Team aus Market zu extrahieren
        for t in [home, away]:
            if t.lower() in market.lower():
                team = t
                break
    return get_safety_speech(team, glitch) if glitch else f"⚽ {team} trifft"

def master_pille_must_have_safe(legs: list) -> list:
    """Stellt sicher: Jede Master Pille hat IMMER einen Safe drin"""
    has_safe = False
    for leg in legs:
        m = (leg.get("market","") if isinstance(leg, dict) else str(leg)).lower()
        if any(k in m for k in ["draw no bet", "dnb", "über 0.5", "over 0.5", "trifft", "x2", "1x"]):
            has_safe = True
            break
    if not has_safe and legs:
        first = legs[0]
        team = first.get("home_team","Team") if isinstance(first, dict) else "Team"
        legs.insert(0, {"market": f"{team} Draw No Bet", "glitch": "TYP5_DNB", "is_banker": True, "home_team": team})
    return legs

LEXIKON_PROMPT_BLOCK = (
    " OWNER VALUE-PATTERN LEXIKON — when a slip matches one of these known profitable patterns, "
    "treat it as a strong, SAFE value play (rate it HIGH) and name the pattern briefly in the analysis: "
    "(1) 2nd-KO-round second leg where the first leg was already won: 'qualify in regular time' @~1.05 is safer than a plain win. "
    "(2) Double-chance/X2 + Over 0.5 + Under 5.5 on a defensively solid side (e.g. Porto) = 1-5 total goals, very safe. "
    "(3) LIVE Over when the game is tied/high-scoring and BOTH teams still push with ~20 min left and odds still >=1.40. "
    "(4) Reliable shot providers: Salah (line starts at 1.5, only if he STARTS), Karetsas 0.5, Zafeiris 0.5, Dembélé 0.5 shots-on-target, Antwerp team Over 0.5. "
    "(5) Draw No Bet on a clear favourite instead of the 1X2 win, for combo safety (~1.25-1.35). "
    "(6) Team trailing on aggregate dominates shots but scores late — 1X2-total-shots or late live Over. "
    "(7) Wingers who score-or-assist most games (Tzolis, Karetsas): 'to score or assist' is under-priced double-chance value. "
    "(8) LUCAS live 1st-half Over: at 0:0 or 1:0 in minute 5-15 with high xG/shots/corners, Over 0.5/1.5 1st half @~1.70+. "
    "(9) Top team WIN + BTTS (Bayern, Man City, PSG, Real vs an offensive opponent) @~2.2-2.8 — they win but concede once."
)

def brain_lessons():
    out = []
    for key, d in GLITCH_LEXIKON.items():
        out.append({
            "id": f"glitch-{key.lower()}",
            "topic": f"Glitch {key}",
            "lesson": f"{d['beschreibung']} — {d['logik']} (Quote {d.get('quote_range','')}, Markt: {d.get('markt','')})",
        })
    return out

# Demo GENERELL
if __name__ == "__main__":
    print("=== GENERELLER Safety Speech Test ===")
    tests = [
        {"home_team":"Ludogorets", "market":"Draw No Bet", "odds":1.27},
        {"home_team":"Antwerp", "market":"Antwerp Team Über 0.5", "odds":1.30},
        {"home_team":"Porto", "market":"X2 + Über 0.5 + Unter 5.5", "odds":1.23},
        {"home_team":"Bayern", "market":"Bayern Sieg + BTTS", "odds":2.40},
        {"home_team":"Irgendein Team", "market":"Über 0.5", "odds":1.25},
    ]
    for t in tests:
        print(build_avatar_speech_for_tip(t))

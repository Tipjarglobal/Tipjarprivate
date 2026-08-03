"""TipJar bet-ticket image rendering (extracted from server.py 2026-07-24).
Pure, self-contained slip helpers + the premium ticket renderer.
"""
import os
import re
import io


def _fmt_selection(sel: str) -> str:
    """Mirror of the frontend formatSelection: clean bookmaker raw text into proper labels."""
    s = (sel or "").strip()
    if not s:
        return s
    m = re.match(r"^total\s+(?:over|über|ueber)\s+(\d+(?:[.,]\d+)?)", s, re.I)
    if m:
        return f"Über {m.group(1).replace(',', '.')} Tore"
    m = re.match(r"^total\s+(?:under|unter)\s+(\d+(?:[.,]\d+)?)", s, re.I)
    if m:
        return f"Unter {m.group(1).replace(',', '.')} Tore"
    if re.search(r"handicap|über|unter|\btore\b|torsch|chance|treffen|draw no bet|ergebnis|btts|\bover\b|\bunder\b", s, re.I):
        return s
    m = re.match(r"^(.+?)\s([+-]?\d+(?:[.,]\d+)?)$", s)
    if m:
        n = m.group(2).replace(",", ".")
        if not n.startswith(("+", "-")):
            n = "+" + n
        return f"{m.group(1).strip()} Handicap {n}"
    return s


def _to_float(v) -> float:
    try:
        return float(str(v or "0").replace(",", ".").replace("€", "").strip())
    except Exception:
        return 0.0


def _split_match(match: str):
    parts = re.split(r"\s[–-]\s|\svs\.?\s", match or "", maxsplit=1)
    home = parts[0].strip() if parts else (match or "")
    away = parts[1].strip() if len(parts) > 1 else ""
    return home, away


def _tip_to_render_legs(tip: dict) -> list:
    """Convert a stored member tip into _render_slip_image legs (one per selection)."""
    rlegs = []
    for lg in (tip.get("legs") or []):
        home, away = _split_match(lg.get("match") or "")
        sels = lg.get("selections") or []
        sodds = lg.get("sel_odds") or []
        combo = lg.get("combo_odds")  # one manual bet-builder odd for the whole game
        for i, sel in enumerate(sels):
            od = _to_float(sodds[i]) if i < len(sodds) else 0.0
            rlegs.append({"home": home, "away": away, "market": _fmt_selection(sel),
                          "odds": od, "result": "open", "combo_odds": combo,
                          "league": lg.get("league", ""), "country": lg.get("country", ""),
                          "date": "", "time": lg.get("kickoff", ""),
                          "banker": bool(lg.get("banker")),
                          "live": bool(lg.get("live")), "live_score": lg.get("live_score") or "",
                          "live_min": lg.get("live_minute")})
    if not rlegs:
        rlegs.append({"home": tip.get("home_team", ""), "away": tip.get("away_team", ""),
                      "market": _fmt_selection(tip.get("market", "")), "odds": _to_float(tip.get("odds")),
                      "result": "open", "league": tip.get("league", ""),
                      "country": tip.get("country", ""), "date": "",
                      "time": tip.get("match_time", "")})
    return rlegs


FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")
CREST_PATH = "/app/frontend/public/tipjar-crest.png"


# Localized labels for the share ticket (owner 2026-06: image text follows the viewer's
# selected app language). Keys kept minimal — only the strings drawn on the ticket.
_TICKET_LABELS = {
    "en": {"open": "OPEN", "live": "LIVE", "won": "WON", "parlay": "PARLAY", "system": "SYSTEM",
           "game": "GAME", "games": "GAMES", "banker": "BANKER", "total": "TOTAL ODDS",
           "max": "MAX ODDS", "stake": "STAKE", "win": "WIN", "poss_win": "POSS. WIN",
           "paid": "PAID OUT", "community": "COMMUNITY PICK", "livepick": "LIVE PICK"},
    "de": {"open": "OFFEN", "live": "LIVE", "won": "GEWONNEN", "parlay": "PARLAY", "system": "SYSTEM",
           "game": "SPIEL", "games": "SPIELE", "banker": "BANKER", "total": "GESAMTQUOTE",
           "max": "MAX. QUOTE", "stake": "EINSATZ", "win": "GEWINN", "poss_win": "MÖGL. GEWINN",
           "paid": "AUSGEZAHLT", "community": "COMMUNITY-TIPP", "livepick": "LIVE-PICK"},
    "es": {"open": "ABIERTO", "live": "EN VIVO", "won": "GANADO", "parlay": "COMBINADA", "system": "SISTEMA",
           "game": "PARTIDO", "games": "PARTIDOS", "banker": "SEGURO", "total": "CUOTA TOTAL",
           "max": "CUOTA MÁX", "stake": "APUESTA", "win": "GANANCIA", "poss_win": "GAN. POSIBLE",
           "paid": "PAGADO", "community": "PICK COMUNIDAD", "livepick": "PICK EN VIVO"},
    "el": {"open": "ΑΝΟΙΧΤΟ", "live": "LIVE", "won": "ΚΕΡΔΙΣΜΕΝΟ", "parlay": "ΠΑΡΟΛΙ", "system": "ΣΥΣΤΗΜΑ",
           "game": "ΑΓΩΝΑΣ", "games": "ΑΓΩΝΕΣ", "banker": "ΣΤΑΝΤΑΡ", "total": "ΣΥΝΟΛΙΚΗ ΑΠΟΔΟΣΗ",
           "max": "ΜΕΓ. ΑΠΟΔΟΣΗ", "stake": "ΠΟΝΤΑΡΙΣΜΑ", "win": "ΚΕΡΔΟΣ", "poss_win": "ΠΙΘ. ΚΕΡΔΟΣ",
           "paid": "ΕΞΟΦΛΗΘΗΚΕ", "community": "ΤΙΠ ΚΟΙΝΟΤΗΤΑΣ", "livepick": "LIVE ΤΙΠ"},
    "fr": {"open": "OUVERT", "live": "LIVE", "won": "GAGNÉ", "parlay": "COMBINÉ", "system": "SYSTÈME",
           "game": "MATCH", "games": "MATCHS", "banker": "SÛR", "total": "COTE TOTALE",
           "max": "COTE MAX", "stake": "MISE", "win": "GAIN", "poss_win": "GAIN POSS.",
           "paid": "PAYÉ", "community": "PICK COMMUNAUTÉ", "livepick": "PICK LIVE"},
    "it": {"open": "APERTA", "live": "LIVE", "won": "VINTA", "parlay": "MULTIPLA", "system": "SISTEMA",
           "game": "PARTITA", "games": "PARTITE", "banker": "SICURO", "total": "QUOTA TOTALE",
           "max": "QUOTA MAX", "stake": "PUNTATA", "win": "VINCITA", "poss_win": "VINCITA POSS.",
           "paid": "PAGATO", "community": "PICK COMUNITÀ", "livepick": "PICK LIVE"},
    "ar": {"open": "مفتوحة", "live": "مباشر", "won": "فائزة", "parlay": "مجمعة", "system": "نظام",
           "game": "مباراة", "games": "مباريات", "banker": "مضمون", "total": "إجمالي الأودز",
           "max": "أقصى أودز", "stake": "الرهان", "win": "الربح", "poss_win": "الربح المحتمل",
           "paid": "مدفوع", "community": "توقع المجتمع", "livepick": "توقع مباشر"},
    "tr": {"open": "AÇIK", "live": "CANLI", "won": "KAZANDI", "parlay": "KOMBİNE", "system": "SİSTEM",
           "game": "MAÇ", "games": "MAÇLAR", "banker": "BANKO", "total": "TOPLAM ORAN",
           "max": "MAKS ORAN", "stake": "BAHİS", "win": "KAZANÇ", "poss_win": "OLASI KAZANÇ",
           "paid": "ÖDENDİ", "community": "TOPLULUK TAHMİNİ", "livepick": "CANLI TAHMİN"},
}


def _render_slip_image(legs, total_odds, stake, winnings, username, ctype, live_info=None,
                       lang="de", bet_type="", system_from=0, system_total=0) -> bytes:
    """Premium TipJar bet-ticket (v6) — a dark, glossy portrait 'ticket' with a gradient
    stage, volt accents, glassy leg panels, a status glow, a tear-off perforation and a
    scannable QR that links back to tipjarglobal.com. Same signature as before."""
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    import io
    from server import _match_key

    def font(name, sz):
        try:
            if name == "FB":   # universal bold fallback (Greek/Cyrillic/Arabic)
                return ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf", sz)
            if name == "FBR":  # universal regular fallback
                return ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", sz)
            return ImageFont.truetype(os.path.join(FONT_DIR, name + ".ttf"), sz)
        except Exception:
            try:
                return ImageFont.truetype(
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", sz)
            except Exception:
                return ImageFont.load_default()

    # display / body font families (bundled OFL fonts)
    DISPLAY = "Anton-Regular"          # big odds & wordmark
    HEAD = "BarlowCondensed-Bold"      # match titles, status
    HEADS = "BarlowCondensed-SemiBold"
    BODY_B = "Barlow-Bold"
    BODY_S = "Barlow-SemiBold"
    BODY_M = "Barlow-Medium"
    BODY = "Barlow-Regular"

    def _fb(txt):
        # any glyph beyond Latin Extended-B → bundled Latin fonts render tofu boxes
        return any(ord(c) > 0x024F for c in (txt or ""))

    def famfor(family, txt):
        """Swap to the universal FreeSans fallback for non-Latin text (Greek/Cyrillic/Arabic)."""
        if not _fb(txt):
            return family
        return "FBR" if family in (BODY, BODY_M, BODY_S) else "FB"

    _scratch = ImageDraw.Draw(Image.new("RGB", (4, 4)))

    def tw(txt, fnt):
        return _scratch.textlength(txt or "", font=fnt)

    def trunc(txt, fnt, maxw):
        txt = txt or ""
        if tw(txt, fnt) <= maxw:
            return txt
        while txt and tw(txt + "…", fnt) > maxw:
            txt = txt[:-1]
        return (txt + "…") if txt else ""

    def fit(txt, family, hi, lo, maxw):
        for sz in range(hi, lo - 1, -1):
            f = font(family, sz)
            if tw(txt, f) <= maxw:
                return f
        return font(family, lo)

    def lfont(family, sz, txt):
        """Label font that swaps to the universal FreeSans fallback for non-Latin (Greek/
        Cyrillic/Arabic) label text so localized ticket labels never render as tofu boxes."""
        return font(famfor(family, txt), sz)

    def _clean(p):
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})", p or "")
        if m:
            return f"{m.group(3)}.{m.group(2)} · {m.group(4)}:{m.group(5)}"
        return p or ""

    # ---- palette ----------------------------------------------------------
    BG_TOP, BG_BOT = (16, 18, 25), (7, 8, 12)
    PANEL = (23, 26, 34)
    PANEL_EDGE = (48, 53, 66)
    INK, SOFT, MUTE, FAINT = (244, 246, 250), (196, 201, 212), (150, 156, 170), (108, 114, 128)
    VOLT = (202, 240, 0)
    CYAN = (56, 209, 236)
    GREEN, RED, AMBER, LIVE = (52, 211, 130), (244, 82, 74), (245, 190, 46), (255, 92, 92)
    won = ctype not in ("pending", "live_pending")
    is_live = ctype == "live_pending"
    LB = _TICKET_LABELS.get(lang or "de", _TICKET_LABELS["de"])
    is_system = (bet_type or "").lower() == "system" and int(system_total or 0) > 0
    STATUS = LIVE if is_live else (AMBER if ctype == "pending" else GREEN)
    status_txt = LB["live"] if is_live else (LB["open"] if ctype == "pending" else LB["won"])

    W = 1080
    M = 34                 # outer margin (gradient stage → ticket)
    P = 42                 # ticket inner padding
    cx0 = M + P
    cx1 = W - M - P
    cw = cx1 - cx0         # content width

    # ---- fonts ------------------------------------------------------------
    f_logo = font(DISPLAY, 62)
    f_tag = font(HEADS, 24)
    f_status = font(HEAD, 34)
    f_chip = font(BODY_B, 26)
    f_market = font(BODY_M, 36)
    f_legodds = font(DISPLAY, 40)
    f_meta = font(BODY_M, 26)
    f_score = font(HEAD, 36)
    f_user = font(HEAD, 46)
    f_label = font(BODY_S, 26)
    f_small = font(BODY_M, 24)
    f_total = font(DISPLAY, 118)
    f_fval = font(HEAD, 46)
    f_url = font(BODY_B, 26)

    # ---- group legs by match ---------------------------------------------
    # Cap by SELECTIONS generously (a game can carry several bet-builder markets), so a
    # 6-game slip with ~5 markets each isn't cut down to 3 games (owner 2026-07-26).
    legs = (legs or [])[:90]
    groups, gidx = [], {}
    for l in legs:
        k = _match_key(l.get("home", ""), l.get("away", ""))
        if k not in gidx:
            gidx[k] = len(groups)
            groups.append({"home": l.get("home", "?") or "?", "away": l.get("away", "?") or "",
                           "league": l.get("league", ""), "country": l.get("country", ""),
                           "date": l.get("date", ""),
                           "time": l.get("time", ""), "result": "", "mkts": [], "combo_odds": None,
                           "banker": False, "live": False, "live_score": "", "live_min": None})
        if l.get("combo_odds") and not groups[gidx[k]]["combo_odds"]:
            groups[gidx[k]]["combo_odds"] = l.get("combo_odds")
        if not groups[gidx[k]]["result"]:
            r = str(l.get("result") or "").strip()
            if r and r.lower() not in ("open", "offen", "won", "lost", "gewonnen",
                                       "verloren", "pending", "void", "-"):
                groups[gidx[k]]["result"] = r
        if l.get("banker"):
            groups[gidx[k]]["banker"] = True
        if l.get("live") and l.get("live_score"):
            groups[gidx[k]]["live"] = True
            groups[gidx[k]]["live_score"] = str(l.get("live_score") or "")
            if l.get("live_min") is not None:
                groups[gidx[k]]["live_min"] = l.get("live_min")
        groups[gidx[k]]["mkts"].append(l)

    # per-group geometry ----------------------------------------------------
    G_PAD = 24          # inner pad of a leg panel
    TITLE_H = 66
    MKT_H = 54
    META_H = 34
    G_GAP = 16
    for g in groups:
        meta = " · ".join(x for x in (g.get("country", ""), g.get("league", ""),
                                      _clean(g.get("date", "")),
                                      _clean(g.get("time", "")) if not g.get("date") else "") if x)
        g["meta"] = meta
        h = G_PAD + TITLE_H + len(g["mkts"]) * MKT_H
        if meta or g.get("banker"):
            h += META_H
        h += G_PAD
        g["h"] = h

    head_h = 150
    meta_bar_h = 58
    content_h = sum(g["h"] + G_GAP for g in groups)
    foot_h = 344
    perf_h = 44
    H = M + head_h + meta_bar_h + content_h + perf_h + foot_h + M

    # ---- background stage (vertical gradient + volt corner glow) ----------
    grad = Image.new("RGB", (1, H))
    for yy in range(H):
        t = yy / max(1, H - 1)
        grad.putpixel((0, yy), tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3)))
    base = grad.resize((W, H)).convert("RGBA")
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W - 520, -320, W + 260, 320], fill=VOLT + (34,))
    gd.ellipse([-300, H - 380, 360, H + 260], fill=STATUS + (26,))
    base.alpha_composite(glow.filter(ImageFilter.GaussianBlur(150)))

    def _bg_at(yy):
        t = min(1.0, max(0.0, yy / max(1, H - 1)))
        return tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3))

    # ---- ticket shadow + body ---------------------------------------------
    tx0, ty0, tx1, ty1 = M, M, W - M, H - M
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([tx0 + 6, ty0 + 16, tx1 + 6, ty1 + 16], 44, fill=(0, 0, 0, 150))
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(34)))
    d = ImageDraw.Draw(base)
    d.rounded_rectangle([tx0, ty0, tx1, ty1], 44, fill=(17, 19, 26, 252), outline=(60, 66, 80), width=2)
    d.rounded_rectangle([tx0 + 2, ty0 + 2, tx1 - 2, ty0 + 8], 6, fill=VOLT + (255,))  # volt top edge

    # faint crest watermark, centred in the legs area
    try:
        crest = Image.open(CREST_PATH).convert("RGBA")
        cwm = 620
        crest = crest.resize((cwm, int(cwm * crest.height / crest.width)))
        a = crest.split()[3].point(lambda v: int(v * 0.05))
        crest.putalpha(a)
        wy = M + head_h + meta_bar_h + max(0, (content_h - crest.height) // 2)
        base.alpha_composite(crest, ((W - crest.width) // 2, max(M + head_h, wy)))
    except Exception:
        pass

    def check_badge(cxp, cyp, r, col):
        d.ellipse([cxp - r, cyp - r, cxp + r, cyp + r], fill=col)
        d.line([(cxp - r * 0.42, cyp), (cxp - r * 0.08, cyp + r * 0.4)], fill=(10, 12, 16), width=5)
        d.line([(cxp - r * 0.08, cyp + r * 0.4), (cxp + r * 0.5, cyp - r * 0.42)], fill=(10, 12, 16), width=5)

    def pill(x0p, y0p, x1p, y1p, col, alpha=255, glow_blur=0):
        if glow_blur:
            gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(gl).rounded_rectangle([x0p, y0p, x1p, y1p], (y1p - y0p) // 2,
                                                 fill=col + (150,))
            base.alpha_composite(gl.filter(ImageFilter.GaussianBlur(glow_blur)))
        d.rounded_rectangle([x0p, y0p, x1p, y1p], (y1p - y0p) // 2, fill=col + (alpha,))

    # ---- header -----------------------------------------------------------
    hy = M + 30
    try:
        cr = Image.open(CREST_PATH).convert("RGBA")
        cs = 96
        cr = cr.resize((cs, int(cs * cr.height / cr.width)))
        base.alpha_composite(cr, (cx0, hy - 6))
        logo_x = cx0 + cs + 22
    except Exception:
        logo_x = cx0
    d.text((logo_x, hy - 8), "TIP", font=f_logo, fill=INK)
    lw = tw("TIP", f_logo)
    d.text((logo_x + lw + 4, hy - 8), "JAR", font=f_logo, fill=VOLT)
    # discreet top-left wordmark only — value-provider vibe, no loud slogan (owner 2026-07-24)
    d.text((logo_x + 3, hy + 60), "tipjarglobal.com", font=f_tag, fill=FAINT)

    # status pill (top-right, with soft glow)
    f_status_l = lfont(HEAD, 34, status_txt)
    st_w = tw(status_txt, f_status_l)
    pw = int(st_w + (108 if is_live else 96))
    py0, py1 = hy - 4, hy + 52
    px1 = cx1
    pill(px1 - pw, py0, px1, py1, STATUS, glow_blur=26)
    inx = px1 - pw + 30
    if is_live:
        d.ellipse([inx, (py0 + py1) // 2 - 9, inx + 18, (py0 + py1) // 2 + 9], fill=(12, 12, 14))
        inx += 34
    else:
        check_badge(inx + 12, (py0 + py1) // 2, 15, (12, 14, 18))
        inx += 40
    d.text((inx, py0 + 8), status_txt, font=f_status_l, fill=(12, 14, 18))

    # ---- meta bar: PARLAY/SYSTEM · N GAMES + optional live score -----------------
    my = M + head_h - 6
    ng = len(groups)
    unit = LB["game"] if ng == 1 else LB["games"]
    if is_system:
        chip = f"{LB['system']} {int(system_from or 0)}/{int(system_total or 0)} · {ng} {unit}"
    else:
        chip = f"{LB['parlay']} · {ng} {unit}"
    f_chip_l = lfont(BODY_B, 26, chip)
    d.rounded_rectangle([cx0, my, cx0 + tw(chip, f_chip_l) + 40, my + 44], 22,
                        outline=VOLT, width=2)
    d.text((cx0 + 20, my + 9), chip, font=f_chip_l, fill=VOLT)
    if live_info and (live_info.get("minute") is not None or live_info.get("score")):
        li = "LIVE"
        if live_info.get("score"):
            li = f"{live_info['score']}"
        if live_info.get("minute") is not None:
            li += f"  {live_info['minute']}'"
        lw2 = tw(li, f_chip)
        d.rounded_rectangle([cx1 - lw2 - 40, my, cx1, my + 44], 22, fill=LIVE + (255,))
        d.text((cx1 - lw2 - 20, my + 9), li, font=f_chip, fill=(12, 12, 14))

    # ---- leg panels -------------------------------------------------------
    y = M + head_h + meta_bar_h
    game_total, any_game_odd = 1.0, False
    for g in groups:
        p0, p1 = cx0, y
        d.rounded_rectangle([p0, p1, cx1, p1 + g["h"]], 22, fill=PANEL + (255,),
                            outline=PANEL_EDGE, width=1)
        d.rounded_rectangle([p0, p1 + 10, p0 + 8, p1 + g["h"] - 10], 4, fill=STATUS + (255,))
        ix = p0 + G_PAD + 16
        ty = p1 + G_PAD
        # title + optional score chip
        away = g["away"]
        title = f"{g['home']}  –  {away}" if away else g["home"]
        chip_x1 = cx1 - G_PAD
        if g.get("live") and g.get("live_score"):
            sc = g["live_score"] + (f"  {g['live_min']}'" if g.get("live_min") is not None else "")
            scw = tw(sc, f_score)
            d.rounded_rectangle([chip_x1 - scw - 30, ty - 2, chip_x1, ty + 44], 12, fill=LIVE)
            d.text((chip_x1 - scw - 15, ty + 1), sc, font=f_score, fill=(12, 12, 14))
            title_max = chip_x1 - scw - 30 - ix - 18
        elif g["result"]:
            sc = g["result"]
            scw = tw(sc, f_score)
            d.rounded_rectangle([chip_x1 - scw - 30, ty - 2, chip_x1, ty + 44], 12,
                                fill=(38, 42, 52))
            d.text((chip_x1 - scw - 15, ty + 1), sc, font=f_score, fill=INK)
            title_max = chip_x1 - scw - 30 - ix - 18
        else:
            title_max = chip_x1 - ix
        mf = fit(title, famfor(HEAD, title), 60, 44, title_max)
        d.text((ix, ty), trunc(title, mf, title_max), font=mf, fill=INK)
        ty += TITLE_H
        # ONE combined quote per GAME, shown right-aligned & vertically centred — a
        # bet-builder game's legs multiply into a single game odd (owner 2026-07-26:
        # "jedes [Spiel] braucht seine quote rechts"). Prefer a MANUAL combined odd the
        # poster entered for the whole game (owner 2026-06); else multiply per-market odds.
        combo = _to_float(g.get("combo_odds"))
        if combo > 1.0:
            game_odd = combo
            got = f"{combo:.2f}"
        else:
            nz = [float(o) for o in (l.get("odds") or 0 for l in g["mkts"]) if o]
            game_odd = 1.0
            for o in nz:
                game_odd *= o
            got = f"{game_odd:.2f}" if nz else ""
        game_total *= (game_odd if got else 1.0)
        if got:
            any_game_odd = True
        gow = tw(got, f_legodds) if got else 0
        mkt_top = ty
        for l in g["mkts"]:
            check_badge(ix + 12, ty + 25, 14, STATUS)
            raw_mkt = l.get("market", "") or ""
            # Shrink the market font to FIT the full text (down to 22px) before truncating, so a long
            # market like 'Anytime Goalscorer o. Ersatzspieler — Robbie Ure' never loses the player.
            mkfont = fit(raw_mkt, famfor(BODY_M, raw_mkt), 36, 22, cw - 130 - gow)
            mtxt = trunc(raw_mkt, mkfont, cw - 130 - gow)
            d.text((ix + 40, ty + 6), mtxt, font=mkfont, fill=SOFT)
            ty += MKT_H
        if got:
            cym = (mkt_top + ty) // 2
            d.text((chip_x1 - gow, cym - 30), got, font=f_legodds, fill=VOLT)
        meta_x = ix + 40
        if g.get("banker"):
            bt = LB["banker"]
            f_bank = lfont(BODY_M, 26, bt)
            bw = tw(bt, f_bank)
            d.rounded_rectangle([ix + 40, ty - 2, ix + 40 + bw + 28, ty + 34], 16, fill=CYAN)
            d.text((ix + 40 + 14, ty + 2), bt, font=f_bank, fill=(10, 14, 18))
            meta_x = ix + 40 + bw + 28 + 16
        if g["meta"]:
            metafont = font(famfor(BODY_M, g["meta"]), 26)
            d.text((meta_x, ty), trunc(g["meta"], metafont, cx1 - G_PAD - meta_x), font=metafont, fill=FAINT)
        y += g["h"] + G_GAP

    # ---- perforation (tear-off) ------------------------------------------
    perf_y = y + perf_h // 2 - 4
    dot = 12
    xdot = tx0 + 40
    while xdot < tx1 - 40:
        d.ellipse([xdot, perf_y - 3, xdot + dot, perf_y + 3], fill=(52, 57, 70))
        xdot += 30
    for cxn in (tx0, tx1):
        r = 22
        d.ellipse([cxn - r, perf_y - r, cxn + r, perf_y + r], fill=_bg_at(perf_y))

    # ---- footer -----------------------------------------------------------
    fy = y + perf_h
    label = {"played": LB["community"], "posted": LB["community"], "live": LB["livepick"],
             "cashed": LB["paid"], "live_pending": LB["livepick"],
             "pending": LB["community"]}.get(ctype, LB["won"])
    # avatar bubble + username
    av_r = 34
    av_cx, av_cy = cx0 + av_r, fy + 30 + av_r
    d.ellipse([av_cx - av_r, av_cy - av_r, av_cx + av_r, av_cy + av_r], fill=(30, 34, 44),
              outline=VOLT, width=3)
    initial = (username or "T").strip().lstrip("@")[:1].upper() or "T"
    fi = font(HEAD, 40)
    d.text((av_cx - tw(initial, fi) / 2, av_cy - 26), initial, font=fi, fill=VOLT)
    d.text((av_cx + av_r + 20, fy + 22), label, font=lfont(BODY_S, 26, label), fill=VOLT)
    uname = "@" + (username or "TipJar").lstrip("@")
    unfont = font(famfor(HEAD, uname), 46)
    d.text((av_cx + av_r + 18, fy + 52), trunc(uname, unfont, cw - 380), font=unfont, fill=INK)

    # hero total odds (right, sits directly above the QR). Prefer the stored total; else
    # fall back to the product of the per-game odds (fixes an EMPTY GESAMTQUOTE and shows a
    # SYSTEM's MAX odds = all legs win). Label switches to "MAX ODDS" for systems.
    eff_total = float(total_odds) if total_odds and float(total_odds) > 1.0 else (
        game_total if any_game_odd and game_total > 1.0 else 0.0)
    ot = f"{eff_total:.2f}" if eff_total > 1.0 else "—"
    otlabel = LB["max"] if is_system else LB["total"]
    f_otl = lfont(BODY_S, 26, otlabel)
    otw = tw(ot, f_total)
    d.text((cx1 - tw(otlabel, f_otl), fy + 20), otlabel, font=f_otl, fill=MUTE)
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(gl).text((cx1 - otw, fy + 40), ot, font=f_total, fill=VOLT + (170,))
    base.alpha_composite(gl.filter(ImageFilter.GaussianBlur(18)))
    d.text((cx1 - otw, fy + 40), ot, font=f_total, fill=VOLT)

    # stake / winnings row (left)
    row_y = fy + 196
    d.line([(cx0, row_y - 16), (cx1, row_y - 16)], fill=(40, 45, 56), width=2)
    col2 = cx0 + 260
    if stake:
        d.text((cx0, row_y), LB["stake"], font=lfont(BODY_M, 24, LB["stake"]), fill=FAINT)
        d.text((cx0, row_y + 28), str(stake), font=f_fval, fill=INK)
    if winnings:
        wlabel = LB["paid"] if ctype == "cashed" else (LB["win"] if won else LB["poss_win"])
        d.text((col2, row_y), wlabel, font=lfont(BODY_M, 24, wlabel), fill=FAINT)
        d.text((col2, row_y + 28), str(winnings), font=f_fval, fill=VOLT)

    out = io.BytesIO()
    base.convert("RGB").save(out, format="WEBP", quality=94, method=6)
    return out.getvalue()

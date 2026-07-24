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
        for i, sel in enumerate(sels):
            od = _to_float(sodds[i]) if i < len(sodds) else 0.0
            rlegs.append({"home": home, "away": away, "market": _fmt_selection(sel),
                          "odds": od, "result": "open",
                          "league": lg.get("league", ""), "date": "", "time": lg.get("kickoff", ""),
                          "banker": bool(lg.get("banker")),
                          "live": bool(lg.get("live")), "live_score": lg.get("live_score") or "",
                          "live_min": lg.get("live_minute")})
    if not rlegs:
        rlegs.append({"home": tip.get("home_team", ""), "away": tip.get("away_team", ""),
                      "market": _fmt_selection(tip.get("market", "")), "odds": _to_float(tip.get("odds")),
                      "result": "open", "league": tip.get("league", ""), "date": "",
                      "time": tip.get("match_time", "")})
    return rlegs


FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")
CREST_PATH = "/app/frontend/public/tipjar-crest.png"


def _render_slip_image(legs, total_odds, stake, winnings, username, ctype, live_info=None) -> bytes:
    """Premium TipJar bet-ticket (v6) — a dark, glossy portrait 'ticket' with a gradient
    stage, volt accents, glassy leg panels, a status glow, a tear-off perforation and a
    scannable QR that links back to tipjarglobal.com. Same signature as before."""
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    import io
    from server import _match_key

    def font(name, sz):
        try:
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
    STATUS = LIVE if is_live else (AMBER if ctype == "pending" else GREEN)
    status_txt = {"pending": "OFFEN", "live_pending": "LIVE"}.get(ctype, "GEWONNEN")

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
                           "league": l.get("league", ""), "date": l.get("date", ""),
                           "time": l.get("time", ""), "result": "", "mkts": [],
                           "banker": False, "live": False, "live_score": "", "live_min": None})
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
    TITLE_H = 52
    MKT_H = 54
    META_H = 34
    G_GAP = 16
    for g in groups:
        meta = " · ".join(x for x in (g.get("league", ""), _clean(g.get("date", "")),
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
    st_w = tw(status_txt, f_status)
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
    d.text((inx, py0 + 8), status_txt, font=f_status, fill=(12, 14, 18))

    # ---- meta bar: PARLAY · N GAMES + optional live score -----------------
    my = M + head_h - 6
    ng = len(groups)
    chip = f"PARLAY · {ng} {'SPIEL' if ng == 1 else 'SPIELE'}"
    d.rounded_rectangle([cx0, my, cx0 + tw(chip, f_chip) + 40, my + 44], 22,
                        outline=VOLT, width=2)
    d.text((cx0 + 20, my + 9), chip, font=f_chip, fill=VOLT)
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
        mf = fit(title, HEAD, 44, 30, title_max)
        d.text((ix, ty), trunc(title, mf, title_max), font=mf, fill=INK)
        ty += TITLE_H
        # ONE combined quote per GAME, shown right-aligned & vertically centred — a
        # bet-builder game's legs multiply into a single game odd (owner 2026-07-26:
        # "jedes [Spiel] braucht seine quote rechts"). Per-market odds are folded into it.
        nz = [float(o) for o in (l.get("odds") or 0 for l in g["mkts"]) if o]
        game_odd = 1.0
        for o in nz:
            game_odd *= o
        got = f"{game_odd:.2f}" if nz else ""
        gow = tw(got, f_legodds) if got else 0
        mkt_top = ty
        for l in g["mkts"]:
            check_badge(ix + 12, ty + 25, 14, STATUS)
            mtxt = trunc(l.get("market", "") or "", f_market, cw - 130 - gow)
            d.text((ix + 40, ty + 6), mtxt, font=f_market, fill=SOFT)
            ty += MKT_H
        if got:
            cym = (mkt_top + ty) // 2
            d.text((chip_x1 - gow, cym - 30), got, font=f_legodds, fill=VOLT)
        meta_x = ix + 40
        if g.get("banker"):
            bt = "BANKER"
            bw = tw(bt, f_meta)
            d.rounded_rectangle([ix + 40, ty - 2, ix + 40 + bw + 28, ty + 34], 16, fill=CYAN)
            d.text((ix + 40 + 14, ty + 2), bt, font=f_meta, fill=(10, 14, 18))
            meta_x = ix + 40 + bw + 28 + 16
        if g["meta"]:
            d.text((meta_x, ty), trunc(g["meta"], f_meta, cx1 - G_PAD - meta_x), font=f_meta, fill=FAINT)
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
    label = {"played": "MITGESPIELT", "posted": "REINGEPOSTET", "live": "LIVE-SERIE",
             "cashed": "AUSGEZAHLT", "live_pending": "LIVE-PICK",
             "pending": "COMMUNITY-TIPP"}.get(ctype, "GEWONNEN")
    # avatar bubble + username
    av_r = 34
    av_cx, av_cy = cx0 + av_r, fy + 30 + av_r
    d.ellipse([av_cx - av_r, av_cy - av_r, av_cx + av_r, av_cy + av_r], fill=(30, 34, 44),
              outline=VOLT, width=3)
    initial = (username or "T").strip().lstrip("@")[:1].upper() or "T"
    fi = font(HEAD, 40)
    d.text((av_cx - tw(initial, fi) / 2, av_cy - 26), initial, font=fi, fill=VOLT)
    d.text((av_cx + av_r + 20, fy + 22), label, font=f_label, fill=VOLT)
    uname = "@" + (username or "TipJar").lstrip("@")
    d.text((av_cx + av_r + 18, fy + 52), trunc(uname, f_user, cw - 380), font=f_user, fill=INK)

    # hero total odds (right, sits directly above the QR)
    ot = f"{float(total_odds):.2f}" if total_odds else "—"
    otw = tw(ot, f_total)
    d.text((cx1 - tw("GESAMTQUOTE", f_label), fy + 20), "GESAMTQUOTE", font=f_label, fill=MUTE)
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(gl).text((cx1 - otw, fy + 40), ot, font=f_total, fill=VOLT + (170,))
    base.alpha_composite(gl.filter(ImageFilter.GaussianBlur(18)))
    d.text((cx1 - otw, fy + 40), ot, font=f_total, fill=VOLT)

    # stake / winnings row (left)
    row_y = fy + 196
    d.line([(cx0, row_y - 16), (cx1, row_y - 16)], fill=(40, 45, 56), width=2)
    col2 = cx0 + 260
    if stake:
        d.text((cx0, row_y), "EINSATZ", font=f_small, fill=FAINT)
        d.text((cx0, row_y + 28), str(stake), font=f_fval, fill=INK)
    if winnings:
        wlabel = "AUSGEZAHLT" if ctype == "cashed" else ("GEWINN" if won else "MÖGL. GEWINN")
        d.text((col2, row_y), wlabel, font=f_small, fill=FAINT)
        d.text((col2, row_y + 28), str(winnings), font=f_fval, fill=VOLT)

    out = io.BytesIO()
    base.convert("RGB").save(out, format="WEBP", quality=94, method=6)
    return out.getvalue()

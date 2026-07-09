"""TipJar-branded 'LOST' multibet slip PNGs for external ads.
Per-leg colour: green=won, red=lost. Live/undecided legs removed."""
from PIL import Image, ImageDraw, ImageFont

FB = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
CREST = "/app/frontend/public/tipjar-crest.png"

VOID = (9, 9, 11)
CARD = (22, 23, 27)
WHITE = (244, 244, 246)
GREY = (150, 152, 158)
LINE = (38, 40, 46)
GREEN = (46, 204, 87)
RED = (240, 68, 60)
AMBER = (245, 190, 60)


def font(path, sz):
    try:
        return ImageFont.truetype(path, sz)
    except Exception:
        return ImageFont.load_default()


SCRATCH = ImageDraw.Draw(Image.new("RGB", (4, 4)))


def fit(txt, path, hi, lo, maxw):
    for sz in range(hi, lo - 1, -2):
        f = font(path, sz)
        if SCRATCH.textlength(txt, font=f) <= maxw:
            return f
    return font(path, lo)


def render(legs, total_odds, stake, potential, out_path, subtitle):
    W, pad = 1080, 60
    f_logo = font(FB, 90)
    f_tag = font(FR, 36)
    f_badge = font(FB, 54)
    f_sub = font(FB, 40)
    f_teams = font(FR, 40)
    f_meta = font(FR, 34)
    f_odd = font(FB, 50)
    f_big = font(FB, 92)
    f_lbl = font(FR, 40)
    f_lblB = font(FB, 54)
    f_foot = font(FB, 40)

    head_h = 230
    foot_h = 340
    row_h = 190

    H = head_h + len(legs) * row_h + foot_h
    img = Image.new("RGB", (W, H), VOID)
    d = ImageDraw.Draw(img)

    try:
        crest = Image.open(CREST).convert("RGBA")
        cw = int(W * 0.6)
        ch = int(cw * crest.height / crest.width)
        crest = crest.resize((cw, ch))
        crest.putalpha(crest.split()[3].point(lambda a: int(a * 0.05)))
        img.paste(crest, ((W - cw) // 2, (H - ch) // 2), crest)
    except Exception:
        pass

    # header
    d.text((pad, 34), "Tip", font=f_logo, fill=WHITE)
    tw = d.textlength("Tip", font=f_logo)
    d.text((pad + tw, 34), "Jar", font=f_logo, fill=GREEN)
    d.text((pad + 4, 134), "Post it. Rate it. Cash it.", font=f_tag, fill=GREY)

    badge = "LOST"
    bw = d.textlength(badge, font=f_badge)
    bx0 = W - pad - bw - 96
    d.rounded_rectangle([bx0, 40, W - pad, 122], 20, fill=RED)
    cx, cy = bx0 + 34, 82
    d.line([(cx - 14, cy - 14), (cx + 14, cy + 14)], fill=VOID, width=8)
    d.line([(cx - 14, cy + 14), (cx + 14, cy - 14)], fill=VOID, width=8)
    d.text((bx0 + 62, 54), badge, font=f_badge, fill=VOID)

    d.text((pad, 176), subtitle, font=f_sub, fill=AMBER)
    d.line([pad, head_h - 16, W - pad, head_h - 16], fill=LINE, width=3)

    y = head_h
    for lg in legs:
        col = GREEN if lg["status"] == "won" else RED
        odd = lg["odd"]
        ow = d.textlength(odd, font=f_odd)
        mkt_f = fit(lg["market"], FB, 46, 30, W - 2 * pad - ow - 40)
        d.text((pad, y), lg["market"], font=mkt_f, fill=WHITE)
        d.text((W - pad - ow, y - 2), odd, font=f_odd, fill=col)
        y += 58
        teams = f"{lg['home']} \u2013 {lg['away']}"
        tf = fit(teams, FR, 40, 26, W - 2 * pad)
        d.text((pad, y), teams, font=tf, fill=(210, 212, 216))
        y += 50
        d.text((pad, y), lg["time"], font=f_meta, fill=GREY)
        res = lg["result"]
        rw = d.textlength(res, font=f_meta)
        d.text((W - pad - rw, y + 2), res, font=f_meta, fill=col)
        y += 60
        d.line([pad, y, W - pad, y], fill=LINE, width=2)
        y += 22

    fy = y + 16
    d.rounded_rectangle([pad, fy, W - pad, H - 34], 28, fill=CARD)
    d.text((pad + 40, fy + 30), "Multibet", font=f_lblB, fill=RED)
    d.text((pad + 40, fy + 108), "Total odds", font=f_lbl, fill=GREY)
    ot = f"{total_odds:.2f}"
    otw = d.textlength(ot, font=f_big)
    d.rounded_rectangle([W - pad - otw - 76, fy + 26, W - pad - 40, fy + 140], 20, fill=RED)
    d.text((W - pad - otw - 58, fy + 34), ot, font=f_big, fill=VOID)
    d.text((pad + 40, fy + 158), "@TipJarHQ", font=f_foot, fill=WHITE)
    st = f"Stake: {stake}"
    d.text((W - pad - d.textlength(st, font=f_lbl) - 40, fy + 164), st, font=f_lbl, fill=GREY)
    pt = f"Potential: {potential}"
    d.text((pad + 40, fy + 220), pt, font=f_foot, fill=GREEN)
    d.text((pad + 40, fy + 280), "tipjarglobal.com", font=f_lbl, fill=AMBER)

    img.save(out_path, format="PNG")
    print("saved", out_path, img.size)


# LIVE / undecided legs removed. Green = won, Red = lost.
slip1 = [
    {"market": "Total Over 2.5", "home": "KF Vllaznia Shkoder", "away": "Malisheva", "time": "09.07  20:00", "odd": "2.14", "result": "2:1", "status": "won"},
    {"market": "1st Half Over 0.5", "home": "HNK Hajduk Split", "away": "MSK Zilina", "time": "09.07  20:00", "odd": "1.40", "result": "HT 1:0", "status": "won"},
    {"market": "1st Half Over 0.5", "home": "NSI Runavik", "away": "Hamrun Spartans", "time": "09.07  20:45", "odd": "1.43", "result": "HT 1:0", "status": "won"},
    {"market": "Both Teams to Score - Yes", "home": "Sarajevo", "away": "Inter Turku", "time": "09.07  21:00", "odd": "2.09", "result": "1:1", "status": "won"},
    {"market": "Double Chance 1X", "home": "Stjarnan", "away": "Vikingur Gota", "time": "09.07  21:00", "odd": "1.73", "result": "1:0", "status": "won"},
    {"market": "Total Over 0.5", "home": "CSKA Sofia", "away": "Derry City", "time": "09.07  20:00", "odd": "1.01", "result": "3:2", "status": "won"},
    {"market": "FC Astana -1.5", "home": "Dinamo Tirana", "away": "FC Astana", "time": "09.07  21:00", "odd": "5.50", "result": "0:1", "status": "lost"},
]

slip2 = [
    {"market": "Total Over 2.5", "home": "US Mondorf-Les-Bains", "away": "Dinamo Tbilisi", "time": "09.07  19:15", "odd": "1.95", "result": "1:2", "status": "won"},
    {"market": "Total Over 2.5", "home": "Caernarfon", "away": "FCI Levadia", "time": "09.07  19:30", "odd": "1.58", "result": "3:1", "status": "won"},
    {"market": "Total Over 2.5", "home": "CE Europa", "away": "Shkendija Tetovo", "time": "09.07  19:30", "odd": "2.16", "result": "0:5", "status": "won"},
    {"market": "Total Under 2.5", "home": "Atletic Club Escaldes", "away": "FK Mornar Bar", "time": "09.07  16:00", "odd": "1.67", "result": "3:2", "status": "lost"},
    {"market": "Total Under 2.5", "home": "Alashkert", "away": "Elimai", "time": "09.07  18:00", "odd": "1.60", "result": "1:1", "status": "won"},
    {"market": "Univ. Cluj 3.5", "home": "Dynamo Kyiv", "away": "Universitatea Cluj", "time": "09.07  19:00", "odd": "1.07", "result": "0:0", "status": "won"},
    {"market": "St. Joseph's 3.5", "home": "Bohemians", "away": "St. Joseph's", "time": "09.07  19:00", "odd": "1.20", "result": "2:0", "status": "won"},
    {"market": "Total Under 3.5", "home": "Velez Mostar", "away": "FC Milsami", "time": "09.07  19:00", "odd": "1.17", "result": "1:1", "status": "won"},
]

render(slip1, 156.61, "1 EUR", "156.61 EUR", "/app/frontend/public/tipjar-slip-1.png", "Multibet  \u00b7  09.07.2026")
render(slip2, 234.05, "1 EUR", "234.05 EUR", "/app/frontend/public/tipjar-slip-2.png", "Multibet  \u00b7  09.07.2026")

"""Generates the Recension org README tiles (light + dark) into profile/tiles/.

Headlines are set in Recension Condensed and converted to outlines, so they
render the same everywhere GitHub shows the SVG. Body copy uses IBM Plex with
system fallbacks.

Run: python3 profile/build.py        (needs: pip install fonttools)
"""
import math
import re
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).parent
OUT = HERE / "tiles"
OUT.mkdir(exist_ok=True)

# Which roadmap stage is in progress. Bump this when a milestone closes.
CURRENT_STAGE = "0"

SANS = '"IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif'
MONO = '"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace'

# Brand tokens. Gold marks one thing only: the node you're looking at (and the period).
THEMES = {
    "dark": dict(page="#05080C", alt="#0D141C", ink="#C4EEF8", head="#EAFBFF", muted="#7C93A3",
                 brand="#00D8F8", blue="#1096F0", gold="#FEC846", node_gold="#FEC846",
                 grid="#00D8F8", grid_op=0.06, on_brand="#05080C", line="#1C2A36"),
    "light": dict(page="#F6F9FB", alt="#ECF2F5", ink="#16232D", head="#05080C", muted="#53656F",
                  brand="#0079A6", blue="#1096F0", gold="#946000", node_gold="#F0AE2A",
                  grid="#0079A6", grid_op=0.07, on_brand="#FFFFFF", line="#D3DEE4"),
}


# ── Recension Condensed → outlines ─────────────────────────────────────────
class Face:
    def __init__(self, path):
        f = TTFont(path)
        self.gs = f.getGlyphSet()
        self.cmap = f.getBestCmap()
        self.hmtx = f["hmtx"]
        self.upm = f["head"].unitsPerEm
        self.cap = f["OS/2"].sCapHeight

    def path(self, text, x, y, size, track=0.0, anchor="start"):
        """Return (svg path d, advance width). y is the baseline; size is cap height in px."""
        s = size / self.cap
        width = self.measure(text, size, track)
        if anchor == "middle":
            x -= width / 2
        elif anchor == "end":
            x -= width
        pen = SVGPathPen(self.gs)
        cx = x
        for ch in text:
            if ch == "%":
                self._percent(pen, cx, y, s)
                cx += 560 * s + track * size
                continue
            g = self.cmap.get(ord(ch))
            if g is None:
                raise ValueError(f"Recension Condensed has no glyph for {ch!r}")
            self.gs[g].draw(TransformPen(pen, (s, 0, 0, -s, cx, y)))
            cx += self.hmtx[g][0] * s + track * size
        d = re.sub(r"-?\d+\.\d+", lambda m: f"{float(m.group()):.1f}", pen.getCommands())
        return d, width

    def measure(self, text, size, track=0.0):
        s = size / self.cap
        w = 0
        for ch in text:
            adv = 560 if ch == "%" else self.hmtx[self.cmap[ord(ch)]][0]
            w += adv * s + track * size
        return w - track * size

    @staticmethod
    def _percent(pen, x, y, s):
        # The font has no %, so draw one in its language: square counters, a heavy slash.
        def box(x0, y0, w, h):
            pts = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)]
            pen.moveTo((x + pts[0][0] * s, y - pts[0][1] * s))
            for px, py in pts[1:]:
                pen.lineTo((x + px * s, y - py * s))
            pen.closePath()
        box(40, 470, 170, 230)
        box(350, 0, 170, 230)
        pen.moveTo((x + 360 * s, y - 700 * s)); pen.lineTo((x + 470 * s, y - 700 * s))
        pen.lineTo((x + 200 * s, y)); pen.lineTo((x + 90 * s, y)); pen.closePath()


BOLD = Face(HERE / "fonts" / "RecensionCondensed-Bold.ttf")
REG = Face(HERE / "fonts" / "RecensionCondensed-Regular.ttf")


def headline(text, x, y, size, fill, gold, anchor="start", face=BOLD, track=0.01):
    """Condensed caps headline. A trailing '.' is set as the gold square period."""
    period = text.endswith(".")
    body = text[:-1] if period else text
    full_w = face.measure(text, size, track)
    if anchor == "middle":
        x0 = x - full_w / 2
    elif anchor == "end":
        x0 = x - full_w
    else:
        x0 = x
    d, w = face.path(body, x0, y, size, track)
    out = f'<path d="{d}" fill="{fill}"/>'
    if period:
        dp, _ = face.path(".", x0 + w + track * size, y, size, track)
        out += f'<path d="{dp}" fill="{gold}"/>'
    return out


def text(x, y, s, size, fill, cls="sans", anchor="start", weight=400, ls="0"):
    fam = MONO if cls == "mono" else SANS
    return (f'<text x="{x}" y="{y}" font-family=\'{fam}\' font-size="{size}" font-weight="{weight}" '
            f'letter-spacing="{ls}" text-anchor="{anchor}" fill="{fill}">{s}</text>')


def eyebrow(x, y, s, t, anchor="start"):
    return text(x, y, s, 15, t["brand"], "mono", anchor, 500, "0.14em")


def svg(w, h, label, body, bg, t, grid=True, radius=18):
    g = ""
    if grid:
        step = 48
        lines = "".join(f'<line x1="{i}" y1="0" x2="{i}" y2="{h}"/>' for i in range(step, w, step))
        lines += "".join(f'<line x1="0" y1="{j}" x2="{w}" y2="{j}"/>' for j in range(step, h, step))
        g = f'<g stroke="{t["grid"]}" stroke-opacity="{t["grid_op"]}" stroke-width="1">{lines}</g>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{label}">
<defs><clipPath id="clip"><rect width="{w}" height="{h}" rx="{radius}"/></clipPath>
<filter id="blur" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="6"/></filter></defs>
<g clip-path="url(#clip)"><rect width="{w}" height="{h}" fill="{bg}"/>{g}
{body}
</g>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="{radius - 0.5}" fill="none" stroke="{t["line"]}"/>
</svg>'''


def pill_pair(cx, y, t, primary, secondary):
    w1 = 30 + len(primary) * 9.0
    w2 = 30 + len(secondary) * 9.0
    gap = 12
    x1 = cx - (w1 + gap + w2) / 2
    x2 = x1 + w1 + gap
    return (f'<rect x="{x1:.1f}" y="{y}" width="{w1:.1f}" height="40" rx="6" fill="{t["brand"]}"/>'
            + text(f"{x1 + w1 / 2:.1f}", y + 25.5, primary, 15, t["on_brand"], "mono", "middle", 600, "0.06em")
            + f'<rect x="{x2 + .75:.1f}" y="{y + .75}" width="{w2 - 1.5:.1f}" height="38.5" rx="5.25" fill="none" stroke="{t["brand"]}" stroke-width="1.5"/>'
            + text(f"{x2 + w2 / 2:.1f}", y + 25.5, secondary, 15, t["brand"], "mono", "middle", 600, "0.06em"))


def trails(w, y_base, t, n=7, spread=22, seed=0.0, op=1.0):
    """Light trails: long cyan→blue curves with a soft glow, like the banners."""
    out = []
    for i in range(n):
        y0 = y_base + i * spread
        a = 26 + i * 7
        pts = []
        for x in range(-20, w + 21, 20):
            yy = y0 - a * math.sin(x / 260 + seed + i * 0.35) - 0.12 * a * math.sin(x / 70 + i)
            pts.append(f"{x},{yy:.1f}")
        p = " ".join(pts)
        width = 1.2 + (n - i) * 0.35
        o = (0.25 + (n - i) * 0.09) * op
        out.append(f'<polyline points="{p}" fill="none" stroke="url(#tr)" stroke-width="{width * 3:.1f}" opacity="{o * 0.35:.2f}" filter="url(#blur)"/>')
        out.append(f'<polyline points="{p}" fill="none" stroke="url(#tr)" stroke-width="{width:.2f}" opacity="{o:.2f}"/>')
    grad = (f'<linearGradient id="tr" x1="0" x2="1"><stop offset="0" stop-color="{t["blue"]}" stop-opacity="0"/>'
            f'<stop offset=".35" stop-color="{t["blue"]}"/><stop offset="1" stop-color="{t["brand"]}"/></linearGradient>')
    return f"<defs>{grad}</defs>" + "".join(out)


def tree(cx, top, scale, t, gold_index=4, glow=True):
    """The Recension lineage tree (same topology as the logo)."""
    N = [(0, 0, 9), (0, 36, 7.5), (-29, 54, 7.2), (29, 54, 7.2), (0, 70, 8.3),
         (-43, 80, 6.4), (-21, 80, 6.4), (21, 80, 6.4), (42, 80, 6.4), (-13, 101, 6.6), (13, 101, 6.6)]
    E = [(0, 1), (1, 2), (1, 3), (1, 4), (2, 5), (2, 6), (3, 7), (3, 8), (4, 9), (4, 10)]
    P = [(cx + x * scale, top + y * scale, r * scale) for x, y, r in N]
    lw = 1.8 * scale
    s = "".join(f'<line x1="{P[a][0]:.1f}" y1="{P[a][1]:.1f}" x2="{P[b][0]:.1f}" y2="{P[b][1]:.1f}" stroke="{t["brand"]}" stroke-width="{lw:.1f}"/>' for a, b in E)
    halo = ""
    if glow:
        gx, gy, _ = P[gold_index]
        halo = (f'<defs><radialGradient id="halo"><stop offset="0" stop-color="{t["node_gold"]}" stop-opacity=".55"/>'
                f'<stop offset="1" stop-color="{t["node_gold"]}" stop-opacity="0"/></radialGradient></defs>'
                f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="{34 * scale:.1f}" fill="url(#halo)"/>')
    nodes = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{t["node_gold"] if i == gold_index else t["brand"]}"/>' for i, (x, y, r) in enumerate(P))
    return halo + s + nodes


def write(name, mode, content):
    (OUT / f"{name}-{mode}.svg").write_text(content)


for mode, t in THEMES.items():
    # ── Hero ───────────────────────────────────────────────────────────
    body = (trails(1200, 330, t, seed=0.4)
            + eyebrow(600, 112, "FDA 510(K) · PREDICATE LINEAGE · BUILT IN PUBLIC", t, "middle")
            + headline("KNOW THE LINEAGE.", 600, 222, 78, t["head"], t["gold"], "middle")
            + text(600, 272, "The citable record of FDA 510(k) device lineage.", 24, t["ink"], anchor="middle"))
    write("hero", mode, svg(1200, 400, "Recension. Know the lineage. The citable record of FDA 510(k) device lineage.", body, t["page"], t))

    # ── The problem (always dark, the "Pro" tile) ──────────────────────
    d = THEMES["dark"]
    body = (eyebrow(80, 104, "WHY THIS EXISTS", d)
            + headline("44.1%", 80, 236, 112, d["head"], d["gold"])
            + text(80, 292, "of devices hit by a Class I recall were cleared using a", 23, d["ink"])
            + text(80, 324, "predicate that had a Class I recall of its own.", 23, d["ink"])
            + text(80, 372, "56 of 127 devices. Risk ratio 6.40 (95% CI 3.59–11.40).", 16, d["muted"], "mono")
            + text(80, 398, "Kadakia et al., JAMA, 2023.", 16, d["muted"], "mono")
            + headline("NOBODY TRACKS THE FAMILY TREE.", 80, 476, 30, d["ink"], d["gold"])
            + f'<g opacity=".95">{tree(960, 128, 3.1, d)}</g>')
    write("problem", mode, svg(1200, 540, "44.1 percent of devices with a Class I recall were cleared using a predicate that also had a Class I recall (Kadakia et al., JAMA, 2023).", body, d["page"], d))

    # ── The graph (half tile) ──────────────────────────────────────────
    body = (eyebrow(295, 92, "THE GRAPH", t, "middle")
            + headline("EVERY PREDICATE.", 295, 160, 44, t["head"], t["gold"], "middle")
            + text(295, 202, "Every 510(k) clearance and the devices", 18, t["ink"], anchor="middle")
            + text(295, 228, "it cited, linked to their recall history.", 18, t["ink"], anchor="middle")
            + tree(295, 292, 2.35, t))
    write("graph", mode, svg(590, 600, "The graph: every 510(k) clearance and the predicates it cited, linked to recall history.", body, t["alt"], t))

    # ── The record (half tile) ─────────────────────────────────────────
    rows = ""
    for i, (label, w) in enumerate([("2026-11-02", 240), ("2026-11-09", 270), ("2026-11-16", 300)]):
        y = 330 + i * 64
        rows += (text(84, y + 22, label, 14, t["muted"], "mono")
                 + f'<rect x="196" y="{y + 6}" width="{w}" height="22" rx="3" fill="{t["brand"]}" opacity="{0.28 + i * 0.22:.2f}"/>')
    asof_x = 196 + 270
    body = (eyebrow(295, 92, "THE RECORD", t, "middle")
            + headline("CITE ANY DATE.", 295, 160, 44, t["head"], t["gold"], "middle")
            + text(295, 202, "Raw snapshots are write-once. Ask what", 18, t["ink"], anchor="middle")
            + text(295, 228, "was known on a date, and get the same answer.", 18, t["ink"], anchor="middle")
            + rows
            + f'<line x1="{asof_x}" y1="306" x2="{asof_x}" y2="534" stroke="{t["node_gold"]}" stroke-width="2" stroke-dasharray="4 5"/>'
            + f'<rect x="{asof_x - 5}" y="301" width="10" height="10" fill="{t["node_gold"]}"/>'
            + text(asof_x, 290, "AS OF", 13, t["gold"], "mono", "middle", 600, "0.12em")
            + text(295, 568, "snapshot_id · DOI per release", 14, t["muted"], "mono", "middle"))
    write("record", mode, svg(590, 600, "The record: write-once snapshots, as-of queries, and a citable snapshot ID and DOI per release.", body, t["alt"], t))

    # ── Roadmap ────────────────────────────────────────────────────────
    stages = [("0", "FOUNDATION"), ("1", "INGESTION"), ("2A", "GRAPH"), ("2B", "MODELING"), ("3", "SCORE"),
              ("4", "OPERATIONS"), ("5", "RESEARCH"), ("6", "BENCHMARK"), ("7", "SIMULATOR")]
    x0, x1, ly = 110, 1090, 236
    step = (x1 - x0) / (len(stages) - 1)
    cur = [s for s, _ in stages].index(CURRENT_STAGE.upper())
    marks = f'<line x1="{x0}" y1="{ly}" x2="{x1}" y2="{ly}" stroke="{t["line"]}" stroke-width="2"/>'
    marks += f'<line x1="{x0}" y1="{ly}" x2="{x0 + step * cur}" y2="{ly}" stroke="{t["brand"]}" stroke-width="2"/>'
    for i, (num, name) in enumerate(stages):
        x = x0 + i * step
        if i < cur:
            dot = f'<circle cx="{x:.1f}" cy="{ly}" r="9" fill="{t["brand"]}"/>'
        elif i == cur:
            dot = (f'<circle cx="{x:.1f}" cy="{ly}" r="22" fill="{t["brand"]}" opacity=".18"/>'
                   f'<circle cx="{x:.1f}" cy="{ly}" r="11" fill="{t["brand"]}"/>')
        else:
            dot = f'<circle cx="{x:.1f}" cy="{ly}" r="8" fill="{t["alt"]}" stroke="{t["muted"]}" stroke-width="1.5"/>'
        col = t["head"] if i == cur else t["muted"]
        marks += dot + headline(num, x, ly - 34, 22, col, t["gold"], "middle")
        marks += text(f"{x:.1f}", ly + 46, name, 12, col, "mono", "middle", 600 if i == cur else 400, "0.1em")
    body = (eyebrow(110, 92, "ROADMAP", t)
            + headline("ONE STAGE AT A TIME.", 110, 146, 36, t["head"], t["gold"])
            + text(1090, 146, "A stage starts when the last one's exit criteria are met. Never by date.", 16, t["muted"], anchor="end")
            + marks)
    write("roadmap", mode, svg(1200, 340, f"Roadmap: stages 0 to 7, currently in stage {CURRENT_STAGE}.", body, t["page"], t))

    # ── Licensing ──────────────────────────────────────────────────────
    cols = [("CODE", "AGPL-3.0", "Run it, read it, fork it. Share your changes."),
            ("DATA", "CC BY-NC 4.0", "Free for research and journalism."),
            ("CITE", "ZENODO DOI", "Every release gets one. CITATION.cff in repo.")]
    body = eyebrow(80, 88, "LICENSING", t)
    for i, (k, v, note) in enumerate(cols):
        x = 80 + i * 370
        body += (text(x, 150, k, 13, t["muted"], "mono", weight=600, ls="0.14em")
                 + headline(v, x, 196, 32, t["head"], t["gold"])
                 + text(x, 232, note, 16, t["ink"]))
    write("licensing", mode, svg(1200, 290, "Licensing: code under AGPL-3.0, data under CC BY-NC 4.0, every release citable via a Zenodo DOI.", body, t["alt"], t, grid=False))

    # ── Contact pills (separate images so each is clickable) ───────────
    for name, label, filled in [("linkedin", "LINKEDIN", True), ("youtube", "YOUTUBE", False), ("x", "X", False), ("email", "EMAIL", False)]:
        w = int(44 + len(label) * 9.6)
        if filled:
            shape = f'<rect width="{w}" height="40" rx="6" fill="{t["brand"]}"/>'
            ink = t["on_brand"]
        else:
            shape = f'<rect x=".75" y=".75" width="{w - 1.5}" height="38.5" rx="5.25" fill="none" stroke="{t["brand"]}" stroke-width="1.5"/>'
            ink = t["brand"]
        write(f"pill-{name}", mode, f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="40" viewBox="0 0 {w} 40" role="img" aria-label="{label.title()}">
{shape}{text(w / 2, 25.5, label, 15, ink, "mono", "middle", 600, "0.08em")}
</svg>''')

print("wrote", len(list(OUT.glob("*.svg"))), "tiles to", OUT)

#!/usr/bin/env python3
"""Generate Widya Yasa's profile cards.

    python3 -m pip install -r scripts/requirements.txt
    python3 scripts/build.py

Edit the DATA block, then run the script again. It writes themed SVGs to
assets/ and refreshes README.md. Pac-Man contribution graphs are left as-is
(regenerate those with scripts/generate-pacman.ps1).

Fonts are subset and embedded (woff2) because SVGs loaded as <img> on GitHub
cannot fetch external font files. Requires fontTools and brotli.
"""

from __future__ import annotations

import base64
import io
import math
import sys
from pathlib import Path
from xml.sax.saxutils import escape

try:
    from fontTools import subset
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
except ImportError:
    sys.exit(
        "Missing dependency. Install with:\n"
        "  python3 -m pip install -r scripts/requirements.txt"
    )

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "scripts" / "fonts"
OUT = ROOT / "assets"
VERSION = "3"

PORTFOLIO = "https://widya-yasa.vercel.app"
GITHUB = "https://github.com/widyasa"
LINKEDIN = "https://linkedin.com/in/widya-yasa"
INSTAGRAM = "https://instagram.com/widya_yasaa"
PATCHSENSE = "https://github.com/Widyasa/patchsense"

# ───────────────────────────── themes ─────────────────────────────
# Light is a printed quest log. Dark is the same UI as a night HUD.
# Text colors are checked against their backgrounds in assert_contrast().

LIGHT = dict(
    id="light",
    field="#f3ecdc",
    panel="#fffaf2",
    band="#efe4cf",
    chip="#fffaf2",
    screen="#161228",
    ink="#1c1730",
    muted="#5e5878",
    gold="#8a5a00",
    gold_shape="#d97706",
    teal="#0f766e",
    stroke="#1c1730",
    stroke_soft="#e4d8c4",
    on_dark="#fffaf2",
    pill="#1c1730",
    pill_ink="#fffaf2",
    dot="#22c55e",
    green="#16a34a",
    amber="#d97706",
    sky="#0369a1",
    kind_teal="#0f766e",
    kind_sky="#1d4ed8",
    kind_violet="#5b21b6",
    kind_rust="#9a3412",
    icon_soft="#f3ecdc",
    marquee_bg="#1c1730",
    marquee_ink="#f6f1e6",
    marquee_mark="#f0c14a",
)

DARK = dict(
    id="dark",
    field="#090d18",
    panel="#121a2b",
    band="#0c1322",
    chip="#1a2438",
    screen="#070912",
    ink="#eef3ff",
    muted="#aeb8d4",
    gold="#f0c14a",
    gold_shape="#f0c14a",
    teal="#5eead4",
    stroke="#e0c36a",
    stroke_soft="#2c3c5c",
    on_dark="#fffaf2",
    pill="#eef3ff",
    pill_ink="#121a2b",
    dot="#22c55e",
    green="#4ade80",
    amber="#fbbf24",
    sky="#38bdf8",
    kind_teal="#5eead4",
    kind_sky="#93c5fd",
    kind_violet="#d6bcfa",
    kind_rust="#fdba74",
    icon_soft="#0c1322",
    marquee_bg="#090d18",
    marquee_ink="#f0c14a",
    marquee_mark="#5eead4",
)

THEMES = (LIGHT, DARK)

RAIL = {
    "patchsense": "#9a3412",
    "akumampu": "#1d4ed8",
    "midnight": "#4c1d95",
}
KIND_KEY = {"patchsense": "kind_rust", "akumampu": "kind_sky", "midnight": "kind_violet"}

# ───────────────────────────── copy (from the existing README only) ─────────────────────────────

PROJECTS = [
    dict(
        slug="patchsense",
        num="01",
        title="PatchSense",
        kind="Rust · CLI · Security · Open Source",
        status="In development",
        desc="Ranks CVEs into Critical, Review, and Defer · MCP server.\n"
             "npm, pip, Composer, Go, Homebrew, Docker, and cargo",
        art="cli",
        href=PATCHSENSE,
        cta="GITHUB",
    ),
    dict(
        slug="akumampu",
        num="02",
        title="Aku Mampu AI",
        kind="Web · LMS",
        desc="Disability-friendly AI training with sign-language\n& screen-reader support across Indonesia",
        art="learn",
        href=PORTFOLIO,
        cta="PORTFOLIO",
    ),
    dict(
        slug="midnight",
        num="03",
        title="Midnight Toys",
        kind="Game · Horror",
        desc="FNAF-style night-guard horror — CCTV, flash, fear bar · Gimersia 2025",
        art="night",
        href=PORTFOLIO,
        cta="PORTFOLIO",
    ),
]

INVENTORY = [
    ("FRONTEND", "green", [
        "TypeScript", "JavaScript", "React", "Next.js", "Vue.js", "Nuxt",
        "Pinia", "Tailwind CSS", "Bootstrap", "shadcn/ui",
    ]),
    ("BACKEND", "amber", [
        "PHP", "Laravel", "Inertia", "Node.js", "Express.js", "Supabase",
        "Prisma", "PostgreSQL", "MySQL", "Rust", "Go",
    ]),
    ("GAME DEV", "sky", ["Unity", "C#", "C"]),
]

QUESTS = [
    ("ANIME", "Enchanted by Frieren", "star", "amber"),
    ("GAMING", "Roguelikes & online games", "dpad", "green"),
    ("EXPLORING", "New places around\nBali & beyond", "compass", "sky"),
    ("FOOD", "New restaurants, or\ncooking at home", "bowl", "kind_violet"),
    ("OPEN SOURCE", "Building\nPatchSense", "branch", "teal"),
]

SECTIONS = [
    ("profile", "PLAYER_PROFILE", "bali, indonesia"),
    ("stages", "FEATURED_STAGES", "featured builds"),
    ("inventory", "INVENTORY", "frontend · backend · game dev"),
    ("contrib", "CONTRIBUTION_GAME", "pac-man"),
    ("quests", "SIDE_QUESTS", "anime · games · exploring · food · oss"),
]

MARQUEE = [
    "SHIP FEATURES",
    "SHARE KNOWLEDGE",
    "ENJOY THE JOURNEY",
    "FREELANCE & FULL-TIME",
    "BALI, INDONESIA",
]

TRAITS = [("FAST", "green"), ("INTENTIONAL", "amber"), ("EASY TO USE", "sky")]

STATS = [
    ("CLASS", "Full-Stack Developer & Game Developer"),
    ("BASE", "Bali, Indonesia"),
    ("STATUS", "Open to freelance & full-time"),
    ("MISSION", "Ship features · share knowledge · enjoy the journey"),
]

# ───────────────────────────── fonts ─────────────────────────────
# family key -> (filename, variable weight or None)
FACES = {
    "display": ("Oxanium-wght.ttf", 700),
    "disp": ("Oxanium-wght.ttf", 500),
    "sans": ("Sora-wght.ttf", 400),
    "semi": ("Sora-wght.ttf", 600),
    "mono": ("JetBrainsMono-Medium.ttf", None),
}

_MASTER = {}


def master_bytes(key: str) -> bytes:
    if key not in _MASTER:
        filename, weight = FACES[key]
        tt = TTFont(FONT_DIR / filename)
        if weight is not None:
            tt = instantiateVariableFont(tt, {"wght": weight}, inplace=False)
        buf = io.BytesIO()
        tt.save(buf)
        _MASTER[key] = buf.getvalue()
    return _MASTER[key]


class Font:
    def __init__(self, key: str):
        self.key = key
        tt = TTFont(io.BytesIO(master_bytes(key)))
        self.upm = tt["head"].unitsPerEm
        self.cmap = tt.getBestCmap()
        self.hmtx = tt["hmtx"]
        os2 = tt["OS/2"]
        cap = os2.sCapHeight or int(self.upm * 0.7)
        self.cap = cap / self.upm

    def width(self, text: str, size: float) -> float:
        adv = 0
        for ch in text:
            gid = self.cmap.get(ord(ch))
            if gid is None:
                raise SystemExit(f"Glyph {ch!r} (U+{ord(ch):04X}) missing from font {self.key}")
            adv += self.hmtx[gid][0]
        return adv * size / self.upm

    def baseline(self, top: float, height: float, size: float) -> float:
        """Baseline that vertically centers the cap height in a box."""
        return top + (height + size * self.cap) / 2


FONTS = {key: Font(key) for key in FACES}
_FACE_CSS = {}


def tw(text: str, font: str, size: float) -> float:
    return FONTS[font].width(text, size)


def font_css(key: str, chars: set[str]) -> str:
    sig = (key, "".join(sorted(chars)))
    if sig in _FACE_CSS:
        return _FACE_CSS[sig]
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga", "calt"]
    opts.name_IDs = ["*"]
    tt = TTFont(io.BytesIO(master_bytes(key)))
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(sorted(chars)))
    sub.subset(tt)
    tt.flavor = "woff2"
    buf = io.BytesIO()
    tt.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    css = (
        f"@font-face{{font-family:'{key}';src:url(data:font/woff2;base64,{b64}) "
        f"format('woff2');font-style:normal;font-weight:400 800;}}"
    )
    _FACE_CSS[sig] = css
    return css


def esc(text: str) -> str:
    return escape(text, {'"': "&quot;"})


# ───────────────────────────── svg ─────────────────────────────

MOTION = """
.blink{animation:blink 1.2s steps(1,end) infinite}
.pulse{animation:pulse 1.8s ease-in-out infinite}
.nudge{animation:nudge 1.5s ease-in-out infinite}
@keyframes blink{50%{opacity:0}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.28}}
@keyframes nudge{0%,100%{transform:translateX(0)}50%{transform:translateX(6px)}}
@media (prefers-reduced-motion:reduce){*{animation:none !important}}
"""


class Svg:
    def __init__(self, w: int, h: int, title: str, desc: str = ""):
        self.w, self.h = w, h
        self.title, self.desc = title, desc
        self.parts: list[str] = []
        self.css: list[str] = []
        self.defs: list[str] = []
        self.used = {k: set() for k in FACES}

    def add(self, *chunks: str) -> None:
        self.parts.extend(chunks)

    def text(self, x, y, text, font="sans", size=16, fill="#000", anchor="start", cls="") -> str:
        self.used[font].update(text)
        FONTS[font].width(text, size)
        anch = f' text-anchor="{anchor}"' if anchor != "start" else ""
        klass = f' class="{cls}"' if cls else ""
        return (
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" '
            f'fill="{fill}"{anch}{klass}>{esc(text)}</text>'
        )

    def render(self, path: Path) -> None:
        faces = "".join(font_css(k, v) for k, v in self.used.items() if v)
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        css = faces + "".join(self.css)
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="t d">'
            f'<title id="t">{esc(self.title)}</title>'
            f'<desc id="d">{esc(self.desc or self.title)}</desc>'
            f"<style>{css}</style>{defs}{''.join(self.parts)}</svg>"
        )
        path.write_text(svg, encoding="utf-8")
        print(f"  {path.relative_to(ROOT)}  {len(svg) / 1024:.1f} KB")


def notch_d(x, y, w, h, c) -> str:
    c = min(c, w / 2, h / 2)
    return (
        f"M{x + c:.2f},{y:.2f} H{x + w - c:.2f} L{x + w:.2f},{y + c:.2f} "
        f"V{y + h - c:.2f} L{x + w - c:.2f},{y + h:.2f} H{x + c:.2f} "
        f"L{x:.2f},{y + h - c:.2f} V{y + c:.2f} Z"
    )


def notch(x, y, w, h, c, fill, stroke=None, sw=0) -> str:
    stroke_attr = f' stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="miter"' if stroke and sw else ""
    return f'<path d="{notch_d(x, y, w, h, c)}" fill="{fill}"{stroke_attr}/>'


def diamond(cx, cy, r, fill) -> str:
    return (
        f'<polygon points="{cx:.1f},{cy - r:.1f} {cx + r:.1f},{cy:.1f} '
        f'{cx:.1f},{cy + r:.1f} {cx - r:.1f},{cy:.1f}" fill="{fill}"/>'
    )


def brackets(x, y, w, h, length, color, sw=2.2) -> str:
    L = length
    return (
        f'<path d="M{x},{y + L} V{y} H{x + L}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="square"/>'
        f'<path d="M{x + w - L},{y} H{x + w} V{y + L}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="square"/>'
        f'<path d="M{x},{y + h - L} V{y + h} H{x + L}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="square"/>'
        f'<path d="M{x + w - L},{y + h} H{x + w} V{y + h - L}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="square"/>'
    )


def lines_of(text: str, font: str, size: float, max_w: float) -> list[str]:
    if "\n" in text:
        lines = text.split("\n")
        for line in lines:
            if tw(line, font, size) > max_w:
                raise SystemExit(f"Line too wide ({tw(line, font, size):.0f}px): {line}")
        return lines
    return wrap(text, font, size, max_w)


def wrap(text: str, font: str, size: float, max_w: float) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else f"{cur} {word}"
        if tw(trial, font, size) <= max_w:
            cur = trial
        else:
            if not cur:
                raise SystemExit(f"Word {word!r} is wider than {max_w}px")
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ───────────────────────────── icons ─────────────────────────────

def icon_cli(t) -> str:
    """Terminal with a shield badge — a CLI, not a brand mark."""
    ink, soft, rust = t["ink"], t["icon_soft"], t["kind_rust"]
    return f'''<g>
      <rect x="0" y="34" width="112" height="74" rx="8" fill="{soft}" stroke="{ink}" stroke-width="2"/>
      <path d="M0 52 H112" stroke="{ink}" stroke-width="2"/>
      <circle cx="16" cy="43" r="3.4" fill="{t["green"]}"/>
      <circle cx="28" cy="43" r="3.4" fill="{t["amber"]}"/>
      <circle cx="40" cy="43" r="3.4" fill="{t["sky"]}"/>
      <path d="M16 68 l10 8 l-10 8" fill="none" stroke="{rust}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M38 88 H72" stroke="{t["muted"]}" stroke-width="2.2" stroke-linecap="round"/>
      <path d="M96 14 l16 7 v20 c0 14 -16 22 -16 22 s-16 -8 -16 -22 V21 Z" fill="{t["panel"]}" stroke="{rust}" stroke-width="2" stroke-linejoin="round"/>
      <path d="M96 32 v10" stroke="{rust}" stroke-width="2.2" stroke-linecap="round"/>
      <circle cx="96" cy="48" r="1.7" fill="{rust}"/>
    </g>'''


def icon_learn(t) -> str:
    ink, teal = t["ink"], t["kind_teal"]
    return f'''<g fill="none" stroke="{ink}" stroke-width="2.1" stroke-linejoin="round" stroke-linecap="round">
      <path d="M16 38 C16 28 46 26 66 36 L66 96 C46 86 16 88 16 98 Z" fill="{t["icon_soft"]}"/>
      <path d="M116 38 C116 28 86 26 66 36 L66 96 C86 86 116 88 116 98 Z" fill="{t["icon_soft"]}"/>
      <path d="M66 36 V96" stroke="{teal}"/>
      <path d="M78 34 h12 l-6 10 z" fill="{t["amber"]}" stroke="{t["amber"]}"/>
      <path d="M128 52 q14 10 0 20 M134 44 q22 18 0 36 M140 36 q30 26 0 52" stroke="{teal}"/>
    </g>'''


def icon_night(t) -> str:
    ink, gold, violet = t["ink"], t["gold_shape"], t["kind_violet"]
    return f'''<g>
      <path fill="{gold}" fill-rule="evenodd" d="M78 18 a22 22 0 1 0 0.1 0 Z M92 18 a16 16 0 1 1 -0.1 0 Z"/>
      <rect x="16" y="58" width="62" height="36" rx="6" fill="{t["icon_soft"]}" stroke="{ink}" stroke-width="2"/>
      <rect x="26" y="48" width="20" height="12" rx="2" fill="{violet}"/>
      <circle cx="47" cy="76" r="9" fill="none" stroke="{ink}" stroke-width="2"/>
      <circle cx="47" cy="76" r="4" fill="{gold}"/>
      <rect x="16" y="108" width="14" height="8" rx="1.5" fill="{violet}" opacity="0.35"/>
      <rect x="34" y="104" width="14" height="12" rx="1.5" fill="{violet}" opacity="0.55"/>
      <rect x="52" y="100" width="14" height="16" rx="1.5" fill="{violet}" opacity="0.8"/>
      <rect x="70" y="96" width="14" height="20" rx="1.5" fill="{violet}" class="pulse"/>
    </g>'''


def icon_star(cx, cy, r, fill) -> str:
    pts = []
    for i in range(8):
        ang = math.pi / 4 * i - math.pi / 2
        rad = r if i % 2 == 0 else r * 0.4
        pts.append(f"{cx + rad * math.cos(ang):.1f},{cy + rad * math.sin(ang):.1f}")
    return f'<polygon points="{" ".join(pts)}" fill="{fill}"/>'


def icon_dpad(cx, cy, color) -> str:
    return (
        f'<circle cx="{cx}" cy="{cy}" r="13" fill="none" stroke="{color}" stroke-width="2"/>'
        f'<path d="M{cx} {cy - 7} V{cy + 7} M{cx - 7} {cy} H{cx + 7}" stroke="{color}" '
        f'stroke-width="2.4" stroke-linecap="round"/>'
    )


def icon_compass(cx, cy, color, needle) -> str:
    return (
        f'<circle cx="{cx}" cy="{cy}" r="13" fill="none" stroke="{color}" stroke-width="2"/>'
        f'<path d="M{cx} {cy - 9} L{cx + 4} {cy + 6} L{cx} {cy + 3} L{cx - 4} {cy + 6} Z" fill="{needle}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="1.8" fill="{color}"/>'
    )


def icon_branch(cx, cy, color) -> str:
    """Git branch, same stroke weight as the other side-quest marks."""
    lx = cx - 6
    return (
        f'<circle cx="{lx}" cy="{cy - 8}" r="3.2" fill="none" stroke="{color}" stroke-width="2"/>'
        f'<circle cx="{lx}" cy="{cy + 8}" r="3.2" fill="none" stroke="{color}" stroke-width="2"/>'
        f'<circle cx="{lx + 12}" cy="{cy - 8}" r="3.2" fill="none" stroke="{color}" stroke-width="2"/>'
        f'<path d="M{lx} {cy - 4.8} V{cy + 4.8} M{lx} {cy - 1} C{lx} {cy - 8} {lx + 12} {cy - 8} {lx + 12} {cy - 4.8}" '
        f'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"/>'
    )


def icon_bowl(cx, cy, color) -> str:
    return (
        f'<path d="M{cx - 14} {cy - 2} H{cx + 14}" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"/>'
        f'<path d="M{cx - 12} {cy - 2} Q{cx} {cy + 16} {cx + 12} {cy - 2}" fill="none" stroke="{color}" stroke-width="2"/>'
        f'<path d="M{cx - 4} {cy - 10} q4 -6 4 0 M{cx + 2} {cy - 12} q3 -5 3 0" fill="none" stroke="{color}" '
        f'stroke-width="1.6" stroke-linecap="round"/>'
    )


ART = {"cli": icon_cli, "learn": icon_learn, "night": icon_night}


# ───────────────────────────── header ─────────────────────────────

HEADER_ALT = (
    "Player card for Widya Yasa, Full-Stack Developer and Game Developer, "
    "based in Bali, Indonesia. Rank P1. Open to freelance and full-time. "
    "Mission: ship features, share knowledge, enjoy the journey. "
    "Focus: frontend, backend, systems, and open source. "
    "Traits: fast, intentional, and easy to use. Opens the portfolio."
)

# Equal spokes on purpose: the chart names focus areas, it does not score them.
FOCUS = ("FRONTEND", "BACKEND", "SYSTEMS", "OSS")


def _ring_points(cx: float, cy: float, r: float) -> list[tuple[float, float]]:
    return [
        (cx + r * math.cos(ang), cy + r * math.sin(ang))
        for ang in (-math.pi / 2, 0, math.pi / 2, math.pi)
    ]


def build_header(t: dict) -> None:
    W, H = 1200, 648
    s = Svg(W, H, "Widya Yasa — player card", HEADER_ALT)
    s.css.append(MOTION)
    s.css.append(
        ".scan{animation:scan 5.2s linear infinite}"
        "@keyframes scan{0%{transform:translateY(0);opacity:0}"
        "8%{opacity:.85}72%{opacity:.3}100%{transform:translateY(200px);opacity:0}}"
        ".ring{stroke-dasharray:18 14;animation:march 18s linear infinite}"
        "@keyframes march{to{stroke-dashoffset:-420}}"
    )
    glow = t["teal"] if t["id"] == "dark" else t["gold_shape"]
    glow_core = "0.42" if t["id"] == "dark" else "0.20"
    s.defs.append(
        f'<linearGradient id="holo" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{t["teal"]}"/>'
        f'<stop offset="0.5" stop-color="{t["gold_shape"]}"/>'
        f'<stop offset="1" stop-color="{t["sky"]}"/>'
        f'</linearGradient>'
        f'<radialGradient id="glow" cx="50%" cy="50%" r="50%">'
        f'<stop offset="0" stop-color="{glow}" stop-opacity="{glow_core}"/>'
        f'<stop offset="0.62" stop-color="{glow}" stop-opacity="0.08"/>'
        f'<stop offset="1" stop-color="{glow}" stop-opacity="0"/>'
        f'</radialGradient>'
        f'<pattern id="grid" width="14" height="14" patternUnits="userSpaceOnUse">'
        f'<path d="M14 0 H0 V14" fill="none" stroke="#f6d56a" stroke-width="0.7" opacity="0.28"/>'
        f'</pattern>'
    )
    s.add(f'<rect width="{W}" height="{H}" fill="{t["field"]}"/>')
    s.add(f'<rect width="{W}" height="4" fill="url(#holo)"/>')

    x, y, w, h, c = 18, 16, 1164, 616, 18
    s.defs.append(f'<clipPath id="card"><path d="{notch_d(x, y, w, h, c)}"/></clipPath>')
    s.add(notch(x, y, w, h, c, t["panel"], t["stroke"], 1.75))
    # Slim gradient rail, clipped so it follows the notched corner.
    s.add(
        f'<rect x="{x}" y="{y}" width="9" height="{h}" fill="url(#holo)" clip-path="url(#card)"/>'
    )
    s.add(notch(x + 8, y + 8, w - 16, h - 16, 12, "none", t["stroke_soft"], 1))
    s.add(brackets(x + 16, y + 16, w - 32, h - 32, 18, t["gold_shape"], 2))

    # HUD
    hud_top, hud_h = 30, 44
    s.add(diamond(56, hud_top + hud_h / 2, 6, t["gold_shape"]))
    s.add(s.text(74, FONTS["mono"].baseline(hud_top, hud_h, 14), "PLAYER_PROFILE", "mono", 14, t["muted"]))
    bali_x = 74 + tw("PLAYER_PROFILE", "mono", 14) + 16
    s.add(s.text(bali_x, FONTS["mono"].baseline(hud_top, hud_h, 14), "BALI, ID", "mono", 14, t["gold"]))

    pill_w, pill_h = 96, 32
    pill_x = x + w - 28 - pill_w
    pill_y = hud_top + (hud_h - pill_h) / 2
    rank_w, rank_h = 118, 32
    rank_x = pill_x - 12 - rank_w
    rank_y = pill_y
    if bali_x + tw("BALI, ID", "mono", 14) + 16 > rank_x:
        raise SystemExit("HUD labels collide with the rank badge")
    s.add(notch(rank_x, rank_y, rank_w, rank_h, 8, t["band"], t["gold_shape"], 1.4))
    s.add(s.text(rank_x + 14, FONTS["mono"].baseline(rank_y, rank_h, 12), "RANK", "mono", 12, t["gold"]))
    s.add(s.text(
        rank_x + rank_w - 16, FONTS["display"].baseline(rank_y, rank_h, 18),
        "P1", "display", 18, t["ink"], anchor="end",
    ))
    s.add(notch(pill_x, pill_y, pill_w, pill_h, 8, t["pill"]))
    s.add(f'<circle cx="{pill_x + 20}" cy="{pill_y + pill_h / 2}" r="4.5" fill="{t["dot"]}" class="pulse"/>')
    s.add(s.text(pill_x + 32, FONTS["mono"].baseline(pill_y, pill_h, 13), "OPEN", "mono", 13, t["pill_ink"]))

    rule_y = y + 68
    s.add(f'<path d="M48 {rule_y} H{x + w - 28}" stroke="{t["stroke_soft"]}" stroke-width="1.25"/>')

    # Holographic emblem
    ecx, ecy, er = 188, 292, 112
    s.add(f'<circle cx="{ecx}" cy="{ecy}" r="{er + 46}" fill="url(#glow)"/>')
    s.add(
        f'<circle class="ring" cx="{ecx}" cy="{ecy}" r="{er + 14}" fill="none" '
        f'stroke="url(#holo)" stroke-width="2.4"/>'
    )
    s.add(
        f'<circle cx="{ecx}" cy="{ecy}" r="{er + 4}" fill="none" stroke="{t["gold_shape"]}" '
        f'stroke-width="1.25" opacity="0.85"/>'
    )
    for i in range(8):
        ang = math.pi / 4 * i
        inner = er + 24
        outer = er + (34 if i % 2 == 0 else 28)
        x1, y1 = ecx + inner * math.cos(ang), ecy + inner * math.sin(ang)
        x2, y2 = ecx + outer * math.cos(ang), ecy + outer * math.sin(ang)
        s.add(
            f'<path d="M{x1:.1f} {y1:.1f} L{x2:.1f} {y2:.1f}" stroke="{t["gold_shape"]}" '
            f'stroke-width="1.6" stroke-linecap="square"/>'
        )
    s.add(f'<circle cx="{ecx}" cy="{ecy}" r="{er}" fill="{t["screen"]}"/>')
    s.defs.append(f'<clipPath id="screen"><circle cx="{ecx}" cy="{ecy}" r="{er - 1}"/></clipPath>')
    s.add(f'<circle cx="{ecx}" cy="{ecy}" r="{er - 1}" fill="url(#grid)" clip-path="url(#screen)"/>')
    s.add(
        f'<g clip-path="url(#screen)"><rect class="scan" x="{ecx - er + 8}" y="{ecy - er + 8}" '
        f'width="{er * 2 - 16}" height="2" fill="#f6d56a" opacity="0"/></g>'
    )
    s.add(s.text(ecx, ecy - 36, "PLAYER", "mono", 13, "#9be7da", anchor="middle"))
    s.add(s.text(ecx, ecy + 24, "WY", "display", 64, "#f6d56a", anchor="middle"))
    cursor_x = ecx + tw("WY", "display", 64) / 2 + 8
    s.add(f'<rect class="blink" x="{cursor_x:.1f}" y="{ecy - 22}" width="4" height="42" fill="#f6d56a"/>')
    s.add(s.text(ecx, ecy + 58, "P1", "mono", 15, "#9be7da", anchor="middle"))

    # Identity sits clear of the emblem and of the focus chart.
    tx = 360
    radar_r = 54
    radar_cx = 1016
    radar_cy = 168
    name_size = 58
    name_w = tw("Widya Yasa", "display", name_size)
    if tx + name_w + 28 > radar_cx - radar_r - tw("OSS", "mono", 12) - 10:
        raise SystemExit("Name collides with the focus chart")
    eyebrow = "FULL-STACK × GAME DEV"
    s.add(s.text(tx, 156, eyebrow, "disp", 18, t["teal"]))
    if tx + tw(eyebrow, "disp", 18) > radar_cx - radar_r - 36:
        raise SystemExit("Eyebrow collides with the focus chart")
    s.add(s.text(tx, 222, "Widya Yasa", "display", name_size, t["ink"]))
    s.add(f'<path d="M{tx} 242 H{tx + 168}" stroke="url(#holo)" stroke-width="3" stroke-linecap="square"/>')

    # Focus chart — four equal axes, labels only, no scores.
    axes = _ring_points(radar_cx, radar_cy, radar_r)
    web = " ".join(f"{px:.1f},{py:.1f}" for px, py in axes)
    inner = " ".join(f"{px:.1f},{py:.1f}" for px, py in _ring_points(radar_cx, radar_cy, radar_r * 0.55))
    s.add(f'<polygon points="{web}" fill="{t["band"]}" stroke="{t["stroke_soft"]}" stroke-width="1.25"/>')
    s.add(f'<polygon points="{inner}" fill="none" stroke="{t["stroke_soft"]}" stroke-width="1"/>')
    for px, py in axes:
        s.add(
            f'<path d="M{radar_cx} {radar_cy} L{px:.1f} {py:.1f}" stroke="{t["stroke_soft"]}" stroke-width="1"/>'
        )
    s.add(f'<polygon points="{web}" fill="url(#holo)" opacity="0.28" stroke="{t["gold_shape"]}" stroke-width="1.6"/>')
    for px, py in axes:
        s.add(diamond(px, py, 3.5, t["gold_shape"]))
    s.add(f'<circle cx="{radar_cx}" cy="{radar_cy}" r="3" fill="{t["ink"]}"/>')
    label_fill = t["gold"]
    top, right, bottom, left = FOCUS
    s.add(s.text(radar_cx, radar_cy - radar_r - 8, top, "mono", 12, label_fill, anchor="middle"))
    s.add(s.text(radar_cx + radar_r + 10, radar_cy + 4, right, "mono", 12, label_fill))
    s.add(s.text(radar_cx, radar_cy + radar_r + 16, bottom, "mono", 12, label_fill, anchor="middle"))
    s.add(s.text(radar_cx - radar_r - 10, radar_cy + 4, left, "mono", 12, label_fill, anchor="end"))
    right_edge = radar_cx + radar_r + 8 + tw(right, "mono", 12)
    if right_edge > x + w - 24:
        raise SystemExit("Focus label runs off the player card")
    if radar_cy - radar_r - 10 < rule_y + 8:
        raise SystemExit("Focus label collides with the HUD rule")

    row_y, row_h = 268, 38
    value_x = tx + 124
    value_max = x + w - 40 - value_x
    for label, value in STATS:
        if tw(value, "sans", 17) > value_max:
            raise SystemExit(f"Stat value too wide: {value}")
        s.add(f'<path d="M{tx} {row_y + row_h - 2} H{x + w - 36}" stroke="{t["stroke_soft"]}" stroke-width="1"/>')
        s.add(f'<rect x="{tx}" y="{row_y + 11}" width="3" height="16" fill="{t["gold_shape"]}"/>')
        s.add(s.text(tx + 14, FONTS["mono"].baseline(row_y, row_h, 13), label, "mono", 13, t["gold"]))
        s.add(s.text(value_x, FONTS["sans"].baseline(row_y, row_h, 17), value, "sans", 17, t["ink"]))
        row_y += row_h

    # Availability bar — full, because the status above is "open". No fake XP number.
    bar_y = row_y + 36
    bar_x, bar_w, bar_h = tx, x + w - 36 - tx, 8
    s.add(s.text(bar_x, FONTS["mono"].baseline(bar_y - 24, 20, 12), "SIGNAL", "mono", 12, t["gold"]))
    s.add(s.text(bar_x + bar_w, FONTS["mono"].baseline(bar_y - 24, 20, 12), "OPEN", "mono", 12, t["ink"], anchor="end"))
    s.add(f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="2" fill="{t["stroke_soft"]}"/>')
    s.add(f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="2" fill="url(#holo)"/>')
    for i in range(1, 8):
        tick = bar_x + bar_w * i / 8
        s.add(f'<path d="M{tick:.1f} {bar_y} V{bar_y + bar_h}" stroke="{t["panel"]}" stroke-width="1.5"/>')

    plates_y, plates_h = 536, 72
    gap = 14
    inner_left, inner_right = 48, x + w - 28
    pw = (inner_right - inner_left - gap * 2) / 3
    if plates_y < bar_y + bar_h + 18:
        raise SystemExit("Trait plates collide with the signal bar")
    for i, (word, color_key) in enumerate(TRAITS):
        px = inner_left + i * (pw + gap)
        mark = t[color_key]
        s.add(notch(px, plates_y, pw, plates_h, 10, t["band"], t["stroke_soft"], 1))
        s.add(f'<rect x="{px + 16}" y="{plates_y + 16}" width="28" height="4" rx="1" fill="{mark}"/>')
        s.add(s.text(
            px + 16, FONTS["display"].baseline(plates_y + 22, plates_h - 30, 20),
            word, "display", 20, t["ink"],
        ))
        if tw(word, "display", 20) > pw - 32:
            raise SystemExit(f"Trait plate too narrow for {word}")

    s.render(OUT / f"header-{t['id']}.svg")


# ───────────────────────────── marquee ─────────────────────────────

MARQUEE_ALT = (
    "Ticker: ship features, share knowledge, enjoy the journey. "
    "Open to freelance and full-time. Bali, Indonesia."
)


def build_marquee(t: dict) -> None:
    W, H = 1200, 48
    s = Svg(W, H, "Mission ticker", MARQUEE_ALT)
    size, gap, r = 16, 22, 5
    seq = 0
    items = []
    for phrase in MARQUEE:
        width = tw(phrase, "disp", size)
        items.append((seq, phrase, width))
        seq += width + gap + r * 2 + gap
    copies = math.ceil((W + seq) / seq)
    dur = max(16, seq / 70)
    s.css.append(
        f".track{{animation:slide {dur:.1f}s linear infinite}}"
        f"@keyframes slide{{to{{transform:translateX(-{seq:.1f}px)}}}}"
        "@media (prefers-reduced-motion:reduce){.track{animation:none}}"
    )
    s.defs.append(f'<clipPath id="mq"><rect width="{W}" height="{H}"/></clipPath>')
    s.add(f'<rect width="{W}" height="{H}" fill="{t["marquee_bg"]}"/>')
    s.add(f'<rect width="{W}" height="2" fill="{t["marquee_mark"]}"/>')
    s.add(f'<rect y="{H - 2}" width="{W}" height="2" fill="{t["marquee_mark"]}"/>')
    y = FONTS["disp"].baseline(0, H, size)
    track = ['<g clip-path="url(#mq)"><g class="track">']
    for n in range(copies):
        origin = n * seq
        for ix, phrase, width in items:
            track.append(s.text(origin + ix, y, phrase, "disp", size, t["marquee_ink"]))
            track.append(diamond(origin + ix + width + gap + r, H / 2, r, t["marquee_mark"]))
    track.append("</g></g>")
    s.add("".join(track))
    s.render(OUT / f"marquee-{t['id']}.svg")


# ───────────────────────────── sections ─────────────────────────────

def build_section(t: dict, key: str, title: str, subtitle: str) -> None:
    W, H = 1200, 72
    alt = {
        "profile": "Section: Player profile",
        "stages": "Section: Featured stages",
        "inventory": "Section: Inventory",
        "contrib": "Section: Contribution game",
        "quests": "Section: Side quests",
    }[key]
    s = Svg(W, H, title, alt)
    s.add(notch(2, 8, W - 4, H - 16, 12, t["panel"], t["stroke"], 1.5))
    s.add(diamond(36, H / 2, 6, t["gold_shape"]))
    title_size = 26
    s.add(s.text(56, FONTS["display"].baseline(8, H - 16, title_size), title, "display", title_size, t["ink"]))
    title_w = tw(title, "display", title_size)
    sub_w = tw(subtitle, "mono", 14)
    rule_x = 56 + title_w + 18
    rule_end = W - 36 - sub_w - 16
    if rule_end - rule_x > 24:
        s.add(
            f'<path d="M{rule_x:.1f} {H / 2} H{rule_end:.1f}" stroke="{t["stroke_soft"]}" '
            f'stroke-width="1.5" stroke-dasharray="2 7" stroke-linecap="round"/>'
        )
    s.add(s.text(W - 28, FONTS["mono"].baseline(8, H - 16, 14), subtitle, "mono", 14, t["muted"], anchor="end"))
    s.render(OUT / f"section-{key}-{t['id']}.svg")


# ───────────────────────────── projects ─────────────────────────────

def project_alt(p: dict) -> str:
    desc = " ".join(p["desc"].split())
    status = f" Status: {p['status']}." if p.get("status") else ""
    where = "Opens the GitHub repository." if "github.com" in p["href"] else "Opens the portfolio."
    return f"Stage {p['num']} — {p['title']}. {p['kind']}.{status} {desc}. {where}"


def build_project(t: dict, p: dict) -> None:
    W, H = 1200, 248
    s = Svg(W, H, f"{p['title']} — stage {p['num']}", project_alt(p))
    s.css.append(MOTION)
    x, y, w, h, c = 3, 3, W - 6, H - 6, 16
    s.defs.append(f'<clipPath id="card"><path d="{notch_d(x, y, w, h, c)}"/></clipPath>')
    s.add(notch(x, y, w, h, c, t["panel"], t["stroke"], 1.75))
    rail = 124
    s.add(f'<rect x="{x}" y="{y}" width="{rail}" height="{h}" fill="{RAIL[p["slug"]]}" clip-path="url(#card)"/>')
    rcx = x + rail / 2
    s.add(s.text(rcx, 92, "STAGE", "mono", 13, "#fffaf2", anchor="middle"))
    s.add(s.text(rcx, 146, p["num"], "display", 44, "#fffaf2", anchor="middle"))

    tx = x + rail + 32
    title_size = 34
    s.add(s.text(tx, 72, p["title"], "display", title_size, t["ink"]))
    title_w = tw(p["title"], "display", title_size)
    if title_w > 640:
        raise SystemExit(f"Title too wide: {p['title']}")
    if p.get("status"):
        label = p["status"].upper()
        chip_w = tw(label, "mono", 13) + 28
        chip_h = 28
        chip_x = tx + title_w + 16
        chip_y = 48
        if chip_x + chip_w > 990:
            raise SystemExit(f"Status chip collides with the stage art: {p['title']}")
        s.add(notch(chip_x, chip_y, chip_w, chip_h, 7, t["band"], t["gold_shape"], 1.25))
        s.add(s.text(
            chip_x + 14, FONTS["mono"].baseline(chip_y, chip_h, 13),
            label, "mono", 13, t["ink"],
        ))
    s.add(s.text(tx, 106, p["kind"], "mono", 16, t[KIND_KEY[p["slug"]]]))
    if tw(p["kind"], "mono", 16) > 820:
        raise SystemExit(f"Kind line too wide: {p['kind']}")
    lines = lines_of(p["desc"], "sans", 18, 820)
    if len(lines) > 2:
        raise SystemExit(f"Description needs more than 2 lines: {p['title']} -> {lines}")
    for i, line in enumerate(lines):
        s.add(s.text(tx, 146 + i * 28, line, "sans", 18, t["muted"]))
    cta = p.get("cta", "PORTFOLIO")
    cta_y = 214
    s.add(s.text(tx, cta_y, cta, "mono", 15, t["ink"]))
    arrow_x = tx + tw(cta, "mono", 15) + 12
    s.add(
        f'<g class="nudge"><path d="M{arrow_x:.1f} {cta_y - 5} h16 M{arrow_x + 8:.1f} {cta_y - 12} '
        f'l8 7 l-8 7" fill="none" stroke="{t["gold_shape"]}" stroke-width="2.2" '
        f'stroke-linecap="round" stroke-linejoin="round"/></g>'
    )
    s.add(f'<g transform="translate(1016 56)">{ART[p["art"]](t)}</g>')
    s.render(OUT / f"project-{p['slug']}-{t['id']}.svg")


# ───────────────────────────── inventory ─────────────────────────────

def inventory_alt() -> str:
    chunks = []
    for title, _color, items in INVENTORY:
        chunks.append(f"{title.title()}: {', '.join(items)}")
    return "Inventory. " + ". ".join(chunks) + "."


def build_inventory(t: dict) -> None:
    chip_font, chip_size, chip_h, chip_gap = "semi", 15, 36, 8
    pad_x = 14
    margin, gap = 8, 14
    col_w = (1200 - margin * 2 - gap * 2) / 3
    inner = col_w - 36
    layouts = []
    for title, color_key, items in INVENTORY:
        rows: list[list[tuple[str, float]]] = []
        row: list[tuple[str, float]] = []
        used = 0.0
        for item in items:
            cw = tw(item, chip_font, chip_size) + pad_x * 2
            if cw > inner:
                raise SystemExit(f"Inventory chip too wide: {item}")
            if row and used + chip_gap + cw > inner:
                rows.append(row)
                row, used = [], 0.0
            if row:
                used += chip_gap
            row.append((item, cw))
            used += cw
        if row:
            rows.append(row)
        layouts.append((title, color_key, rows))
    head_h = 58
    body = max(len(rows) for _t, _c, rows in layouts)
    col_h = 20 + head_h + body * chip_h + (body - 1) * chip_gap + 18
    H = int(margin + col_h + margin)
    s = Svg(1200, H, "Inventory", inventory_alt())
    for i, (title, color_key, rows) in enumerate(layouts):
        x = margin + i * (col_w + gap)
        y = margin
        s.add(notch(x, y, col_w, col_h, 14, t["panel"], t["stroke"], 1.6))
        accent = t[color_key]
        s.add(f'<rect x="{x + 18}" y="{y + 18}" width="8" height="28" rx="2" fill="{accent}"/>')
        s.add(s.text(x + 36, FONTS["display"].baseline(y + 12, 40, 20), title, "display", 20, t["ink"]))
        s.add(f'<path d="M{x + 18} {y + head_h} H{x + col_w - 18}" stroke="{t["stroke_soft"]}" stroke-width="1.25"/>')
        cy = y + head_h + 14
        for row in rows:
            cx = x + 18
            for label, cw in row:
                s.add(
                    f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cw:.1f}" height="{chip_h}" rx="8" '
                    f'fill="{t["chip"]}" stroke="{t["stroke_soft"]}" stroke-width="1.15"/>'
                )
                s.add(f'<rect x="{cx + 1:.1f}" y="{cy + 8:.1f}" width="3.5" height="{chip_h - 16}" rx="1.5" fill="{accent}"/>')
                s.add(s.text(
                    cx + pad_x, FONTS[chip_font].baseline(cy, chip_h, chip_size),
                    label, chip_font, chip_size, t["ink"],
                ))
                cx += cw + chip_gap
            cy += chip_h + chip_gap
    s.render(OUT / f"inventory-{t['id']}.svg")


# ───────────────────────────── side quests ─────────────────────────────

def quests_alt() -> str:
    bits = [f"{name.title()}: {' '.join(detail.split())}" for name, detail, _a, _c in QUESTS]
    return "Side quests. " + ". ".join(bits) + "."


def build_sidequests(t: dict) -> None:
    W, H = 1200, 210
    s = Svg(W, H, "Side quests", quests_alt())
    x, y, w, h = 3, 3, W - 6, H - 6
    s.add(notch(x, y, w, h, 16, t["panel"], t["stroke"], 1.75))
    n = len(QUESTS)
    cell = w / n
    for i, (name, detail, art, color_key) in enumerate(QUESTS):
        cx = x + cell * i
        if i:
            s.add(f'<path d="M{cx:.1f} {y + 22} V{y + h - 22}" stroke="{t["stroke_soft"]}" stroke-width="1.25"/>')
        color = t[color_key]
        icx, icy = cx + cell / 2, y + 46
        if art == "star":
            s.add(icon_star(icx, icy, 14, color))
        elif art == "dpad":
            s.add(icon_dpad(icx, icy, color))
        elif art == "compass":
            s.add(icon_compass(icx, icy, color, t["gold_shape"]))
        elif art == "branch":
            s.add(icon_branch(icx, icy, color))
        else:
            s.add(icon_bowl(icx, icy, color))
        s.add(s.text(icx, y + 92, name, "mono", 13, t["gold"], anchor="middle"))
        lines = lines_of(detail, "semi", 16, cell - 36)
        if len(lines) > 2:
            raise SystemExit(f"Side quest wraps too far: {detail}")
        for li, line in enumerate(lines):
            s.add(s.text(icx, y + 126 + li * 24, line, "semi", 16, t["ink"], anchor="middle"))
    s.render(OUT / f"sidequests-{t['id']}.svg")


# ───────────────────────────── footer ─────────────────────────────

FOOTER_ALT = (
    "Join the party. I'm open. Got a project, collab idea, or just want to say hi? "
    "Let's build something intentional. Opens the portfolio."
)


def build_footer(t: dict) -> None:
    W, H = 1200, 236
    s = Svg(W, H, "Join the party", FOOTER_ALT)
    s.css.append(MOTION)
    x, y, w, h = 3, 3, W - 6, H - 6
    s.add(notch(x, y, w, h, 18, t["panel"], t["stroke"], 1.75))
    s.add(brackets(x + 14, y + 14, w - 28, h - 28, 14, t["gold_shape"], 1.8))
    s.add(s.text(48, 64, "JOIN_THE_PARTY", "mono", 15, t["gold"]))
    s.add(s.text(48, 124, "I'm open", "display", 60, t["ink"]))
    s.add(s.text(48, 168, "Got a project, collab idea, or just want to say hi?", "sans", 20, t["muted"]))
    s.add(s.text(48, 200, "Let's build something intentional.", "semi", 20, t["ink"]))

    label = "OPEN PORTFOLIO"
    bw = tw(label, "mono", 16) + 56
    bh = 54
    bx = W - 48 - bw
    by = (H - bh) / 2
    s.add(notch(bx, by, bw, bh, 10, t["pill"]))
    s.add(f'<circle cx="{bx + 22}" cy="{by + bh / 2}" r="5" fill="{t["dot"]}" class="pulse"/>')
    s.add(s.text(bx + 36, FONTS["mono"].baseline(by, bh, 16), label, "mono", 16, t["pill_ink"]))
    s.render(OUT / f"footer-{t['id']}.svg")


# ───────────────────────────── readme ─────────────────────────────

def picture(name: str, alt: str, href: str | None = None) -> str:
    light = f"./assets/{name}-light.svg?v={VERSION}"
    dark = f"./assets/{name}-dark.svg?v={VERSION}"
    block = (
        "<picture>\n"
        f'  <source media="(prefers-color-scheme: dark)" srcset="{dark}" />\n'
        f'  <source media="(prefers-color-scheme: light)" srcset="{light}" />\n'
        f'  <img alt="{esc(alt)}" src="{light}" width="100%" />\n'
        "</picture>"
    )
    if href:
        return f'<a href="{href}">\n{block}\n</a>'
    return block


def build_readme() -> None:
    projects = "\n\n".join(
        f'<p align="center">\n{picture(f"project-{p["slug"]}", project_alt(p), p["href"])}\n</p>'
        for p in PROJECTS
    )
    sections = {key: picture(f"section-{key}", alt) for key, _title, _sub in SECTIONS
                for alt in [{
                    "profile": "Section: Player profile",
                    "stages": "Section: Featured stages",
                    "inventory": "Section: Inventory",
                    "contrib": "Section: Contribution game",
                    "quests": "Section: Side quests",
                }[key]]}
    links = (
        f'<p align="center">\n'
        f'  <a href="{PORTFOLIO}">Portfolio</a>\n'
        f'  &nbsp;·&nbsp;\n'
        f'  <a href="{GITHUB}">GitHub</a>\n'
        f'  &nbsp;·&nbsp;\n'
        f'  <a href="{LINKEDIN}">LinkedIn</a>\n'
        f'  &nbsp;·&nbsp;\n'
        f'  <a href="{INSTAGRAM}">Instagram</a>\n'
        f'</p>'
    )
    readme = f'''<!--
  Widya Yasa — profile README
  Portfolio: {PORTFOLIO}
  Regenerate cards: python3 scripts/build.py
  Regenerate Pac-Man graph: scripts/generate-pacman.ps1
-->

<p align="center">
{picture("header", HEADER_ALT, PORTFOLIO)}
</p>

<p align="center">
{picture("marquee", MARQUEE_ALT)}
</p>

{links}

{sections["profile"]}

I build web apps and game experiences that feel **fast**, **intentional**, and **easy to use**.
Currently taking freelance projects and open to full-time opportunities.

I'm someone who genuinely enjoys learning new things and sharing them with others — casual chats, sharing sessions, mentoring. I stay active in tech communities because the best way to grow is to be around people who are just as excited to learn.

I love open source — currently building [PatchSense]({PATCHSENSE}), a Rust CLI for CVE triage.

{sections["stages"]}

{projects}

<p>→ more builds on the <a href="{PORTFOLIO}">portfolio</a></p>

{sections["inventory"]}

<p align="center">
{picture("inventory", inventory_alt())}
</p>

{sections["contrib"]}

<div align="center">

<!-- Pac-Man eats the contribution grid — regenerate: scripts/generate-pacman.ps1 -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/pacman-contribution-graph-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="./assets/pacman-contribution-graph.svg" />
  <img alt="Pac-Man eating the GitHub contribution graph" src="./assets/pacman-contribution-graph.svg" width="100%" />
</picture>

</div>

{sections["quests"]}

<p align="center">
{picture("sidequests", quests_alt())}
</p>

<p align="center">
{picture("footer", FOOTER_ALT, PORTFOLIO)}
</p>

{links}
'''
    # The two-space break in the original tagline is a markdown hard break.
    readme = readme.replace(
        "easy to use**.\nCurrently",
        "easy to use**.  \nCurrently",
    )
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    print("  README.md")


# ───────────────────────────── contrast gate ─────────────────────────────

def _lum(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    vals = []
    for i in range(3):
        c = int(h[i * 2:i * 2 + 2], 16) / 255
        vals.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = vals
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def assert_contrast() -> None:
    pairs = []
    for t in THEMES:
        pairs += [
            (t["ink"], t["panel"], f"{t['id']} ink/panel"),
            (t["ink"], t["band"], f"{t['id']} ink/band"),
            (t["ink"], t["field"], f"{t['id']} ink/field"),
            (t["muted"], t["panel"], f"{t['id']} muted/panel"),
            (t["gold"], t["panel"], f"{t['id']} gold/panel"),
            (t["teal"], t["panel"], f"{t['id']} teal/panel"),
            (t["pill_ink"], t["pill"], f"{t['id']} pill"),
            (t["kind_teal"], t["panel"], f"{t['id']} kind teal"),
            (t["kind_sky"], t["panel"], f"{t['id']} kind sky"),
            (t["kind_violet"], t["panel"], f"{t['id']} kind violet"),
            (t["kind_rust"], t["panel"], f"{t['id']} kind rust"),
            (t["marquee_ink"], t["marquee_bg"], f"{t['id']} marquee"),
            ("#f6d56a", t["screen"], f"{t['id']} monogram"),
            ("#9be7da", t["screen"], f"{t['id']} screen label"),
        ]
    for slug, rail in RAIL.items():
        pairs.append(("#fffaf2", rail, f"rail {slug}"))
    bad = []
    for fg, bg, label in pairs:
        ratio = contrast(fg, bg)
        if ratio < 4.5:
            bad.append(f"{label}: {ratio:.2f} ({fg} on {bg})")
    if bad:
        raise SystemExit("Contrast below 4.5:1\n" + "\n".join(bad))


def main() -> None:
    assert_contrast()
    OUT.mkdir(exist_ok=True)
    pacman = [
        OUT / "pacman-contribution-graph.svg",
        OUT / "pacman-contribution-graph-dark.svg",
    ]
    before = {p: p.read_bytes() for p in pacman}
    print("Building cards:")
    for t in THEMES:
        build_header(t)
        build_marquee(t)
        for key, title, subtitle in SECTIONS:
            build_section(t, key, title, subtitle)
        for project in PROJECTS:
            build_project(t, project)
        build_inventory(t)
        build_sidequests(t)
        build_footer(t)
    build_readme()
    after = {p: p.read_bytes() for p in pacman}
    if before != after:
        raise SystemExit("Pac-Man SVGs were modified; the generator must not touch them.")
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for needle in (
        "Stage 01", "Stage 02", "Stage 03", "PatchSense", "Aku Mampu AI", "Midnight Toys",
        PATCHSENSE, "In development", "Critical, Review, and Defer",
        PORTFOLIO, LINKEDIN, INSTAGRAM, GITHUB,
    ):
        if needle not in text:
            raise SystemExit(f"README is missing {needle!r}")
    if "Stage 04" in text or "Velnara" in text:
        raise SystemExit("Retired stage copy is still in the README")
    print("Done.")


if __name__ == "__main__":
    main()

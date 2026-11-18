#!/usr/bin/env python3
"""THE WORLD IN ONE DAY -- Tuesday, 17 November 2026.

A dense newspaper front page drawn from scratch with the Python
standard library only. No network, no downloaded assets, no fonts
from disk: every letter is rendered by a 5x7 bitmap font defined
below, every shape is drawn by the Canvas class, and the PNG is
encoded by hand (zlib + struct).

Layout (1024 x 1024, deep-navy masthead on cream paper):
  masthead          -- title, date line, story count
  figures strip     -- the day in four figures
  map + top stories -- a simplified world map with the day's
                       hotspots, beside three illustrated leads
  story grid        -- 40 verified stories in seven sections,
                       two columns, headline + one-line deck each
"""

import struct
import zlib
from pathlib import Path

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
CREAM = (247, 241, 227)
PAPER = (250, 246, 236)
NAVY = (16, 28, 56)
NAVY2 = (27, 47, 94)
RED = (179, 32, 44)
INK = (26, 26, 26)
GREY = (90, 90, 88)
FAINT = (200, 196, 184)
SEA = (213, 229, 238)
LAND = (227, 211, 168)
LAND_EDGE = (27, 47, 94)
WHITE = (255, 255, 255)
SKY_DUSK = (58, 44, 86)
SKY_ORANGE = (214, 116, 52)
FIRE = (232, 122, 30)
FIRE2 = (245, 196, 66)
SMOKE = (70, 66, 72)
WATER = (28, 44, 74)

# ------------------------------------------------------------- 5x7 font
# Each glyph is 7 rows of 5 pixels, "#" = on, "." = off.
# Uppercase letters, digits and the punctuation the page uses.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "01010", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "*": ("00000", "00100", "10101", "01110", "10101", "00100", "00000"),
    "@": ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
    "#": ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
}


def glyph(ch):
    return FONT.get(ch, FONT["?"])


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)
        self.fill(bg)

    def fill(self, color):
        self.px[:] = bytes(color) * (self.w * self.h)

    def put(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def rect(self, x, y, w, h, color):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            self.px[base:(yy * self.w + x1) * 3] = bytes(color) * (x1 - x0)

    def hline(self, x, y, w, color):
        self.rect(x, y, w, 1, color)

    def vline(self, x, y, h, color):
        self.rect(x, y, 1, h, color)

    def line(self, x0, y0, x1, y1, color):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.put(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def polyline(self, pts, color):
        for a, b in zip(pts, pts[1:]):
            self.line(a[0], a[1], b[0], b[1], color)
        if len(pts) > 2:
            self.line(pts[-1][0], pts[-1][1], pts[0][0], pts[0][1], color)

    def polyfill(self, pts, color):
        # Even-odd scanline fill.
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for a, b in zip(xs[::2], xs[1::2]):
                self.rect(int(a), y, max(1, int(b) - int(a)), 1, color)

    def disc(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)

    # ------------------------------------------------------------ text
    def text_w(self, s, scale):
        return len(s) * 6 * scale

    def draw_text(self, s, x, y, scale, color):
        s = s.upper()
        cx = x
        for ch in s:
            g = glyph(ch)
            for row in range(7):
                bits = g[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.rect(cx + col * scale, y + row * scale,
                                  scale, scale, color)
            cx += 6 * scale
        return cx

    def text_centred(self, s, cx, y, scale, color):
        w = self.text_w(s, scale)
        return self.draw_text(s, cx - w // 2, y, scale, color)

    def wrap(self, s, max_w, scale):
        """Word-wrap to lines of at most max_w pixels; returns lines."""
        words, lines, cur = s.split(), [], ""
        for word in words:
            trial = (cur + " " + word).strip()
            if self.text_w(trial, scale) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

# ------------------------------------------------------------- the day
# 40 stories, all reported on Tuesday 17 November 2026.
# Each item: (headline <= 40 chars, deck <= 81 chars).
SECTIONS = [
    ("EUROPE", [
        ("KERCH BRIDGE SHUT AFTER STRIKE",
         "Ukraine hits the Crimea link; Russia strikes Kyiv bridges in reply."),
        ("BRITAIN SANCTIONS SETTLER FIRMS",
         "Eight Israeli settlement companies hit over West Bank expansion."),
        ("LE PEN PLEDGES EARLIER RETIREMENT",
         "Far-right leader promises lower pension age if she wins power."),
        ("EU CHARGES TEMU OVER ILLEGAL GOODS",
         "Brussels accuses the shopping app of selling banned products."),
        ("NATO DROPS ALBANIA SUMMIT FOR 2027",
         "Tirana offers to host the alliance meeting in 2028 instead."),
        ("UK SETS OUT EU SUMMIT PACKAGE",
         "London unveils its agenda for the next UK-EU leaders' meeting."),
        ("UKRAINE TALKS END WITHOUT DEAL",
         "Kyiv negotiates with US and Europe; no agreement reached."),
        ("SERBIAN MIG-29 CRASH KILLS PILOT",
         "Serbian fighter jet crashes during a training flight."),
    ]),
    ("MIDDLE EAST", [
        ("TANKERS BURNING OFF HORMUZ",
         "Ships hit mines near the strait; Iran's foreign minister talks in Oman."),
        ("DRONES TARGET US BASE IN BAHRAIN",
         "Iranian drones intercepted over Sheikh Isa; no casualties reported."),
        ("ISRAEL URGED TO OPEN GAZA CROSSINGS",
         "UK, Australia, Canada and Italy press for aid as winter nears."),
        ("HOUTHIS ADVANCE IN YEMEN",
         "Government forces retreat from the Red Sea coast."),
        ("OIL CAUGHT BETWEEN TWO FORCES",
         "Rising Mideast exports clash with tanker attacks in the Gulf."),
    ]),
    ("ASIA-PACIFIC", [
        ("XI, TRUMP AND PUTIN TO MEET",
         "Three leaders gather in Shenzhen at APEC on 19 November."),
        ("JAPAN SCRAMBLES JETS ON INCURSION",
         "Russian aircraft violate Japanese airspace, Tokyo says."),
        ("IMRAN KHAN FEARS DYING IN JAIL",
         "Ex-PM seeks hospital transfer from his Pakistani cell."),
        ("ZELENSKYY ASKS SPACEX FOR MORE",
         "Kyiv urges Starshield limits lifted; Musk says Pentagon decides."),
        ("QUAD LEADERS MEET IN MANILA",
         "Trump, Albanese, Modi and Takaichi hold talks in the Philippines."),
        ("PHUKET FIRE KILLS 11, INJURES 16",
         "Blaze sweeps a Thai resort town; cause under investigation."),
        ("TRUMP MAY MEET KIM IN CHINA",
         "US president signals a possible meeting during his China trip."),
    ]),
    ("AMERICAS", [
        ("US LOSES MEASLES-FREE STATUS",
         "Most cases in 30 years as the disease spreads nationwide."),
        ("FAA HALTS ROUTER ROLLOUT",
         "Agency pauses upgrade after nationwide ground stop."),
        ("FLIGHTS GROUNDED ACROSS AMERICA",
         "Air-traffic system failure strands travellers nationwide."),
        ("HUANG RESIGNS FROM NVIDIA",
         "Ex-chief quits amid affair and spy reports; would return if asked."),
        ("SHIP HITS NEW ORLEANS DOCK",
         "Steering failure causes collision on the Mississippi river."),
        ("THREE DIE IN GRAND CANYON CRASH",
         "Light aircraft goes down in the Arizona canyon."),
    ]),
    ("AFRICA", [
        ("ERITREA ELIMINATES TRACHOMA",
         "WHO confirms the eye disease wiped out in the Horn of Africa."),
        ("17 KILLED IN SOUTH AFRICA SHOOTINGS",
         "Two mass shootings rock communities in one day."),
        ("4.1 QUAKE OFF LIBYA COAST",
         "Tremor felt along the Mediterranean shoreline."),
        ("EU-RWANDA RETURN-HUB PLAN SPARKS ROW",
         "Migrant deportation scheme draws criticism across Europe."),
    ]),
    ("MARKETS & TECH", [
        ("BITCOIN STALLS BELOW $65,000",
         "Cryptocurrency down 15 percent this month as risk appetite fades."),
        ("BECKHAM FIRM SUES COTY FOR $41M",
         "Company claims breach over fragrance licensing deal."),
        ("WEBSITES HACKED TO STEAL CRYPTO",
         "Attacks target iPhone users through compromised popular sites."),
        ("TWO WORLD CUPS TO OVERLAP",
         "FIFA and ICC plan 2030 tournaments on the same dates."),
        ("US TIGHTENS GLOBAL AI CHIP RULES",
         "Washington extends controls on advanced chip exports."),
    ]),
    ("SCIENCE & WORLD", [
        ("CHEMICALS COST $1.1 TRILLION A YEAR",
         "UN puts the yearly health bill from hormone disruptors at $1.1 trillion."),
        ("SCHOOL PHONE POUCHES LIFT SCORES",
         "Small test-score boost found in schools that lock phones away."),
        ("COP31 TALKS ENTER DECISIVE STAGE",
         "Climate negotiators in Antalya push for a final deal."),
        ("DEPARDIEU PLEADS GUILTY",
         "French actor admits assault and drops his appeal."),
        ("EPSTEIN DEATH DOUBTED BY EXPERT",
         "Forensic expert says Epstein was murdered, not suicide."),
    ]),
]

FIGURES = [
    ("1,336", "DRONES CLAIMED SHOT DOWN"),
    ("$65,000", "BITCOIN, DOWN 15% IN NOV"),
    ("$1.1 TRILLION", "YEARLY COST OF CHEMICALS"),
    ("1.7M", "DISPLACED IN GAZA"),
]

# Three illustrated leads: (draw function name, headline, deck).
LEADS = [
    ("bridge", "KERCH BRIDGE SHUT",
     "Ukraine hits the Crimea link; Russia hits Kyiv."),
    ("tanker", "TANKERS BURNING OFF HORMUZ",
     "Ships hit mines near the strait; talks open in Oman."),
    ("summit", "XI, TRUMP AND PUTIN TO MEET",
     "Three leaders meet in Shenzhen at APEC on 19 November."),
]

# ------------------------------------------------------------- map data
# Coarse continent outlines as (lon, lat) points, equirectangular.
CONTINENTS = [
    [(-168, 66), (-140, 70), (-125, 71), (-110, 68), (-95, 69), (-85, 66),
     (-80, 73), (-65, 60), (-55, 52), (-60, 47), (-70, 44), (-75, 35),
     (-80, 32), (-85, 30), (-90, 21), (-97, 16), (-105, 20), (-115, 28),
     (-125, 40), (-125, 49), (-140, 60), (-155, 58), (-165, 60)],
    [(-80, 10), (-75, 5), (-80, -5), (-81, -15), (-75, -20), (-70, -25),
     (-65, -35), (-60, -45), (-55, -40), (-50, -30), (-40, -20), (-35, -8),
     (-40, 0), (-50, 5), (-60, 8), (-70, 10)],
    [(-10, 36), (-5, 44), (-2, 48), (0, 51), (5, 53), (8, 57), (10, 59),
     (18, 56), (21, 55), (24, 58), (28, 60), (30, 62), (25, 65), (20, 70),
     (15, 68), (10, 64), (5, 60), (0, 55), (-5, 50), (-9, 43), (-9, 38)],
    [(-17, 15), (-15, 25), (-10, 30), (-5, 35), (0, 36), (10, 37),
     (20, 32), (30, 31), (35, 28), (40, 20), (43, 12), (48, 11), (51, 10),
     (45, 0), (40, -10), (35, -20), (32, -28), (28, -33), (20, -35),
     (15, -30), (12, -18), (13, -10), (9, 0), (8, 4), (-8, 5),
     (-13, 8), (-17, 12)],
    [(30, 36), (35, 36), (40, 38), (45, 40), (50, 42), (55, 45), (60, 45),
     (65, 50), (70, 55), (75, 60), (80, 65), (90, 70), (100, 72),
     (110, 73), (120, 72), (130, 70), (140, 72), (150, 70), (160, 66),
     (170, 66), (175, 64), (165, 60), (160, 55), (150, 50), (145, 45),
     (140, 40), (135, 35), (130, 32), (125, 30), (120, 25), (115, 20),
     (110, 15), (105, 10), (100, 8), (95, 10), (90, 15), (85, 20),
     (80, 15), (75, 10), (70, 8), (65, 12), (60, 15), (55, 20),
     (50, 25), (48, 30), (45, 32), (40, 35)],
    [(113, -22), (114, -30), (115, -35), (120, -34), (125, -32),
     (130, -32), (135, -35), (140, -38), (145, -38), (150, -37),
     (153, -32), (150, -25), (146, -20), (142, -15), (140, -12),
     (135, -12), (130, -13), (125, -15), (120, -20)],
    [(130, 31), (132, 33), (135, 35), (138, 37), (140, 39), (141, 41),
     (143, 43), (145, 44), (142, 42), (140, 38), (137, 35), (133, 33)],
]

# (lon, lat, label, label dx, label dy)
HOTSPOTS = [
    (31, 50, "KYIV", 6, -3),
    (56, 27, "HORMUZ", 6, -3),
    (35, 31, "GAZA", -34, 4),
    (114, 22, "SHENZHEN", -52, -3),
    (121, 15, "MANILA", 6, 4),
    (-0.1, 51.5, "LONDON", -46, -3),
    (-77, 39, "WASHINGTON", -72, -3),
    (139, 35, "TOKYO", 6, -3),
    (98, 8, "PHUKET", 6, 4),
    (50.5, 26, None, 0, 0),
    (73, 33, None, 0, 0),
    (28, -26, None, 0, 0),
    (39, 15, None, 0, 0),
    (13, 33, None, 0, 0),
]


# ------------------------------------------------------------- drawing
def draw_masthead(cv):
    cv.rect(0, 0, W, 96, NAVY)
    cv.text_centred("THE WORLD IN ONE DAY", W // 2, 12, 4, CREAM)
    cv.text_centred("TUESDAY 17 NOVEMBER 2026", W // 2, 50, 2, WHITE)
    cv.text_centred("40 STORIES - SIX CONTINENTS - ONE DAY", W // 2, 74, 1,
                    (168, 186, 214))
    cv.rect(0, 92, W, 4, RED)


def draw_figures(cv):
    cv.draw_text("THE DAY IN FOUR FIGURES", 16, 102, 1, RED)
    bw = 240
    for i, (num, label) in enumerate(FIGURES):
        x = 16 + i * 252
        if i:
            cv.vline(x - 8, 118, 32, FAINT)
        cv.draw_text(num, x, 118, 2, NAVY)
        cv.draw_text(label, x, 138, 1, GREY)


def draw_map(cv, x0, y0, w, h):
    cv.rect(x0, y0, w, h, SEA)
    cv.rect(x0, y0, w, 1, NAVY)
    cv.rect(x0, y0 + h - 1, w, 1, NAVY)

    def proj(lon, lat):
        px = x0 + int((lon + 180) / 360.0 * w)
        py = y0 + int((90 - lat) / 150.0 * h)
        return (px, py)

    for cont in CONTINENTS:
        pts = [proj(lon, lat) for lon, lat in cont]
        cv.polyfill(pts, LAND)
        cv.polyline(pts, LAND_EDGE)
    for lon, lat, label, dx, dy in HOTSPOTS:
        px, py = proj(lon, lat)
        cv.disc(px, py, 3, RED)
        cv.disc(px, py, 1, WHITE)
        if label:
            cv.draw_text(label, px + dx, py + dy, 1, NAVY)


def draw_lead_bridge(cv, x, y, w, h):
    cv.rect(x, y, w, h, SKY_DUSK)
    cv.rect(x, y + h - 12, w, 12, WATER)
    cv.rect(x, y + 10, w, 2, SKY_ORANGE)
    # towers
    cv.rect(x + 52, y + 2, 4, 18, (210, 205, 195))
    cv.rect(x + w - 66, y + 2, 4, 18, (210, 205, 195))
    cv.rect(x + 52, y + 2, w - 118, 2, (210, 205, 195))
    # deck: left span intact, a gap, then the broken span plunging down
    cv.rect(x, y + 20, w // 2 - 30, 4, (210, 205, 195))
    cv.line(x + w // 2 - 30, y + 24, x + w // 2 + 26, y + h - 6,
            (210, 205, 195))
    cv.line(x + w // 2 - 30, y + 22, x + w // 2 + 26, y + h - 8,
            (210, 205, 195))
    cv.rect(x + w // 2 + 26, y + h - 8, w - w // 2 - 34, 3,
            (210, 205, 195))
    # smoke over the break + fire glow in the water
    cv.disc(x + w // 2 - 6, y + 6, 5, SMOKE)
    cv.disc(x + w // 2 + 4, y + 3, 4, SMOKE)
    cv.disc(x + w // 2 + 8, y + h - 5, 3, FIRE2)


def draw_lead_tanker(cv, x, y, w, h):
    cv.rect(x, y, w, h, SKY_DUSK)
    cv.rect(x, y + h - 12, w, 12, WATER)
    cv.rect(x, y + 10, w, 2, SKY_ORANGE)
    # hull
    cv.rect(x + 30, y + 18, w - 60, 7, (40, 38, 44))
    cv.rect(x + 48, y + 10, 18, 8, (40, 38, 44))
    cv.rect(x + w - 90, y + 12, 12, 6, (40, 38, 44))
    # flames
    for fx, fh in ((w // 2 - 26, 12), (w // 2 - 8, 16), (w // 2 + 10, 11)):
        cv.polyfill([(x + fx, y + 18), (x + fx + 6, y + 18 - fh),
                     (x + fx + 12, y + 18)], FIRE)
        cv.polyfill([(x + fx + 3, y + 18), (x + fx + 6, y + 18 - fh + 6),
                     (x + fx + 9, y + 18)], FIRE2)
    cv.disc(x + w // 2, y + 3, 5, SMOKE)
    # fire glow reflected in the water
    cv.rect(x + w // 2 - 14, y + h - 4, 28, 2, FIRE)


def draw_lead_summit(cv, x, y, w, h):
    cv.rect(x, y, w, h, NAVY2)
    # three flag panels, each 3 stripes: China, United States, Russia
    fw = (w - 40) // 3
    # China: red field, yellow stars
    fx = x + 16
    cv.rect(fx, y + 5, fw, 20, (196, 30, 40))
    cv.disc(fx + 8, y + 11, 2, (255, 222, 0))
    cv.disc(fx + 16, y + 9, 1, (255, 222, 0))
    cv.disc(fx + 16, y + 14, 1, (255, 222, 0))
    # United States: red/white stripes, blue canton
    fx = x + 16 + fw + 4
    for i in range(5):
        cv.rect(fx, y + 5 + i * 4, fw, 4,
                (178, 34, 52) if i % 2 == 0 else (240, 240, 240))
    cv.rect(fx, y + 5, fw // 2, 12, (40, 60, 140))
    # Russia: white, blue, red
    fx = x + 16 + 2 * (fw + 4)
    cv.rect(fx, y + 5, fw, 7, (240, 240, 240))
    cv.rect(fx, y + 12, fw, 7, (0, 60, 160))
    cv.rect(fx, y + 19, fw, 6, (200, 30, 40))


DRAW_LEAD = {"bridge": draw_lead_bridge, "tanker": draw_lead_tanker,
             "summit": draw_lead_summit}


def draw_leads(cv, x0, y0, w):
    cv.draw_text("TOP OF THE DAY", x0, y0, 1, RED)
    y = y0 + 14
    for kind, head, deck in LEADS:
        DRAW_LEAD[kind](cv, x0, y, w, 30)
        cv.draw_text(head, x0, y + 33, 2, INK)
        cv.draw_text(deck, x0, y + 50, 1, GREY)
        y += 58


def draw_section_header(cv, x, y, name):
    cv.draw_text(name, x, y, 2, NAVY2)
    cv.rect(x, y + 17, 488, 2, RED)


def draw_story(cv, x, y, head, deck):
    cv.rect(x, y + 2, 6, 6, RED)
    cv.draw_text(head, x + 11, y, 2, INK)
    cv.draw_text(deck, x + 11, y + 15, 1, GREY)
    return 22  # block height


def draw_grid(cv, y_top):
    # Column 1: EUROPE, MIDDLE EAST, AFRICA, MARKETS & TECH (22 stories)
    # Column 2: ASIA-PACIFIC, AMERICAS, SCIENCE & WORLD (18 stories)
    col1 = dict([SECTIONS[0], SECTIONS[1], SECTIONS[4], SECTIONS[5]])
    col2 = dict([SECTIONS[2], SECTIONS[3], SECTIONS[6]])
    for x0, sections in ((16, col1), (520, col2)):
        y = y_top
        for name, stories in sections.items():
            draw_section_header(cv, x0, y, name)
            y += 24
            for head, deck in stories:
                y += draw_story(cv, x0, y, head, deck)
            y += 8


def render():
    cv = Canvas(W, H, CREAM)
    draw_masthead(cv)
    draw_figures(cv)
    cv.hline(16, 156, W - 32, FAINT)
    cv.draw_text("WHERE THE DAY HAPPENED", 16, 164, 1, RED)
    draw_map(cv, 16, 180, 624, 168)
    draw_leads(cv, 656, 164, 352)
    cv.hline(16, 356, W - 32, FAINT)
    draw_grid(cv, 366)
    cv.hline(16, 1006, W - 32, FAINT)
    cv.text_centred("ALL STORIES REPORTED ON 17 NOVEMBER 2026",
                    W // 2, 1012, 1, GREY)
    return cv


# ------------------------------------------------------------- PNG out
def write_png(cv, path):
    def chunk(tag, data):
        c = tag + data
        return (struct.pack(">I", len(data)) + c +
                struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF))

    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * cv.w * 3:(y + 1) * cv.w * 3]
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    Path(path).write_bytes(png)
    return len(png)


def main():
    out = Path(__file__).resolve().parent / "entry.png"
    n = write_png(render(), out)
    print(f"wrote {out} ({n} bytes)")


if __name__ == "__main__":
    main()

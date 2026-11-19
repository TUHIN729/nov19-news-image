"""news-image-20261119: draw a one-page newspaper front page summing up
Thursday 19 November 2026, and write it to /output/entry.png.

Pure Python standard library only: no network, no fonts on disk, no
randomness and no timestamps, so two runs write byte-identical PNGs.
Text is rendered with a small built-in 5x7 bitmap font; pictures are
drawn with rectangles, circles, lines and triangles.
"""

import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 243, 234)
INK = (22, 28, 38)
NAVY = (20, 33, 61)
GOLD = (212, 175, 55)
WHITE = (255, 255, 255)
LIGHT = (238, 234, 224)
GREY = (90, 96, 110)

# ------------------------------------------------------------- 5x7 font
# Each glyph is 7 rows of 5 bits, "1" = filled pixel.
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
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "+": ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
}


def text_width(text, scale):
    return len(text) * (6 * scale) - scale


def wrap(text, max_chars):
    """Greedy word wrap; returns a list of lines, each <= max_chars."""
    lines = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for w in words:
            if not cur:
                cur = w
            elif len(cur) + 1 + len(w) <= max_chars:
                cur += " " + w
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    return lines


# ------------------------------------------------------------------ canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def fill_rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i] = c[0]
                self.px[i + 1] = c[1]
                self.px[i + 2] = c[2]

    def rect(self, x, y, w, h, c, t=1):
        self.fill_rect(x, y, w, t, c)
        self.fill_rect(x, y + h - t, w, t, c)
        self.fill_rect(x, y, t, h, c)
        self.fill_rect(x + w - t, y, t, h, c)

    def hline(self, x0, x1, y, c, t=1):
        self.fill_rect(x0, y, x1 - x0, t, c)

    def vline(self, x, y0, y1, c, t=1):
        self.fill_rect(x, y0, t, y1 - y0, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.fill_rect(x0 - t // 2, y0 - t // 2, t, t, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set(xx, yy, c)

    def ring(self, cx, cy, r, c, t=2):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d = (xx - cx) ** 2 + (yy - cy) ** 2
                if (r - t) ** 2 <= d <= r * r:
                    self.set(xx, yy, c)

    def triangle(self, x0, y0, x1, y1, x2, y2, c):
        # Fill by scanline: test pixel centres against barycentric signs.
        minx = max(0, min(x0, x1, x2))
        maxx = min(self.w - 1, max(x0, x1, x2))
        miny = max(0, min(y0, y1, y2))
        maxy = min(self.h - 1, max(y0, y1, y2))

        def sign(ax, ay, bx, by, cx, cy):
            return (ax - cx) * (by - cy) - (bx - cx) * (ay - cy)

        d = sign(x0, y0, x1, y1, x2, y2)
        if d == 0:
            return
        for yy in range(miny, maxy + 1):
            for xx in range(minx, maxx + 1):
                s1 = sign(xx, yy, x0, y0, x1, y1)
                s2 = sign(xx, yy, x1, y1, x2, y2)
                s3 = sign(xx, yy, x2, y2, x0, y0)
                neg = (s1 < 0) or (s2 < 0) or (s3 < 0)
                pos = (s1 > 0) or (s2 > 0) or (s3 > 0)
                if not (neg and pos):
                    self.set(xx, yy, c)

    def text(self, x, y, s, scale, c):
        cx = x
        for ch in s:
            g = FONT.get(ch, FONT[" "])
            for row in range(7):
                bits = g[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.fill_rect(
                            cx + col * scale, y + row * scale,
                            scale, scale, c)
            cx += 6 * scale
        return cx

    def text_center(self, y, s, scale, c, cx0=0, cx1=None):
        if cx1 is None:
            cx1 = self.w
        w = text_width(s, scale)
        self.text(cx0 + (cx1 - cx0 - w) // 2, y, s, scale, c)


# ------------------------------------------------------------------ icons
def icon_summit(cv, x, y, s):
    # Three leaders at a table: three heads above a long table.
    cv.fill_rect(x, y + 58, s, 10, (120, 72, 20))
    cv.fill_rect(x + 8, y + 68, 6, s - 68, (120, 72, 20))
    cv.fill_rect(x + s - 14, y + 68, 6, s - 68, (120, 72, 20))
    heads = [(x + 18, (180, 60, 50)), (x + s // 2, (20, 60, 120)),
             (x + s - 18, (200, 170, 40))]
    for hx, col in heads:
        cv.circle(hx, y + 26, 15, col)
        cv.fill_rect(hx - 16, y + 42, 32, 16, col)


def icon_gulf(cv, x, y, s):
    # Blast starburst over a sea line.
    cx, cy = x + s // 2, y + s // 2 - 8
    cv.circle(cx, cy, 12, (220, 60, 30))
    for dx, dy in ((0, -34), (24, -24), (34, 0), (24, 24),
                   (0, 34), (-24, 24), (-34, 0), (-24, -24)):
        cv.triangle(cx, cy, cx + dx, cy + dy,
                    cx + dx // 3 + 8, cy + dy // 3, (245, 140, 40))
    cv.circle(cx, cy, 12, (220, 60, 30))
    cv.fill_rect(x, y + s - 22, s, 6, (30, 90, 140))
    cv.fill_rect(x, y + s - 12, s, 4, (30, 90, 140))


def icon_gta(cv, x, y, s):
    # Vice City skyline under a pink sunset sun.
    cv.fill_rect(x, y, s, s, (58, 28, 84))
    cv.circle(x + s - 22, y + 22, 16, (255, 120, 140))
    heights = (34, 52, 44, 62, 40, 56, 48)
    bw = s // 7
    for i, hh in enumerate(heights):
        bx = x + i * bw
        cv.fill_rect(bx + 2, y + s - 18 - hh, bw - 4, hh + 18, (20, 16, 40))
        for wy in range(y + s - 16 - hh, y + s - 20, 9):
            cv.fill_rect(bx + 5, wy, 4, 4, (255, 210, 90))


def icon_chip(cv, x, y, s):
    # Green computer chip.
    cv.fill_rect(x, y, s, s, (16, 110, 60))
    for i in range(5):
        cv.fill_rect(x + 8 + i * 16, y - 0, 6, 8, (200, 200, 200))
        cv.fill_rect(x + 8 + i * 16, y + s - 8, 6, 8, (200, 200, 200))
    cv.fill_rect(x + 18, y + 18, s - 36, s - 36, (30, 160, 90))
    cv.fill_rect(x + 30, y + 30, s - 60, s - 60, (10, 70, 40))
    cv.text(x + 34, y + 38, "NV", 2, (140, 255, 180))


def icon_voyager(cv, x, y, s):
    # Deep space, gold dish probe, dotted path to a far star.
    cv.fill_rect(x, y, s, s, (10, 16, 44))
    for sx, sy in ((10, 14), (30, 40), (62, 10), (74, 52), (20, 66)):
        cv.circle(x + sx, y + sy, 2, WHITE)
    cv.circle(x + s - 14, y + 14, 5, GOLD)
    for i in range(6):
        cv.set(x + 14 + i * 9, y + s - 16 - i * 7, GOLD)
        cv.set(x + 15 + i * 9, y + s - 16 - i * 7, GOLD)
    cv.triangle(x + 26, y + 58, x + 52, y + 58, x + 39, y + 30, (212, 175, 55))
    cv.circle(x + 39, y + 30, 7, (212, 175, 55))
    cv.line(x + 39, y + 58, x + 39, y + 74, (200, 200, 200), 3)


def icon_eu(cv, x, y, s):
    # Blue field, ring of twelve gold stars.
    cv.fill_rect(x, y, s, s, (0, 51, 153))
    import math
    cx, cy = x + s // 2, y + s // 2
    for k in range(12):
        a = k * math.pi / 6
        cv.circle(int(cx + 30 * math.cos(a)), int(cy + 30 * math.sin(a)),
                  4, GOLD)
    cv.text(x + s // 2 - 6, y + s // 2 - 7, "E", 2, WHITE)


def icon_asia(cv, x, y, s):
    # India flag (top) and Japan flag (bottom) side by side.
    hw = s // 2 - 4
    cv.fill_rect(x, y + 6, hw, 12, (255, 153, 51))
    cv.fill_rect(x, y + 18, hw, 12, WHITE)
    cv.fill_rect(x, y + 30, hw, 12, (19, 136, 8))
    cv.circle(x + hw // 2, y + 24, 5, (0, 0, 128))
    cv.fill_rect(x + hw + 8, y + 6, hw, 36, WHITE)
    cv.rect(x + hw + 8, y + 6, hw, 36, INK, 1)
    cv.circle(x + hw + 8 + hw // 2, y + 24, 9, (188, 0, 45))
    cv.fill_rect(x, y + 52, s, 4, INK)
    cv.text(x + 6, y + 62, "2+2", 2, INK)


def icon_fed(cv, x, y, s):
    # Rising chart arrow.
    cv.fill_rect(x, y, s, s, (235, 240, 245))
    cv.vline(x + 10, y + 10, y + s - 14, INK, 3)
    cv.hline(x + 10, x + s - 8, y + s - 14, INK, 3)
    pts = [(x + 14, y + 62), (x + 32, y + 54), (x + 48, y + 58),
           (x + 64, y + 40), (x + 80, y + 24)]
    for a, b in zip(pts, pts[1:]):
        cv.line(a[0], a[1], b[0], b[1], (16, 130, 60), 4)
    cv.triangle(pts[-1][0], pts[-1][1], pts[-1][0] - 14, pts[-1][1] + 2,
                pts[-1][0] - 2, pts[-1][1] + 14, (16, 130, 60))
    cv.text(x + 12, y + 8, "%", 2, (16, 130, 60))


ICONS = {
    "summit": icon_summit, "gulf": icon_gulf, "gta": icon_gta,
    "chip": icon_chip, "voyager": icon_voyager, "eu": icon_eu,
    "asia": icon_asia, "fed": icon_fed,
}

# ---------------------------------------------------------------- stories
STORIES = [
    ("SUMMIT", (20, 60, 120), "summit",
     "TRUMP, XI AND PUTIN MEET IN SHENZHEN",
     "TRILATERAL TALKS OPEN AT THE APEC SUMMIT AS TRUMP LANDS IN CHINA."),
    ("MIDDLE EAST", (178, 34, 34), "gulf",
     "US AND IRAN EXCHANGE FIRE IN THE GULF",
     "US HITS A MISSILE SITE ON QESHM ISLAND. IRAN STRIKES A US BASE IN KUWAIT AND HITS BAHRAIN AGAIN."),
    ("GAMING", (128, 40, 140), "gta",
     "GTA VI ROLLS OUT AROUND THE WORLD",
     "GAMERS ENTER VICE CITY AS THE LONG-AWAITED GAME EARNS NEAR-PERFECT REVIEWS."),
    ("TECH", (16, 110, 60), "chip",
     "NVIDIA PROMISES EARLIER PAY RISES",
     "ACTING CEO COLETTE KRESS PLEDGES MORE STOCK GRANTS. H-SERIES CHIP SHIPMENTS TO CHINA STOP."),
    ("SPACE", (30, 40, 90), "voyager",
     "VOYAGER 1 REACHES ONE LIGHT-DAY",
     "THE NASA PROBE REACHES A MILESTONE ONE LIGHT-DAY AWAY FROM HOME."),
    ("EUROPE", (0, 51, 153), "eu",
     "EU PROPOSES 45BN UKRAINE LOAN",
     "THE LOAN IS REPAID AFTER RUSSIA PAYS REPARATIONS, THE PLAN SAYS."),
    ("ASIA", (150, 80, 10), "asia",
     "INDIA AND JAPAN HOLD 2+2 TALKS",
     "DEFENCE DIALOGUE IN TOKYO AS THE QUAD SETS UP A BUSINESS LEADERS FORUM."),
    ("MARKETS", (16, 130, 60), "fed",
     "FED MINUTES POINT TO MORE HIKES",
     "MOST OFFICIALS EXPECT FURTHER INTEREST-RATE RISES, THE MINUTES SHOW."),
]


def draw_card(cv, x, y, w, h, tag, color, icon, headline, body):
    cv.fill_rect(x, y, w, h, WHITE)
    cv.rect(x, y, w, h, INK, 2)
    cv.fill_rect(x, y, w, 32, color)
    cv.text(x + 12, y + 9, tag, 2, WHITE)
    ICONS[icon](cv, x + 14, y + 46, 88)
    tx = x + 116
    tw = w - 116 - 14
    max_chars = tw // 12  # scale-2 advance is 12 px
    hl = wrap(headline, max_chars)[:3]
    yy = y + 46
    for line in hl:
        cv.text(tx, yy, line, 2, INK)
        yy += 17
    yy += 6
    cv.hline(tx, tx + tw, yy, LIGHT, 2)
    yy += 8
    # Four body lines fit when the headline took only two; otherwise three.
    body_lines = 4 if len(hl) <= 2 else 3
    for line in wrap(body, max_chars)[:body_lines]:
        cv.text(tx, yy, line, 2, (52, 58, 70))
        yy += 17


def draw():
    cv = Canvas(W, H, PAPER)
    # Masthead.
    cv.fill_rect(0, 0, W, 148, NAVY)
    cv.text_center(22, "THE WORLD TODAY", 7, WHITE)
    cv.text_center(88, "THURSDAY, 19 NOVEMBER 2026", 4, GOLD)
    cv.hline(0, W, 148, GOLD, 4)
    cv.text_center(162, "EIGHT STORIES FROM AROUND THE WORLD", 2, INK)
    # Story grid: 2 columns x 4 rows.
    gx, gy = 24, 196
    cw, ch, gap = 482, 192, 12
    for i, (tag, color, icon, headline, body) in enumerate(STORIES):
        cx = gx + (i % 2) * (cw + gap)
        cy = gy + (i // 2) * (ch + gap)
        draw_card(cv, cx, cy, cw, ch, tag, color, icon, headline, body)
    return cv


# -------------------------------------------------------------------- PNG
def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(cv, path):
    raw = bytearray()
    for yy in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[yy * cv.w * 3:(yy + 1) * cv.w * 3]
    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    data += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(data)


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(outdir, exist_ok=True)
    write_png(draw(), os.path.join(outdir, "entry.png"))


if __name__ == "__main__":
    main()

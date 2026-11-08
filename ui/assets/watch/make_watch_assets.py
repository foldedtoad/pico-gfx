# Railroad-grade pocket-watch dial (Arabic numerals, outer red minute
# numerals, triangle markers, sunk small seconds) for a 240x240 GC9A01.
# Drawn at 4x and downsampled; dial pre-dithered to RGB565.
import math
from PIL import Image, ImageDraw, ImageFont

S, W = 4, 240
C = W * S / 2
FONT = "fonts/BodoniModa.ttf"                     # SIL OFL

WHITE_IN, WHITE_OUT = (252, 251, 247), (236, 233, 224)
INK = (22, 20, 20)
RED = (178, 52, 40)
STEEL = (18, 20, 30)                              # near-black blued steel
NICKEL_D, NICKEL_L = (112, 110, 102), (222, 220, 210)

def sc(v): return v * S
def iw(v): return max(1, int(round(v * S)))
def polar(cx, cy, r, deg):
    a = math.radians(deg - 90); return cx + r * math.cos(a), cy + r * math.sin(a)

def bodoni(size, weight=700, opsz=28):
    f = ImageFont.truetype(FONT, int(sc(size)))
    f.set_variation_by_axes([weight, opsz])
    return f

def radial(img, cx, cy, r, cin, cout):
    d = ImageDraw.Draw(img)
    for i in range(140, 0, -1):
        t = i / 140
        col = tuple(int(cin[k] + (cout[k] - cin[k]) * t ** 2.2) for k in range(3))
        d.ellipse([cx - r * t, cy - r * t, cx + r * t, cy + r * t], fill=col)

def bezel(img, r_out):
    d = ImageDraw.Draw(img)
    for a in range(360):
        t = 0.5 + 0.5 * math.cos(math.radians(a - 135))
        col = tuple(int(NICKEL_D[k] + (NICKEL_L[k] - NICKEL_D[k]) * t) for k in range(3))
        d.pieslice([C - r_out, C - r_out, C + r_out, C + r_out], a - 0.6, a + 0.6, fill=col)

def text_radial(img, txt, font, r, deg, fill, cx=C, cy=C):
    tw = int(font.getlength(txt)) + sc(4); th = int(sc(14))
    layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((tw / 2, th / 2), txt, font=font, fill=fill + (255,), anchor="mm")
    rot = layer.rotate(-deg, resample=Image.BICUBIC, expand=True)
    x, y = polar(cx, cy, r, deg)
    img.paste(rot, (int(x - rot.width / 2), int(y - rot.height / 2)), rot)

def triangle(d, r_tip, deg, size, fill, cx=C, cy=C):
    tip = polar(cx, cy, r_tip, deg)
    base_c = polar(cx, cy, r_tip + size, deg)
    a = math.radians(deg)
    dx, dy = math.cos(a) * size * 0.6, math.sin(a) * size * 0.6
    d.polygon([tip, (base_c[0] - dx, base_c[1] - dy), (base_c[0] + dx, base_c[1] + dy)], fill=fill)

def make_dial():
    img = Image.new("RGB", (W * S, W * S), (0, 0, 0))
    bezel(img, sc(120))
    d = ImageDraw.Draw(img)
    d.ellipse([C - sc(113.5), C - sc(113.5), C + sc(113.5), C + sc(113.5)], fill=(90, 88, 80))
    radial(img, C, C, sc(112.5), WHITE_IN, WHITE_OUT)
    d = ImageDraw.Draw(img)

    # outer red minute numerals 5..60, radial
    red_f = bodoni(7.2, weight=500, opsz=10)
    for m in range(5, 61, 5):
        text_radial(img, str(m), red_f, sc(106.5), (m % 60) * 6, RED)
    # triangles at five-minute positions, pointing inward
    for m in range(0, 60, 5):
        triangle(d, sc(98.5), m * 6, sc(3.2), INK)
    # minute dashes
    for m in range(60):
        if m % 5:
            deg = m * 6
            d.line([polar(C, C, sc(94.5), deg), polar(C, C, sc(100.5), deg)], fill=INK, width=iw(1.5))

    # faint sunk-centre line
    r = sc(54)
    d.ellipse([C - r, C - r, C + r, C + r], outline=(190, 180, 168), width=iw(0.5))

    # upright Arabic hour numerals (6 hidden by the seconds dial)
    num_f = bodoni(25, weight=900, opsz=12)    # low opsz = sturdier hairlines
    num12 = bodoni(27, weight=900, opsz=12)
    for h in range(1, 13):
        if h == 6:
            continue
        x, y = polar(C, C, sc(77 if h != 12 else 76), h * 30)
        f = num12 if h == 12 else num_f
        d.text((x, y), str(h), font=f, fill=INK, anchor="mm")

    # maker's name
    script = ImageFont.truetype("fonts/BodoniModa-Italic.ttf", int(sc(11.5)))
    script.set_variation_by_axes([600, 14])
    yname = C - sc(31)
    name = "FoldedToad"
    d.text((C, yname), name, font=script, fill=INK, anchor="mm")

    # sunk small seconds
    scx, scy, sr = C, C + sc(48), sc(29)
    d.ellipse([scx - sr - sc(1), scy - sr - sc(1), scx + sr + sc(1), scy + sr + sc(1)], fill=(205, 200, 190))
    radial(img, scx, scy, sr, (246, 244, 238), (232, 229, 220))
    d = ImageDraw.Draw(img)
    for s in range(60):
        deg = s * 6
        if s % 10 == 0:
            d.line([polar(scx, scy, sr - sc(5.5), deg), polar(scx, scy, sr - sc(1.2), deg)], fill=INK, width=iw(1.3))
        elif s % 5 == 0:
            d.line([polar(scx, scy, sr - sc(4), deg), polar(scx, scy, sr - sc(1.2), deg)], fill=INK, width=iw(0.9))
        else:
            d.line([polar(scx, scy, sr - sc(2.8), deg), polar(scx, scy, sr - sc(1.2), deg)], fill=INK, width=iw(0.6))
    sec_f = bodoni(6.4, weight=500, opsz=8)
    for s in range(10, 61, 10):
        x, y = polar(scx, scy, sr - sc(11), (s % 60) * 6)
        d.text((x, y), str(s), font=sec_f, fill=INK, anchor="mm")

    return img.resize((W, W), Image.LANCZOS)

# ---------------------------------------------------------------- hands
def spade_hand(length, tail, shaft_w, pear_at, pear_r, hub_r):
    pad = 4
    w = int(2 * max(pear_r, hub_r) + 2 * pad)
    w += w % 2                      # even width -> pivot exactly on the axis
    h = int(length + tail + 2 * pad)
    img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    px, py = w * S / 2, (pad + length) * S
    col = STEEL + (255,)
    # shaft from tail to pear
    d.polygon([(px - sc(shaft_w) / 2, py + sc(tail)), (px + sc(shaft_w) / 2, py + sc(tail)),
               (px + sc(shaft_w) * 0.35, py - sc(pear_at)), (px - sc(shaft_w) * 0.35, py - sc(pear_at))], fill=col)
    # pear: teardrop pointing to tip
    cy = py - sc(pear_at)
    r = sc(pear_r)
    d.ellipse([px - r, cy - r * 1.25, px + r, cy + r * 0.9], fill=col)
    d.polygon([(px - r * 0.92, cy - r * 0.45), (px + r * 0.92, cy - r * 0.45), (px, cy - r * 2.6)], fill=col)
    # fine needle tip beyond pear
    d.polygon([(px - sc(0.7), cy - r * 2.2), (px + sc(0.7), cy - r * 2.2), (px, py - sc(length))], fill=col)
    # hub
    d.ellipse([px - sc(hub_r), py - sc(hub_r), px + sc(hub_r), py + sc(hub_r)], fill=col)
    return img.resize((w, h), Image.LANCZOS), w / 2, pad + length

def seconds_hand(length, tail):
    pad = 3
    w, h = 2 * pad + 6, int(length + tail + 2 * pad)
    img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    px, py = w * S / 2, (pad + length) * S
    col = STEEL + (255,)
    d.polygon([(px - sc(0.6), py), (px + sc(0.6), py), (px, py - sc(length))], fill=col)
    d.line([(px, py), (px, py + sc(tail))], fill=col, width=iw(1.1))
    for rr, yy in ((sc(2.2), py), (sc(2.0), py + sc(tail))):
        d.ellipse([px - rr, yy - rr, px + rr, yy + rr], fill=col)
    return img.resize((w, h), Image.LANCZOS), w / 2, pad + length

# ---------------------------------------------------------------- RGB565 dither
B = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
def dither565(im):
    im = im.convert("RGB"); px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            t = (B[y & 3][x & 3] + 0.5) / 16 - 0.5
            def q(v, bits):
                st = 255 / ((1 << bits) - 1)
                return int(round(min(255, max(0, v + t * st)) / st) * st)
            r, g, b = px[x, y]; px[x, y] = (q(r, 5), q(g, 6), q(b, 5))
    return im

# Colour correction for the panel. Cheap GC9A01 IPS modules have a cool (bluish)
# white point, so near-white enamel looks blue. Scale R, G, B before dithering
# to warm it back up. (1, 1, 1) = no correction.
PANEL_TINT = (1.00, 0.93, 0.78)

def tint(im, k):
    r, g, b = im.split()
    return Image.merge("RGB", [ch.point(lambda v, f=f: min(255, int(v * f + 0.5)))
                               for ch, f in zip((r, g, b), k)])

dial = dither565(tint(make_dial(), PANEL_TINT))
hour, hpx, hpy = spade_hand(length=54, tail=9, shaft_w=2.8, pear_at=36, pear_r=4.6, hub_r=5.5)
minute, mpx, mpy = spade_hand(length=98, tail=11, shaft_w=2.0, pear_at=80, pear_r=3.6, hub_r=4.5)
second, spx, spy = seconds_hand(length=25, tail=6)
SUB = (120, 168)

dial.save("dial_face.png")
import sys; hour.save("hand_hour.png")
minute.save("hand_minute.png"); second.save("hand_second.png")

def place(base, hand, px, py, cx, cy, deg):
    w, h = hand.size
    side = int(2 * max(px, w - px, py, h - py)) + 2
    c = Image.new("RGBA", (side, side), (0, 0, 0, 0)); c.paste(hand, (int(side / 2 - px), int(side / 2 - py)))
    r = c.rotate(-deg, resample=Image.BICUBIC); base.paste(r, (int(cx - side / 2), int(cy - side / 2)), r)

def preview(hh, mm, ss, name):
    base = dial.convert("RGBA")
    place(base, second, spx, spy, *SUB, ss * 6)
    place(base, hour, hpx, hpy, 120, 120, (hh % 12 + mm / 60) * 30)
    place(base, minute, mpx, mpy, 120, 120, (mm + ss / 60) * 6)
    d = ImageDraw.Draw(base)
    d.ellipse([118, 118, 122, 122], fill=(70, 70, 80, 255))
    m = Image.new("L", (W, W), 0); ImageDraw.Draw(m).ellipse([0, 0, W - 1, W - 1], fill=255)
    out = Image.new("RGB", (W, W), (20, 20, 20)); out.paste(base, (0, 0), m)
    out.resize((480, 480), Image.NEAREST).save(name)

preview(10, 9, 36, "preview_2x.png")
print("hour", hour.size, (hpx, hpy), "minute", minute.size, (mpx, mpy), "second", second.size, (spx, spy), "subdial", SUB)

# EEZ placement table: pivot must land on the dial centre / sub-seconds centre
print()
print("%-11s %-16s %-8s %-9s %s" % ("widget", "bitmap", "W x H", "pivot", "X, Y"))
print("%-11s %-16s %-8s %-9s %s" % ("img_dial", "dial_face.png", "240x240", "-", "0, 0"))
for name, f, img, px, py, (cx, cy) in (
        ("img_second", "hand_second.png", second, spx, spy, SUB),
        ("img_hour", "hand_hour.png", hour, hpx, hpy, (120, 120)),
        ("img_minute", "hand_minute.png", minute, mpx, mpy, (120, 120))):
    assert px == int(px) and py == int(py), "pivot must be whole pixels"
    print("%-11s %-16s %-8s %-9s %d, %d" % (name, f, "%dx%d" % img.size,
          "%d, %d" % (px, py), cx - px, cy - py))

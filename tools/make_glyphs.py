#!/usr/bin/env python3
"""Build the FFNx replacement pages of the FF8 menu icon texture with Steam Deck glyphs, for every language.

FFNx loads menu/hires/iconfl01_04 and iconfl03_04 for the sprites the game draws from those pages with
palette 4 (CLUT row 260 in icon.sp1). Only those sprites are drawn; the rest of each page stays
transparent because it is never sampled with palette 4.

Cell positions come from icon.sp1: a sprite at VRAM (u, v) lies on hires page
iconfl0<(u >= 128) + 2 * (v >= 128)> at ((u % 128) * 8, (v % 128) * 8) in the 1024 atlas.
FFNx (steam_stock_launcher) shows these PS icons for the DirectInput buttons below,
which on a Deck are: Cross = A, Circle = B, Square = X, Triangle = Y, L1, R1, L2, R2,
Select = View, Start = Menu.

Without the hires pages (Japanese data, or the low-res font option) the game draws the same sprites
from the single low-res page menu/icon (256 x 256 VRAM), so icon_04 is the four hires pages side by
side at the same 8 px per VRAM pixel. icon.sp1 is identical in all languages for these sprites.
Each language has its own folder: data/<eng|fre|ger|ita|spa|jp>/menu.

Output is uncompressed DDS (B8G8R8A8, one mip): FFNx tries mod_ext "dds" before "png", so only a DDS
can compete with other texture mods (e.g. AxlRose's UI) - then J8's load order decides.

Usage: make_glyphs.py <Textures folder>   (writes data/<lang>/menu/hires/iconfl0[13]_04.dds, icon_04.dds)
"""
import os, struct, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = ['/usr/share/fonts/TTF/DejaVuSans-Bold.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']
FONT = next((f for f in FONTS if os.path.exists(f)), FONTS[0])
SS = 4  # supersampling
MAX_H = 80  # button glyphs taller than this overlap the next text row
BUTTONS = ('face', 'bumper', 'trigger', 'wide')
LANGS = ('eng', 'fre', 'ger', 'ita', 'spa', 'jp')
HIRES_LANGS = ('eng', 'fre', 'ger', 'ita', 'spa')  # the Japanese data has no hires icon pages

BODY_TOP, BODY_BOTTOM = (74, 77, 84), (30, 31, 35)
RIM = (150, 154, 162)
LEGEND = (255, 255, 255)

# (page, x, y, w, h, kind, label) in 1024-atlas pixels
CELLS = [
    # page 01, v 112: sp1 ids 139 START, 133 Circle, 134 Cross, 135 Square, 132 Triangle
    (1, 256, 896, 256, 128, 'wide', 'menu'),
    (1, 512, 896, 128, 128, 'face', 'B'),
    (1, 640, 896, 128, 128, 'face', 'A'),
    (1, 768, 896, 128, 128, 'face', 'X'),
    (1, 896, 896, 128, 128, 'face', 'Y'),
    # page 03, v 128: ids 136 SELECT, 131 R1, 129 R2, 130 L1, 128 L2
    (3, 256, 0, 256, 128, 'wide', 'view'),
    (3, 512, 0, 128, 128, 'bumper', 'R1'),
    (3, 640, 0, 128, 128, 'trigger', 'R2'),
    (3, 768, 0, 128, 128, 'bumper', 'L1'),
    (3, 896, 0, 128, 128, 'trigger', 'L2'),
    # page 03, v 240..255: small fixed set, ids 245 Circle, 246 Cross, 247 Square, 244 Triangle,
    # 243 R1, 241 R2, 242 L1, 240 L2
    (3, 640, 896, 64, 64, 'face', 'B'),
    (3, 704, 896, 64, 64, 'face', 'A'),
    (3, 640, 960, 64, 64, 'face', 'X'),
    (3, 704, 960, 64, 64, 'face', 'Y'),
    (3, 768, 896, 128, 64, 'bumper', 'R1'),
    (3, 896, 896, 128, 64, 'trigger', 'R2'),
    (3, 768, 960, 128, 64, 'bumper', 'L1'),
    (3, 896, 960, 128, 64, 'trigger', 'L2'),
    # other palette-4 sprites on these pages
    (1, 256, 512, 64, 128, 'arrow', ''),        # id 6: menu pointer arrow (u160 v64, 8x16)
    (1, 768, 768, 128, 128, 'letter', 'A'),     # id 178 (u224 v96)
    (3, 0, 0, 128, 128, 'face', 'L'),           # id 137 (u128 v128)
    (2, 896, 0, 128, 128, 'face', 'R'),         # id 138 (u112 v128); iconfl02 is not replaced, low-res page only
    (3, 256, 896, 128, 128, 'star', ''),        # id 175 (u160 v240)
    # ids 140..143: D-pad with one arm lit, built from 8x8 arm tiles (u176..207 v80..95)
    (1, 384, 640, 64, 64, 'dpad', 'up+'),
    (1, 512, 640, 64, 64, 'dpad', 'up'),
    (1, 448, 640, 64, 64, 'dpad', 'right+'),
    (1, 576, 640, 64, 64, 'dpad', 'right'),
    (1, 384, 704, 64, 64, 'dpad', 'left+'),
    (1, 512, 704, 64, 64, 'dpad', 'left'),
    (1, 448, 704, 64, 64, 'dpad', 'down+'),
    (1, 576, 704, 64, 64, 'dpad', 'down'),
]


def downsample(img, w, h):
    """Scale down and make alpha binary: the engine draws these sprites without blending."""
    small = img.convert('RGBa').resize((w, h), Image.LANCZOS).convert('RGBA')
    mask = small.getchannel('A').point(lambda a: 255 if a >= 128 else 0)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    out.paste(small.convert('RGB'), (0, 0), mask)
    return out


def gradient_fill(size, mask, top, bottom):
    w, h = size
    grad = Image.new('RGBA', (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        grad.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)) + (255,))
    layer = Image.new('RGBA', size, (0, 0, 0, 0))
    layer.paste(grad.resize(size), (0, 0), mask)
    return layer


def text_center(draw, box, text, size):
    font = ImageFont.truetype(FONT, size)
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    x0, y0, x1, y1 = box
    draw.text(((x0 + x1 - (r - l)) / 2 - l, (y0 + y1 - (b - t)) / 2 - t), text, font=font, fill=LEGEND)


def shape_mask(size, kind, box):
    m = Image.new('L', size, 0)
    d = ImageDraw.Draw(m)
    x0, y0, x1, y1 = box
    if kind == 'face':
        d.ellipse(box, fill=255)
    elif kind == 'bumper':  # rounded bar
        d.rounded_rectangle(box, radius=(y1 - y0) * 0.38, fill=255)
    elif kind == 'trigger':  # taller, strongly rounded top
        d.rounded_rectangle(box, radius=(x1 - x0) * 0.22, fill=255)
        d.pieslice((x0, y0, x1, y0 + (x1 - x0) * 0.9), 180, 360, fill=255)
    elif kind == 'pill':
        d.rounded_rectangle(box, radius=(y1 - y0) / 2, fill=255)
    return m


def draw_button(size, kind, box, rim_px):
    layer = Image.new('RGBA', size, (0, 0, 0, 0))
    x0, y0, x1, y1 = box
    outer = shape_mask(size, kind, box)
    layer.alpha_composite(gradient_fill(size, outer, RIM, (70, 72, 78)))
    inner = shape_mask(size, kind, (x0 + rim_px, y0 + rim_px, x1 - rim_px, y1 - rim_px))
    layer.alpha_composite(gradient_fill(size, inner, BODY_TOP, BODY_BOTTOM))
    return layer


def view_symbol(draw, cx, cy, s, width):
    a = s * 0.62
    draw.rectangle((cx - s / 2, cy - s / 2, cx - s / 2 + a, cy - s / 2 + a), outline=LEGEND, width=width)
    draw.rectangle((cx + s / 2 - a, cy + s / 2 - a, cx + s / 2, cy + s / 2), fill=LEGEND)


def menu_symbol(draw, cx, cy, s, width):
    for k in (-1, 0, 1):
        y = cy + k * s * 0.36
        draw.rounded_rectangle((cx - s / 2, y - width / 2, cx + s / 2, y + width / 2), radius=width / 2, fill=LEGEND)


def glyph(w, h, kind, label):
    if kind == 'dpad':
        return dpad_tile(w, h, label)
    if kind == 'arrow':
        return arrow(w, h)
    if kind == 'star':
        return star(w, h)
    if kind == 'letter':
        return letter(w, h, label)
    W, H = w * SS, h * SS
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    unit = min(W, H)
    rim = max(round(unit * 0.045), SS * 2)
    if kind == 'face':
        box = (0, 0, W - 1, H - 1)
        img.alpha_composite(draw_button((W, H), kind, box, rim))
        text_center(ImageDraw.Draw(img), box, label, round((box[3] - box[1]) * 0.62))
    elif kind in ('bumper', 'trigger'):
        if kind == 'bumper':
            box = (0, 0, W - 1, round(H * 0.82))
        else:
            box = (0, 0, round(W * 0.8), H - 1)
        img.alpha_composite(draw_button((W, H), kind, box, rim))
        tb = (box[0], box[1] + (box[3] - box[1]) * (0.12 if kind == 'trigger' else 0), box[2], box[3])
        text_center(ImageDraw.Draw(img), tb, label, round(min((box[3] - box[1]) * 0.62, (box[2] - box[0]) * 0.42)))
    elif kind == 'wide':  # View / Menu
        box = (0, 0, W - 1, H - 1)
        img.alpha_composite(draw_button((W, H), 'pill', box, rim))
        d = box[3] - box[1]
        cx, cy, s = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2, d * 0.5
        (view_symbol if label == 'view' else menu_symbol)(ImageDraw.Draw(img), cx, cy, s, max(round(d * 0.08), SS))
    return downsample(img, w, h)


OUTLINE = (20, 20, 24, 255)


def styled(size, mask, rim, top, bottom, outline_px, rim_px):
    """Dark outline around mask, a rim in colour rim, then the body as a top-to-bottom gradient."""
    grow = mask.filter(ImageFilter.MaxFilter(2 * outline_px + 1))
    body = mask.filter(ImageFilter.MinFilter(2 * rim_px + 1))
    layer = Image.new('RGBA', size, (0, 0, 0, 0))
    layer.paste(Image.new('RGBA', size, OUTLINE), (0, 0), grow)
    layer.alpha_composite(gradient_fill(size, mask, rim, tuple(c * 3 // 5 for c in rim)))
    layer.alpha_composite(gradient_fill(size, body, top, bottom))
    return layer


def poly_mask(size, points):
    m = Image.new('L', size, 0)
    ImageDraw.Draw(m).polygon(points, fill=255)
    return m


def dpad_tile(w, h, label):
    """One D-pad arm in its 8x8 tile (layout as in vanilla): the flat end points outward, the tip to
    the centre. Up/down arms fill x 1..7, y 0..6 (down: y 0..6 too, tip at the top); left/right fill
    x 0..6, y 1..7. A '+' label is the lit arm (pressed direction)."""
    W, H = w * SS, h * SS
    u = W / 8  # one VRAM pixel
    lit = label.endswith('+')
    d = label.rstrip('+')
    o = 0.7 * u
    if d in ('up', 'down'):
        x0, x1, y0, y1 = 1 * u + o, 7 * u - o, 0 + o, 6 * u - o
        if d == 'up':
            pts = [(x0, y0), (x1, y0), (x1, y1 - 2.4 * u), ((x0 + x1) / 2, y1), (x0, y1 - 2.4 * u)]
        else:
            pts = [(x0, y1), (x1, y1), (x1, y0 + 2.4 * u), ((x0 + x1) / 2, y0), (x0, y0 + 2.4 * u)]
    else:
        x0, x1, y0, y1 = 0 + o, 6 * u - o, 1 * u + o, 7 * u - o
        if d == 'left':
            pts = [(x0, y0), (x0, y1), (x1 - 2.4 * u, y1), (x1, (y0 + y1) / 2), (x1 - 2.4 * u, y0)]
        else:
            pts = [(x1, y0), (x1, y1), (x0 + 2.4 * u, y1), (x0, (y0 + y1) / 2), (x0 + 2.4 * u, y0)]
    mask = poly_mask((W, H), pts)
    if lit:
        img = styled((W, H), mask, (255, 255, 255), (250, 250, 252), (196, 200, 208), round(o), round(0.35 * u))
    else:
        img = styled((W, H), mask, RIM, BODY_TOP, BODY_BOTTOM, round(o), round(0.35 * u))
    return downsample(img, w, h)


def arrow(w, h):
    """Menu pointer: red triangle pointing right, in the top-left 5.5 x 10 VRAM px of its 8x16 cell."""
    W, H = w * SS, h * SS
    u = W / 8
    o = 0.6 * u
    mask = poly_mask((W, H), [(o, o), (5.5 * u - o, 5 * u), (o, 10 * u - o)])
    img = styled((W, H), mask, (255, 150, 140), (236, 52, 40), (150, 16, 12), round(o), round(0.4 * u))
    return downsample(img, w, h)


def star(w, h):
    import math
    W, H = w * SS, h * SS
    cx, cy, r_out = W / 2, H / 2 + H * 0.03, W * 0.44
    r_in = r_out * 0.45
    pts = [(cx + (r_out if k % 2 == 0 else r_in) * math.sin(k * math.pi / 5),
            cy - (r_out if k % 2 == 0 else r_in) * math.cos(k * math.pi / 5)) for k in range(10)]
    o = round(W * 0.045)
    img = styled((W, H), poly_mask((W, H), pts), (170, 245, 180), (96, 220, 120), (24, 130, 56), o, round(W * 0.03))
    return downsample(img, w, h)


def letter(w, h, text):
    W, H = w * SS, h * SS
    font = ImageFont.truetype(FONT, round(H * 0.82))
    mask = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(mask)
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    d.text(((W - (r - l)) / 2 - l, (H - (b - t)) / 2 - t), text, font=font, fill=255)
    img = styled((W, H), mask, (150, 154, 162), (255, 255, 255), (205, 208, 214), round(W * 0.035), round(W * 0.03))
    return downsample(img, w, h)


def dds(im):
    """Legacy DDS header, 32-bit A8R8G8B8 (BGRA in memory), no mipmaps."""
    w, h = im.size
    pf = struct.pack('<II4sIIIII', 32, 0x41, b'\0\0\0\0', 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    head = struct.pack('<4sIIIIIII', b'DDS ', 124, 0x100F, h, w, w * 4, 0, 1) + b'\0' * 44 + pf
    head += struct.pack('<IIIII', 0x1000, 0, 0, 0, 0)
    assert len(head) == 128
    r, g, b, a = im.convert('RGBA').split()
    return head + Image.merge('RGBA', (b, g, r, a)).tobytes()


def page_atlas(page):
    atlas = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
    for p, x, y, w, h, kind, label in CELLS:
        if p != page:
            continue
        atlas.paste((0, 0, 0, 0), (x, y, x + w, y + h))
        if kind in BUTTONS and h > MAX_H:
            w, h = round(w * MAX_H / h), MAX_H
        atlas.alpha_composite(glyph(w, h, kind, label), (x, y))
    return atlas


def build(out):
    pages = {page: page_atlas(page) for page in (1, 2, 3)}
    lowres = Image.new('RGBA', (2048, 2048), (0, 0, 0, 0))
    for page, atlas in pages.items():
        lowres.alpha_composite(atlas, ((page & 1) * 1024, (page >> 1) * 1024))
    files = {f'hires/iconfl{page:02d}_04.dds': dds(pages[page]) for page in (1, 3)}
    files['icon_04.dds'] = dds(lowres)
    for lang in LANGS:
        for name, data in files.items():
            if name.startswith('hires/') and lang not in HIRES_LANGS:
                continue
            path = os.path.join(out, 'data', lang, 'menu', name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as f:
                f.write(data)
            print(path)


if __name__ == '__main__':
    build(sys.argv[1])

"""
textures.py
===========
All textures are generated procedurally with Pillow (no external assets),
converted to float32 NumPy arrays in the range [0, 1] and cached.

Nearest-neighbour and bilinear samplers live here as well; the bilinear one is
Part-B extension #2.
"""

import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


# ------------------------------------------------------------- generators ----
def _grass(size=128, seed=12):
    rng = random.Random(seed)
    img = Image.new("RGB", (size, size), (44, 118, 54))
    d = ImageDraw.Draw(img)
    for _ in range(int(size * 7)):
        x, y = rng.randrange(size), rng.randrange(size)
        tone = rng.choice([(32, 92, 42), (56, 136, 62), (72, 152, 76), (25, 78, 36)])
        d.line((x, y, x + rng.randint(-2, 2), y - rng.randint(3, 7)), fill=tone)
    # broad soft patches
    for _ in range(18):
        x, y = rng.randrange(size), rng.randrange(size)
        r = rng.randint(6, 16)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(40, 108, 50))
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    return img


def _stone(size=128, seed=7):
    rng = random.Random(seed)
    img = Image.new("RGB", (size, size), (150, 154, 158))
    d = ImageDraw.Draw(img)
    bh = size // 4
    bw = size // 2
    for row in range(4):
        offset = (row % 2) * (bw // 2)
        for col in range(-1, 3):
            x0 = col * bw + offset
            y0 = row * bh
            shade = rng.randint(-22, 22)
            base = (152 + shade, 156 + shade, 160 + shade)
            d.rectangle((x0 + 2, y0 + 2, x0 + bw - 2, y0 + bh - 2), fill=base)
            d.line((x0 + 2, y0 + 2, x0 + bw - 2, y0 + 2), fill=(196, 200, 204))
            d.line((x0 + 2, y0 + bh - 2, x0 + bw - 2, y0 + bh - 2), fill=(98, 102, 106))
    for _ in range(int(size * 3)):
        x, y = rng.randrange(size), rng.randrange(size)
        c = rng.randint(120, 185)
        d.point((x, y), fill=(c, c + 2, c + 4))
    return img


def _water(size=128, seed=3):
    img = Image.new("RGB", (size, size), (18, 92, 156))
    px = img.load()
    for y in range(size):
        for x in range(size):
            w = (np.sin((x / size) * 2 * np.pi * 3 + (y / size) * 2 * np.pi * 2) + 1) * 0.5
            h = (np.sin((y / size) * 2 * np.pi * 5) + 1) * 0.5
            r = int(10 + 30 * w)
            g = int(70 + 70 * h)
            b = int(140 + 90 * w)
            px[x, y] = (r, g, b)
    d = ImageDraw.Draw(img)
    for _ in range(6):
        y = random.randrange(size)
        d.arc((0, y, size, y + 18), 180, 360, fill=(160, 225, 255))
    return img


def _checker(size=64):
    img = Image.new("RGB", (size, size), (245, 245, 245))
    d = ImageDraw.Draw(img)
    cell = size // 8
    for r in range(8):
        for c in range(8):
            if (r + c) % 2:
                d.rectangle((c * cell, r * cell, (c + 1) * cell - 1, (r + 1) * cell - 1),
                            fill=(18, 18, 18))
    return img


def _radial(size=64, base=(210, 40, 45), light=(255, 140, 130)):
    """Radial gradient used for apples and worm segments."""
    img = Image.new("RGB", (size, size), base)
    px = img.load()
    cx, cy = size * 0.38, size * 0.34
    for y in range(size):
        for x in range(size):
            d = np.hypot((x - cx) / size, (y - cy) / size)
            f = max(0.0, 1.0 - d * 2.2)
            px[x, y] = tuple(int(base[i] * (1 - f) + light[i] * f) for i in range(3))
    return img


def _feather(size=64, base=(118, 104, 148)):
    rng = random.Random(5)
    img = Image.new("RGB", (size, size), base)
    d = ImageDraw.Draw(img)
    for _ in range(220):
        x, y = rng.randrange(size), rng.randrange(size)
        v = rng.randint(-18, 18)
        d.line((x, y, x + 2, y + rng.randint(-6, 6)),
               fill=(base[0] + v, base[1] + v, base[2] + v))
    return img


def _wood(size=64):
    img = Image.new("RGB", (size, size), (120, 84, 48))
    d = ImageDraw.Draw(img)
    for x in range(0, size, 4):
        d.line((x, 0, x, size), fill=(96, 64, 36))
    for _ in range(30):
        y = random.randrange(size)
        d.line((0, y, size, y), fill=(134, 96, 56))
    return img


# ------------------------------------------------------------------ cache ----
_CACHE = {}


def _to_array(img):
    arr = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    return arr


def get(name):
    """
    Return a cached float32 texture array (H, W, 3).

    name in {"grass", "stone", "water", "checker", "apple", "gold",
             "worm", "feather", "wood"}
    """
    if name in _CACHE:
        return _CACHE[name]

    if name == "grass":
        arr = _to_array(_grass())
    elif name == "stone":
        arr = _to_array(_stone())
    elif name == "water":
        arr = _to_array(_water())
    elif name == "checker":
        arr = _to_array(_checker())
    elif name == "apple":
        arr = _to_array(_radial(base=(190, 32, 40), light=(255, 150, 140)))
    elif name == "gold":
        arr = _to_array(_radial(base=(214, 150, 18), light=(255, 240, 130)))
    elif name == "worm":
        arr = _to_array(_radial(base=(216, 92, 48), light=(255, 196, 130)))
    elif name == "feather":
        arr = _to_array(_feather())
    elif name == "wood":
        arr = _to_array(_wood())
    else:
        raise KeyError(name)

    _CACHE[name] = arr
    return arr


def save_all_assets():
    """Write every generated texture to assets/ so the submission includes them."""
    os.makedirs(ASSET_DIR, exist_ok=True)
    for name in ["grass", "stone", "water", "checker", "apple", "gold",
                 "worm", "feather", "wood"]:
        arr = get(name)
        Image.fromarray((arr * 255).astype(np.uint8)).save(
            os.path.join(ASSET_DIR, f"{name}.png"))


# ---------------------------------------------------------------- samplers ---
def sample_nearest(tex, u, v):
    """u, v may be any non-negative value; the texture repeats."""
    h, w, _ = tex.shape
    tx = np.nan_to_num(u, nan=0.0, posinf=0.0, neginf=0.0)
    ty = np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0)
    tx = (tx * w)
    ty = (ty * h)
    tx = np.clip(tx, 0.0, 4096.0).astype(np.int32) % w
    ty = np.clip(ty, 0.0, 4096.0).astype(np.int32) % h
    return tex[ty, tx]


def sample_bilinear(tex, u, v):
    """
    Bilinear filtering (Part-B extension): fetch 4 neighbouring texels and
    blend them with the fractional coordinates.
    """
    h, w, _ = tex.shape
    u = np.nan_to_num(u, nan=0.0, posinf=0.0, neginf=0.0)
    v = np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0)
    fx = np.clip(u * w - 0.5, -1e6, 1e6)
    fy = np.clip(v * h - 0.5, -1e6, 1e6)
    x0 = np.floor(fx).astype(np.int32)
    y0 = np.floor(fy).astype(np.int32)
    ax = (fx - x0)[..., None]
    ay = (fy - y0)[..., None]

    x0m = x0 % w
    x1m = (x0 + 1) % w
    y0m = y0 % h
    y1m = (y0 + 1) % h

    c00 = tex[y0m, x0m]
    c10 = tex[y0m, x1m]
    c01 = tex[y1m, x0m]
    c11 = tex[y1m, x1m]
    top = c00 * (1 - ax) + c10 * ax
    bottom = c01 * (1 - ax) + c11 * ax
    return top * (1 - ay) + bottom * ay

"""Headless scene preview (no window) for quick visual checks."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

import config as C
from camera import Camera, PRESET_ELEVATED, PRESET_FOLLOW
from game import Game
from raster import Renderer
from scene import draw_scene


def shot(name, preset=PRESET_ELEVATED, perspective=True, size=(896, 560),
         bilinear=False, fog=True, az=None, el=None, dist=None):
    game = Game(seed=C.SEED)
    cam = Camera(game.cols, game.rows)
    cam.perspective = perspective
    cam.apply_preset(preset)
    if az is not None:
        cam.azimuth_deg = az
    if el is not None:
        cam.elevation_deg = el
    if dist is not None:
        cam.distance = dist

    r = Renderer(*size)
    r.bilinear = bilinear
    r.fog_enabled = fog

    t0 = time.perf_counter()
    draw_scene(game, cam, r, size[0], size[1], apply_fog=fog)
    dt = (time.perf_counter() - t0) * 1000

    Image.fromarray(r.to_surface_array()).save(name)
    print(f"{name}: {size[0]}x{size[1]} tris={r.triangles_drawn} "
          f"culled={r.triangles_culled} clipped={r.triangles_clipped} "
          f"render={dt:.1f} ms")


if __name__ == "__main__":
    shot("preview_elev.png", PRESET_ELEVATED, True)
    shot("preview_follow.png", PRESET_FOLLOW, True, size=(640, 400))
"""
tools/perf_bench.py
===================
Reproducible performance measurement for the report.

For every resolution preset and every camera preset it renders 12 frames
head-less and reports average frame time, FPS and triangle counts.
Run:  python tools/perf_bench.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config as C
from camera import Camera, PRESET_ELEVATED, PRESET_FOLLOW
from game import Game
from raster import Renderer
from scene import draw_scene

FRAMES = 12


def bench(size, preset, label):
    g = Game(seed=C.SEED)
    cam = Camera(g.cols, g.rows)
    cam.apply_preset(preset)
    r = Renderer(*size)

    # one warm-up frame (texture caches, mesh caches)
    draw_scene(g, cam, r, size[0], size[1])
    t0 = time.perf_counter()
    for _ in range(FRAMES):
        g.update(1.0 / 60.0, (0.0, -1.0))
        draw_scene(g, cam, r, size[0], size[1])
    ms = (time.perf_counter() - t0) * 1000.0 / FRAMES
    print(f"{label:10s} {size[0]:4d}x{size[1]:<4d} {label2(preset):9s} "
          f"{ms:7.1f} ms  {1000.0 / ms:5.2f} fps  tris={r.triangles_drawn:4d}")


def label2(preset):
    return {PRESET_ELEVATED: "elevated", PRESET_FOLLOW: "follow"}[preset]


if __name__ == "__main__":
    print("software renderer benchmark (python 3.13, numpy only)")
    for name, w, h in C.RESOLUTION_PRESETS:
        for preset in (PRESET_ELEVATED, PRESET_FOLLOW):
            bench((w, h), preset, name)

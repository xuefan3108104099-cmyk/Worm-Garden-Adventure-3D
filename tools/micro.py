"""Timing breakdown of the whole scene draw (per draw call)."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

import config as C
import mesh as MSH
import textures as T
from camera import Camera, PRESET_FOLLOW
from game import Game
from raster import Renderer

g = Game(seed=C.SEED)
cam = Camera(g.cols, g.rows)
cam.apply_preset(PRESET_FOLLOW)
cam.update(g.pos, 640, 400)
r = Renderer(640, 400)
r.set_camera(cam)


def call(label, fn):
    t0 = time.perf_counter()
    fn()
    print(f"{label:14s} {(time.perf_counter() - t0) * 1000:7.2f} ms")


r.fog_enabled = False
r.clear()

call("build water", lambda: g.water_meshes())
wm = g.water_meshes()
call("water draw", lambda: r.draw_mesh(wm, T.get("water"), cull=False, fog=False))

call("build apples", lambda: (g.apple_meshes("apple"), g.apple_stems()))
am = g.apple_meshes("apple")
call("apples draw", lambda: r.draw_mesh(am, T.get("apple")))

call("build birds", lambda: (g.bird_meshes(), g.bird_wings()))
bm = g.bird_meshes()
call("birds draw", lambda: r.draw_mesh(bm, T.get("feather")))

call("build worm", lambda: g.worm_mesh())
call("worm draw", lambda: r.draw_mesh(g.worm_mesh(), T.get("worm")))

call("walls draw", lambda: r.draw_mesh(g.wall_mesh, T.get("stone")))
call("floor draw", lambda: r.draw_mesh(g.floor_mesh, T.get("grass"), cull=False, fog=False))

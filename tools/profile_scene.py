"""Profile the cost of each scene group."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config as C
from camera import Camera, PRESET_ELEVATED
from game import Game
from raster import Renderer
import scene as S


def timed(label, fn, n=3):
    fn()  # warmup
    t0 = time.perf_counter()
    for _ in range(n):
        fn()
    dt = (time.perf_counter() - t0) / n * 1000
    print(f"{label:12s} {dt:8.2f} ms")
    return dt


game = Game(seed=C.SEED)
cam = Camera(game.cols, game.rows)
cam.apply_preset(PRESET_ELEVATED)
cam.update(game.pos, 896, 560)
r = Renderer(896, 560)
r.set_camera(cam)

counts = {}
for name, mesh in [
    ("floor", game.floor_mesh),
    ("water", game.water_meshes()),
    ("walls", game.wall_mesh),
    ("poles", game.flag_poles()),
    ("flags", game.flag_start()),
    ("apples", game.apple_meshes("apple")),
    ("gold", game.apple_meshes("gold")),
    ("stems", game.apple_stems()),
    ("birds", game.bird_meshes()),
    ("wings", game.bird_wings()),
    ("worm", game.worm_mesh()),
]:
    counts[name] = len(mesh["pos"])

print("triangle counts:", counts, "total", sum(counts.values())


      )
r.clear()
timed("clear", lambda: r.clear())
timed("floor", lambda: r.draw_mesh(game.floor_mesh, __import__("textures").get("grass"), cull=False))
timed("walls", lambda: r.draw_mesh(game.wall_mesh, __import__("textures").get("stone")))
timed("apples", lambda: r.draw_mesh(game.apple_meshes("apple"), __import__("textures").get("apple")))
timed("birds", lambda: r.draw_mesh(game.bird_meshes(), __import__("textures").get("feather")))
timed("worm", lambda: r.draw_mesh(game.worm_mesh(), __import__("textures").get("worm")))

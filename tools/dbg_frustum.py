"""Check the frustum test against real chunks."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

import config as C
from camera import Camera, PRESET_ELEVATED
from game import Game
from frustum import Frustum

g = Game(seed=C.SEED)
cam = Camera(g.cols, g.rows)
cam.apply_preset(PRESET_ELEVATED)
cam.update(g.pos, 896, 560)
f = Frustum.from_camera(cam, 896, 560)

print("eye", cam.eye, "forward", cam.basis[2])
print("chunks", len(g.wall_chunks))
ok = 0
for ch in g.wall_chunks:
    v = f.aabb_visible(ch["centre"], ch["half"])
    ok += bool(v)
    d = np.asarray(ch["centre"]) - f.eye
    print(ch["centre"], "visible" if v else "no",
          "depth=%.2f" % (d @ f.forward),
          ["%.2f" % (n @ d + dd) for n, dd in f.planes])
print("visible", ok)

"""Draw every wall chunk (no culling) to verify the geometry is complete."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image

import config as C
import textures as T
from camera import Camera, PRESET_ELEVATED
from game import Game
from raster import Renderer

g = Game(seed=C.SEED)
cam = Camera(g.cols, g.rows)
cam.apply_preset(PRESET_ELEVATED)
cam.update(g.pos, 896, 560)
r = Renderer(896, 560)
r.set_camera(cam)
r.clear()
r.draw_mesh(g.floor_mesh, T.get("grass"), cull=False, fog=False)
for ch in g.wall_chunks:
    r.draw_mesh(ch["mesh"], T.get("stone"))
Image.fromarray(r.to_surface_array()).save("preview_allwalls.png")
print("chunks", len(g.wall_chunks), "tris", r.triangles_drawn)

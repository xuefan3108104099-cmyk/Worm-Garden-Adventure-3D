"""Quick smoke test: render a small maze to PNG without opening a window."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

import config as C
import maze as M
import mesh as MSH
import textures as T
from camera import Camera
from raster import Renderer


def render(size=(640, 400), cols=10, rows=10, seed=3, presp=True, out="test.png"):
    mz = M.generate_maze(cols, rows, seed=seed)
    runs = M.collect_wall_runs(mz, cols, rows)
    boxes = M.runs_to_boxes(runs)
    walls = MSH.maze_wall_mesh(boxes)
    floor = MSH.floor_quad(cols, rows)

    cam = Camera(cols, rows)
    cam.perspective = presp
    cam.apply_preset(1)
    cam.azimuth_deg = 90
    cam.elevation_deg = 55
    cam.distance = max(cols, rows) * 1.55 + 4
    cam.update(np.array([0.5, 0.22, rows / 2 + 0.5]), *size)

    r = Renderer(*size)
    r.set_camera(cam)
    r.clear()

    t0 = time.perf_counter()
    r.draw_mesh(floor, T.get("grass"), tint=(0.8, 0.9, 0.8))
    r.draw_mesh(walls, T.get("stone"), tint=(1.0, 1.0, 1.0))
    dt = (time.perf_counter() - t0) * 1000

    arr = r.to_surface_array()
    Image.fromarray(arr).save(out)
    print(f"{out}: {size[0]}x{size[1]} tris={r.triangles_drawn} "
          f"culled={r.triangles_culled} clipped={r.triangles_clipped} "
          f"render={dt:.2f} ms")


if __name__ == "__main__":
    render(presp=True, out="test_persp.png")
    render(presp=False, out="test_ortho.png")

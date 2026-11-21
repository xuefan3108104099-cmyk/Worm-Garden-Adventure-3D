"""
tools/make_figures.py
=====================
Renders every figure used in the report into screenshots/.

All images are produced head-less (no window): the software renderer writes a
framebuffer, PIL saves it as PNG.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image, ImageDraw

import config as C
import textures as T
from camera import Camera, PRESET_ELEVATED, PRESET_SIDE, PRESET_FOLLOW
from game import Game
from raster import Renderer
from scene import draw_scene

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(HERE, "screenshots")
os.makedirs(SHOTS, exist_ok=True)


def shim_camera(eye, target, size):
    """Minimal camera object for the texture-filtering demo scene."""
    import math3d as MT

    class Shim:
        pass

    cam = Shim()
    cam.eye = np.asarray(eye, dtype=float)
    cam.basis = MT.camera_basis(cam.eye, np.asarray(target, dtype=float))
    cam.perspective = True
    cam.near = C.NEAR_PLANE
    cam.focal_px = lambda: MT.focal_length(size[1], C.FOV_Y_DEG)
    cam.ortho_pixels_per_unit = lambda: 45.0
    cam.distance = float(np.linalg.norm(cam.eye - np.asarray(target, float)))
    cam.update = lambda *a, **k: None
    return cam


def render_filter_demo(bilinear, tag):
    """Grazing-angle floor quad: nearest vs bilinear is obvious."""
    import mesh as MSH

    size = (640, 400)
    r = Renderer(*size)
    r.bilinear = bilinear
    r.fog_enabled = False
    r.set_camera(shim_camera((3.0, 1.6, -2.0), (3.0, 0.0, 6.0), size))
    r.clear()
    quad = MSH.quad([(0, 0, 0), (0, 0, 12), (8, 0, 12), (8, 0, 0)],
                    uv_corners=[(0, 0), (0, 6), (4, 6), (4, 0)])
    r.draw_mesh(quad, T.get("stone"), tint=(1.0, 1.0, 1.0), cull=False, fog=False)
    Image.fromarray(r.to_surface_array()).save(os.path.join(SHOTS, f"{tag}.png"))
    print(f"{tag:26s} bilinear={bilinear}")



def render(preset=PRESET_FOLLOW, size=(896, 560), perspective=True, az=None,
           el=None, dist=None, fog=True, bilinear=False, normals=False,
           depth=False, wire=False, walk_steps=0, tag=""):
    g = Game(seed=C.SEED)
    for _ in range(walk_steps):
        g.update(0.03, (0.0, -1.0))
    cam = Camera(g.cols, g.rows)
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
    r.debug_normals = normals
    r.debug_wireframe = wire
    draw_scene(g, cam, r, size[0], size[1], apply_fog=fog)

    if depth:
        img = Image.fromarray(r.depth_image())
    else:
        img = Image.fromarray(r.to_surface_array())
        if wire:
            draw = ImageDraw.Draw(img)
            for a, b in r.wire_segments:
                # skip segments whose endpoints run far outside the framebuffer
                if max(abs(a[0]), abs(a[1]), abs(b[0]), abs(b[1])) > 1.5 * max(size):
                    continue
                draw.line([a[0], a[1], b[0], b[1]], fill=(255, 255, 255), width=1)

    path = os.path.join(SHOTS, f"{tag}.png")
    img.save(path)
    print(f"{tag:26s} {size[0]}x{size[1]}  tris={r.triangles_drawn:4d}  "
          f"chunks={getattr(r, 'chunks_drawn', 0)}/{getattr(r, 'chunks_total', 0)}")
    return path


if __name__ == "__main__":
    # 1. overview, both projections
    render(PRESET_ELEVATED, (896, 560), perspective=True, tag="fig01_perspective")
    render(PRESET_ELEVATED, (896, 560), perspective=False, tag="fig02_orthographic")

    # 2. debug views of the same follow camera
    render(PRESET_FOLLOW, (640, 400), wire=True, tag="fig03_wireframe")
    render(PRESET_FOLLOW, (640, 400), normals=True, tag="fig04_normals")
    render(PRESET_FOLLOW, (640, 400), depth=True, tag="fig05_depth")

    # 3. Part-B fog: same camera, on and off (camera looks along the lit side)
    render(PRESET_SIDE, (640, 400), az=35, el=22, dist=17, fog=False,
           tag="fig06_fog_off")
    render(PRESET_SIDE, (640, 400), az=35, el=22, dist=17, fog=True,
           tag="fig07_fog_on")

    # 4. Part-B bilinear filtering: grazing-angle floor quad
    render_filter_demo(False, "fig08_nearest")
    render_filter_demo(True, "fig09_bilinear")

    # 5. gameplay shot after a few steps
    render(PRESET_FOLLOW, (640, 400), walk_steps=8, tag="fig10_gameplay")

    # 6. resolution comparison happens in perf.py (timings, not images)
    print("figures written to", SHOTS)

"""
first_cube.py
=============
Milestone demo M1-M4 (handbook section 4): a single textured cube
transformed by hand-built 4x4 matrices.

It reuses the project's own math (math3d), mesh and renderer modules,
so it doubles as a sanity check of the whole pipeline:

    M1 vector / dot / cross        -> normal + lighting term
    M2 4x4 matrix multiplication   -> model matrix T @ R @ S
    M3 camera basis + view matrix  -> world -> camera space
    M4 perspective projection      -> screen space + z-buffer

Run:  python first_cube.py            (writes first_cube.png)
"""

import math

import numpy as np
from PIL import Image

import config as C
import math3d as MT
import mesh as MSH
import textures as T
from raster import Renderer


def build_view(eye, target, width, height):
    """M3: an explicit 4x4 view matrix + projection matrix."""
    right, up, forward = MT.camera_basis(eye, target)
    view = np.eye(4, dtype=float)
    view[0, :3] = right
    view[1, :3] = up
    view[2, :3] = forward          # camera looks down +Z
    view[:3, 3] = -view[:3, :3] @ np.asarray(eye, dtype=float)

    f = MT.focal_length(height, C.FOV_Y_DEG)
    proj = np.zeros((4, 4), dtype=float)
    proj[0, 0] = f
    proj[1, 1] = f
    proj[2, 2] = 1.0
    proj[2, 3] = 0.0
    return view, proj, f


def main():
    width, height = 640, 400
    renderer = Renderer(width, height)

    # M2: model matrix = translate * rotate_y * rotate_x * scale
    angle = math.radians(28.0)
    model = (MT.translation(0.0, 1.1, 3.2)
             @ MT.rotation_y(angle)
             @ MT.rotation_x(math.radians(18.0))
             @ MT.scale(1.4))

    cube = MSH.box((0.0, 0.0, 0.0), (1.0, 1.0, 1.0), uv_repeat=1.0)
    cube = MSH.transform_mesh(cube, model)
    cube = MSH.transform_mesh(cube, np.eye(4))  # keep the dtype path exercised

    floor = MSH.tiled_floor(8, 8, tile=2.0)
    floor = MSH.transform_mesh(floor, MT.translation(0.0, -0.7, 1.0))

    eye = np.array([3.2, 2.6, -0.4], dtype=float)
    target = np.array([0.0, 0.5, 3.4], dtype=float)
    view, proj, f = build_view(eye, target, width, height)

    # The renderer wants a camera object; build a tiny shim for this demo.
    class DemoCamera:
        pass

    cam = DemoCamera()
    cam.eye = eye
    cam.basis = MT.camera_basis(eye, target)
    cam.perspective = True
    cam.near = C.NEAR_PLANE
    cam.fov_y = C.FOV_Y_DEG
    cam.focal_px = lambda: f
    cam.ortho_pixels_per_unit = lambda: 45.0
    cam.update = lambda *a, **k: None
    cam.distance = 4.0
    cam.info = lambda: f"M1-M4 cube demo  view={view.shape} proj={proj.shape}"

    renderer.set_camera(cam)
    renderer.clear()
    renderer.draw_mesh(floor, T.get("grass"), tint=(0.85, 0.9, 0.8), cull=False,
                       fog=False)
    renderer.draw_mesh(cube, T.get("checker"), tint=(1.0, 1.0, 1.0))

    img = renderer.to_surface_array()
    Image.fromarray(img).save("first_cube.png")
    print("first_cube.png written; triangles drawn:", renderer.triangles_drawn)
    print("view matrix:\n", np.round(view, 3))
    print("projection matrix (f = %.1f):\n" % f, np.round(proj, 3))


if __name__ == "__main__":
    main()

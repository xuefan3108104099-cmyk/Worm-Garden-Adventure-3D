"""
frustum.py
==========
Six-plane view frustum used for coarse spatial culling.

Culling whole blocks of maze walls before any triangle is transformed is the
single biggest win in this project: the overview needs every block, but the
third-person camera only touches a handful of them.
"""

import numpy as np


class Frustum:
    def __init__(self, eye, right, up, forward, tan_x, tan_y, near,
                 perspective=True):
        self.eye = np.asarray(eye, dtype=float)
        self.right = np.asarray(right, dtype=float)
        self.up = np.asarray(up, dtype=float)
        self.forward = np.asarray(forward, dtype=float)
        self.tan_x = tan_x
        self.tan_y = tan_y
        self.near = near
        self.perspective = perspective

        # Each plane is stored as (n, d) with the inside test  n.p + d >= 0.
        # Orthographic:  |x| <= half_w, |y| <= half_h, z >= near
        # Perspective:   the same, but the half extents grow with depth.
        if perspective:
            # inside  <=>  |d.right| <= tan_x * (d.forward)
            normals = [
                (tan_x * self.forward - self.right, 0.0),   # right
                (tan_x * self.forward + self.right, 0.0),   # left
                (tan_y * self.forward - self.up, 0.0),      # top
                (tan_y * self.forward + self.up, 0.0),      # bottom
            ]
        else:
            normals = [
                (self.right, tan_x),
                (-self.right, tan_x),
                (self.up, tan_y),
                (-self.up, tan_y),
            ]

        # Plane equation n.p + d >= 0; the plane passes through the eye,
        # so d = -n.eye shifted by the extra offset stored in `normals`.
        self.planes = [(n, -(n @ self.eye) + off) for n, off in normals]

    @classmethod
    def from_camera(cls, camera, width, height):
        tan_y = np.tan(np.radians(camera.fov_y) / 2.0)
        tan_x = tan_y * (width / float(height))
        if not camera.perspective:
            # For ortho, convert the pixel scale into world half extents.
            tan_x = (width / 2.0) / camera.ortho_pixels_per_unit()
            tan_y = (height / 2.0) / camera.ortho_pixels_per_unit()
        return cls(camera.eye, *camera.basis, tan_x=tan_x, tan_y=tan_y,
                   near=camera.near, perspective=camera.perspective)

    def aabb_visible(self, centre, half):
        """Conservative test: True if the box may touch the frustum."""
        c = np.asarray(centre, dtype=float)
        h = np.asarray(half, dtype=float)
        for n, d in self.planes:
            # reject only when *every* corner is on the outside of the plane
            support = (abs(n[0]) * h[0] + abs(n[1]) * h[1] + abs(n[2]) * h[2])
            if n @ c + support + d <= 0.0:
                return False
        # near plane: reject when the whole box is behind it
        depth = (c - self.eye) @ self.forward
        support_f = abs(self.forward[0]) * h[0] + abs(self.forward[1]) * h[1] \
            + abs(self.forward[2]) * h[2]
        if depth + support_f < self.near:
            return False
        return True

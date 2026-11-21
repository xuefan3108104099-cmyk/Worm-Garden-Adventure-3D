"""
camera.py
=========
Orbit camera with three presets (elevated / side / follow), perspective or
orthographic projection, and Q/E orbit + mouse-wheel zoom.

The camera never touches game data: it only produces an eye position and an
orthonormal basis (right, up, forward) used by the renderer.
"""

import numpy as np

import config as C
from math3d import camera_basis, focal_length


PRESET_ELEVATED = 1
PRESET_SIDE = 2
PRESET_FOLLOW = 3

PRESET_NAMES = {
    PRESET_ELEVATED: "1 ELEVATED",
    PRESET_SIDE: "2 SIDE",
    PRESET_FOLLOW: "3 FOLLOW",
}


class Camera:
    def __init__(self, maze_w, maze_h):
        self.maze_centre = np.array([maze_w / 2.0, 0.0, maze_h / 2.0])
        self.preset = PRESET_ELEVATED
        self.perspective = True
        self.azimuth_deg = 90.0          # 0 = looking from +Z, 90 = from +X
        self.elevation_deg = 55.0
        self.distance = 21.0
        self.follow_yaw_deg = 225.0
        self.ortho_half_height = None    # derived from distance + fov
        self.fov_y = C.FOV_Y_DEG
        self.near = C.NEAR_PLANE
        self.eye = np.zeros(3)
        self.target = np.zeros(3)
        self.basis = None
        self.width = 896
        self.height = 560

    # ------------------------------------------------------------ presets ----
    def apply_preset(self, preset):
        self.preset = preset
        if preset == PRESET_ELEVATED:
            self.elevation_deg = 68.0
            self.azimuth_deg = 90.0
            self.distance = self.fit_distance()
        elif preset == PRESET_SIDE:
            self.elevation_deg = 34.0          # low enough for a "garden wall" feel
            self.azimuth_deg = 35.0            # looking from the lit side (+X / +Z)
            self.distance = self.fit_distance() * 0.70
        elif preset == PRESET_FOLLOW:
            self.elevation_deg = 72.0
            self.distance = 4.6
            self.azimuth_deg = self.follow_yaw_deg

    def fit_distance(self, aspect=1.6, margin=0.94):
        """
        Smallest distance at which the whole maze (including the wall tops)
        projects inside the viewport.  Solved by bisection on the distance.
        """
        w = 640.0
        h = w / aspect
        focal = (h / 2.0) / np.tan(np.radians(self.fov_y) / 2.0)

        corners = []
        for x in (0.0, self.maze_centre[0] * 2.0):
            for z in (0.0, self.maze_centre[2] * 2.0):
                for y in (0.0, C.WALL_H):
                    corners.append(np.array([x, y, z]))
        corners = np.array(corners)

        def fits(dist):
            az = np.radians(self.azimuth_deg)
            el = np.radians(self.elevation_deg)
            off = np.array([np.cos(el) * np.sin(az), np.sin(el),
                            np.cos(el) * np.cos(az)]) * dist
            eye = self.maze_centre + off
            right, up, forward = camera_basis(eye, self.maze_centre)
            d = corners - eye
            cz = d @ forward
            if np.any(cz <= 0.1):
                return False
            sx = w / 2.0 + focal * (d @ right) / cz
            sy = h / 2.0 - focal * (d @ up) / cz
            return (np.all(np.abs(sx - w / 2.0) <= (w / 2.0) * margin) and
                    np.all(np.abs(sy - h / 2.0) <= (h / 2.0) * margin))

        lo, hi = 4.0, 90.0
        if not fits(hi):
            return hi
        for _ in range(22):
            mid = (lo + hi) / 2.0
            if fits(mid):
                hi = mid
            else:
                lo = mid
        return float(hi)

    # ----------------------------------------------------------- controls ----
    def orbit(self, delta_deg):
        self.azimuth_deg = (self.azimuth_deg + delta_deg) % 360.0
        if self.preset == PRESET_FOLLOW:
            self.follow_yaw_deg = self.azimuth_deg

    def zoom(self, factor):
        lo, hi = (3.0, 12.0) if self.preset == PRESET_FOLLOW else (8.0, 45.0)
        self.distance = float(np.clip(self.distance * factor, lo, hi))

    def toggle_projection(self):
        self.perspective = not self.perspective

    # ------------------------------------------------------------- update ----
    def update(self, worm_pos, render_w, render_h):
        """Recompute eye, target and basis for the current frame."""
        self.width, self.height = render_w, render_h

        if self.preset == PRESET_FOLLOW:
            target = np.array([worm_pos[0], 0.25, worm_pos[2]], dtype=float)
        else:
            target = self.maze_centre.copy()

        az = np.radians(self.azimuth_deg)
        el = np.radians(float(np.clip(self.elevation_deg, 3.0, 88.0)))
        offset = np.array([
            np.cos(el) * np.sin(az),
            np.sin(el),
            np.cos(el) * np.cos(az),
        ]) * self.distance

        self.target = target
        self.eye = target + offset
        self.basis = camera_basis(self.eye, self.target)

        # For a fair perspective/orthographic comparison the orthographic
        # scale is chosen so that the target plane has the same apparent size.
        self.ortho_half_height = self.distance * np.tan(np.radians(self.fov_y) / 2.0)
        return self.eye, self.basis

    # -------------------------------------------------------------- details ----
    def focal_px(self):
        return focal_length(self.height, self.fov_y)

    def ortho_pixels_per_unit(self):
        return (self.height / 2.0) / max(1e-6, self.ortho_half_height)

    def info(self):
        return (f"proj={'PERSP' if self.perspective else 'ORTHO'}  "
                f"pos=({self.eye[0]:.2f},{self.eye[1]:.2f},{self.eye[2]:.2f})  "
                f"dist={self.distance:.1f}  az={self.azimuth_deg:.0f}  "
                f"el={self.elevation_deg:.0f}  near={self.near:.2f}")






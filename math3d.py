"""
math3d.py
=========
Vector helpers, 4x4 homogeneous matrices and the camera basis.

Column-vector convention:  p_world = M @ p_local  with p = (x, y, z, w).
Points use w = 1 (translation applies), directions use w = 0 (translation ignored).
Matrix composition reads right to left: M = T @ R @ S  (scale, then rotate, then translate).
"""

import numpy as np


# ---------------------------------------------------------------- vectors ----
def normalized(v):
    """Return a unit vector; raises on a zero-length vector."""
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    if n < 1e-8:
        raise ValueError("Zero-length vector")
    return v / n


def dot(a, b):
    return float(np.dot(a, b))


def cross(a, b):
    return np.cross(a, b)


# --------------------------------------------------------------- matrices ----
def identity():
    return np.eye(4, dtype=float)


def translation(tx, ty, tz):
    """4x4 translation matrix."""
    m = np.eye(4, dtype=float)
    m[:3, 3] = (tx, ty, tz)
    return m


def rotation_y(angle_rad):
    """Rotation about the world Y (up) axis (right-handed, column vectors)."""
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    return np.array([
        [c, 0.0, s, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [-s, 0.0, c, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ], dtype=float)


def rotation_x(angle_rad):
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    return np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, c, -s, 0.0],
        [0.0, s, c, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ], dtype=float)


def rotation_z(angle_rad):
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    return np.array([
        [c, -s, 0.0, 0.0],
        [s, c, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ], dtype=float)


def scale(sx, sy=None, sz=None):
    """Non-uniform scale matrix. scale(s) scales uniformly."""
    if sy is None:
        sy = sx
    if sz is None:
        sz = sx
    return np.diag([float(sx), float(sy), float(sz), 1.0])


def transform_point(m, p):
    """Transform a point (w = 1)."""
    v = np.array([p[0], p[1], p[2], 1.0], dtype=float)
    return (m @ v)[:3]


def transform_direction(m, d):
    """Transform a direction (w = 0) - translation is ignored."""
    v = np.array([d[0], d[1], d[2], 0.0], dtype=float)
    return (m @ v)[:3]


def transform_points(m, pts):
    """Vectorised point transform for an (N,3) array."""
    pts = np.asarray(pts, dtype=float)
    homo = np.concatenate([pts, np.ones((len(pts), 1))], axis=1)
    return (homo @ m.T)[:, :3]


# ----------------------------------------------------------------- camera ----
def camera_basis(eye, target, up=(0.0, 1.0, 0.0)):
    """
    Build the orthonormal camera basis (right, up, forward).

    forward = normalize(target - eye)
    right   = normalize(cross(forward, up))
    up      = cross(right, forward)
    """
    eye = np.asarray(eye, dtype=float)
    target = np.asarray(target, dtype=float)
    forward = normalized(target - eye)
    up = np.asarray(up, dtype=float)
    right = np.cross(forward, up)          # +X on screen points to the right
    if np.linalg.norm(right) < 1e-6:
        # Looking straight up/down: pick a different reference up vector.
        right = np.cross(forward, np.array([0.0, 0.0, 1.0]))
    right = normalized(right)
    up = np.cross(right, forward)
    return right, up, forward


def world_to_camera(points, eye, basis):
    """(N,3) world points -> (N,3) camera-space points."""
    right, up, forward = basis
    d = np.asarray(points, dtype=float) - np.asarray(eye, dtype=float)
    return np.stack([d @ right, d @ up, d @ forward], axis=1)


# ------------------------------------------------------------- projection ----
def focal_length(height, fov_y_deg):
    return (height / 2.0) / np.tan(np.radians(fov_y_deg) / 2.0)


def project_perspective(c, width, height, fov_y_deg=70.0):
    """c = (x,y,depth) -> (sx, sy, depth) or None if behind the near plane."""
    x, y, z = c
    if z <= 0.0:
        return None
    f = focal_length(height, fov_y_deg)
    return (width / 2.0 + f * x / z, height / 2.0 - f * y / z, z)


def project_orthographic(c, width, height, pixels_per_unit=45.0):
    x, y, z = c
    if z <= 0.0:
        return None
    return (width / 2.0 + pixels_per_unit * x,
            height / 2.0 - pixels_per_unit * y,
            z)

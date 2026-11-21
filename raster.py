"""
raster.py
=========
The software renderer.

Pipeline per mesh:
    world vertices -> camera space -> back-face cull -> near-plane clip
    -> perspective divide -> screen-space bounding box -> barycentric
    -> z-buffer test -> texture sample -> ambient + diffuse shading -> fog
    -> framebuffer

Everything here is hand-written with NumPy; Pygame is only used later to
present this framebuffer and to draw the HUD.
"""

import numpy as np

import config as C
from textures import sample_nearest, sample_bilinear


# --------------------------------------------------------------- clipping ----
def clip_triangle_near(triangle, uv, near):
    """
    Sutherland-Hodgman clip of one triangle against the camera-space plane
    z = near.  Returns a list of (positions (k,3), uvs (k,2)) triangles
    (a fan when the clipped polygon has four vertices).
    """
    pts = [np.asarray(p, dtype=float) for p in triangle]
    uvs = [np.asarray(t, dtype=float) for t in uv]

    vis_p, vis_uv = [], []
    for i in range(3):
        start, end = pts[i], pts[(i + 1) % 3]
        ts, te = uvs[i], uvs[(i + 1) % 3]
        a_in = start[2] >= near
        b_in = end[2] >= near
        if a_in != b_in:
            t = (near - start[2]) / (end[2] - start[2])
            vis_p.append(start + t * (end - start))
            vis_uv.append(ts + t * (te - ts))
        if b_in:
            vis_p.append(end)
            vis_uv.append(te)

    if len(vis_p) < 3:
        return []

    if len(vis_p) == 3:
        return [(np.array(vis_p), np.array(vis_uv))]

    fan = []
    for i in range(1, len(vis_p) - 1):
        fan.append((np.array([vis_p[0], vis_p[i], vis_p[i + 1]]),
                    np.array([vis_uv[0], vis_uv[i], vis_uv[i + 1]])))
    return fan


# ---------------------------------------------------------------- renderer ---
class Renderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.color = np.zeros((height, width, 3), dtype=np.float32)
        self.zbuffer = np.full((height, width), np.inf, dtype=np.float32)

        self.eye = np.zeros(3)
        self.basis = None
        self.perspective = True
        self.focal = 1.0
        self.ortho_s = 45.0
        self.near = C.NEAR_PLANE

        self.bilinear = False          # Part-B extension #2 toggle
        self.fog_enabled = True        # Part-B extension #1 toggle
        self.fog_density = 1.0
        self.fog_start = C.FOG_START
        self.fog_end = C.FOG_END

        self.debug_wireframe = False
        self.debug_normals = False
        self.debug_depth = False

        self.wire_segments = []
        self.triangles_drawn = 0
        self.triangles_culled = 0
        self.triangles_clipped = 0
        self.triangles_zskipped = 0
        self._means = {}

    # ------------------------------------------------------------- setup ----
    def resize(self, width, height):
        self.width, self.height = int(width), int(height)
        self.color = np.zeros((self.height, self.width, 3), dtype=np.float32)
        self.zbuffer = np.full((self.height, self.width), np.inf, dtype=np.float32)

    def set_camera(self, camera):
        self.eye = camera.eye.copy()
        self.basis = camera.basis
        self.perspective = camera.perspective
        self.near = camera.near
        self.focal = camera.focal_px()
        self.ortho_s = camera.ortho_pixels_per_unit()

    def clear(self, sky_top=(0.35, 0.55, 0.80), sky_bottom=(0.72, 0.84, 0.92)):
        """Vertical sky gradient and an infinite depth buffer."""
        t = np.linspace(0.0, 1.0, self.height, dtype=np.float32)[:, None, None]
        top = np.array(sky_top, dtype=np.float32)
        bottom = np.array(sky_bottom, dtype=np.float32)
        self.color[:] = top * (1.0 - t) + bottom * t
        self.zbuffer.fill(np.inf)
        self.wire_segments.clear()
        self.triangles_drawn = 0
        self.triangles_culled = 0
        self.triangles_clipped = 0

    # ---------------------------------------------------------- projection --
    def project(self, cam):
        """Camera-space points (...,3) -> screen (...,2) plus depth."""
        x, y, z = cam[..., 0], cam[..., 1], cam[..., 2]
        if self.perspective:
            sx = self.width / 2.0 + self.focal * x / z
            sy = self.height / 2.0 - self.focal * y / z
        else:
            sx = self.width / 2.0 + self.ortho_s * x
            sy = self.height / 2.0 - self.ortho_s * y
        return np.stack([sx, sy], axis=-1), z

    def project_point(self, world):
        """Single world point -> (sx, sy, depth) or None."""
        right, up, forward = self.basis
        d = np.asarray(world, dtype=float) - self.eye
        cam = np.array([d @ right, d @ up, d @ forward])
        if cam[2] <= self.near:
            return None
        if self.perspective:
            sx = self.width / 2.0 + self.focal * cam[0] / cam[2]
            sy = self.height / 2.0 - self.focal * cam[1] / cam[2]
        else:
            sx = self.width / 2.0 + self.ortho_s * cam[0]
            sy = self.height / 2.0 - self.ortho_s * cam[1]
        return float(sx), float(sy), float(cam[2])

    # -------------------------------------------------------------- meshes ---
    def draw_mesh(self, mesh, texture=None, tint=(1.0, 1.0, 1.0),
                  cull=True, fog=True, light=C.LIGHT_DIR):
        if mesh is None or len(mesh["pos"]) == 0:
            return

        pos = mesh["pos"]                                  # (T,3,3) world
        uv = mesh["uv"]                                    # (T,3,2)

        right, up, forward = self.basis
        d = pos - self.eye                                 # (T,3,3)
        cam = np.stack([np.einsum("tij,j->ti", d, right),
                        np.einsum("tij,j->ti", d, up),
                        np.einsum("tij,j->ti", d, forward)], axis=2)

        # ---- geometric face normals (outward if the winding is consistent)
        e1 = pos[:, 1] - pos[:, 0]
        e2 = pos[:, 2] - pos[:, 0]
        n = np.cross(e1, e2)
        ln = np.linalg.norm(n, axis=1)
        good = ln > 1e-10
        n[good] /= ln[good, None]
        n[~good] = 0.0

        centroid = pos.mean(axis=1)
        to_eye = self.eye - centroid
        if cull:
            facing = np.einsum("ti,ti->t", n, to_eye) > 0.0
            self.triangles_culled += int((~facing).sum())
        else:
            facing = np.ones(len(pos), dtype=bool)
            # flip normals towards the camera for two-sided surfaces
            flip = np.einsum("ti,ti->t", n, to_eye) < 0.0
            n[flip] *= -1.0

        valid_depth = cam[:, :, 2].min(axis=1) >= self.near
        candidates = np.nonzero(facing & good)[0]

        intensity_all = C.AMBIENT_K + C.DIFFUSE_K * np.clip(n @ light, 0.0, None)
        tint = np.asarray(tint, dtype=np.float32)

        # ---- fast path: fully in front of the near plane, project in bulk
        simple = candidates[valid_depth[candidates]]
        if len(simple):
            proj, depth = self.project(cam[simple])
            flat_uv = uv[simple]
            # front-to-back: nearer triangles first so later pixels are
            # rejected by the coarse z test / the per-pixel z-buffer test
            order = np.argsort(depth.min(axis=1))
            for k in order:
                idx = simple[k]
                self._emit(cam[idx], flat_uv[k], proj[k], depth[k],
                           float(intensity_all[idx]), n[idx], texture, tint,
                           fog and fog, level=0)

        # ---- slow path: clip against the near plane
        clipped = candidates[~valid_depth[candidates]]
        self.triangles_clipped += len(clipped)
        for idx in clipped:
            for poly_p, poly_uv in clip_triangle_near(cam[idx], uv[idx], self.near):
                proj, depth = self.project(poly_p)
                flat_uv = poly_uv
                for t in range(len(poly_p) - 2):
                    tri = [0, t + 1, t + 2]
                    self._raster(proj[tri], depth[tri], flat_uv[tri],
                                 float(intensity_all[idx]), n[idx], texture,
                                 tint, fog and fog)

    # ------------------------------------------------------------ rasterize ---
    def _emit(self, cam_tri, uv_tri, proj, depth, intensity, normal, texture,
              tint, fog, level):
        """
        Rasterise one triangle, subdividing it first when its screen-space
        bounding box is much larger than the screen.  A wall seen from very
        close projects to a long thin sliver whose bounding box is the whole
        screen; four smaller triangles waste far fewer pixels.
        """
        x0 = max(int(np.floor(proj[:, 0].min())), 0)
        x1 = min(int(np.ceil(proj[:, 0].max())), self.width - 1)
        y0 = max(int(np.floor(proj[:, 1].min())), 0)
        y1 = min(int(np.ceil(proj[:, 1].max())), self.height - 1)
        area = max(0, x1 - x0 + 1) * max(0, y1 - y0 + 1)

        if (level < 2 and area > 2 * self.width * self.height
                and depth.min() > self.near * 1.5):
            a, b, c = cam_tri
            ab, bc, ca = (a + b) * 0.5, (b + c) * 0.5, (c + a) * 0.5
            ua, ub, uc = uv_tri[0], uv_tri[1], uv_tri[2]
            uab, ubc, uca = (ua + ub) * 0.5, (ub + uc) * 0.5, (uc + ua) * 0.5
            subs = [
                (np.array([a, ab, ca]), np.array([ua, uab, uca])),
                (np.array([ab, b, bc]), np.array([uab, ub, ubc])),
                (np.array([ca, bc, c]), np.array([uca, ubc, uc])),
                (np.array([ab, bc, ca]), np.array([uab, ubc, uca])),
            ]
            for sub_p, sub_uv in subs:
                sub_proj, sub_depth = self.project(sub_p)
                self._emit(sub_p, sub_uv, sub_proj, sub_depth, intensity,
                           normal, texture, tint, fog, level + 1)
            return

        self._raster(proj, depth, uv_tri, intensity, normal, texture, tint, fog)

    def texture_mean(self, texture):
        key = id(texture)
        if key not in self._means:
            self._means[key] = texture.reshape(-1, 3).mean(axis=0)
        return self._means[key]

    def _raster(self, sxy, depth3, uv3, intensity, normal, texture, tint, fog):
        w, h = self.width, self.height
        x0 = max(int(np.floor(sxy[:, 0].min())), 0)
        x1 = min(int(np.ceil(sxy[:, 0].max())), w - 1)
        y0 = max(int(np.floor(sxy[:, 1].min())), 0)
        y1 = min(int(np.ceil(sxy[:, 1].max())), h - 1)
        if x1 < x0 or y1 < y0:
            return

        if self.debug_wireframe:
            self.wire_segments.append((
                (sxy[0, 0], sxy[0, 1]), (sxy[1, 0], sxy[1, 1])))
            self.wire_segments.append((
                (sxy[1, 0], sxy[1, 1]), (sxy[2, 0], sxy[2, 1])))
            self.wire_segments.append((
                (sxy[2, 0], sxy[2, 1]), (sxy[0, 0], sxy[0, 1])))

        if self.debug_normals:
            col = np.clip(normal * 0.5 + 0.5, 0.0, 1.0)
            self._fill_flat(sxy, x0, x1, y0, y1, col.astype(np.float32))
            return

        # ---- coarse z test: skip the whole triangle if it is fully behind
        zb_slice = self.zbuffer[y0:y1 + 1, x0:x1 + 1]
        if depth3.min() > float(zb_slice.max()):
            self.triangles_zskipped += 1
            return

        a, b, c = sxy
        v0 = b - a
        v1 = c - a
        d00 = v0 @ v0
        d01 = v0 @ v1
        d11 = v1 @ v1
        denom = d00 * d11 - d01 * d01
        if abs(denom) < 1e-12:
            return
        if (x1 - x0 + 1) * (y1 - y0 + 1) <= 1:
            return

        xs = np.arange(x0, x1 + 1, dtype=np.float32) + 0.5
        ys = np.arange(y0, y1 + 1, dtype=np.float32) + 0.5
        px = xs[None, :] - a[0]
        py = ys[:, None] - a[1]

        d20 = px * v0[0] + py * v0[1]
        d21 = px * v1[0] + py * v1[1]
        wb = (d11 * d20 - d01 * d21) / denom
        wc = (d00 * d21 - d01 * d20) / denom
        wa = 1.0 - wb - wc

        mask = np.minimum(wa, np.minimum(wb, wc)) >= -1e-5
        if not mask.any():
            return

        z = depth3
        if self.perspective:
            iz0, iz1, iz2 = 1.0 / z[0], 1.0 / z[1], 1.0 / z[2]
            invz = wa * iz0 + wb * iz1 + wc * iz2
            invz = np.maximum(invz, 1e-9)
            depth = 1.0 / invz
            uz0, uz1, uz2 = uv3[0, 0] * iz0, uv3[1, 0] * iz1, uv3[2, 0] * iz2
            vz0, vz1, vz2 = uv3[0, 1] * iz0, uv3[1, 1] * iz1, uv3[2, 1] * iz2
        else:
            invz = None
            depth = wa * z[0] + wb * z[1] + wc * z[2]
            iz0 = iz1 = iz2 = 1.0

        zb_slice = self.zbuffer[y0:y1 + 1, x0:x1 + 1]
        mask &= depth < zb_slice
        if not mask.any():
            return

        # ---- texture coordinates with perspective-correct interpolation
        area = (x1 - x0 + 1) * (y1 - y0 + 1)
        if texture is not None and area > 48:
            if self.perspective:
                u = (wa * uz0 + wb * uz1 + wc * uz2) / invz
                v = (wa * vz0 + wb * vz1 + wc * vz2) / invz
            else:
                u = wa * uv3[0, 0] + wb * uv3[1, 0] + wc * uv3[2, 0]
                v = wa * uv3[0, 1] + wb * uv3[1, 1] + wc * uv3[2, 1]
            if self.bilinear:
                rgb = sample_bilinear(texture, u, v)
            else:
                rgb = sample_nearest(texture, u, v)
            shaded = rgb * (intensity * tint)
        elif texture is not None:
            # tiny triangle: one average texel is visually indistinguishable
            mean = self.texture_mean(texture)
            shaded = mean * (intensity * tint)
        else:
            rgb = tint
            shaded = np.asarray(tint, dtype=np.float32) * intensity

        if fog and float(depth.max()) > self.fog_start:
            f = np.clip((depth - self.fog_start) /
                        max(1e-6, self.fog_end - self.fog_start),
                        0.0, 1.0) * self.fog_density
            shaded = shaded * (1.0 - f[..., None]) + C.FOG_COLOR * f[..., None]

        col_slice = self.color[y0:y1 + 1, x0:x1 + 1]
        if shaded.ndim == 1:
            col_slice[mask] = shaded
        else:
            col_slice[mask] = shaded[mask]
        zb_slice[mask] = depth[mask]
        self.triangles_drawn += 1

    def _fill_flat(self, sxy, x0, x1, y0, y1, color):
        """Flat-coloured triangle (used by the normal debug view)."""
        a, b, c = sxy
        v0 = b - a
        v1 = c - a
        denom = v0[0] * v1[1] - v0[1] * v1[0]
        if abs(denom) < 1e-12:
            return
        xs = np.arange(x0, x1 + 1, dtype=np.float32) + 0.5
        ys = np.arange(y0, y1 + 1, dtype=np.float32) + 0.5
        px = xs[None, :] - a[0]
        py = ys[:, None] - a[1]
        wb = (px * v1[1] - py * v1[0]) / denom
        wc = (v0[0] * py - v0[1] * px) / denom
        wa = 1.0 - wb - wc
        mask = (wa >= 0) & (wb >= 0) & (wc >= 0)
        if mask.any():
            self.color[y0:y1 + 1, x0:x1 + 1][mask] = color
            self.triangles_drawn += 1

    # ------------------------------------------------------------ billboards --
    def draw_billboard(self, world, radius_world, color, alpha=1.0):
        """
        Camera-facing soft disc for particles.  Depth-tested against the
        z-buffer so sparks/fireworks behind walls are hidden.
        """
        proj = self.project_point(world)
        if proj is None:
            return
        sx, sy, depth = proj
        if self.perspective:
            rpx = radius_world * self.focal / max(depth, 1e-4)
        else:
            rpx = radius_world * self.ortho_s
        rpx = float(np.clip(rpx, 1.0, 40.0))
        x0 = max(int(sx - rpx), 0)
        x1 = min(int(sx + rpx), self.width - 1)
        y0 = max(int(sy - rpx), 0)
        y1 = min(int(sy + rpx), self.height - 1)
        if x1 < x0 or y1 < y0:
            return

        xs = np.arange(x0, x1 + 1, dtype=np.float32) + 0.5
        ys = np.arange(y0, y1 + 1, dtype=np.float32) + 0.5
        dx = xs[None, :] - sx
        dy = ys[:, None] - sy
        dist2 = dx * dx + dy * dy
        mask = dist2 <= rpx * rpx

        zb = self.zbuffer[y0:y1 + 1, x0:x1 + 1]
        mask &= depth < zb
        if not mask.any():
            return

        soft = np.clip(1.0 - np.sqrt(dist2) / max(rpx, 1e-4), 0.0, 1.0)[..., None]
        col = np.asarray(color, dtype=np.float32)[None, None, :] * soft
        col = col * alpha + self.color[y0:y1 + 1, x0:x1 + 1] * (1.0 - alpha * soft)
        self.color[y0:y1 + 1, x0:x1 + 1][mask] = col[mask]

    # --------------------------------------------------------------- output ----
    def depth_image(self):
        """Grayscale depth visualisation for the F3 debug mode."""
        z = self.zbuffer.copy()
        finite = np.isfinite(z)
        if not finite.any():
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)
        hi = np.percentile(z[finite], 95)
        z = np.clip(z, 0.0, hi) / max(hi, 1e-6)
        gray = (1.0 - z)  # near = bright
        gray[~finite] = 0.0
        img = np.repeat(gray[..., None], 3, axis=2)
        return (np.clip(img, 0, 1) * 255).astype(np.uint8)

    def to_surface_array(self):
        """uint8 RGB array ready for pygame.image.frombuffer."""
        arr = np.clip(self.color, 0.0, 1.0)
        return (arr * 255.0 + 0.5).astype(np.uint8)

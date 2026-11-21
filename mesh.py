"""
mesh.py
=======
Low-poly meshes expressed as triangle soups.

Every mesh is a dict:
    {"pos": (T, 3, 3) float64 world-space triangle vertices,
     "uv":  (T, 3, 2) float64 texture coordinates}

Face normals are NOT stored: the renderer derives them with the cross product
of two edges, which guarantees the normal always matches the actual geometry.
Winding is fixed at build time so that all normals point outwards.
"""

import numpy as np

import config as C


# ---------------------------------------------------------------- helpers ----
def _fix_winding(pos, uv, expected_normal):
    """
    Ensure triangle (a, b, c) faces `expected_normal`.

    If cross(b-a, c-a) points the wrong way, b and c are swapped (this also
    swaps their UVs so the texture is not mirrored).
    """
    out_pos = []
    out_uv = []
    for tri, tuv in zip(pos, uv):
        a, b, c = tri
        n = np.cross(b - a, c - a)
        if np.dot(n, expected_normal) < 0:
            tri = np.array([a, c, b])
            tuv = np.array([tuv[0], tuv[2], tuv[1]])
        out_pos.append(tri)
        out_uv.append(tuv)
    return np.array(out_pos), np.array(out_uv)


def _quad(a, b, c, d, uvs, normal):
    """Two triangles for the quad a-b-c-d with matching UV corners."""
    pos = [
        np.array([a, b, c]),
        np.array([a, c, d]),
    ]
    uv = [
        np.array([uvs[0], uvs[1], uvs[2]]),
        np.array([uvs[0], uvs[2], uvs[3]]),
    ]
    return _fix_winding(pos, uv, np.asarray(normal, dtype=float))


def empty_mesh():
    return {"pos": np.zeros((0, 3, 3)), "uv": np.zeros((0, 3, 2))}


def merge_meshes(meshes):
    meshes = [m for m in meshes if len(m["pos"])]
    if not meshes:
        return empty_mesh()
    return {
        "pos": np.concatenate([m["pos"] for m in meshes], axis=0).astype(np.float32),
        "uv": np.concatenate([m["uv"] for m in meshes], axis=0).astype(np.float32),
    }


def transform_mesh(mesh, matrix):
    """Apply a 4x4 model matrix to every vertex."""
    pos = mesh["pos"].reshape(-1, 3)
    homo = np.concatenate([pos, np.ones((len(pos), 1))], axis=1)
    new = (homo @ matrix.T)[:, :3].reshape(-1, 3, 3)
    return {"pos": new, "uv": mesh["uv"].copy()}


def translated(mesh, offset):
    """Cheap translation of an already built mesh (one vector add)."""
    return {"pos": mesh["pos"] + np.asarray(offset, dtype=np.float32),
            "uv": mesh["uv"]}


# ------------------------------------------------------------------- box -----
def box(center, size, uv_repeat=1.0):
    """
    Axis-aligned rectangular prism (12 triangles, 6 faces).

    `center` and `size` are 3-tuples in world units.  UVs are expressed in
    world units so that a texture tiles once per world unit by default.
    """
    cx, cy, cz = center
    sx, sy, sz = size
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0

    v = np.array([
        [cx - hx, cy - hy, cz - hz],   # 0
        [cx + hx, cy - hy, cz - hz],   # 1
        [cx + hx, cy + hy, cz - hz],   # 2
        [cx - hx, cy + hy, cz - hz],   # 3
        [cx - hx, cy - hy, cz + hz],   # 4
        [cx + hx, cy - hy, cz + hz],   # 5
        [cx + hx, cy + hy, cz + hz],   # 6
        [cx - hx, cy + hy, cz + hz],   # 7
    ], dtype=float)

    k = float(uv_repeat)
    w, h, d = sx * k, sy * k, sz * k

    faces = [
        # (corners, normal, (quad width, quad height))
        ((0, 3, 2, 1), (0, 0, -1), (w, h)),   # -Z
        ((4, 5, 6, 7), (0, 0, 1), (w, h)),    # +Z
        ((0, 1, 5, 4), (0, -1, 0), (w, d)),   # -Y
        ((3, 7, 6, 2), (0, 1, 0), (w, d)),    # +Y
        ((0, 4, 7, 3), (-1, 0, 0), (d, h)),   # -X
        ((1, 2, 6, 5), (1, 0, 0), (d, h)),    # +X
    ]

    pos, uv = [], []
    for corners, normal, (qw, qh) in faces:
        a, b, c, e = (v[i] for i in corners)
        uvs = [(0.0, qh), (qw, qh), (qw, 0.0), (0.0, 0.0)]
        p, t = _quad(a, b, c, e, uvs, normal)
        pos.append(p)
        uv.append(t)

    return {"pos": np.concatenate(pos).astype(np.float32),
            "uv": np.concatenate(uv).astype(np.float32)}


# ----------------------------------------------------------------- sphere ----
def sphere(center, radius, segments=8, rings=4, uv_repeat=1.0, squash=(1, 1, 1)):
    """
    Low-poly UV sphere.  rings = number of latitude bands (>=2).
    """
    segments = max(3, int(segments))
    rings = max(2, int(rings))
    cx, cy, cz = center
    sx, sy, sz = squash

    verts = []      # (ring, seg) index -> position
    uvs = []
    for r in range(rings + 1):
        phi = np.pi * r / rings              # 0 (top) .. pi (bottom)
        y = np.cos(phi)
        rad = np.sin(phi)
        for s in range(segments + 1):
            theta = 2.0 * np.pi * s / segments
            x = rad * np.cos(theta)
            z = rad * np.sin(theta)
            verts.append([cx + x * radius * sx,
                          cy + y * radius * sy,
                          cz + z * radius * sz])
            uvs.append([s / segments * uv_repeat, r / rings * uv_repeat])

    pos, uv = [], []
    for r in range(rings):
        for s in range(segments):
            i0 = r * (segments + 1) + s
            i1 = i0 + 1
            i2 = i0 + (segments + 1)
            i3 = i2 + 1
            a, b, c, d = verts[i0], verts[i2], verts[i3], verts[i1]
            t0, t1, t2, t3 = uvs[i0], uvs[i2], uvs[i3], uvs[i1]
            # outward normal approximated by the quad centroid direction
            centroid = (np.array(a) + np.array(b) + np.array(c) + np.array(d)) / 4.0
            n = centroid - np.array([cx, cy, cz])
            if np.linalg.norm(n) < 1e-9:
                n = np.array([0.0, 1.0, 0.0])
            p, t = _quad(a, b, c, d, [t0, t1, t2, t3], n)
            pos.append(p)
            uv.append(t)

    return {"pos": np.concatenate(pos).astype(np.float32),
            "uv": np.concatenate(uv).astype(np.float32)}


# ------------------------------------------------------------------- quad ----
def quad(corners, uv_corners=None):
    """
    Single planar quad from four world-space corners (counter-clockwise seen
    from the side the normal should point to).  Used for the floor, flags,
    water discs and wing planes.
    """
    corners = [np.asarray(c, dtype=float) for c in corners]
    if uv_corners is None:
        uv_corners = [(0, 1), (1, 1), (1, 0), (0, 0)]
    normal = np.cross(corners[1] - corners[0], corners[2] - corners[0])
    if np.linalg.norm(normal) < 1e-12:
        normal = np.array([0.0, 1.0, 0.0])
    pos, uv = _quad(*corners, uv_corners, normal)
    return {"pos": pos.astype(np.float32), "uv": uv.astype(np.float32)}


# ------------------------------------------------------------------ floor ----
def tiled_floor(cols, rows, tile=4.0):
    """Ground plane split into square tiles (coarse z-rejection works better)."""
    tiles = []
    x = 0.0
    while x < cols:
        z = 0.0
        nx = min(x + tile, cols)
        while z < rows:
            nz = min(z + tile, rows)
            a = np.array([x, 0.0, z])
            b = np.array([nx, 0.0, z])
            c = np.array([nx, 0.0, nz])
            d = np.array([x, 0.0, nz])
            uv = [(x / tile, z / tile), (nx / tile, z / tile),
                  (nx / tile, nz / tile), (x / tile, nz / tile)]
            tiles.append(quad([a, d, c, b], uv))
            z = nz
        x = nx
    return merge_meshes(tiles)


# ----------------------------------------------------------------- walls -----
def maze_wall_mesh(boxes, uv_repeat=0.5):
    """Build one static mesh from the merged wall boxes of maze.py."""
    return merge_meshes([
        box(b["centre"], b["size"], uv_repeat=uv_repeat) for b in boxes
    ])

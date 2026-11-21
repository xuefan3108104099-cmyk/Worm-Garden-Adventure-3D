"""
tests/test_math3d.py
====================
Unit tests for the hand-written maths layer (milestones M1-M4).

Run from the project root:   python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config as C
import math3d as MT
import maze as M
import mesh as MSH
from raster import Renderer, clip_triangle_near


class TestVectors(unittest.TestCase):
    def test_dot_and_cross_are_orthogonal(self):
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([-2.0, 0.5, 4.0])
        c = MT.cross(a, b)
        self.assertAlmostEqual(float(np.dot(c, a)), 0.0, places=9)
        self.assertAlmostEqual(float(np.dot(c, b)), 0.0, places=9)

    def test_normalize(self):
        v = MT.normalized([3.0, 0.0, 4.0])
        self.assertAlmostEqual(float(np.linalg.norm(v)), 1.0, places=12)
        self.assertAlmostEqual(v[0], 0.6, places=12)


class TestMatrices(unittest.TestCase):
    def test_rotation_y_is_right_handed(self):
        # +90 degrees about +Y maps +X onto -Z (right-handed, column vectors)
        m = MT.rotation_y(np.pi / 2)
        p = MT.transform_point(m, (1.0, 0.0, 0.0))
        np.testing.assert_allclose(p, (0.0, 0.0, -1.0), atol=1e-12)

    def test_composition_order_right_to_left(self):
        m = MT.translation(1.0, 0.0, 0.0) @ MT.scale(2.0)
        p = MT.transform_point(m, (1.0, 1.0, 1.0))
        np.testing.assert_allclose(p, (3.0, 2.0, 2.0), atol=1e-12)

    def test_direction_ignores_translation(self):
        m = MT.translation(5.0, 6.0, 7.0)
        d = MT.transform_direction(m, (1.0, 0.0, 0.0))
        np.testing.assert_allclose(d, (1.0, 0.0, 0.0), atol=1e-12)


class TestCameraBasis(unittest.TestCase):
    def test_orthonormal(self):
        right, up, forward = MT.camera_basis((0, 0, 0), (0, 0, -1))
        self.assertAlmostEqual(float(right @ up), 0.0, places=12)
        self.assertAlmostEqual(float(right @ forward), 0.0, places=12)
        self.assertAlmostEqual(float(up @ forward), 0.0, places=12)
        for v in (right, up, forward):
            self.assertAlmostEqual(float(np.linalg.norm(v)), 1.0, places=12)

    def test_screen_right_is_world_east_when_looking_north(self):
        # Looking towards -Z, screen +X must be world +X (no mirrored image).
        right, up, forward = MT.camera_basis((0, 0, 0), (0, 0, -1))
        np.testing.assert_allclose(right, (1.0, 0.0, 0.0), atol=1e-12)
        np.testing.assert_allclose(up, (0.0, 1.0, 0.0), atol=1e-12)

    def test_world_to_camera_round_trip(self):
        eye = np.array([2.0, 3.0, 4.0])
        basis = MT.camera_basis(eye, (0.0, 1.0, 0.0))
        pts = np.array([[2.0, 3.0, 4.0], [1.0, 1.0, 1.0]])
        cam = MT.world_to_camera(pts, eye, basis)
        np.testing.assert_allclose(cam[0], (0.0, 0.0, 0.0), atol=1e-12)
        self.assertGreater(cam[1, 2], 0.0)


class TestProjection(unittest.TestCase):
    def test_point_on_view_axis_hits_screen_centre(self):
        sx, sy, depth = MT.project_perspective((0.0, 0.0, 5.0), 640, 400, 70.0)
        self.assertAlmostEqual(sx, 320.0, places=9)
        self.assertAlmostEqual(sy, 200.0, places=9)
        self.assertAlmostEqual(depth, 5.0, places=9)

    def test_behind_camera_returns_none(self):
        self.assertIsNone(MT.project_perspective((0.0, 0.0, -1.0), 640, 400))

    def test_focal_length(self):
        f = MT.focal_length(400, 90.0)
        self.assertAlmostEqual(f, 200.0, places=9)


class TestNearClipping(unittest.TestCase):
    def test_triangle_crossing_near_plane_is_split(self):
        tri = np.array([[0.0, 0.0, 2.0],
                        [1.0, 0.0, -1.0],
                        [0.0, 1.0, 0.5]])
        uv = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
        parts = clip_triangle_near(tri, uv, near=0.1)
        self.assertEqual(len(parts), 2)          # a 4-vertex polygon -> fan
        for p, t in parts:
            self.assertTrue(np.all(p[:, 2] >= 0.1 - 1e-9))
            self.assertEqual(p.shape, (3, 3))
            self.assertEqual(t.shape, (3, 2))

    def test_triangle_fully_inside_is_untouched(self):
        tri = np.array([[0.0, 0.0, 2.0], [1.0, 0.0, 2.0], [0.0, 1.0, 2.0]])
        uv = np.zeros((3, 2))
        parts = clip_triangle_near(tri, uv, near=0.1)
        self.assertEqual(len(parts), 1)
        # identical shape, vertices may be re-ordered by the clipper
        pts = parts[0][0]
        self.assertEqual(pts.shape, (3, 3))
        for p in pts:
            self.assertTrue(any(np.allclose(p, q) for q in tri))


class TestMaze(unittest.TestCase):
    def test_cell_center(self):
        p = M.cell_center_3d(2, 3, 0.0)
        np.testing.assert_allclose(p, (2.5, 0.0, 3.5))

    def test_generation_is_deterministic(self):
        a = M.generate_maze(5, 4, seed=99)
        b = M.generate_maze(5, 4, seed=99)
        self.assertEqual(a, b)

    def test_perfect_maze_has_cells_minus_one_openings(self):
        cols, rows = 6, 5
        maze = M.generate_maze(cols, rows, seed=7)
        openings = 0
        for r in range(rows):
            for c in range(cols):
                if c + 1 < cols and not maze[r][c]["walls"]["E"]:
                    openings += 1
                if r + 1 < rows and not maze[r][c]["walls"]["S"]:
                    openings += 1
        self.assertEqual(openings, cols * rows - 1)

    def test_every_cell_is_reachable(self):
        cols, rows = 8, 6
        maze = M.generate_maze(cols, rows, seed=3)
        start = (0, 0)
        seen, stack = {start}, [start]
        while stack:
            cell = stack.pop()
            for n in M.get_available_neighbours(maze, cell, cols, rows):
                if n not in seen:
                    seen.add(n)
                    stack.append(n)
        self.assertEqual(len(seen), cols * rows)

    def test_circle_wall_collision(self):
        box = (0.0, 1.0, 0.0, 0.1)          # x0, x1, z0, z1
        self.assertTrue(M.circle_hits_xz(0.5, 0.1, 0.2, box))
        self.assertFalse(M.circle_hits_xz(0.5, 1.0, 0.2, box))


class TestRaster(unittest.TestCase):
    def test_z_buffer_keeps_nearest_triangle(self):
        r = Renderer(64, 64)
        r.eye = np.zeros(3)
        r.basis = MT.camera_basis((0, 0, 0), (0, 0, 1))
        r.focal = MT.focal_length(64, 70.0)
        r.perspective = True
        r.clear()
        far = MSH.quad([(-1, -1, 5), (1, -1, 5), (1, 1, 5), (-1, 1, 5)],
                       uv_corners=[(0, 0), (1, 0), (1, 1), (0, 1)])
        near = MSH.quad([(-0.5, -0.5, 2), (0.5, -0.5, 2), (0.5, 0.5, 2),
                         (-0.5, 0.5, 2)],
                        uv_corners=[(0, 0), (1, 0), (1, 1), (0, 1)])
        r.draw_mesh(far, None, tint=(1.0, 0.0, 0.0), cull=False, fog=False)
        r.draw_mesh(near, None, tint=(0.0, 1.0, 0.0), cull=False, fog=False)
        centre = r.color[32, 32]
        self.assertGreater(centre[1], centre[0])   # green wins over red
        self.assertAlmostEqual(float(r.zbuffer[32, 32]), 2.0, places=4)


if __name__ == "__main__":
    unittest.main(verbosity=2)

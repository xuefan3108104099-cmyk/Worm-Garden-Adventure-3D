"""
game.py
=======
All gameplay in world space.

Reused from the original 2D game (unchanged rules):
    * depth-first maze generation and wall flags
    * start/finish cells and the four-apple unlock rule
    * bird routing between connected cells
    * apple values (3 x 50 + 1 x 100), level progression, score, timer

Re-implemented for 3D:
    * X/Z movement with circle-vs-AABB sliding collision
    * a genuine vertical jump (Euler integration of gravity)
    * height-aware water / bird / apple collisions
    * 3D meshes for worm, apples, birds, water, flags
"""

import math
import random
import time

import numpy as np

import config as C
import maze as M
import mesh as MSH
import textures as T
from particles import ParticleSystem


class Game:
    def __init__(self, cols=C.COLS, rows=C.ROWS, seed=C.SEED, static_seed=None):
        self.cols = cols
        self.rows = rows
        self.base_seed = seed
        self.rng = random.Random(seed)
        self.particles = ParticleSystem(random.Random(seed + 1))

        self.level = 1
        self.score = 0
        self.collected = 0
        self.message = ""
        self.message_timer = 0.0
        self.won = False

        self.exit_unlocked = False
        self.worm_history = []

        # ---- cached unit meshes ---------------------------------------------
        # Spheres are generated once and only translated every frame; building
        # them from scratch each frame was a measurable cost.
        zero = np.zeros(3)
        self._base_apple = MSH.sphere(zero, C.APPLE_RADIUS, segments=8, rings=3)
        self._base_stem = MSH.box((0.0, C.APPLE_RADIUS - 0.01, 0.0),
                                  (0.025, 0.14, 0.025), uv_repeat=2.0)
        self._base_leaf = MSH.quad([
            (-0.01, C.APPLE_RADIUS + 0.03, 0.0),
            (0.11, C.APPLE_RADIUS + 0.05, 0.03),
            (0.10, C.APPLE_RADIUS + 0.08, -0.02),
            (-0.01, C.APPLE_RADIUS + 0.06, -0.02),
        ])
        self._base_bird = MSH.sphere(zero, 0.17, segments=6, rings=3,
                                     squash=(1.35, 0.85, 1.0))
        self._base_bird_head = MSH.sphere(zero, 0.10, segments=6, rings=3)
        self._base_worm_head = MSH.sphere(zero, 0.20, segments=8, rings=4)
        self._base_worm_seg = [MSH.sphere(zero, 0.155 - 0.012 * i, segments=8,
                                          rings=3) for i in (1, 2, 3)]
        self._base_water = MSH.quad(
            [(-C.WATER_RADIUS, 0.0, -C.WATER_RADIUS),
             (-C.WATER_RADIUS, 0.0, C.WATER_RADIUS),
             (C.WATER_RADIUS, 0.0, C.WATER_RADIUS),
             (C.WATER_RADIUS, 0.0, -C.WATER_RADIUS)])

        self.build_level(first=True)

    # ------------------------------------------------------------ level ------
    def build_level(self, first=False):
        level_seed = self.base_seed + self.level * 37
        self.maze = M.generate_maze(self.cols, self.rows, seed=level_seed)
        self.start = M.start_cell(self.rows)
        self.finish = M.finish_cell(self.cols, self.rows)

        self.wall_runs = M.collect_wall_runs(self.maze, self.cols, self.rows)
        boxes = M.runs_to_boxes(self.wall_runs)
        self.colliders = [b["collider"] for b in boxes]

        # ---- spatial chunks: the frustum culls whole 4x4-cell blocks --------
        # Long wall runs are split so that no box crosses a chunk boundary;
        # each chunk then gets a tight axis-aligned bounding box.
        chunk = 4.0
        pieces = []
        for b in boxes:
            cx, cz = b["centre"][0], b["centre"][2]
            sx, sz = b["size"][0], b["size"][2]
            nx = max(1, int(math.ceil(sx / chunk)))
            nz = max(1, int(math.ceil(sz / chunk)))
            for ix in range(nx):
                for iz in range(nz):
                    cx2 = cx - sx / 2.0 + sx * (ix + 0.5) / nx
                    cz2 = cz - sz / 2.0 + sz * (iz + 0.5) / nz
                    pieces.append({
                        "centre": np.array([cx2, b["centre"][1], cz2]),
                        "size": np.array([sx / nx, b["size"][1], sz / nz]),
                    })
        self.wall_boxes = pieces
        self.wall_mesh = MSH.maze_wall_mesh(pieces)

        groups = {}
        for b in pieces:
            key = (int(b["centre"][0] // chunk), int(b["centre"][2] // chunk))
            groups.setdefault(key, []).append(b)

        self.wall_chunks = []
        for key, boxes in groups.items():
            c = np.array([(key[0] + 0.5) * chunk, C.WALL_H * 0.5,
                          (key[1] + 0.5) * chunk], dtype=float)
            h = np.array([chunk * 0.5, C.WALL_H * 0.5, chunk * 0.5], dtype=float)
            self.wall_chunks.append({"centre": c, "half": h,
                                     "mesh": MSH.maze_wall_mesh(boxes)})
        # The floor is split into 4x4 chunks: small triangles can be rejected
        # by the coarse z-test once walls already cover them (big speed-up).
        self.floor_mesh = MSH.tiled_floor(self.cols, self.rows, tile=4.0)

        # ---- spawn worm ------------------------------------------------------
        self.pos = M.cell_center_3d(self.start[0], self.start[1], C.GROUND_Y)
        self.vy = 0.0
        self.grounded = True
        self.jump_cooldown = 0.0
        self.yaw = 0.0
        self.moving = False
        self.worm_history = [self.pos.copy() for _ in range(24)]
        self.walk_timer = 0.0

        # ---- hazards / collectibles / enemies --------------------------------
        self.build_water_holes()
        self.build_apples()
        self.build_birds()

        self.particles.clear()
        self.collected = 0
        self.exit_unlocked = False
        self.start_time = time.time()

    def build_water_holes(self):
        self.water_holes = []
        self.water_cells = set()
        cells = [(x, y) for y in range(self.rows) for x in range(self.cols)
                 if (x, y) != self.start and (x, y) != self.finish]
        self.rng.shuffle(cells)
        for cell in cells[:C.WATER_HOLE_COUNT]:
            self.water_cells.add(cell)
            self.water_holes.append({
                "cell": cell,
                "pos": M.cell_center_3d(cell[0], cell[1], 0.0),
                "phase": self.rng.uniform(0, 2 * math.pi),
            })

    def build_apples(self):
        self.apples = []
        cells = []
        for y in range(self.rows):
            for x in range(self.cols):
                if (x, y) in (self.start, self.finish):
                    continue
                if (x, y) in self.water_cells:
                    continue
                cells.append((x, y))
        self.rng.shuffle(cells)
        rewards = [("apple", C.SILVER_VALUE)] * 3 + [("gold", C.GOLD_VALUE)]
        for cell, (kind, value) in zip(cells, rewards):
            self.apples.append({
                "cell": cell,
                "base": M.cell_center_3d(cell[0], cell[1], 0.28),
                "kind": kind,
                "value": value,
                "collected": False,
                "phase": self.rng.uniform(0, 2 * math.pi),
            })

    def build_birds(self):
        self.birds = []
        count = min(2 + self.level, 8)
        cells = [(x, y) for y in range(self.rows) for x in range(self.cols)
                 if (x, y) != self.start and (x, y) != self.finish
                 and (x, y) not in self.water_cells]
        self.rng.shuffle(cells)
        for cell in cells[:count]:
            neighbours = M.get_available_neighbours(self.maze, cell, self.cols, self.rows)
            if not neighbours:
                continue
            target = self.rng.choice(neighbours)
            self.birds.append({
                "cell": cell,
                "target": target,
                "previous": cell,
                "pos": M.cell_center_3d(cell[0], cell[1], C.FLY_HEIGHT),
                "speed": C.ENEMY_SPEED + self.rng.uniform(-0.2, 0.4),
                "phase": self.rng.uniform(0, 2 * math.pi),
            })

    # ---------------------------------------------------------- collisions ----
    def circle_hits_wall(self, x, z, radius):
        for box in self.colliders:
            if M.circle_hits_xz(x, z, radius, box):
                return True
        return False

    def move_worm(self, dx, dz, dt):
        """Move in X and Z separately so the worm slides along walls."""
        speed = C.BALL_SPEED
        mx = dx * speed * dt
        mz = dz * speed * dt
        max_step = 0.08
        steps = max(1, int(math.ceil(max(abs(mx), abs(mz)) / max_step)))
        sx, sz = mx / steps, mz / steps
        for _ in range(steps):
            new_x = self.pos[0] + sx
            new_x = float(np.clip(new_x, C.BALL_RADIUS, self.cols - C.BALL_RADIUS))
            if not self.circle_hits_wall(new_x, self.pos[2], C.BALL_RADIUS):
                self.pos[0] = new_x
            new_z = self.pos[2] + sz
            new_z = float(np.clip(new_z, C.BALL_RADIUS, self.rows - C.BALL_RADIUS))
            if not self.circle_hits_wall(self.pos[0], new_z, C.BALL_RADIUS):
                self.pos[2] = new_z

    # -------------------------------------------------------------- update ----
    def update(self, dt, move_dir, jump_pressed=False):
        dt = min(dt, 0.05)

        # ---- vertical jump (Euler integration, real world Y -----------------
        if jump_pressed and self.grounded and self.jump_cooldown <= 0:
            self.vy = C.JUMP_SPEED
            self.grounded = False
            self.jump_cooldown = C.JUMP_COOLDOWN

        self.vy -= C.GRAVITY * dt
        self.pos[1] += self.vy * dt
        if self.pos[1] <= C.GROUND_Y:
            self.pos[1] = C.GROUND_Y
            self.vy = 0.0
            self.grounded = True
        if self.jump_cooldown > 0:
            self.jump_cooldown = max(0.0, self.jump_cooldown - dt)

        # ---- horizontal movement --------------------------------------------
        dx, dz = float(move_dir[0]), float(move_dir[1])
        length = math.hypot(dx, dz)
        self.moving = length > 1e-6
        if self.moving:
            dx, dz = dx / length, dz / length
            self.move_worm(dx, dz, dt)
            self.yaw = math.atan2(dx, dz)
            self.walk_timer += dt
            if self.walk_timer >= C.SPARK_INTERVAL:
                self.walk_timer = 0.0
                self.particles.spark(self.pos + np.array([0, -0.1, 0]),
                                     direction=(dx, 0, dz))

        # ---- worm trail for the segmented body -------------------------------
        self.worm_history.append(self.pos.copy())
        if len(self.worm_history) > 30:
            self.worm_history.pop(0)

        # ---- hazards ---------------------------------------------------------
        if self.check_water():
            return
        self.update_birds(dt)
        if self.check_bird_collision():
            return
        self.update_apples()
        self.check_finish()
        self.particles.update(dt)

        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""

    def is_airborne(self):
        return self.pos[1] > C.GROUND_Y + 0.03

    def check_water(self):
        """Only a grounded worm falls in - jumping over water is safe."""
        if self.is_airborne():
            return False
        for hole in self.water_holes:
            dx = self.pos[0] - hole["pos"][0]
            dz = self.pos[2] - hole["pos"][2]
            if math.hypot(dx, dz) < C.BALL_RADIUS + C.WATER_RADIUS:
                self.reset_worm()
                self.set_message("Splash! Back to the start.")
                return True
        return False

    def update_birds(self, dt):
        for bird in self.birds:
            target = M.cell_center_3d(bird["target"][0], bird["target"][1], C.FLY_HEIGHT)
            delta = target - bird["pos"]
            dist = float(np.linalg.norm(delta))
            if dist <= 0.05:
                bird["pos"] = target.copy()
                bird["previous"] = bird["cell"]
                bird["cell"] = bird["target"]
                neighbours = M.get_available_neighbours(
                    self.maze, bird["cell"], self.cols, self.rows)
                if neighbours:
                    options = [n for n in neighbours if n != bird["previous"]]
                    bird["target"] = self.rng.choice(options or neighbours)
            else:
                bird["pos"] += (delta / dist) * min(dist, bird["speed"] * dt)

    def check_bird_collision(self):
        # The original 2D rule is a circle test in the X/Z plane, so the same
        # test is used here: the birds fly above the walls but they still
        # catch the worm when it passes underneath them.
        for bird in self.birds:
            dx = self.pos[0] - bird["pos"][0]
            dz = self.pos[2] - bird["pos"][2]
            if math.hypot(dx, dz) < C.BALL_RADIUS + C.ENEMY_RADIUS:
                self.reset_worm()
                self.set_message("A bird bumped you! Back to the start.")
                return True
        return False

    def apple_height(self, apple, t=None):
        t = time.time() if t is None else t
        return C.APPLE_BOB_AMPLITUDE * math.sin(
            2 * math.pi * C.APPLE_BOB_FREQUENCY * t + apple["phase"])

    def update_apples(self):
        for apple in self.apples:
            if apple["collected"]:
                continue
            centre = apple["base"] + np.array([0.0, self.apple_height(apple), 0.0])
            if float(np.linalg.norm(self.pos - centre)) < C.APPLE_CATCH_RADIUS + C.APPLE_RADIUS:
                apple["collected"] = True
                self.collected += 1
                self.score += apple["value"]
                if self.collected >= C.TOTAL_APPLES:
                    self.exit_unlocked = True
                    self.set_message("All apples collected - the exit is open!")

    def check_finish(self):
        centre = M.cell_center_3d(self.finish[0], self.finish[1], C.GROUND_Y)
        if float(np.linalg.norm(self.pos - centre)) < C.FINISH_CATCH_RADIUS:
            if self.collected >= C.TOTAL_APPLES:
                self.level += 1
                self.set_message(f"Level {self.level}!")
                self.build_level()
            else:
                remaining = C.TOTAL_APPLES - self.collected
                self.set_message(f"Collect the remaining {remaining} apple(s) first!")
                self.reset_worm()

    # ------------------------------------------------------------- helpers ----
    def reset_worm(self):
        self.pos = M.cell_center_3d(self.start[0], self.start[1], C.GROUND_Y)
        self.vy = 0.0
        self.grounded = True
        self.jump_cooldown = 0.0
        self.worm_history = [self.pos.copy() for _ in range(24)]

    def restart(self):
        self.level = 1
        self.score = 0
        self.particles.clear()
        self.build_level()

    def set_message(self, text, seconds=2.2):
        self.message = text
        self.message_timer = seconds

    def elapsed(self):
        return time.time() - self.start_time

    # -------------------------------------------------------------- meshes ----
    def worm_mesh(self):
        forward = np.array([math.sin(self.yaw), 0.0, math.cos(self.yaw)])
        right = np.array([math.cos(self.yaw), 0.0, -math.sin(self.yaw)])
        # body segments trail behind the head, with a gentle sine wiggle
        t = time.time()
        meshes = []
        for i in (1, 2, 3):
            pos = (self.pos - forward * (0.17 * i)
                   + right * (0.035 * math.sin(t * 9.0 - i * 1.2)))
            pos = pos.copy()
            pos[1] = max(C.BALL_RADIUS * 0.85, self.pos[1] + 0.02)
            meshes.append(MSH.translated(self._base_worm_seg[i - 1], pos))
        meshes.append(MSH.translated(self._base_worm_head, self.pos))
        return MSH.merge_meshes(meshes)

    def worm_eye_positions(self):
        """Two small white spheres so the head reads as a face."""
        forward = np.array([math.sin(self.yaw), 0.0, math.cos(self.yaw)])
        right = np.array([math.cos(self.yaw), 0.0, -math.sin(self.yaw)])
        base = self.pos + forward * 0.155 + np.array([0, 0.075, 0])
        return base + right * 0.07, base - right * 0.07

    def apple_meshes(self, kind):
        meshes = []
        t = time.time()
        for apple in self.apples:
            if apple["collected"] or apple["kind"] != kind:
                continue
            centre = apple["base"] + np.array([0.0, self.apple_height(apple, t), 0.0])
            meshes.append(MSH.translated(self._base_apple, centre))
        return MSH.merge_meshes(meshes)

    def apple_stems(self):
        meshes = []
        t = time.time()
        for apple in self.apples:
            if apple["collected"]:
                continue
            centre = apple["base"] + np.array([0.0, self.apple_height(apple, t), 0.0])
            meshes.append(MSH.translated(self._base_stem, centre))
            meshes.append(MSH.translated(self._base_leaf, centre))
        return MSH.merge_meshes(meshes)

    def bird_meshes(self):
        meshes = []
        for bird in self.birds:
            meshes.append(MSH.translated(self._base_bird, bird["pos"]))
            forward = np.array([0.0, 0.0, 1.0])
            d = M.cell_center_3d(bird["target"][0], bird["target"][1],
                                 C.FLY_HEIGHT) - bird["pos"]
            if np.linalg.norm(d) > 1e-6:
                forward = d / np.linalg.norm(d)
            head = bird["pos"] + forward * 0.14 + np.array([0, 0.09, 0])
            meshes.append(MSH.translated(self._base_bird_head, head))
        return MSH.merge_meshes(meshes)

    def bird_wings(self):
        """Two animated flat wings per bird (sine flap)."""
        meshes = []
        t = time.time()
        for bird in self.birds:
            d = M.cell_center_3d(bird["target"][0], bird["target"][1],
                                 C.FLY_HEIGHT) - bird["pos"]
            forward = d / (np.linalg.norm(d) + 1e-9)
            right = np.cross(np.array([0.0, 1.0, 0.0]), forward)
            if np.linalg.norm(right) < 1e-6:
                right = np.array([1.0, 0.0, 0.0])
            right /= np.linalg.norm(right)

            flap = math.sin(t * 11.0 + bird["phase"]) * 0.42
            p = bird["pos"] + np.array([0, 0.02, 0])

            for side in (-1.0, 1.0):
                tip = p + right * (0.30 * side) + np.array([0, 0.10 * flap * side + 0.03, 0])
                back = p - forward * 0.13
                tip_b = tip - forward * 0.13
                meshes.append(MSH.quad([back, tip, tip_b, back - forward * 0.02],
                                       uv_corners=[(0, 0), (1, 0), (1, 1), (0, 1)]))
        return MSH.merge_meshes(meshes)

    def water_meshes(self, camera_eye=None):
        meshes = []
        t = time.time()
        for hole in self.water_holes:
            wobble = 0.012 + 0.01 * math.sin(t * 3 + hole["phase"])
            offset = np.array([hole["pos"][0], wobble, hole["pos"][2]])
            meshes.append(MSH.translated(self._base_water, offset))
        return MSH.merge_meshes(meshes)

    def flag_poles(self):
        meshes = [
            MSH.box((0.06, 0.6, self.start[1] + 0.5), (0.06, 1.2, 0.06), uv_repeat=2.0),
            MSH.box((self.cols - 0.06, 0.6, self.finish[1] + 0.5),
                    (0.06, 1.2, 0.06), uv_repeat=2.0),
        ]
        return MSH.merge_meshes(meshes)

    def flag_start(self):
        t = time.time()
        wave = math.sin(t * 2.4) * 0.045
        sx, sz = 0.06, self.start[1] + 0.5
        y2 = 1.05
        return MSH.quad([
            (sx, y2, sz),
            (sx + 0.46, y2 - 0.02 + wave, sz + wave),
            (sx + 0.46, y2 - 0.24, sz + wave),
            (sx, y2 - 0.25, sz),
        ])

    def flag_finish(self):
        t = time.time()
        wave = math.sin(t * 2.4) * 0.045
        fx, fz = self.cols - 0.06, self.finish[1] + 0.5
        y2 = 1.05
        return MSH.quad([
            (fx, y2, fz),
            (fx + 0.52, y2 - 0.02 + wave, fz + wave),
            (fx + 0.52, y2 - 0.30, fz + wave),
            (fx, y2 - 0.30, fz),
        ], uv_corners=[(0, 1), (1, 1), (1, 0), (0, 0)])

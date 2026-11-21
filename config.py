"""
config.py
=========
Global constants for "Worm's Garden Adventure 3D".

Units: one maze cell = 1 world unit (the original 50 px cell).
World axes (right-handed): X = east, Y = up, Z = south.
"""

import numpy as np

# ----------------------------------------------------------------------------
# World / maze (values copied from the original 2D game and scaled by 1/50)
# ----------------------------------------------------------------------------
COLS = 23                    # original COLS
ROWS = 15                    # original ROWS
CELL = 1.0                   # 1 world unit per cell (50 px -> 1 unit)

WALL_H = 0.75                # 0.75 world units, from the handbook
WALL_T = 8.0 / 50.0          # 0.16 world units (original 8 px wall thickness)

BALL_RADIUS = 11.0 / 50.0    # 0.22 world units
BALL_SPEED = 230.0 / 50.0    # 4.6 world units / second
GROUND_Y = BALL_RADIUS       # sphere centre height when standing on the floor
ENEMY_RADIUS = 10.0 / 50.0   # 0.20
ENEMY_SPEED = 75.0 / 50.0    # 1.5 world units / second
FLY_HEIGHT = 0.95            # bird body centre: above the 0.75 wall tops

WATER_HOLE_COUNT = 9
WATER_RADIUS = 13.0 / 50.0   # 0.26

TOTAL_APPLES = 4
SILVER_VALUE = 50
GOLD_VALUE = 100
APPLE_RADIUS = 0.16
APPLE_CATCH_RADIUS = BALL_RADIUS + 12.0 / 50.0   # original BALL_RADIUS + 12 px
APPLE_BOB_AMPLITUDE = 0.05
APPLE_BOB_FREQUENCY = 1.5

FINISH_CATCH_RADIUS = 17.0 / 50.0   # original check_finish distance (17 px)

# Genuine vertical jump (handbook section 11.3)
GRAVITY = 10.0               # world units / s^2
JUMP_SPEED = 3.2             # world units / s
JUMP_COOLDOWN = 0.35

# ----------------------------------------------------------------------------
# Display / rendering
# ----------------------------------------------------------------------------
WINDOW_W, WINDOW_H = 1280, 800
FOV_Y_DEG = 70.0
NEAR_PLANE = 0.10

# framebuffer presets (window aspect 1.6; heights follow the handbook idea)
RESOLUTION_PRESETS = [
    ("FAST", 480, 300),
    ("BALANCED", 640, 400),
    ("HIGH", 896, 560),
    ("NATIVE", 1280, 800),
]
DEFAULT_PRESET = 0           # FAST, keeps the software renderer interactive

FOG_COLOR = np.array([0.70, 0.79, 0.86], dtype=np.float32)
FOG_START = 8.0
FOG_END = 30.0

AMBIENT_K = 0.34
DIFFUSE_K = 0.66
LIGHT_DIR = np.array([0.42, 0.86, 0.28], dtype=np.float32)   # surface -> light
LIGHT_DIR = LIGHT_DIR / np.linalg.norm(LIGHT_DIR)

SKY_COLOR = np.array([0.53, 0.70, 0.86], dtype=np.float32)

MAX_PARTICLES = 260
SPARK_INTERVAL = 0.015

SEED = 12                    # fixed seed -> reproducible screenshots

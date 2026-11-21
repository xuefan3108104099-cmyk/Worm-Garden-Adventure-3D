"""
maze.py
=======
Maze topology - the depth-first recursive-backtracking generator is reused
from the original 2D game without changing its rules.  Only the presentation
layer changes: cells are converted to 3D world coordinates and the wall flags
become box meshes / colliders.

World axes: X = east (= column), Y = up, Z = south (= row).
Cell (col, row) centre = (col + 0.5, height, row + 0.5).
"""

import random

import numpy as np

import config as C

DIRECTIONS = {
    "N": (0, -1, "S"),
    "E": (1, 0, "W"),
    "S": (0, 1, "N"),
    "W": (-1, 0, "E"),
}


# --------------------------------------------------------------------------
def generate_maze(cols=None, rows=None, seed=None):
    """
    Original depth-first backtracking generator.

    Returns maze[row][col] = {"walls": {"N","E","S","W"}, "visited": bool}.
    """
    cols = C.COLS if cols is None else cols
    rows = C.ROWS if rows is None else rows
    rng = random.Random(seed)

    maze = [
        [{"walls": {"N": True, "E": True, "S": True, "W": True},
          "visited": False} for _ in range(cols)]
        for _ in range(rows)
    ]

    start = (0, rows // 2)
    stack = [start]
    sx, sy = start
    maze[sy][sx]["visited"] = True

    while stack:
        x, y = stack[-1]
        neighbours = []
        for direction, (dx, dy, opposite) in DIRECTIONS.items():
            nx, ny = x + dx, y + dy
            if 0 <= nx < cols and 0 <= ny < rows and not maze[ny][nx]["visited"]:
                neighbours.append((nx, ny, direction, opposite))
        if neighbours:
            nx, ny, direction, opposite = rng.choice(neighbours)
            maze[y][x]["walls"][direction] = False
            maze[ny][nx]["walls"][opposite] = False
            maze[ny][nx]["visited"] = True
            stack.append((nx, ny))
        else:
            stack.pop()

    # Entrance (west of the start cell) and exit (east of the finish cell)
    maze[start[1]][start[0]]["walls"]["W"] = False
    finish = (cols - 1, rows // 2)
    maze[finish[1]][finish[0]]["walls"]["E"] = False
    return maze


def start_cell(rows=None):
    rows = C.ROWS if rows is None else rows
    return (0, rows // 2)


def finish_cell(cols=None, rows=None):
    cols = C.COLS if cols is None else cols
    rows = C.ROWS if rows is None else rows
    return (cols - 1, rows // 2)


def cell_center_3d(col, row, height=0.0):
    """Convert a maze cell to a world-space point (handbook section 4)."""
    return np.array([col + 0.5, height, row + 0.5], dtype=float)


def get_available_neighbours(maze, cell, cols=None, rows=None):
    """Cells reachable through an open wall - reused for the birds' routing."""
    cols = C.COLS if cols is None else cols
    rows = C.ROWS if rows is None else rows
    x, y = cell
    out = []
    for direction, (dx, dy, _opposite) in DIRECTIONS.items():
        if not maze[y][x]["walls"][direction]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < cols and 0 <= ny < rows:
                out.append((nx, ny))
    return out


def collect_wall_runs(maze, cols=None, rows=None):
    """
    Emit wall runs (same strategy as the original draw_maze so that no wall is
    drawn twice):

        * every cell contributes its N wall and its W wall
        * only the last column contributes E walls
        * only the last row contributes S walls

    Consecutive runs on the same line are merged, which cuts the triangle count
    of the static maze by roughly a factor of three.

    Returns a list of dicts: {"axis": "x"|"z", "fixed": float, "start": float,
    "end": float}
    """
    cols = C.COLS if cols is None else cols
    rows = C.ROWS if rows is None else rows

    if cols < 0 or rows < 0:
        raise ValueError("negative maze size")

    runs = []

    # --- walls perpendicular to Z (run along X): N walls + last-row S walls
    for row in range(rows + 1):
        if row < rows:
            flags = [maze[row][col]["walls"]["N"] for col in range(cols)]
        else:
            flags = [maze[row - 1][col]["walls"]["S"] for col in range(cols)]
        col = 0
        while col < cols:
            if flags[col]:
                start = col
                while col + 1 < cols and flags[col + 1]:
                    col += 1
                runs.append({"axis": "x", "fixed": float(row),
                             "start": float(start), "end": float(col + 1)})
            col += 1

    # --- walls perpendicular to X (run along Z): W walls + last-column E walls
    for c in range(cols + 1):
        if c < cols:
            flags = [maze[r][c]["walls"]["W"] for r in range(rows)]
        else:
            flags = [maze[r][c - 1]["walls"]["E"] for r in range(rows)]
        row = 0
        while row < rows:
            if flags[row]:
                start = row
                while row + 1 < rows and flags[row + 1]:
                    row += 1
                runs.append({"axis": "z", "fixed": float(c),
                             "start": float(start), "end": float(row + 1)})
            row += 1

    return runs


def runs_to_boxes(runs):
    """
    Convert a wall run into the world-space box description used by both the
    renderer and the collision code: (centre(3), size(3), collider(4)).

    Thickness = 0.16 so the visual mesh and the collider footprint agree.
    """
    boxes = []
    half_t = C.WALL_T / 2.0
    for run in runs:
        if run["axis"] == "x":
            length = run["end"] - run["start"]
            centre = ((run["start"] + run["end"]) / 2.0,
                      C.WALL_H / 2.0,
                      run["fixed"])
            size = (length, C.WALL_H, C.WALL_T)
            collider = (run["start"], run["end"],
                        run["fixed"] - half_t, run["fixed"] + half_t)
        else:
            length = run["end"] - run["start"]
            centre = (run["fixed"],
                      C.WALL_H / 2.0,
                      (run["start"] + run["end"]) / 2.0)
            size = (C.WALL_T, C.WALL_H, length)
            collider = (run["fixed"] - half_t, run["fixed"] + half_t,
                        run["start"], run["end"])
        boxes.append({"centre": np.array(centre, dtype=float),
                      "size": np.array(size, dtype=float),
                      "collider": collider})
    return boxes


# --------------------------------------------------------------------------
def circle_hits_xz(px, pz, radius, box):
    """
    Circle (X/Z footprint) against an axis-aligned box (x0, x1, z0, z1).

    Closest point on the box to the circle centre; if the squared distance is
    smaller than r^2 the circles overlap.  Box thickness matches the 0.16 wall.
    """
    x0, x1, z0, z1 = box
    nearest_x = max(x0, min(px, x1))
    nearest_z = max(z0, min(pz, z1))
    dx = px - nearest_x
    dz = pz - nearest_z
    return dx * dx + dz * dz < radius * radius

"""
tools/fig_bird.py
=================
Screenshot of the "bird" hazard: the worm is teleported into the cell under
the first bird and the follow camera is used, so the bird is large in frame.

Run:  python tools\\fig_bird.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np
import pygame

import config as C
from camera import PRESET_FOLLOW
from main import App

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    app = App()
    app.set_preset(1)
    app.camera.apply_preset(PRESET_FOLLOW)

    bird = app.game.birds[0]
    cell = bird["target"]
    # stand two cells away from the bird so both are in frame
    app.game.pos = np.array([cell[0] + 0.5, C.BALL_RADIUS, cell[1] + 2.5])

    for _ in range(3):
        app.game.update(0.05, (0.0, -1.0))
        app.draw_scene()
        app.present(app.renderer.to_surface_array())
        from hud import draw_hud
        draw_hud(app, app.screen, app.game, app.camera, app.renderer)

    out = os.path.join(ROOT, "screenshots", "fig13_bird.png")
    pygame.image.save(app.screen, out)
    pygame.quit()
    print("written", out, "bird at", np.round(bird["pos"], 2))


if __name__ == "__main__":
    main()

"""
tools/record_demo.py
====================
Records a scripted 2-minute demonstration of the game without a window and
encodes it to MP4 with ffmpeg (through imageio-ffmpeg).

The recording walks the same code path as the real game: game.update ->
draw_scene -> present -> draw_hud, so every feature shown in the video is
produced by the same renderer the player uses.

Run:  python tools\\record_demo.py
Out:  screenshots\\demo.mp4   (1280x800, 10 fps, about 2 minutes)
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np
import pygame

import config as C
from camera import PRESET_ELEVATED, PRESET_SIDE, PRESET_FOLLOW
from main import App

FPS = 10
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "screenshots", "demo.mp4")


class Director:
    """A tiny timeline: every entry is (duration_s, setup_fn, keys)."""

    def __init__(self, app):
        self.app = app
        self.t = 0.0

    def step(self, dt, keys=(0.0, 0.0), jump=False):
        app = self.app
        app.game.update(dt, keys, jump_pressed=jump)
        app.draw_scene()
        rgb = app.renderer.to_surface_array()
        surface, rect = app.present(rgb)
        if app.renderer.debug_wireframe:
            scale = rect[2] / app.fb_w
            for a, b in app.renderer.wire_segments:
                pygame.draw.line(surface, (255, 255, 255),
                                 (a[0] * scale, a[1] * scale),
                                 (b[0] * scale, b[1] * scale), 1)
        app.fps = FPS
        app.frame_ms = app.render_ms
        from hud import draw_hud
        draw_hud(app, app.screen, app.game, app.camera, app.renderer)
        pygame.display.flip()
        return pygame.image.tostring(app.screen, "RGB")


def main():
    app = App()
    app.set_preset(0)                      # 480x300 FAST keeps the recording quick
    app.camera.apply_preset(PRESET_FOLLOW)
    d = Director(app)
    g = app.game

    ffmpeg = None
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    if not ffmpeg:
        raise SystemExit("ffmpeg not available - pip install imageio-ffmpeg")

    proc = subprocess.Popen(
        [ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{app.window_w}x{app.window_h}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", OUT],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def shots(seconds, keys=(0.0, 0.0), jump_every=None):
        n = int(round(seconds * FPS))
        for i in range(n):
            jump = jump_every is not None and (i % jump_every == 0)
            frame = d.step(1.0 / FPS, keys, jump)
            proc.stdin.write(frame)

    # 1. intro: follow camera, walking forward -----------------------------
    g.set_message("Worm's Garden Adventure 3D - software renderer")
    shots(6, (0.0, -1.0))
    g.set_message("W A S D move, SPACE jump")
    shots(6, (-1.0, 0.0))
    shots(6, (0.0, -1.0), jump_every=12)

    # 2. elevated camera ---------------------------------------------------
    app.camera.apply_preset(PRESET_ELEVATED)
    g.set_message("1 - elevated camera preset")
    shots(8, (0.0, -1.0))

    # 3. orthographic projection ------------------------------------------
    app.camera.toggle_projection()
    g.set_message("P - orthographic projection")
    shots(8)
    app.camera.toggle_projection()
    g.set_message("P - back to perspective")
    shots(6)

    # 4. side camera + orbit ----------------------------------------------
    app.camera.apply_preset(PRESET_SIDE)
    g.set_message("2 - side camera, Q / E orbit")
    for _ in range(8):
        app.camera.orbit(-6.0)
    shots(14, (0.0, -1.0))

    # 5. fog on / off (shown on the wide side view, where the depth is visible)
    app.camera.apply_preset(PRESET_SIDE)
    app.renderer.fog_enabled = False
    g.set_message("G - fog OFF")
    shots(9)
    app.renderer.fog_enabled = True
    g.set_message("G - fog ON (Part B)")
    shots(9)

    # 6. bilinear filtering on a grazing floor
    app.camera.zoom(0.75)
    app.renderer.bilinear = False
    g.set_message("T - nearest sampling")
    shots(6)
    app.renderer.bilinear = True
    g.set_message("T - bilinear sampling (Part B)")
    shots(8)
    app.renderer.bilinear = False
    app.camera.apply_preset(PRESET_FOLLOW)

    # 7. debug views -------------------------------------------------------
    app.renderer.debug_wireframe = True
    g.set_message("F1 - wireframe: every rasterised triangle")
    shots(7)
    app.renderer.debug_wireframe = False

    app.renderer.debug_normals = True
    g.set_message("F2 - face normals as RGB")
    shots(7)
    app.renderer.debug_normals = False

    app.renderer.debug_depth = True
    g.set_message("F3 - depth buffer")
    for i in range(int(7 * FPS)):
        app.game.update(1.0 / FPS, (0.0, -1.0))
        app.draw_scene()
        rgb = app.renderer.depth_image()
        app.present(rgb)
        from hud import draw_hud
        draw_hud(app, app.screen, app.game, app.camera, app.renderer)
        pygame.display.flip()
        proc.stdin.write(pygame.image.tostring(app.screen, "RGB"))
    app.renderer.debug_depth = False

    # 8. resolution presets -------------------------------------------------
    for idx in (1, 2, 0):
        app.set_preset(idx)
        g.set_message(f"F5 - resolution {C.RESOLUTION_PRESETS[idx][0]}")
        shots(4, (0.0, -1.0))

    # 9. finale: fireworks + walking to the flag ---------------------------
    g.set_message("Thanks for watching - collecting apples and the flag")
    for i in range(int(12 * FPS)):
        if i % (3 * FPS) == 0:
            g.particles.firework(g.pos + np.array([0.0, 0.4, 0.0]))
        proc.stdin.write(d.step(1.0 / FPS, (0.0, -1.0)))

    proc.stdin.close()
    proc.wait()
    pygame.quit()
    print("video written to", OUT, os.path.getsize(OUT) // 1024, "kB")


if __name__ == "__main__":
    main()

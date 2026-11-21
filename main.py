"""
main.py
=======
Entry point: window, input, game loop, framebuffer presentation and HUD.

Controls
    WASD / arrows   move (X/Z world plane)
    SPACE           jump (real vertical physics)
    P               perspective <-> orthographic
    1 / 2 / 3       elevated / side / follow camera presets
    Q / E           orbit the camera left / right
    mouse wheel     zoom
    T               bilinear texture filtering on/off  (Part B extension)
    G               fog on/off                        (Part B extension)
    F1              wireframe overlay
    F2              face-normal view
    F3              depth-buffer view
    F5              cycle render resolution presets
    F12             save a screenshot
    R               restart the run
    ESC             quit
"""

import math
import os
import sys
import time

import numpy as np
import pygame

import config as C
import maze as M
import mesh as MSH
import textures as T
from camera import Camera, PRESET_ELEVATED, PRESET_SIDE, PRESET_FOLLOW, PRESET_NAMES
from game import Game
from raster import Renderer
from hud import draw_hud
from scene import draw_scene as draw_scene_3d

HERE = os.path.dirname(os.path.abspath(__file__))
SHOT_DIR = os.path.join(HERE, "screenshots")


def window_to_render(mx, my, rect):
    """Map a window mouse position to framebuffer pixel coordinates."""
    x0, y0, w, h = rect
    if w <= 0 or h <= 0:
        return None
    rx = (mx - x0) / w
    ry = (my - y0) / h
    if not (0.0 <= rx <= 1.0 and 0.0 <= ry <= 1.0):
        return None
    return rx, ry


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Worm's Garden Adventure 3D")
        self.window_w, self.window_h = C.WINDOW_W, C.WINDOW_H
        self.screen = pygame.display.set_mode((self.window_w, self.window_h), pygame.RESIZABLE)

        self.preset_index = C.DEFAULT_PRESET
        self.fb_w, self.fb_h = C.RESOLUTION_PRESETS[self.preset_index][1:]

        self.game = Game(seed=C.SEED)
        self.camera = Camera(self.game.cols, self.game.rows)
        self.camera.apply_preset(PRESET_FOLLOW)
        self.renderer = Renderer(self.fb_w, self.fb_h)

        self.clock = pygame.time.Clock()
        self.font = self._load_font(20)
        self.small = self._load_font(16)
        self.big = self._load_font(26, bold=True)

        self.running = True
        self.show_help = True
        self.render_ms = 0.0
        self.fps = 0.0
        self.frame_ms = 0.0
        self.rect = (0, 0, self.window_w, self.window_h)
        self.shot_index = 0
        self.jump_requested = False
        os.makedirs(SHOT_DIR, exist_ok=True)

    # ------------------------------------------------------------ helpers ----
    @staticmethod
    def _load_font(size, bold=False):
        """Monospace font with a graceful fallback to pygame's default font."""
        try:
            return pygame.font.SysFont("Consolas", size, bold=bold)
        except Exception:
            return pygame.font.Font(None, size)

    def set_preset(self, index):
        index %= len(C.RESOLUTION_PRESETS)
        self.preset_index = index
        name, w, h = C.RESOLUTION_PRESETS[index]
        self.fb_w, self.fb_h = w, h
        self.renderer.resize(w, h)

    def present(self, rgb):
        frame = pygame.image.frombuffer(np.ascontiguousarray(rgb).tobytes(),
                                        (self.fb_w, self.fb_h), "RGB")
        scale = min(self.window_w / self.fb_w, self.window_h / self.fb_h)
        dw = max(1, int(round(self.fb_w * scale)))
        dh = max(1, int(round(self.fb_h * scale)))
        dx = (self.window_w - dw) // 2
        dy = (self.window_h - dh) // 2
        self.screen.fill((0, 0, 0))
        scaled = pygame.transform.smoothscale(frame, (dw, dh))
        self.screen.blit(scaled, (dx, dy))
        self.rect = (dx, dy, dw, dh)
        return scaled, self.rect

    def save_shot(self):
        name = os.path.join(SHOT_DIR, f"manual_{self.shot_index:02d}.png")
        pygame.image.save(self.screen, name)
        self.shot_index += 1
        self.game.set_message(f"Saved {os.path.basename(name)}")

    def screen_to_ground(self, mx, my):
        """Mouse pixel -> ray -> intersection with the ground plane Y = 0."""
        mapped = window_to_render(mx, my, self.rect)
        if mapped is None:
            return None
        rx, ry = mapped
        px = rx * self.fb_w
        py = ry * self.fb_h
        right, up, forward = self.camera.basis
        if self.camera.perspective:
            dx = (px - self.fb_w / 2.0) / self.camera.focal_px()
            dy = -(py - self.fb_h / 2.0) / self.camera.focal_px()
        else:
            dx = (px - self.fb_w / 2.0) / self.camera.ortho_pixels_per_unit()
            dy = -(py - self.fb_h / 2.0) / self.camera.ortho_pixels_per_unit()
        direction = right * dx + up * dy + forward
        direction = direction / np.linalg.norm(direction)
        eye = self.camera.eye
        if abs(direction[1]) < 1e-6:
            return None
        t = -eye[1] / direction[1]
        if t <= 0:
            return None
        point = eye + direction * t
        return np.array([np.clip(point[0], 0.0, self.game.cols),
                         max(0.05, point[1]),
                         np.clip(point[2], 0.0, self.game.rows)])

    # -------------------------------------------------------------- draw -----
    def draw_scene(self):
        g = self.game
        t0 = time.perf_counter()
        draw_scene_3d(g, self.camera, self.renderer, self.fb_w, self.fb_h,
                      apply_fog=self.renderer.fog_enabled)
        self.render_ms = (time.perf_counter() - t0) * 1000.0

    # ------------------------------------------------------------- events ----
    def handle_events(self):
        g = self.game
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.VIDEORESIZE:
                self.window_w = max(640, event.w)
                self.window_h = max(400, event.h)
                self.screen = pygame.display.set_mode((self.window_w, self.window_h),
                                                      pygame.RESIZABLE)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_p:
                    self.camera.toggle_projection()
                elif event.key == pygame.K_1:
                    self.camera.apply_preset(PRESET_ELEVATED)
                elif event.key == pygame.K_2:
                    self.camera.apply_preset(PRESET_SIDE)
                elif event.key == pygame.K_3:
                    self.camera.apply_preset(PRESET_FOLLOW)
                elif event.key == pygame.K_q:
                    self.camera.orbit(-6.0)
                elif event.key == pygame.K_e:
                    self.camera.orbit(6.0)
                elif event.key == pygame.K_SPACE:
                    self.jump_requested = True
                elif event.key == pygame.K_r:
                    g.restart()
                    g.set_message("Restarted")
                elif event.key == pygame.K_f:
                    g.particles.firework(g.pos + np.array([0.0, 0.35, 0.0]))
                elif event.key == pygame.K_t:
                    self.renderer.bilinear = not self.renderer.bilinear
                    g.set_message("Bilinear filtering " +
                                  ("ON" if self.renderer.bilinear else "OFF"))
                elif event.key == pygame.K_g:
                    self.renderer.fog_enabled = not self.renderer.fog_enabled
                    g.set_message("Fog " +
                                  ("ON" if self.renderer.fog_enabled else "OFF"))
                elif event.key == pygame.K_F1:
                    self.renderer.debug_wireframe = not self.renderer.debug_wireframe
                elif event.key == pygame.K_F2:
                    self.renderer.debug_normals = not self.renderer.debug_normals
                elif event.key == pygame.K_F3:
                    self.renderer.debug_depth = not self.renderer.debug_depth
                elif event.key == pygame.K_F5:
                    self.set_preset(self.preset_index + 1)
                    g.set_message(f"Resolution {C.RESOLUTION_PRESETS[self.preset_index][0]}")
                elif event.key == pygame.K_F12:
                    self.save_shot()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    p = self.screen_to_ground(*event.pos)
                    if p is not None:
                        g.particles.firework(p)
                elif event.button == 4:
                    self.camera.zoom(0.9)
                elif event.button == 5:
                    self.camera.zoom(1.1)

            elif event.type == pygame.MOUSEWHEEL:
                self.camera.zoom(0.9 if event.y > 0 else 1.1)

    # --------------------------------------------------------------- loop ----
    def run(self):
        frames = 0
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, 0.05)
            self.handle_events()

            keys = pygame.key.get_pressed()
            dx = float(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - \
                 float(keys[pygame.K_a] or keys[pygame.K_LEFT])
            dz = float(keys[pygame.K_s] or keys[pygame.K_DOWN]) - \
                 float(keys[pygame.K_w] or keys[pygame.K_UP])

            # optional scripted input for automated smoke tests
            scripted = getattr(self, "scripted_keys", "")
            if scripted:
                dx = 1.0 if "d" in scripted else (-1.0 if "a" in scripted else 0.0)
                dz = 1.0 if "s" in scripted else (-1.0 if "w" in scripted else 0.0)
            if not self.running:
                break

            self.game.update(dt, (dx, dz), jump_pressed=self.jump_requested)
            self.jump_requested = False
            self.draw_scene()

            if self.renderer.debug_depth:
                rgb = self.renderer.depth_image()
            else:
                rgb = self.renderer.to_surface_array()

            surface, rect = self.present(rgb)

            if self.renderer.debug_wireframe:
                scale = rect[2] / self.fb_w
                for a, b in self.renderer.wire_segments:
                    pygame.draw.line(surface, (255, 255, 255),
                                     (a[0] * scale, a[1] * scale),
                                     (b[0] * scale, b[1] * scale), 1)

            draw_hud(self, self.screen, self.game, self.camera, self.renderer)
            pygame.display.flip()
            self.fps = 0.9 * self.fps + 0.1 * (1.0 / max(dt, 1e-4))
            self.frame_ms = self.render_ms

            frames += 1
            limit = getattr(self, "scripted_frames", 0)
            if limit and frames >= limit:
                shot = getattr(self, "scripted_shot", "")
                if shot:
                    pygame.image.save(self.screen, shot)
                self.running = False

        pygame.quit()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Worm's Garden Adventure 3D")
    parser.add_argument("--frames", type=int, default=0,
                        help="run N frames then quit (used for automated tests)")
    parser.add_argument("--shot", type=str, default="",
                        help="save the window to this PNG before quitting")
    parser.add_argument("--preset", type=int, default=-1,
                        help="0 FAST, 1 BALANCED, 2 HIGH, 3 NATIVE")
    parser.add_argument("--walk", type=str, default="",
                        help="hold these keys for the first frames, e.g. 'w'")
    args = parser.parse_args()

    app = App()
    if args.preset >= 0:
        app.set_preset(args.preset)
    if args.frames:
        app.scripted_frames = args.frames
        app.scripted_shot = args.shot
        app.scripted_keys = args.walk
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())

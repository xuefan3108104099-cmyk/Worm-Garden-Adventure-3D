"""
hud.py
======
Screen-space HUD drawn with Pygame *after* the 3D framebuffer has been
presented, so text never rotates with the camera.
"""

import pygame

import config as C


def _text(screen, font, text, pos, color, shadow=True):
    if shadow:
        shadow_img = font.render(text, True, (0, 0, 0))
        screen.blit(shadow_img, (pos[0] + 1, pos[1] + 1))
    img = font.render(text, True, color)
    screen.blit(img, pos)
    return img.get_width()


def draw_hud(app, screen, game, camera, renderer):
    w, h = app.window_w, app.window_h

    # ---------------------------------------------------------- top bar -----
    bar = pygame.Surface((w, 62), pygame.SRCALPHA)
    bar.fill((12, 38, 22, 205))
    screen.blit(bar, (0, 0))
    pygame.draw.line(screen, (90, 168, 96), (0, 62), (w, 62), 2)

    _text(screen, app.font, f"LEVEL: {game.level}", (16, 18), (255, 255, 255))
    _text(screen, app.font, f"SCORE: {game.score}", (190, 18), (255, 205, 60))
    _text(screen, app.font,
          f"APPLES: {game.collected}/{C.TOTAL_APPLES}", (390, 18), (255, 130, 130))
    minutes = int(game.elapsed() // 60)
    seconds = int(game.elapsed() % 60)
    _text(screen, app.font, f"TIME: {minutes:02d}:{seconds:02d}", (600, 18),
          (235, 235, 235))

    preset = C.RESOLUTION_PRESETS[app.preset_index][0]
    _text(screen, app.small,
          f"FPS {app.fps:5.1f} | {app.fb_w}x{app.fb_h} {preset} | "
          f"tris {renderer.triangles_drawn} | {app.render_ms:6.2f} ms",
          (w - 430, 22), (170, 230, 180))

    # ------------------------------------------------------------ message ---
    if game.message:
        img = app.font.render(game.message, True, (255, 240, 160))
        pad = 10
        box = pygame.Surface((img.get_width() + 2 * pad, img.get_height() + 2 * pad),
                             pygame.SRCALPHA)
        box.fill((0, 0, 0, 150))
        screen.blit(box, (w // 2 - box.get_width() // 2, 76))
        screen.blit(img, (w // 2 - img.get_width() // 2, 76 + pad))

    # ---------------------------------------------------------- bottom bar --
    inst = ("WASD move   SPACE jump   P projection   1/2/3 camera   "
            "Q/E orbit   wheel zoom   T bilinear   G fog   F1 wire  F3 depth   "
            "F5 quality   R restart")
    _text(screen, app.small, inst, (14, h - 26), (215, 235, 215))

    # ------------------------------------------------------- debug panel ----
    lines = [
        camera.info(),
        f"follow target=({camera.target[0]:.1f},{camera.target[2]:.1f})  "
        f"worm=({game.pos[0]:.2f},{game.pos[1]:.2f},{game.pos[2]:.2f})  "
        f"grounded={game.grounded}",
        f"fog={'on' if renderer.fog_enabled else 'off'}  "
        f"bilinear={'on' if renderer.bilinear else 'off'}  "
        f"culled={renderer.triangles_culled}  clipped={renderer.triangles_clipped}",
    ]
    y = h - 120
    for line in lines:
        _text(screen, app.small, line, (14, y), (200, 220, 235))
        y += 19

    # ------------------------------------------------------------- help -----
    if app.show_help:
        help_lines = [
            "Worm's Garden Adventure 3D  -  software renderer",
            "Collect 4 apples to unlock the finish flag.",
            "Q/E orbit, wheel zoom, P perspective/ortho.",
        ]
        y = 84
        for line in help_lines:
            _text(screen, app.small, line, (w - 330, y), (220, 240, 220))
            y += 18

"""
scene.py
========
Submits the whole scene to the renderer.  Shared by the interactive game
(main.py) and by the headless screenshot tool.

Draw order: ground, hazards, walls (chunk culled), markers, collectibles,
birds, worm, particles.  The floor is drawn first and the walls afterwards be-
cause the walls are almost always in front of the floor, and the renderer's
coarse z-test can then reject hidden floor tiles cheaply.
"""

import config as C
import mesh as MSH
import textures as T
from frustum import Frustum


def draw_scene(game, camera, renderer, width, height, apply_fog=True):
    camera.update(game.pos, width, height)
    renderer.set_camera(camera)

    renderer.fog_enabled = apply_fog
    renderer.fog_start = max(2.6, camera.distance * 0.28)
    renderer.fog_end = max(9.0, camera.distance * 1.7)

    r = renderer
    g = game
    frustum = Frustum.from_camera(camera, width, height)

    r.clear()

    # ground first (textured tiles, UVs in world units)
    r.draw_mesh(g.floor_mesh, T.get("grass"), tint=(0.78, 0.88, 0.76),
                cull=False, fog=False)
    # hazards
    r.draw_mesh(g.water_meshes(), T.get("water"), tint=(1.0, 1.0, 1.0),
                cull=False, fog=False)

    # static maze: only the 4x4-cell blocks inside the frustum are submitted
    r.chunks_total = len(g.wall_chunks)
    r.chunks_drawn = 0
    visible_chunks = [ch for ch in g.wall_chunks
                      if frustum.aabb_visible(ch["centre"], ch["half"])]
    # front-to-back: hidden triangles are rejected early by the coarse z-test
    visible_chunks.sort(key=lambda ch: float(
        (ch["centre"] - camera.eye) @ camera.basis[2]))
    for chunk in visible_chunks:
        r.chunks_drawn += 1
        r.draw_mesh(chunk["mesh"], T.get("stone"), tint=(0.95, 0.96, 1.0),
                    fog=apply_fog)

    # markers
    r.draw_mesh(g.flag_poles(), T.get("wood"), tint=(0.9, 0.85, 0.75))
    r.draw_mesh(g.flag_start(), None, tint=(0.16, 0.86, 0.30), cull=False)
    r.draw_mesh(g.flag_finish(), T.get("checker"), tint=(1.0, 1.0, 1.0), cull=False)
    # collectibles
    r.draw_mesh(g.apple_meshes("apple"), T.get("apple"), tint=(1.0, 1.0, 1.0))
    r.draw_mesh(g.apple_meshes("gold"), T.get("gold"), tint=(1.0, 1.0, 1.0))
    r.draw_mesh(g.apple_stems(), T.get("wood"), tint=(0.9, 0.85, 0.7))
    # birds
    r.draw_mesh(g.bird_meshes(), T.get("feather"), tint=(0.8, 0.8, 0.95))
    r.draw_mesh(g.bird_wings(), T.get("feather"), tint=(0.7, 0.7, 0.9), cull=False)
    # worm
    r.draw_mesh(g.worm_mesh(), T.get("worm"), tint=(1.0, 1.0, 1.0))
    eye_l, eye_r = g.worm_eye_positions()
    eyes = MSH.merge_meshes([MSH.sphere(eye_l, 0.045, segments=5, rings=2),
                             MSH.sphere(eye_r, 0.045, segments=5, rings=2)])
    r.draw_mesh(eyes, None, tint=(1.0, 1.0, 1.0))
    # particles last (alpha billboards, depth tested)
    g.particles.draw(r)

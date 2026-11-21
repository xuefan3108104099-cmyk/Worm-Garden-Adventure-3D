"""
particles.py
============
3D particle system: sparks from the worm's trail and mouse-click fireworks.

Each particle keeps the same fields as the original 2D game (pos, vel, life,
max_life, size, color) but pos/vel are 3-component world vectors.  Particles are
drawn as camera-facing billboards and depth-tested, so they disappear behind
walls.
"""

import math
import random

import numpy as np

import config as C


class ParticleSystem:
    def __init__(self, rng=None):
        self.rng = rng or random.Random(4)
        self.particles = []

    def clear(self):
        self.particles.clear()

    def _add(self, p):
        self.particles.append(p)
        if len(self.particles) > C.MAX_PARTICLES:
            del self.particles[:len(self.particles) - C.MAX_PARTICLES]

    def spark(self, pos, direction=(0, 0, 0)):
        """Small orange spark emitted while the worm walks."""
        ang = self.rng.uniform(0, 2 * math.pi)
        speed = self.rng.uniform(0.6, 3.0)
        vel = np.array([math.cos(ang) * speed,
                        self.rng.uniform(0.4, 1.6),
                        math.sin(ang) * speed])
        vel += np.asarray(direction) * 0.8
        life = self.rng.uniform(0.35, 0.9)
        self._add({
            "pos": np.asarray(pos, dtype=float).copy(),
            "vel": vel,
            "life": life,
            "max_life": life,
            "size": self.rng.uniform(0.012, 0.03),
            "color": (1.0, 0.72, 0.18),
        })

    def firework(self, pos, colors=((0.2, 0.55, 1.0), (1.0, 0.3, 0.6), (0.65, 0.28, 1.0))):
        """Radial burst used for the mouse-click celebration."""
        for _ in range(self.rng.randint(70, 110)):
            ang = self.rng.uniform(0, 2 * math.pi)
            elev = self.rng.uniform(-0.3, 1.0)
            speed = self.rng.uniform(2.0, 7.0)
            vel = np.array([math.cos(ang) * speed * 0.8,
                            elev * speed,
                            math.sin(ang) * speed * 0.8])
            life = self.rng.uniform(0.8, 1.6)
            self._add({
                "pos": np.asarray(pos, dtype=float).copy(),
                "vel": vel,
                "life": life,
                "max_life": life,
                "size": self.rng.uniform(0.015, 0.04),
                "color": self.rng.choice(colors),
            })

    def update(self, dt):
        alive = []
        for p in self.particles:
            p["vel"][1] -= 4.0 * dt                 # light gravity
            p["pos"] += p["vel"] * dt
            p["vel"] *= 0.94 ** (dt * 60.0)
            p["life"] -= dt
            if p["pos"][1] < 0.01:                  # stay above the floor
                p["pos"][1] = 0.01
                p["vel"][1] *= -0.25
            if p["life"] > 0:
                alive.append(p)
        self.particles[:] = alive

    def draw(self, renderer):
        for p in self.particles:
            fade = max(0.0, p["life"] / p["max_life"])
            renderer.draw_billboard(p["pos"], p["size"] * (0.4 + 0.6 * fade),
                                    p["color"], alpha=fade)

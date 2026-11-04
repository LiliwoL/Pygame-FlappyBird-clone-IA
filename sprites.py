"""Procedurally generate custom sprites and sound effects.

The custom art is drawn with pygame drawing primitives and saved as PNG/WAV
files in the assets directory on first run. The game then loads these files,
so they can be replaced with hand-authored art if desired.
"""

import os
import math
import struct
import wave

import pygame

from settings import (
    ASSETS_DIR, COLORS,
    BIRD_SPRITE, PIPE_SPRITE, PIPE_RIM_SPRITE,
    BACKGROUND_SPRITE, GROUND_SPRITE, CLOUD_SPRITE,
    FLAP_SOUND_FILE, POINT_SOUND_FILE, HIT_SOUND_FILE, PIPE_WIDTH,
    WIDTH, HEIGHT, SKY_TOP, SKY_BOTTOM,
)


def _ensure_assets_dir():
    os.makedirs(ASSETS_DIR, exist_ok=True)


# --------------------------------------------------------------------------- #
# Drawing helpers
# --------------------------------------------------------------------------- #

def _rounded_rect(surface, color, rect, radius):
    """Draw a filled rectangle with rounded corners."""
    x, y, w, h = rect
    r = min(radius, w // 2, h // 2)
    pygame.draw.rect(surface, color, (x + r, y, w - 2 * r, h))
    pygame.draw.rect(surface, color, (x, y + r, w, h - 2 * r))
    pygame.draw.circle(surface, color, (x + r, y + r), r)
    pygame.draw.circle(surface, color, (x + w - r, y + r), r)
    pygame.draw.circle(surface, color, (x + r, y + h - r), r)
    pygame.draw.circle(surface, color, (x + w - r, y + h - r), r)


def _flare(surface, color, center, angle, length, spread):
    """Draw a short line burst used for the background sun rays."""
    rad = math.radians(angle)
    ex = center[0] + math.cos(rad) * length
    ey = center[1] + math.sin(rad) * length
    rad2 = math.radians(angle + spread)
    ex2 = center[0] + math.cos(rad2) * length
    ey2 = center[1] + math.sin(rad2) * length
    pygame.draw.line(surface, color, center, (ex, ey), 3)
    pygame.draw.line(surface, color, center, (ex2, ey2), 2)


# --------------------------------------------------------------------------- #
# Sprites
# --------------------------------------------------------------------------- #

def create_background():
    """Vertical sky gradient, sun and a distant hill line."""
    surf = pygame.Surface((WIDTH, HEIGHT))
    top, bottom = SKY_TOP, SKY_BOTTOM
    for y in range(HEIGHT):
        t = y / max(HEIGHT - 1, 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        pygame.draw.line(surf, color, (0, y), (WIDTH, y))

    # Sun
    sun = (255, 245, 200)
    sun_cx, sun_cy = WIDTH - 70, 120
    for i in range(12):
        _flare(surf, (255, 240, 190, 0), (sun_cx, sun_cy), i * 30, 46, 12)
    pygame.draw.circle(surf, (255, 236, 170), (sun_cx, sun_cy), 30)
    pygame.draw.circle(surf, sun, (sun_cx, sun_cy), 26)

    # Distant hills (soft blue-green, behind the foreground ground)
    hill = (160, 214, 180)
    hill_dark = (140, 198, 165)
    points = []
    for x in range(0, WIDTH + 1, 12):
        hills = 40 * math.sin(x / 95) + 22 * math.sin(x / 47 + 1.3)
        points.append((x, 420 - hills))
    pygame.draw.polygon(surf, hill, points + [(WIDTH, HEIGHT), (0, HEIGHT)])
    ridge = []
    for x in range(0, WIDTH + 1, 12):
        hills = 40 * math.sin(x / 95 + 2.0) + 22 * math.sin(x / 47 + 2.6)
        ridge.append((x, 470 - hills))
    pygame.draw.polygon(surf, hill_dark, ridge + [(WIDTH, HEIGHT), (0, HEIGHT)])
    return surf


def create_cloud():
    """A fluffy white cloud sprite (with alpha)."""
    surf = pygame.Surface((150, 90), pygame.SRCALPHA)
    base_color = (255, 255, 255, 225)
    shadow_color = (235, 240, 245, 200)
    puffs = [(30, 58, 26), (58, 42, 30), (88, 42, 34), (116, 56, 26), (73, 58, 32)]
    for cx, cy, r in puffs:
        pygame.draw.circle(surf, shadow_color, (cx, cy + 6), r)
        pygame.draw.circle(surf, base_color, (cx, cy), r)
    return surf


def create_ground():
    """Scrolling ground strip: dirt base with grass top and texture."""
    surf = pygame.Surface((WIDTH, 110), pygame.SRCALPHA)
    dirt = COLORS["ground_dirt"]
    grass = COLORS["ground_grass"]
    dark_grass = COLORS["ground_dark_grass"]
    # dirt
    surf.fill(dirt)
    # grass layer
    pygame.draw.rect(surf, grass, (0, 0, WIDTH, 18))
    pygame.draw.rect(surf, dark_grass, (0, 14, WIDTH, 6))
    # dirt speckles
    for i in range(90):
        x = (i * 37) % WIDTH
        y = 30 + (i * 53) % 70
        shade = 15 if i % 3 == 0 else -12
        c = tuple(max(0, min(255, v + shade)) for v in dirt)
        pygame.draw.rect(surf, c, (x, y, 6, 4))
    # grass tufts
    for i in range(0, WIDTH, 26):
        pygame.draw.line(surf, dark_grass,
                         (i + 8, 18), (i + 8, 26), 3)
        pygame.draw.line(surf, grass,
                         (i + 14, 18), (i + 14, 25), 3)
    return surf


def create_pipe():
    """Body of a pipe column (green with vertical shading)."""
    body, _ = create_pipe_capsule()
    return body


def _pipe_make(width, height):
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    base = COLORS["pipe"]
    edge = COLORS["pipe_edge"]
    dark = COLORS["pipe_dark"]
    third = width // 3
    # vertical bands for a cylindrical look
    for x in range(width):
        if x < third:
            c = tuple(min(255, int(v * 1.06)) for v in edge)
        elif x < width - third:
            c = base
        else:
            c = tuple(int(v * 0.82) for v in dark)
        pygame.draw.line(surf, c, (x, 0), (x, height))
    return surf


def create_pipe_capsule():
    """Return (body_surface, rim_surface)."""
    body = _pipe_make(PIPE_WIDTH, 960)
    # slightly wider rim block
    rim_w, rim_h = PIPE_WIDTH + 8, 30
    rim = _pipe_make(rim_w, rim_h)
    return body, rim


def create_bird():
    """The player character: a rounded bird with wing, tail, eye and beak."""
    size = 64
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    body = COLORS["bird_body"]
    outline = COLORS["bird_outline"]
    wing = COLORS["bird_wing"]
    beak = COLORS["bird_beak"]
    beak_outline = COLORS["bird_beak_outline"]
    cx, cy = size // 2, size // 2

    # tail feathers
    pygame.draw.polygon(surf, body,
                        [(18, 26), (6, 22), (14, 30), (4, 34), (18, 38)])
    # body (circle, slightly flattened)
    pygame.draw.circle(surf, outline, (cx, cy), 24)
    pygame.draw.ellipse(surf, body, (cx - 22, cy - 20, 44, 40))
    # belly highlight
    pygame.draw.ellipse(surf, (255, 238, 150), (cx - 6, cy + 2, 20, 14))
    # wing
    pygame.draw.ellipse(surf, outline, (cx - 14, cy - 8, 24, 24))
    pygame.draw.ellipse(surf, wing, (cx - 12, cy - 6, 20, 20))
    # beak
    pygame.draw.polygon(surf, beak_outline,
                        [(cx + 16, cy - 6), (cx + 32, cy), (cx + 18, cy + 6)])
    pygame.draw.polygon(surf, beak,
                        [(cx + 16, cy - 5), (cx + 30, cy), (cx + 17, cy + 5)])
    # eye
    pygame.draw.circle(surf, COLORS["bird_eye"], (cx + 10, cy - 12), 8)
    pygame.draw.circle(surf, COLORS["bird_pupil"], (cx + 13, cy - 12), 3)
    return surf


# --------------------------------------------------------------------------- #
# Sound effects (tiny synthesized tones)
# --------------------------------------------------------------------------- #

def _write_wav(path, frames, rate=22050):
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(frames)


def _tone(freq, ms, decay=0.35, vol=0.2, square=False):
    rate = 22050
    n = int(rate * ms / 1000)
    frames = bytearray()
    for i in range(n):
        t = i / rate
        env = math.exp(-decay * t)
        if square:
            v = math.copysign(1.0, math.sin(2 * math.pi * freq * t))
            sample = v * vol * env
        else:
            sample = math.sin(2 * math.pi * freq * t) * vol * env
        frames += struct.pack("<h", int(max(-1, min(1, sample)) * 32000))
    return bytes(frames)


def create_sounds():
    _write_wav(FLAP_SOUND_FILE, _tone(520, 90, 22, 0.22, square=True))
    point = _tone(880, 70, 18, 0.2) + _tone(1320, 90, 16, 0.2)
    _write_wav(POINT_SOUND_FILE, point)
    hit = _tone(180, 150, 10, 0.3, square=True) + _tone(90, 200, 6, 0.25, square=True)
    _write_wav(HIT_SOUND_FILE, hit)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def generate_all(force=False):
    """Create all assets as files. Returns True if anything was written."""
    _ensure_assets_dir()
    wrote = False
    pygame.display.init()
    pygame.display.set_mode((1, 1))

    def save(surf, path):
        nonlocal wrote
        if force or not os.path.exists(path):
            pygame.image.save(surf, path)
            wrote = True

    save(create_background(), BACKGROUND_SPRITE)
    save(create_cloud(), CLOUD_SPRITE)
    save(create_ground(), GROUND_SPRITE)
    body, rim = create_pipe_capsule()
    save(body, PIPE_SPRITE)
    save(rim, PIPE_RIM_SPRITE)
    save(create_bird(), BIRD_SPRITE)

    if force or not all(os.path.exists(p) for p in
                        (FLAP_SOUND_FILE, POINT_SOUND_FILE, HIT_SOUND_FILE)):
        create_sounds()
        wrote = True
    return wrote


if __name__ == "__main__":
    print("Generating assets...")
    generate_all(force=True)
    print("Done.")

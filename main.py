"""Flappy Bird Clone - a playable pygame implementation.

Custom sprites are procedurally generated (see sprites.py) and saved under
assets/. Run `python main.py` to play. Uses LEFT click / Space / Up to flap.
"""

import asyncio
import math
import os

import pygame

import settings as S
from sprites import generate_all

# State identifiers
STATE_READY = "ready"
STATE_PLAYING = "playing"
STATE_GAMEOVER = "gameover"

GROUND_HEIGHT = 110          # height of the scrolling ground strip
GROUND_TOP = S.HEIGHT - GROUND_HEIGHT

BEST_SCORE_FILE = os.path.join(os.path.dirname(__file__), "best_score.txt")


class Pipe:
    """A single vertical pipe pair (top + bottom) with a scoring gap."""

    def __init__(self, x, gap_center, gap, body, rim):
        self.x = x
        self.top_height = gap_center - gap // 2
        self.bottom_y = gap_center + gap // 2
        self.passed = False
        self.body = body
        self.rim = rim
        self.speed = S.PIPE_SPEED

    @property
    def rect_top(self):
        return pygame.Rect(self.x, self.top_height - 960,
                           S.PIPE_WIDTH, 960)

    @property
    def rect_bottom(self):
        return pygame.Rect(self.x, self.bottom_y, S.PIPE_WIDTH, 960)

    def update(self):
        self.x -= self.speed

    def offscreen(self):
        return self.x < -S.PIPE_WIDTH - 80

    def draw(self, screen):
        screen.blit(self.body, (self.x, self.top_height - 960))
        screen.blit(self.rim, (self.x - 4, self.top_height - 30))
        screen.blit(self.body, (self.x, self.bottom_y))
        screen.blit(self.rim, (self.x - 4, self.bottom_y))


class Cloud:
    def __init__(self, x, y, scale):
        self.x = x
        self.y = y
        self.scale = scale
        w, h = CLOUD_W, CLOUD_H
        self.w = int(w * scale)
        self.h = int(h * scale)
        self.speed = 0.4 * scale

    def update(self):
        self.x -= self.speed
        if self.x < -self.w:
            self.x = S.WIDTH + 60
            self.y = 40 + (hash(self) % 180)

    def draw(self, screen):
        surf = pygame.transform.smoothscale(CLOUD_IMG, (self.w, self.h))
        screen.blit(surf, (self.x, self.y))


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((S.WIDTH, S.HEIGHT))
        pygame.display.set_caption(S.TITLE)
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.Font(None, 68)
        self.font_mid = pygame.font.Font(None, 34)
        self.font_small = pygame.font.Font(None, 26)

        self.load_assets()
        self.reset()
        self.best_score = self.load_best_score()

    # ------------------------------------------------------------------ #
    # Asset loading
    # ------------------------------------------------------------------ #
    def load_assets(self):
        # Generate the procedural art/sounds on first run on the desktop. In
        # the web build (pygbag) the assets are already bundled, so we skip
        # generation entirely (avoids unnecessary file writes in the browser).
        required = (S.BACKGROUND_SPRITE, S.CLOUD_SPRITE, S.GROUND_SPRITE,
                    S.BIRD_SPRITE, S.PIPE_SPRITE, S.PIPE_RIM_SPRITE,
                    S.FLAP_SOUND_FILE, S.POINT_SOUND_FILE, S.HIT_SOUND_FILE)
        if not all(os.path.exists(p) for p in required):
            generate_all(force=True)
        global CLOUD_IMG, CLOUD_W, CLOUD_H
        self.bg_img = pygame.image.load(S.BACKGROUND_SPRITE).convert()
        CLOUD_IMG = pygame.image.load(S.CLOUD_SPRITE).convert_alpha()
        CLOUD_W, CLOUD_H = CLOUD_IMG.get_width(), CLOUD_IMG.get_height()
        self.ground_img = pygame.image.load(S.GROUND_SPRITE).convert()
        self.bird_img = pygame.image.load(S.BIRD_SPRITE).convert_alpha()
        self.pipe_body = pygame.image.load(S.PIPE_SPRITE).convert_alpha()
        self.pipe_rim = pygame.image.load(S.PIPE_RIM_SPRITE).convert_alpha()

        # sounds (ignore failures if no audio device)
        try:
            pygame.mixer.init()
            self.snd_flap = pygame.mixer.Sound(S.FLAP_SOUND_FILE)
            self.snd_point = pygame.mixer.Sound(S.POINT_SOUND_FILE)
            self.snd_hit = pygame.mixer.Sound(S.HIT_SOUND_FILE)
            self.sound_ok = True
        except Exception:
            self.snd_flap = self.snd_point = self.snd_hit = None
            self.sound_ok = False

    # ------------------------------------------------------------------ #
    # State helpers
    # ------------------------------------------------------------------ #
    def reset(self):
        self.state = STATE_READY
        self.bird_x = S.BIRD_X
        self.bird_y = S.HEIGHT // 2
        self.vel = 0.0
        self.rotation = 0.0
        self.score = 0
        self.pipes = []
        self._pipe_timer = 0
        self.scroll = 0.0
        self.clouds = [Cloud(90, 90, 1.1), Cloud(260, 170, 0.75),
                       Cloud(380, 60, 0.9)]
        self.flash_alpha = 0
        self.bird_dead = False

    def load_best_score(self):
        try:
            with open(BEST_SCORE_FILE) as f:
                return int(f.read().strip())
        except Exception:
            return 0

    def save_best_score(self):
        try:
            with open(BEST_SCORE_FILE, "w") as f:
                f.write(str(self.best_score))
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Difficulty
    # ------------------------------------------------------------------ #
    def current_gap(self):
        shrink = min(self.score * S.GAP_SHRINK_PER_POINT,
                     S.PIPE_GAP - S.PIPE_MIN_GAP)
        return S.PIPE_GAP - int(shrink)

    def current_pipe_speed(self):
        return S.PIPE_SPEED + self.score * S.SPEED_INCREASE_PER_POINT

    def gap_center(self):
        import random
        lo = S.PIPE_MARGIN + self.current_gap() // 2
        hi = GROUND_TOP - S.PIPE_MARGIN - self.current_gap() // 2
        return random.uniform(lo, hi)

    def spawn_pipe(self):
        gap = self.current_gap()
        center = self.gap_center()
        p = Pipe(S.WIDTH + 10, center, gap, self.pipe_body, self.pipe_rim)
        p.speed = self.current_pipe_speed()
        self.pipes.append(p)

    # ------------------------------------------------------------------ #
    # Input
    # ------------------------------------------------------------------ #
    def flap(self):
        self.vel = S.FLAP_STRENGTH
        self.try_play(self.snd_flap)

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
            if event.key in (pygame.K_SPACE, pygame.K_UP):
                self.on_action()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.on_action()
        return True

    def on_action(self):
        self._unlock_audio()
        if self.state == STATE_READY:
            self.state = STATE_PLAYING
            self.flap()
        elif self.state == STATE_PLAYING:
            self.flap()
        elif self.state == STATE_GAMEOVER:
            # small delay before allowing restart
            if self.flash_alpha == 0:
                self.reset()

    def _unlock_audio(self):
        """Initialise the WebAudio context on the first user gesture.

        Browsers block audio until a user interaction has happened, so we
        (re)initialise the mixer here. No-op when running on the desktop.
        """
        try:
            import pygbag  # only present in the web build
        except Exception:
            return
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            pygame.mixer.stop()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Update
    # ------------------------------------------------------------------ #
    def update(self):
        # always scroll the world
        self.scroll = (self.scroll + S.PIPE_SPEED) % S.WIDTH
        for c in self.clouds:
            c.update()

        if self.state == STATE_READY:
            # gentle bobbing
            self.bird_y = S.HEIGHT // 2 + math.sin(pygame.time.get_ticks() / 260) * 6
            self.rotation = 10 * math.cos(pygame.time.get_ticks() / 260)
            return

        # physics (playing or gameover)
        self.vel = min(self.vel + S.GRAVITY, S.MAX_FALL_SPEED)
        self.bird_y += self.vel

        # rotation based on velocity
        target = S.FLAP_ROTATE_UP if self.vel < 0 else \
            max(S.FLAP_ROTATE_DOWN, -45 - self.vel * 4)
        self.rotation += (target - self.rotation) * 0.2

        if self.state == STATE_GAMEOVER:
            self._update_death()
            return

        # spawn pipes
        speed = self.current_pipe_speed()
        self._pipe_timer += speed
        if self._pipe_timer >= S.PIPE_SPACING:
            self._pipe_timer = 0
            self.spawn_pipe()
        for p in self.pipes:
            p.speed = speed
            p.update()

        # scoring + collision
        bird_center = pygame.math.Vector2(self.bird_x, self.bird_y)
        for p in self.pipes:
            if not p.passed and p.x + S.PIPE_WIDTH < self.bird_x:
                p.passed = True
                self.score += 1
                self.try_play(self.snd_point)
                if self.score > self.best_score:
                    self.best_score = self.score
                    self.save_best_score()
            if self.collides(p):
                self.die()
                return

        self.pipes = [p for p in self.pipes if not p.offscreen()]

        # hit ground or ceiling
        if self.bird_y + BIRD_HALF > GROUND_TOP:
            self.bird_y = GROUND_TOP - BIRD_HALF
            self.die()
        elif self.bird_y - BIRD_HALF < 0:
            self.bird_y = BIRD_HALF

    def collides(self, pipe):
        r = BIRD_HALF
        cx, cy = self.bird_x, self.bird_y
        # circle-rect collision against both pipe rectangles
        for rect in (pipe.rect_top, pipe.rect_bottom):
            closest_x = max(rect.left, min(cx, rect.right))
            closest_y = max(rect.top, min(cy, rect.bottom))
            dx, dy = cx - closest_x, cy - closest_y
            if dx * dx + dy * dy < r * r:
                return True
        return False

    def die(self):
        if self.bird_dead:
            return
        self.bird_dead = True
        self.state = STATE_GAMEOVER
        self.try_play(self.snd_hit)
        self.flash_alpha = 140
        if self.score > self.best_score:
            self.best_score = self.score
            self.save_best_score()

    def _update_death(self):
        # fade the impact flash over time
        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - 8)
        # bird falls and continues, but pipes stop moving forward-ish
        if self.bird_y + BIRD_HALF > GROUND_TOP:
            self.bird_y = GROUND_TOP - BIRD_HALF
            self.vel = 0

    def try_play(self, sound):
        if not self.sound_ok or sound is None:
            return
        try:
            sound.play()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Draw
    # ------------------------------------------------------------------ #
    def draw(self):
        self.screen.blit(self.bg_img, (0, 0))
        for c in self.clouds:
            c.draw(self.screen)

        # pipes below/around the bird
        for p in self.pipes:
            p.draw(self.screen)

        self._draw_bird()

        # ground (scrolling)
        offset = int(self.scroll * 1.0)
        for x in range(-offset, S.WIDTH, self.ground_img.get_width()):
            self.screen.blit(self.ground_img, (x, GROUND_TOP))

        self._draw_hud()

        # impact flash
        if self.flash_alpha > 0:
            overlay = pygame.Surface((S.WIDTH, S.HEIGHT))
            overlay.fill((255, 255, 255))
            overlay.set_alpha(int(self.flash_alpha))
            self.screen.blit(overlay, (0, 0))

        pygame.display.flip()

    def _draw_bird(self):
        scaled = pygame.transform.rotozoom(self.bird_img,
                                           -self.rotation, 0.7)
        rect = scaled.get_rect(center=(self.bird_x, self.bird_y))
        self.screen.blit(scaled, rect)

    def _draw_hud(self):
        color = (255, 255, 255)
        outline = (0, 0, 0)
        if self.state == STATE_READY:
            self._text("Flappy Bird", self.font_big, S.WIDTH // 2,
                       S.HEIGHT * 0.18, center=(S.WIDTH // 2, S.HEIGHT * 0.18))
        if self.state in (STATE_PLAYING, STATE_GAMEOVER):
            self._text(str(self.score), self.font_big, S.WIDTH // 2, 90,
                       center=(S.WIDTH // 2, 90))

        if self.state == STATE_READY:
            text = self.font_mid.render("Click or press Space to flap",
                                        True, color)
            rect = text.get_rect(center=(S.WIDTH // 2, S.HEIGHT * 0.55))
            self.screen.blit(text, rect)
        elif self.state == STATE_GAMEOVER:
            panel = pygame.Surface((S.WIDTH - 60, 180), pygame.SRCALPHA)
            panel.fill((30, 40, 60, 210))
            self.screen.blit(panel, (30, S.HEIGHT * 0.32))
            self._text("Game Over", self.font_big,
                       S.WIDTH // 2, S.HEIGHT * 0.36,
                       center=(S.WIDTH // 2, S.HEIGHT * 0.36))
            self._text("Score: %d    Best: %d" % (self.score, self.best_score),
                       self.font_mid, S.WIDTH // 2, S.HEIGHT * 0.45,
                       center=(S.WIDTH // 2, S.HEIGHT * 0.45))
            self._text("Click to play again", self.font_small,
                       S.WIDTH // 2, S.HEIGHT * 0.52,
                       center=(S.WIDTH // 2, S.HEIGHT * 0.52))

    def _text(self, content, font, x, y, color=(255, 255, 255),
              outline=(0, 0, 0), center=None):
        img = font.render(str(content), True, color)
        shadow = font.render(str(content), True, outline)
        if center:
            r = shadow.get_rect(center=center)
            shadow_r = shadow.get_rect(center=(center[0] + 3, center[1] + 3))
        else:
            shadow_r = (x + 3, y + 3)
            r = (x, y)
        self.screen.blit(shadow, shadow_r)
        self.screen.blit(img, r)

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
    async def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if not self.handle_event(event):
                    running = False
            self.update()
            self.draw()
            self.clock.tick(S.FPS)
            # Yield to the event loop so the web (pygbag) renderer can copy
            # the screen to the canvas. Harmless on the desktop.
            await asyncio.sleep(0)
        pygame.quit()


BIRD_HALF = 22          # effective collision half-size (bird sprite ~0.7 of 64px)


async def main():
    game = Game()
    await game.run()


if __name__ == "__main__":
    asyncio.run(main())

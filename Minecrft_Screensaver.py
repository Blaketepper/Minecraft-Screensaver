"""
Minecraft-style screensaver in Python using pygame.

How to run:
    pip install pygame
    python minecraft_screensaver.py

Exit: press any key, click mouse, or move mouse.

This version hides the mouse cursor while the screensaver is running
and restores it when the program exits.
"""

import pygame
import random
import math
import sys
from dataclasses import dataclass

# ---------- CONFIG ----------
FPS = 60
BLOCK_FALL_RATE = (150, 400)  # pixels per second (min, max)
BLOCK_SPAWN_RATE = 0.08       # average seconds between new falling blocks
BLOCK_SIZE_PIXELS = 10        # base pixel size for "pixel art block" (will be scaled)
CLOUD_SPEED = 10              # px/s
CLOUD_COUNT = 5
BG_COLOR = (10, 20, 35)       # deep night blue
BOB_AMPLITUDE = 8
BOB_SPEED = 0.8               # cycles per second
# ----------------------------

# Simple color palette inspired by Minecraft
GRASS_TOP = (106, 190, 48)
DIRT = (121, 85, 58)
GRASS_EDGE = (86, 160, 36)
STONE = (100, 100, 100)
WOOD = (93, 57, 24)
SINCE = pygame.init()  # initialize early


@dataclass
class FallingBlock:
    x: float
    y: float
    size: int
    vy: float
    color: tuple
    life: float  # seconds remaining for fadeout
    max_life: float


def draw_pixel_block(surface, x, y, pixel_map, pixel_size):
    for row_i, row in enumerate(pixel_map):
        for col_i, col in enumerate(row):
            if col:
                rect = pygame.Rect(x + col_i * pixel_size, y + row_i * pixel_size, pixel_size, pixel_size)
                surface.fill(col, rect)


def generate_grass_block_map():
    M = [
        [None, None, (86,160,36),(106,190,48),(106,190,48),(106,190,48),(106,190,48),(106,190,48),(86,160,36),None,None],
        [None, (86,160,36),(106,190,48),(106,190,48),(106,190,48),(106,190,48),(106,190,48),(106,190,48),(106,190,48),(86,160,36),None],
        [(86,160,36),(106,190,48),(106,190,48),(106,190,48),(106,190,48),(106,190,48),(106,190,48),(106,190,48),(106,190,48),(106,190,48),(86,160,36)],
        [(86,160,36),(106,190,48),(106,190,48),(106,190,48),(106,190,48),(106,190,48),(106,190,48),(106,190,48),(106,190,48),(86,160,36),(86,160,36)],
        [(121,85,58),(121,85,58),(121,85,58),(121,85,58),(121,85,58),(121,85,58),(121,85,58),(121,85,58),(121,85,58),(121,85,58),(121,85,58)],
        [(121,85,58),(121,85,58),(121,85,58),(121,85,58),(121,85,58),(121,85,58),(121,85,58),(121,85,58),(121,85,58),(121,85,58),(121,85,58)],
        [(100,100,100),(100,100,100),(100,100,100),(100,100,100),(100,100,100),(100,100,100),(100,100,100),(100,100,100),(100,100,100),(100,100,100),(100,100,100)],
        [(100,100,100),(100,100,100),(100,100,100),(100,100,100),(100,100,100),(100,100,100),(100,100,100),(100,100,100),(100,100,100),(100,100,100),(100,100,100)],
        [None, (93,57,24),(93,57,24),(93,57,24),(93,57,24),(93,57,24),(93,57,24),(93,57,24),(93,57,24),(93,57,24), None],
        [None, None,(93,57,24),(93,57,24),(93,57,24),(93,57,24),(93,57,24),(93,57,24),(93,57,24), None, None],
        [None, None, None,(93,57,24),(93,57,24),(93,57,24),(93,57,24), None, None, None, None],
    ]
    return M


def make_cloud_surface(width_px, height_px):
    surf = pygame.Surface((width_px, height_px), pygame.SRCALPHA)
    for _ in range(8):
        rx = random.randint(0, width_px)
        ry = random.randint(0, height_px//2)
        r = random.randint(height_px//6, height_px//3)
        pygame.draw.ellipse(surf, (255,255,255,60), pygame.Rect(rx-r//1.5, ry-r//1.2, r*2, r))
    return surf


def main():
    pygame.display.init()
    info = pygame.display.Info()
    screen_w, screen_h = info.current_w, info.current_h

    screen = pygame.display.set_mode((screen_w, screen_h), pygame.FULLSCREEN | pygame.DOUBLEBUF)
    pygame.display.set_caption("Minecraft Screensaver")
    clock = pygame.time.Clock()

    # --- HIDE/GRAB MOUSE ---
    # Hide the cursor while screensaver runs and grab input so the OS cursor doesn't show.
    pygame.mouse.set_visible(False)
    try:
        pygame.event.set_grab(True)
    except Exception:
        # not critical if grab isn't supported on some platforms
        pass

    # pixel art scaling
    base_map = generate_grass_block_map()
    map_w = len(base_map[0])
    map_h = len(base_map)
    target_block_width = min(screen_w // 5, 450)
    pixel_size = max(2, target_block_width // map_w)

    block_surf = pygame.Surface((map_w * pixel_size, map_h * pixel_size), pygame.SRCALPHA)
    draw_pixel_block(block_surf, 0, 0, base_map, pixel_size)
    shadow = pygame.Surface((block_surf.get_width(), block_surf.get_height()), pygame.SRCALPHA)
    shadow.fill((0,0,0,50))
    block_surf.blit(shadow, (3, 3), special_flags=pygame.BLEND_RGBA_SUB)
    draw_pixel_block(block_surf, 0, 0, base_map, pixel_size)

    falling = []
    spawn_accum = 0.0
    spawn_interval = BLOCK_SPAWN_RATE

    clouds = []
    for i in range(CLOUD_COUNT):
        w = random.randint(screen_w//6, screen_w//3)
        h = max(40, w // 6)
        surf = make_cloud_surface(w, h)
        x = random.uniform(-w, screen_w)
        y = random.uniform(20, screen_h * 0.35)
        speed = random.uniform(CLOUD_SPEED * 0.5, CLOUD_SPEED * 1.5)
        clouds.append([x, y, surf, speed])

    start_mouse_pos = pygame.mouse.get_pos()
    start_ticks = pygame.time.get_ticks()

    running = True
    try:
        while running:
            dt = clock.tick(FPS) / 1000.0
            spawn_accum += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    running = False
                elif event.type == pygame.MOUSEMOTION:
                    # Exit on mouse movement from initial position
                    if event.pos != start_mouse_pos:
                        running = False

            if spawn_accum >= spawn_interval:
                spawn_accum -= spawn_interval
                spawn_interval = max(0.02, random.gauss(BLOCK_SPAWN_RATE, BLOCK_SPAWN_RATE * 0.4))
                size = random.choice([1, 1, 1, 2])
                px_size = int(pixel_size * size)
                x = random.uniform(0, screen_w - px_size)
                y = -px_size - random.uniform(0, screen_h * 0.1)
                speed = random.uniform(*BLOCK_FALL_RATE)
                color = random.choice([GRASS_TOP, GRASS_EDGE, DIRT, STONE, WOOD])
                life = 2.5 + random.random() * 2.0
                falling.append(FallingBlock(x, y, px_size, speed, color, life, life))

            for b in falling:
                b.y += b.vy * dt
                b.life -= dt
            falling = [b for b in falling if b.life > 0 and b.y < screen_h + 200]

            for cloud in clouds:
                cloud[0] += cloud[3] * dt
                if cloud[0] > screen_w + cloud[2].get_width():
                    cloud[0] = -cloud[2].get_width() - random.uniform(0, screen_w * 0.2)
                    cloud[1] = random.uniform(20, screen_h * 0.35)
                    cloud[3] = random.uniform(CLOUD_SPEED * 0.5, CLOUD_SPEED * 1.5)

            screen.fill(BG_COLOR)
            t = (pygame.time.get_ticks() - start_ticks) / 1000.0
            bob = math.sin(2 * math.pi * BOB_SPEED * t) * BOB_AMPLITUDE

            for cloud in clouds:
                cx = int(cloud[0] + math.sin((cloud[1] + t) * 0.2) * 20)
                cy = int(cloud[1] + math.sin(t + cloud[0]*0.001) * 6 + bob*0.1)
                screen.blit(cloud[2], (cx, cy))

            for b in falling:
                alpha = max(0, min(255, int(255 * (b.life / b.max_life))))
                rect = pygame.Surface((b.size, b.size), pygame.SRCALPHA)
                rect.fill(b.color + (alpha,))
                screen.blit(rect, (b.x, b.y))

            block_x = (screen_w - block_surf.get_width()) // 2
            block_y = int(screen_h * 0.5 - block_surf.get_height() // 2 + bob)
            shadow_rect = pygame.Surface((block_surf.get_width() + 40, 20), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_rect, (0,0,0,80), shadow_rect.get_rect())
            screen.blit(shadow_rect, (block_x - 20, block_y + block_surf.get_height() - 8 + 10))
            screen.blit(block_surf, (block_x, block_y))

            if random.random() < 0.04:
                rx = random.randint(block_x, block_x + block_surf.get_width())
                ry = random.randint(block_y, block_y + block_surf.get_height())
                pygame.draw.circle(screen, (255,255,255,120), (rx, ry), 1)

            font = pygame.font.SysFont("Arial", 16)
            txt = font.render("Minecraft Screensaver — press any key or move mouse to exit", True, (200, 200, 200))
            txt.set_alpha(90)
            screen.blit(txt, (20, screen_h - 30))

            pygame.display.flip()

    finally:
        # restore mouse visibility/grab before quitting so the cursor returns to normal
        try:
            pygame.mouse.set_visible(True)
            pygame.event.set_grab(False)
        except Exception:
            pass
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        pygame.quit()
        print("Screensaver crashed:", e)
        raise

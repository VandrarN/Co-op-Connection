#! src="https://pygame-web.github.io/cdn/0.9.3/pythons.js" data-os="fs,snd,gui" data-python="3.12" data-_sdl2="canvas"

import pygame
import asyncio
import sys
import os

pygame.init()

W, H = 900, 1350
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Co-op Connection Phase 1 Background Test")

font_big = pygame.font.SysFont(None, 64, bold=True)
font_small = pygame.font.SysFont(None, 36, bold=True)

bg = None
bg_status = "Not loaded yet"

def try_load_background():
    global bg, bg_status

    candidates = [
        "StartScreen_BG.png",
        "assets/StartScreen_BG.png",
        "./StartScreen_BG.png",
        "./assets/StartScreen_BG.png",
    ]

    for path in candidates:
        try:
            if os.path.exists(path):
                img = pygame.image.load(path)
                bg = pygame.transform.smoothscale(img, (W, H))
                bg_status = f"Loaded: {path}"
                return
        except Exception as e:
            bg_status = f"Failed: {path} -> {e}"

    bg_status = "StartScreen_BG.png not found"

try_load_background()

async def main():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        if bg:
            screen.blit(bg, (0, 0))
        else:
            screen.fill((170, 35, 185))
            line1 = font_big.render("BACKGROUND NOT LOADED", True, (255, 245, 120))
            line2 = font_small.render(bg_status, True, (255, 255, 255))
            screen.blit(line1, line1.get_rect(center=(W // 2, 240)))
            screen.blit(line2, line2.get_rect(center=(W // 2, 310)))

        pygame.display.flip()
        await asyncio.sleep(0)

asyncio.run(main())

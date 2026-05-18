#! src="https://pygame-web.github.io/cdn/0.9.3/pythons.js" data-os="fs,snd,gui" data-python="3.12" data-_sdl2="canvas"

import pygame
import asyncio
import sys

pygame.init()

W, H = 900, 1350
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Co-op Connection Debug Test")

font_big = pygame.font.SysFont(None, 76, bold=True)
font_small = pygame.font.SysFont(None, 42, bold=True)

async def main():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        screen.fill((170, 35, 185))

        pygame.draw.rect(
            screen,
            (255, 245, 120),
            pygame.Rect(70, 140, W - 140, 260),
            border_radius=30
        )

        pygame.draw.rect(
            screen,
            (20, 10, 30),
            pygame.Rect(70, 140, W - 140, 260),
            width=8,
            border_radius=30
        )

        line1 = font_big.render(
            "PYGAME STARTED",
            True,
            (20, 10, 30)
        )

        line2 = font_small.render(
            "If you see this, main.py is running.",
            True,
            (20, 10, 30)
        )

        line3 = font_small.render(
            "Canvas drawing works.",
            True,
            (20, 10, 30)
        )

        screen.blit(line1, line1.get_rect(center=(W // 2, 220)))
        screen.blit(line2, line2.get_rect(center=(W // 2, 300)))
        screen.blit(line3, line3.get_rect(center=(W // 2, 355)))

        pygame.display.flip()

        await asyncio.sleep(0)

asyncio.run(main())

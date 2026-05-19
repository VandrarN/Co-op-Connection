#! src="https://pygame-web.github.io/cdn/0.9.3/pythons.js" data-os="fs,snd,gui" data-python="3.12" data-_sdl2="canvas"

import pygame
import asyncio
import sys
import os

pygame.init()

W, H = 900, 1350
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Co-op Connection Phase 2 Title Test")

font = pygame.font.SysFont(None, 42)
font_big = pygame.font.SysFont(None, 58, bold=True)
font_num = pygame.font.SysFont("georgia", 54)

name_a = ""
name_b = ""
active_field = 0
mirror_coins = 3
online_enabled = False

TITLE_NAME_BOX_W = 526
TITLE_NAME_BOX_H = 54
TITLE_NAME_BOX1_POS = (186, 486)
TITLE_NAME_BOX2_POS = (189, 650)

ENTER_RECT = pygame.Rect(153, 1000, 286, 68)
QUIT_RECT = pygame.Rect(462, 1000, 282, 72)
ONLINE_RECT = pygame.Rect(168, 850, 430, 97)
ONLINE_CHECK_RECT = pygame.Rect(218, 899, 45, 45)
ONLINE_X_RECT = pygame.Rect(226, 907, 30, 30)

MINUS_RECT = pygame.Rect(650, 772, 54, 42)
PLUS_RECT = pygame.Rect(715, 772, 54, 42)

bg = None
bg_status = "Not loaded yet"

def get_title_name_boxes():
    box1 = pygame.Rect(TITLE_NAME_BOX1_POS[0], TITLE_NAME_BOX1_POS[1], TITLE_NAME_BOX_W, TITLE_NAME_BOX_H)
    box2 = pygame.Rect(TITLE_NAME_BOX2_POS[0], TITLE_NAME_BOX2_POS[1], TITLE_NAME_BOX_W, TITLE_NAME_BOX_H)
    return box1, box2

def load_background():
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

def draw_x(rect):
    pad = 5
    pygame.draw.line(screen, (98, 48, 10), (rect.left + pad, rect.top + pad), (rect.right - pad, rect.bottom - pad), 4)
    pygame.draw.line(screen, (98, 48, 10), (rect.right - pad, rect.top + pad), (rect.left + pad, rect.bottom - pad), 4)

def draw_title():
    if bg:
        screen.blit(bg, (0, 0))
    else:
        screen.fill((170, 35, 185))
        msg = font_big.render("BACKGROUND NOT LOADED", True, (255, 245, 120))
        screen.blit(msg, msg.get_rect(center=(W // 2, 240)))

    mx, my = pygame.mouse.get_pos()
    box1, box2 = get_title_name_boxes()

    for idx, box in enumerate([box1, box2]):
        if idx == active_field:
            pygame.draw.rect(screen, (255, 210, 120), box, width=4, border_radius=14)

    t1 = font.render(name_a, True, (70, 50, 35))
    t2 = font.render(name_b, True, (70, 50, 35))

    screen.blit(t1, (box1.x + 22, box1.y + (box1.h - t1.get_height()) // 2))
    screen.blit(t2, (box2.x + 22, box2.y + (box2.h - t2.get_height()) // 2))

    num = font_num.render(str(mirror_coins), True, (55, 25, 5))
    screen.blit(num, num.get_rect(center=(551, int(H * (1243 / 2048)) - 8)))

    if MINUS_RECT.collidepoint((mx, my)):
        pygame.draw.rect(screen, (255, 225, 145), MINUS_RECT, width=3, border_radius=10)
    if PLUS_RECT.collidepoint((mx, my)):
        pygame.draw.rect(screen, (255, 225, 145), PLUS_RECT, width=3, border_radius=10)

    if ONLINE_RECT.collidepoint((mx, my)):
        pygame.draw.rect(screen, (255, 225, 145), ONLINE_CHECK_RECT, width=3, border_radius=6)

    if online_enabled:
        draw_x(ONLINE_X_RECT)

    if ENTER_RECT.collidepoint((mx, my)):
        pygame.draw.rect(screen, (255, 220, 150), ENTER_RECT, width=4, border_radius=16)

    if QUIT_RECT.collidepoint((mx, my)):
        pygame.draw.rect(screen, (255, 220, 150), QUIT_RECT, width=4, border_radius=16)

def draw_placeholder_game():
    screen.fill((40, 30, 25))
    msg1 = font_big.render("TITLE SCREEN WORKS", True, (255, 245, 210))
    msg2 = font.render("Gameplay is not restored yet.", True, (255, 245, 210))
    msg3 = font.render(f"{name_a or 'Player 1'} + {name_b or 'Player 2'}", True, (255, 245, 210))

    screen.blit(msg1, msg1.get_rect(center=(W // 2, 430)))
    screen.blit(msg2, msg2.get_rect(center=(W // 2, 505)))
    screen.blit(msg3, msg3.get_rect(center=(W // 2, 570)))

load_background()

async def main():
    global name_a, name_b, active_field, mirror_coins, online_enabled

    state = "title"

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                if state == "title":
                    if event.key == pygame.K_RETURN:
                        state = "game"
                    elif event.key == pygame.K_TAB:
                        active_field = 1 - active_field
                    elif event.key == pygame.K_BACKSPACE:
                        if active_field == 0:
                            name_a = name_a[:-1]
                        else:
                            name_b = name_b[:-1]
                    else:
                        ch = event.unicode
                        if ch and ch.isprintable():
                            if active_field == 0 and len(name_a) < 18:
                                name_a += ch
                            elif active_field == 1 and len(name_b) < 18:
                                name_b += ch

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == "title":
                    pos = event.pos
                    box1, box2 = get_title_name_boxes()

                    if box1.collidepoint(pos):
                        active_field = 0
                    elif box2.collidepoint(pos):
                        active_field = 1

                    if MINUS_RECT.collidepoint(pos):
                        mirror_coins = max(0, mirror_coins - 1)

                    if PLUS_RECT.collidepoint(pos):
                        mirror_coins = min(5, mirror_coins + 1)

                    if ONLINE_RECT.collidepoint(pos):
                        online_enabled = not online_enabled

                    if ENTER_RECT.collidepoint(pos):
                        state = "game"

                    if QUIT_RECT.collidepoint(pos):
                        pygame.quit()
                        sys.exit()

        if state == "title":
            draw_title()
        else:
            draw_placeholder_game()

        pygame.display.flip()
        await asyncio.sleep(0)

asyncio.run(main())

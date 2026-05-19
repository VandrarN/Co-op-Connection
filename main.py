#! src="https://pygame-web.github.io/cdn/0.9.3/pythons.js" data-os="fs,snd,gui" data-python="3.12" data-_sdl2="canvas"

import pygame
import asyncio
import sys
import os

pygame.init()

W, H = 900, 1350
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Co-op Connection Phase 2B Title UI Test")

ui_font = pygame.font.SysFont(None, 31)
placeholder_font = pygame.font.SysFont(None, 58, bold=True)

name_a = ""
name_b = ""
active_field = 0
title_mirror_coins = 3
TITLE_MIRROR_MIN = 0
TITLE_MIRROR_MAX = 5
playing_online_enabled = False
title_coin_rects = {}
state = "title"

TITLE_NAME_BOX_W = 526
TITLE_NAME_BOX_H = 54
TITLE_NAME_BOX1_POS = (186, 486)
TITLE_NAME_BOX2_POS = (189, 650)

ONLINE_TOGGLE_POS = (168, 850)
ONLINE_TOGGLE_SIZE = (430, 97)
ONLINE_TOGGLE_CHECK_RECT = pygame.Rect(218, 899, 45, 45)
ONLINE_TOGGLE_X_RECT = pygame.Rect(226, 907, 30, 30)

ENTER_RECT = pygame.Rect(153, 1000, 286, 68)
QUIT_RECT = pygame.Rect(462, 1000, 282, 72)

_MIRROR_MINUS_IMG = None
_MIRROR_PLUS_IMG = None
bg = None


def resource_path(relative):
    candidates = [
        relative,
        os.path.join(".", relative),
        os.path.join("assets", relative),
        os.path.join(".", "assets", relative),
    ]
    for path in candidates:
        try:
            if os.path.exists(path):
                return path
        except Exception:
            pass
    return relative


def load_image(filename, alpha=False):
    try:
        img = pygame.image.load(resource_path(filename))
        if alpha:
            try:
                return img.convert_alpha()
            except Exception:
                return img
        try:
            return img.convert()
        except Exception:
            return img
    except Exception:
        return None


def load_background():
    global bg
    img = load_image("StartScreen_BG.png", alpha=False)
    if img:
        bg = pygame.transform.smoothscale(img, (W, H))


def get_title_name_boxes():
    return (
        pygame.Rect(TITLE_NAME_BOX1_POS[0], TITLE_NAME_BOX1_POS[1], TITLE_NAME_BOX_W, TITLE_NAME_BOX_H),
        pygame.Rect(TITLE_NAME_BOX2_POS[0], TITLE_NAME_BOX2_POS[1], TITLE_NAME_BOX_W, TITLE_NAME_BOX_H),
    )


def draw_x(rect):
    xsurf = pygame.Surface(rect.size, pygame.SRCALPHA)
    pad = max(4, int(min(rect.w, rect.h) * 0.16))
    ink = (98, 48, 10, 235)
    glow = (255, 185, 70, 55)
    pygame.draw.line(xsurf, glow, (pad, pad), (rect.w - pad, rect.h - pad), 7)
    pygame.draw.line(xsurf, glow, (rect.w - pad, pad), (pad, rect.h - pad), 7)
    pygame.draw.line(xsurf, ink, (pad, pad), (rect.w - pad, rect.h - pad), 4)
    pygame.draw.line(xsurf, ink, (rect.w - pad, pad), (pad, rect.h - pad), 4)
    screen.blit(xsurf, rect.topleft)


def draw_title():
    global title_coin_rects, _MIRROR_MINUS_IMG, _MIRROR_PLUS_IMG

    if bg:
        screen.blit(bg, (0, 0))
    else:
        screen.fill((170, 35, 185))
        msg = placeholder_font.render("BACKGROUND NOT LOADED", True, (255, 245, 120))
        screen.blit(msg, msg.get_rect(center=(W // 2, 240)))

    mx, my = pygame.mouse.get_pos()
    box1, box2 = get_title_name_boxes()
    title_coin_rects = {}

    for idx, box in enumerate([box1, box2]):
        if idx == active_field:
            s = pygame.Surface(box.size, pygame.SRCALPHA)
            pygame.draw.rect(s, (255, 200, 120, 120), s.get_rect(), width=3, border_radius=14)
            screen.blit(s, box.topleft)

    t1 = ui_font.render(name_a, True, (70, 50, 35))
    t2 = ui_font.render(name_b, True, (70, 50, 35))
    screen.blit(t1, (box1.x + 22, box1.y + (box1.h - t1.get_height()) // 2))
    screen.blit(t2, (box2.x + 22, box2.y + (box2.h - t2.get_height()) // 2))

    ribbon_w = int(W * 0.78)
    ribbon_h = int(H * 0.085)
    ribbon_x = (W - ribbon_w) // 2
    ribbon_y = int(H * 0.595)

    btn_w = int(ribbon_h * 0.90)
    btn_h = int(ribbon_h * 0.70)
    gap = int(btn_w * 0.28)
    right_pad = int(ribbon_h * 0.22)

    plus_rect = pygame.Rect(ribbon_x + ribbon_w - right_pad - btn_w, ribbon_y + (ribbon_h - btn_h) // 2, btn_w, btn_h)
    minus_rect = pygame.Rect(plus_rect.x - gap - btn_w, ribbon_y + (ribbon_h - btn_h) // 2, btn_w, btn_h)

    plus_anchor_cx = plus_rect.centerx
    minus_anchor_cx = minus_rect.centerx

    if _MIRROR_MINUS_IMG is None:
        _MIRROR_MINUS_IMG = load_image("MirrorMinus.png", alpha=True) or False
    if _MIRROR_PLUS_IMG is None:
        _MIRROR_PLUS_IMG = load_image("MirrorPlus.png", alpha=True) or False

    centerline_y = int(H * (1243 / 2048))
    num_font = pygame.font.SysFont("georgia", 54, bold=False)
    num_surf = num_font.render(str(title_mirror_coins), True, (55, 25, 5))
    sh_surf = num_font.render(str(title_mirror_coins), True, (25, 12, 3))
    nx = 551 - num_surf.get_width() // 2
    ny = centerline_y - 8 - num_surf.get_height() // 2
    screen.blit(sh_surf, (nx + 1, ny + 1))
    screen.blit(num_surf, (nx, ny))

    target_h = max(24, int(num_surf.get_height() * 0.90))
    if _MIRROR_MINUS_IMG and _MIRROR_PLUS_IMG:
        minus_aspect = _MIRROR_MINUS_IMG.get_width() / max(1, _MIRROR_MINUS_IMG.get_height())
        plus_aspect = _MIRROR_PLUS_IMG.get_width() / max(1, _MIRROR_PLUS_IMG.get_height())
    else:
        minus_aspect = plus_aspect = 1.0

    minus_rect.size = (max(24, int(target_h * minus_aspect)), target_h)
    plus_rect.size = (max(24, int(target_h * plus_aspect)), target_h)

    pair_center_x = int((minus_anchor_cx + plus_anchor_cx) / 2)
    pair_gap = 6
    total_w = minus_rect.w + pair_gap + plus_rect.w
    minus_rect.left = pair_center_x - (total_w // 2)
    minus_rect.centery = centerline_y
    plus_rect.left = minus_rect.right + pair_gap
    plus_rect.centery = centerline_y

    ribbon_right = ribbon_x + ribbon_w - int(ribbon_h * 0.10)
    if plus_rect.right > ribbon_right:
        shift = plus_rect.right - ribbon_right
        minus_rect.x -= shift
        plus_rect.x -= shift

    title_coin_rects["minus_shared"] = minus_rect
    title_coin_rects["plus_shared"] = plus_rect

    if _MIRROR_MINUS_IMG and _MIRROR_PLUS_IMG:
        screen.blit(pygame.transform.smoothscale(_MIRROR_MINUS_IMG, minus_rect.size), minus_rect.topleft)
        screen.blit(pygame.transform.smoothscale(_MIRROR_PLUS_IMG, plus_rect.size), plus_rect.topleft)
    else:
        pygame.draw.rect(screen, (90, 60, 40), minus_rect, border_radius=10)
        pygame.draw.rect(screen, (90, 60, 40), plus_rect, border_radius=10)
        screen.blit(ui_font.render("-", True, (255, 240, 220)), (minus_rect.x + minus_rect.w // 2 - 6, minus_rect.y + minus_rect.h // 2 - 10))
        screen.blit(ui_font.render("+", True, (255, 240, 220)), (plus_rect.x + plus_rect.w // 2 - 6, plus_rect.y + plus_rect.h // 2 - 10))

    online_rect = pygame.Rect(ONLINE_TOGGLE_POS, ONLINE_TOGGLE_SIZE)
    title_coin_rects["online_toggle"] = online_rect

    if online_rect.collidepoint((mx, my)):
        hover = pygame.Surface(ONLINE_TOGGLE_CHECK_RECT.size, pygame.SRCALPHA)
        pygame.draw.rect(hover, (255, 225, 145, 75), hover.get_rect(), width=3, border_radius=6)
        screen.blit(hover, ONLINE_TOGGLE_CHECK_RECT.topleft)

    if playing_online_enabled:
        draw_x(ONLINE_TOGGLE_X_RECT)

    title_coin_rects["enter"] = ENTER_RECT
    title_coin_rects["quit"] = QUIT_RECT

    for rect in [ENTER_RECT, QUIT_RECT]:
        if rect.collidepoint((mx, my)):
            s = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(s, (255, 220, 150, 90), s.get_rect(), width=3, border_radius=16)
            screen.blit(s, rect.topleft)

    dbg = pygame.font.SysFont(None, 24).render("Phase 2B title UI test", True, (30, 20, 15))
    screen.blit(dbg, (14, 1314))


def draw_placeholder_game():
    screen.fill((40, 30, 25))
    msg1 = placeholder_font.render("TITLE SCREEN WORKS", True, (255, 245, 210))
    msg2 = ui_font.render("Gameplay is not restored yet.", True, (255, 245, 210))
    msg3 = ui_font.render(f"{name_a or 'Player 1'} + {name_b or 'Player 2'}", True, (255, 245, 210))
    screen.blit(msg1, msg1.get_rect(center=(W // 2, 430)))
    screen.blit(msg2, msg2.get_rect(center=(W // 2, 505)))
    screen.blit(msg3, msg3.get_rect(center=(W // 2, 570)))


load_background()


async def main():
    global name_a, name_b, active_field, title_mirror_coins, playing_online_enabled, state

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

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and state == "title":
                click_pos = event.pos
                box1, box2 = get_title_name_boxes()

                if box1.collidepoint(click_pos):
                    active_field = 0
                elif box2.collidepoint(click_pos):
                    active_field = 1

                if title_coin_rects.get("minus_shared") and title_coin_rects["minus_shared"].collidepoint(click_pos):
                    title_mirror_coins = max(TITLE_MIRROR_MIN, title_mirror_coins - 1)

                if title_coin_rects.get("plus_shared") and title_coin_rects["plus_shared"].collidepoint(click_pos):
                    title_mirror_coins = min(TITLE_MIRROR_MAX, title_mirror_coins + 1)

                if title_coin_rects.get("online_toggle") and title_coin_rects["online_toggle"].collidepoint(click_pos):
                    playing_online_enabled = not playing_online_enabled

                if title_coin_rects.get("enter") and title_coin_rects["enter"].collidepoint(click_pos):
                    state = "game"

                if title_coin_rects.get("quit") and title_coin_rects["quit"].collidepoint(click_pos):
                    pygame.quit()
                    sys.exit()

        if state == "title":
            draw_title()
        else:
            draw_placeholder_game()

        pygame.display.flip()
        await asyncio.sleep(0)


asyncio.run(main())

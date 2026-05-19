#! src="https://pygame-web.github.io/cdn/0.9.3/pythons.js" data-os="fs,snd,gui" data-python="3.12" data-_sdl2="canvas"

import pygame
import asyncio
import sys
import os
import io
import base64
import random

pygame.init()

W, H = 900, 1350
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Co-op Connection Phase 4 Dice Visual Test")

ui_font = pygame.font.SysFont(None, 31)
small_font = pygame.font.SysFont(None, 26)
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
active_player = 0

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

BTN_W = 160
BTN_H = 70
BTN_GAP = 14
BTN_Y = 1216
_btn_row_x0 = 21

GAME_BUTTONS = {
    "ROLL": pygame.Rect(_btn_row_x0 + 0 * (BTN_W + BTN_GAP), BTN_Y, BTN_W, BTN_H),
    "DRAW": pygame.Rect(_btn_row_x0 + 1 * (BTN_W + BTN_GAP), BTN_Y, BTN_W, BTN_H),
    "NEXT": pygame.Rect(_btn_row_x0 + 2 * (BTN_W + BTN_GAP), BTN_Y, BTN_W, BTN_H),
    "SKIP": pygame.Rect(_btn_row_x0 + 3 * (BTN_W + BTN_GAP), BTN_Y, BTN_W, BTN_H),
    "MIRROR": pygame.Rect(_btn_row_x0 + 4 * (BTN_W + BTN_GAP), BTN_Y, BTN_W, BTN_H),
}

_MIRROR_MINUS_IMG = None
_MIRROR_PLUS_IMG = None
_PLAYER_PANEL_IMG = None
start_bg = None
table_bg_1 = None

ICON_CACHE = {}
DICE_FACES = ["CASUAL", "SOUL", "SOUL", "FUN", "ASSUMPTION", "COLD", "FREE", "WILDCARD"]
current_dice_face = "CASUAL"
dice_roll_timer = 0.0
dice_rolling = False

DICE_ICON_FILES = {
    "CASUAL": "Leaf.png",
    "SOUL": "Sapphire.png",
    "FUN": "Sun.png",
    "HEART": "Heart.png",
    "HOT": "dice_icon_hot.png",
    "ASSUMPTION": "dice_icon_assumption.png",
    "COLD": "dice_icon_cold.png",
    "FREE": "dice_icon_free.png",
    "WILDCARD": "Cloud.png",
}


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



def crop_alpha(surf):
    try:
        mask = pygame.mask.from_surface(surf)
        rects = mask.get_bounding_rects()
        if not rects:
            return surf
        r = rects[0].copy()
        for rr in rects[1:]:
            r.union_ip(rr)
        cropped = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        cropped.blit(surf, (0, 0), area=r)
        return cropped
    except Exception:
        return surf


def fit_to_square(surf, square_px, fill=0.90):
    w, h = surf.get_size()
    if w <= 0 or h <= 0:
        return surf
    target = int(square_px * fill)
    scale = target / max(w, h)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    return pygame.transform.smoothscale(surf, (new_w, new_h))


def get_icon_surface(key, size=56):
    cache_key = (key, size)
    if cache_key in ICON_CACHE:
        return ICON_CACHE[cache_key]

    out = pygame.Surface((size, size), pygame.SRCALPHA)
    filename = DICE_ICON_FILES.get(key)
    img = load_image(filename, alpha=True) if filename else None

    if img:
        cropped = crop_alpha(img)
        fitted = fit_to_square(cropped, size, fill=0.92)
        out.blit(fitted, fitted.get_rect(center=(size // 2, size // 2)))
    else:
        # Safe fallback if any icon fails to load.
        pygame.draw.circle(out, (235, 210, 140), (size // 2, size // 2), size // 3)
        txt = pygame.font.SysFont(None, max(14, size // 4), bold=True).render(key[:1], True, (70, 45, 25))
        out.blit(txt, txt.get_rect(center=(size // 2, size // 2)))

    ICON_CACHE[cache_key] = out
    return out


def cover_scale(img):
    if not img:
        return None
    iw, ih = img.get_size()
    if iw <= 0 or ih <= 0:
        return None
    if (iw, ih) == (W, H):
        return img
    scale = max(W / iw, H / ih)
    sw = max(1, int(iw * scale))
    sh = max(1, int(ih * scale))
    scaled = pygame.transform.smoothscale(img, (sw, sh))
    out = pygame.Surface((W, H)).convert()
    out.blit(scaled, ((W - sw) // 2, (H - sh) // 2))
    return out


def load_assets():
    global start_bg, table_bg_1, _PLAYER_PANEL_IMG
    start = load_image("StartScreen_BG.png", alpha=False)
    if start:
        start_bg = cover_scale(start)
    table = load_image("GameTable_BG_1.png", alpha=False)
    if table:
        table_bg_1 = cover_scale(table)
    _PLAYER_PANEL_IMG = load_image("PlayerNamePanel.png", alpha=True) or False


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
    if start_bg:
        screen.blit(start_bg, (0, 0))
    else:
        screen.fill((170, 35, 185))
        msg = placeholder_font.render("START BACKGROUND NOT LOADED", True, (255, 245, 120))
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

    pair_center_x = int((plus_anchor_cx + minus_anchor_cx) / 2)
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

    dbg = pygame.font.SysFont(None, 24).render("Phase 4: table + player panel + dice roll", True, (30, 20, 15))
    screen.blit(dbg, (14, 1314))


def draw_dice(center):
    x, y = center
    size = 84
    rect = pygame.Rect(0, 0, size, size)
    rect.center = (x, y)

    lift = 0
    angle = 0
    if dice_rolling:
        lift = int(22 * abs(pygame.math.Vector2(1, 0).rotate(dice_roll_timer * 720).y))
        angle = int((dice_roll_timer * 720) % 360)

    dice_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(dice_surf, (250, 244, 232), dice_surf.get_rect(), border_radius=14)
    pygame.draw.rect(dice_surf, (210, 195, 170), dice_surf.get_rect().inflate(-8, -8), width=2, border_radius=12)

    icon = get_icon_surface(current_dice_face, 58)
    dice_surf.blit(icon, icon.get_rect(center=(size // 2, size // 2)))

    if dice_rolling:
        dice_surf = pygame.transform.rotate(dice_surf, angle)
        draw_rect = dice_surf.get_rect(center=(x, y - lift))
    else:
        draw_rect = dice_surf.get_rect(center=(x, y))

    screen.blit(dice_surf, draw_rect.topleft)


def draw_button_hover(rect):
    mx, my = pygame.mouse.get_pos()
    if rect.collidepoint((mx, my)):
        s = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (255, 220, 150, 85), s.get_rect(), width=3, border_radius=16)
        screen.blit(s, rect.topleft)


class PlayerPanel:
    def __init__(self):
        self.names = ["Player 1", "Player 2"]
        self.active = 0
        self.glow_t = 1.0
        self.pos = (-52, 585)
        self.target_w = int(298 * 1.2)
        self._scaled = None
        self._scaled_size = None

    def set_names(self, a, b):
        self.names = [a or "Player 1", b or "Player 2"]

    def swap_turn(self):
        self.active = 1 - self.active
        self.glow_t = 0.0

    def update(self, dt):
        self.glow_t = min(1.0, self.glow_t + dt * 2.5)

    def _scaled_panel(self):
        global _PLAYER_PANEL_IMG
        if not _PLAYER_PANEL_IMG:
            return None
        iw, ih = _PLAYER_PANEL_IMG.get_size()
        if iw <= 0 or ih <= 0:
            return None
        target_w = self.target_w
        target_h = max(1, int(ih * (target_w / iw)))
        if self._scaled is None or self._scaled_size != (target_w, target_h):
            self._scaled = pygame.transform.smoothscale(_PLAYER_PANEL_IMG, (target_w, target_h))
            self._scaled_size = (target_w, target_h)
        return self._scaled

    def draw(self):
        panel = self._scaled_panel()
        x, y = self.pos

        if panel is None:
            panel_w, row_h = 258, 42
            gap = 10
            outer_h = row_h * 2 + gap + 18
            outer = pygame.Rect(x, y, panel_w, outer_h)
            box = pygame.Surface(outer.size, pygame.SRCALPHA)
            pygame.draw.rect(box, (88, 56, 36, 235), box.get_rect(), border_radius=16)
            pygame.draw.rect(box, (140, 98, 68, 230), box.get_rect(), width=3, border_radius=16)
            screen.blit(box, outer.topleft)
            row_rects = [
                pygame.Rect(x + 12, y + 10, panel_w - 24, row_h),
                pygame.Rect(x + 12, y + 10 + row_h + gap, panel_w - 24, row_h),
            ]
        else:
            screen.blit(panel, (x, y))
            pw, ph = panel.get_size()
            row_rects = [
                pygame.Rect(x + int(pw * 0.296), y + int(ph * 0.333), int(pw * 0.438), int(ph * 0.122)),
                pygame.Rect(x + int(pw * 0.296), y + int(ph * 0.539), int(pw * 0.438), int(ph * 0.122)),
            ]

        for i, rect in enumerate(row_rects):
            if i == self.active:
                base_a = 52
                pulse_a = int(42 * (1.0 - self.glow_t))
                a = max(0, min(120, base_a + pulse_a))
                glow = pygame.Surface(rect.size, pygame.SRCALPHA)
                pygame.draw.rect(glow, (255, 210, 150, a), glow.get_rect(), border_radius=12)
                pygame.draw.rect(glow, (255, 244, 210, min(120, a + 16)), glow.get_rect(), width=2, border_radius=12)
                screen.blit(glow, rect.topleft)

            name = self.names[i]
            draw_font = ui_font
            txt_main = draw_font.render(name, True, (90, 55, 32))
            txt_shadow = draw_font.render(name, True, (240, 223, 192))

            available_w = rect.w - 16
            if txt_main.get_width() > available_w and len(name) > 1:
                shrink = max(9, int(draw_font.get_height() * available_w / max(1, txt_main.get_width())))
                draw_font = pygame.font.SysFont(None, shrink)
                txt_main = draw_font.render(name, True, (90, 55, 32))
                txt_shadow = draw_font.render(name, True, (240, 223, 192))

            tx = rect.x + 10
            ty = rect.y + (rect.h - txt_main.get_height()) // 2
            screen.blit(txt_shadow, (tx + 1, ty + 1))
            screen.blit(txt_main, (tx, ty))


players = PlayerPanel()


def draw_table_screen():
    if table_bg_1:
        screen.blit(table_bg_1, (0, 0))
    else:
        screen.fill((60, 43, 30))
        msg = placeholder_font.render("TABLE BG 1 NOT LOADED", True, (255, 245, 210))
        screen.blit(msg, msg.get_rect(center=(W // 2, 240)))

    players.draw()
    draw_dice((W // 2, H // 2 + 190))

    for rect in GAME_BUTTONS.values():
        draw_button_hover(rect)

    msg = pygame.font.SysFont(None, 24).render("Phase 4 dice visual test: Roll changes dice face; no cards/content yet", True, (60, 35, 20))
    screen.blit(msg, (14, 1314))



def start_dice_roll():
    global dice_rolling, dice_roll_timer, current_dice_face
    dice_rolling = True
    dice_roll_timer = 0.0
    current_dice_face = random.choice(DICE_FACES)


def update_dice(dt):
    global dice_rolling, dice_roll_timer, current_dice_face
    if not dice_rolling:
        return
    dice_roll_timer += dt
    if dice_roll_timer < 0.85:
        if random.random() < 0.35:
            current_dice_face = random.choice(DICE_FACES)
    else:
        current_dice_face = random.choice(DICE_FACES)
        dice_rolling = False


load_assets()


async def main():
    global name_a, name_b, active_field, title_mirror_coins, playing_online_enabled, state, active_player

    clock = pygame.time.Clock()

    while True:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if state == "game":
                        state = "title"
                    else:
                        pygame.quit()
                        sys.exit()

                if state == "title":
                    if event.key == pygame.K_RETURN:
                        players.set_names(name_a.strip() or "Player 1", name_b.strip() or "Player 2")
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
                click_pos = event.pos

                if state == "title":
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
                        players.set_names(name_a.strip() or "Player 1", name_b.strip() or "Player 2")
                        state = "game"

                    if title_coin_rects.get("quit") and title_coin_rects["quit"].collidepoint(click_pos):
                        pygame.quit()
                        sys.exit()

                elif state == "game":
                    for key, rect in GAME_BUTTONS.items():
                        if rect.collidepoint(click_pos):
                            if key == "ROLL":
                                start_dice_roll()
                            if key == "NEXT":
                                players.swap_turn()
                                active_player = players.active

        if state == "game":
            players.update(dt)
            update_dice(dt)

        if state == "title":
            draw_title()
        else:
            draw_table_screen()

        pygame.display.flip()
        await asyncio.sleep(0)


asyncio.run(main())

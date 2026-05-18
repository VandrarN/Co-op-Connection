#! src="https://pygame-web.github.io/cdn/0.9.3/pythons.js" data-os="fs,snd,gui" data-python="3.12" data-_sdl2="canvas"
import os
os.environ['SDL_VIDEO_CENTERED'] = '1'

import pygame
import sys
import math
import random
import asyncio
import io
import base64

from content_manager import ContentManager

try:
    from PIL import Image
except Exception:
    Image = None

try:
    from embedded_player_panel import PLAYER_PANEL_PNG_B64
except Exception:
    PLAYER_PANEL_PNG_B64 = None


def _load_embedded_player_panel():
    if not PLAYER_PANEL_PNG_B64:
        return None
    try:
        raw = base64.b64decode(PLAYER_PANEL_PNG_B64)
        return pygame.image.load(io.BytesIO(raw), "PlayerNamePanel.png").convert_alpha()
    except Exception:
        return None


# --- Resource path helper (supports PyInstaller onefile + pygbag/browser archive layout) ---
def resource_path(relative: str) -> str:
    """Return a usable path for bundled assets.

    In desktop Python the assets sit beside main.py. In pygbag/GitHub Pages the
    archive can be unpacked with a slightly different working directory, so a
    simple relative path may fail silently and fall back to the beige debug
    background. This helper searches the common mounted locations before giving
    up. It does not change any asset or visual design; it only finds the same
    files reliably.
    """
    rel = relative.replace("\\", os.sep).replace("/", os.sep)
    bases = []
    for b in (
        getattr(sys, "_MEIPASS", None),
        os.path.abspath(os.path.dirname(__file__)) if "__file__" in globals() else None,
        os.getcwd(),
        "/data/data/org.python/assets",
    ):
        if b and b not in bases:
            bases.append(b)

    for base in bases:
        # pygbag unpacks app files under an assets/ directory in the browser.
        # Try both the normal project-relative path and the browser archive path.
        for candidate in (
            os.path.join(base, rel),
            os.path.join(base, "assets", rel),
            os.path.join(base, "assets", os.path.basename(rel)),
        ):
            if os.path.exists(candidate):
                return candidate

    # Last-resort browser archive search: find by the final filename.
    target = os.path.basename(rel)
    for base in bases:
        try:
            for root, _dirs, files in os.walk(base):
                if target in files:
                    return os.path.join(root, target)
        except Exception:
            pass

    return os.path.join(bases[0] if bases else os.getcwd(), rel)

# --- Mirror coin button image cache ---
_MIRROR_MINUS_IMG = None
_MIRROR_PLUS_IMG = None
_ONLINE_TOGGLE_IMG = None

def _load_alpha_image(filename: str):
    """Load an image with transparency if it exists (PyInstaller-safe).

    Fallback order:
      1) pygame native alpha load
      2) Pillow RGBA conversion
      3) BMP fallback with magenta colorkey
    """
    path = resource_path(filename)
    if os.path.exists(path):
        try:
            return pygame.image.load(path).convert_alpha()
        except Exception:
            pass

        if Image is not None:
            try:
                pil = Image.open(path).convert("RGBA")
                raw = pil.tobytes()
                size = pil.size
                return pygame.image.fromstring(raw, size, "RGBA").convert_alpha()
            except Exception:
                pass

    stem, _ = os.path.splitext(filename)
    bmp_path = resource_path(stem + "_fallback.bmp")
    if os.path.exists(bmp_path):
        try:
            img = pygame.image.load(bmp_path).convert()
            img.set_colorkey((255, 0, 255))
            return img.convert_alpha()
        except Exception:
            return None

    return None

# --- Icon image cache ---
_LEAF_IMG = None
_LEAF_CROP = None

pygame.init()
pygame.display.set_caption("Co-op Connection — Vertical Slice (Content Loader)")

# The game logic is authored in this fixed portrait coordinate system.
# The actual OS window can be any size; the finished frame is scaled down/up
# at presentation time and mouse clicks are mapped back into this design space.
DESIGN_SIZE = (900, 1350)
PORTRAIT_SIZE = DESIGN_SIZE
LANDSCAPE_SIZE = DESIGN_SIZE
IS_WEB = (sys.platform == "emscripten")

def _fit_initial_window(design_size):
    """Choose an initial OS window that fits on the user's desktop.

    The logical game canvas stays 900x1350 for all hitboxes/art alignment.
    Only the outer window starts smaller when the monitor cannot fit the full
    portrait canvas. This keeps the game responsive without forcing a huge
    window off-screen.
    """
    dw, dh = design_size
    try:
        info = pygame.display.Info()
        max_w = max(320, int(info.current_w * 0.90))
        max_h = max(480, int(info.current_h * 0.86))
    except Exception:
        max_w, max_h = dw, dh
    scale = min(1.0, max_w / dw, max_h / dh)
    return (max(320, int(dw * scale)), max(480, int(dh * scale)))

INITIAL_WINDOW_SIZE = DESIGN_SIZE if IS_WEB else _fit_initial_window(DESIGN_SIZE)

W, H = DESIGN_SIZE

# Browser builds are most reliable when the pygame display surface itself is
# the authored 900x1350 portrait canvas. On desktop we keep the original
# offscreen canvas + resizable-window presentation path.
if IS_WEB:
    window = pygame.display.set_mode(DESIGN_SIZE)
    screen = window
    window_size = DESIGN_SIZE
    _present_rect = pygame.Rect(0, 0, *DESIGN_SIZE)
else:
    window = pygame.display.set_mode(INITIAL_WINDOW_SIZE, pygame.RESIZABLE)
    screen = pygame.Surface(DESIGN_SIZE).convert()
    window_size = INITIAL_WINDOW_SIZE
    _present_rect = pygame.Rect(0, 0, *INITIAL_WINDOW_SIZE)

clock = pygame.time.Clock()

def _compute_present_rect(win_size=None):
    if IS_WEB:
        return pygame.Rect(0, 0, W, H)
    if win_size is None:
        win_size = window.get_size()
    ww, wh = win_size
    scale = min(ww / W, wh / H)
    sw = max(1, int(W * scale))
    sh = max(1, int(H * scale))
    return pygame.Rect((ww - sw) // 2, (wh - sh) // 2, sw, sh)

def set_resolution(size):
    """Keep the logical canvas fixed; only recompute the presentation rect."""
    global W, H, _present_rect
    W, H = DESIGN_SIZE
    _present_rect = _compute_present_rect()
    return screen

def window_to_design(pos):
    """Convert a real window mouse position into the 900x1350 design canvas."""
    if IS_WEB:
        return (int(pos[0]), int(pos[1]))
    x, y = pos
    if _present_rect.w <= 0 or _present_rect.h <= 0:
        return (0, 0)
    dx = (x - _present_rect.x) * W / _present_rect.w
    dy = (y - _present_rect.y) * H / _present_rect.h
    return (int(dx), int(dy))

def design_mouse_pos():
    return window_to_design(pygame.mouse.get_pos())

def present_frame():
    """Present the fixed 900x1350 canvas without resampling when possible.

    The art is authored at DESIGN_SIZE. Drawing 1:1 keeps parchment/wood texture
    crisp; only resizable windows need final presentation scaling.
    """
    if IS_WEB:
        pygame.display.flip()
        return

    window.fill((12, 10, 14))
    if _present_rect.size == DESIGN_SIZE:
        window.blit(screen, _present_rect.topleft)
    else:
        scaled = pygame.transform.smoothscale(screen, (_present_rect.w, _present_rect.h))
        window.blit(scaled, _present_rect.topleft)
    pygame.display.flip()

def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - pow(1 - t, 3)

def ease_out_quart(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - pow(1 - t, 4)

def lerp(a, b, t):
    return a + (b - a) * t

def clamp(v, a, b):
    return max(a, min(b, v))

def draw_round_rect(surf, rect, color, radius=18, width=0):
    pygame.draw.rect(surf, color, rect, width=width, border_radius=radius)

COL_BG1 = (70, 80, 110)
COL_BG2 = (30, 35, 55)
COL_TABLE = (92, 68, 48)
COL_TABLE_DARK = (72, 52, 36)
COL_PARCH = (245, 236, 220)
COL_PARCH_EDGE = (210, 188, 160)
COL_TEXT = (55, 40, 30)

THEME = {
    "CASUAL": {"rgb": (90, 170, 120)},
    "SOUL":   {"rgb": (90, 135, 210)},
    "FUN":    {"rgb": (235, 200, 90)},
    "HEART":  {"rgb": (215, 95, 125)},
    "HOT":    {"rgb": (255, 110, 60)},
    "ASSUMPTION": {"rgb": (70, 120, 235)},
    "COLD":   {"rgb": (120, 200, 255)},
    "FREE":   {"rgb": (220, 140, 255)},
    "WILDCARD":   {"rgb": (235, 235, 240)},
}

# Dice remains visually the same cube, but internally uses stage-based face pools.
# Dice face pools expand as the table progresses through the unlock stages.
DICE_STAGES = {
    # Stage 1: Base Game (d8)
    1: ["CASUAL", "SOUL", "SOUL", "FUN", "ASSUMPTION", "COLD", "FREE", "WILDCARD"],
    # Stage 2: Heart Unlocked (d12)
    2: ["CASUAL", "SOUL", "SOUL", "FUN", "HEART", "HEART", "HEART", "ASSUMPTION", "COLD", "FREE", "WILDCARD", "WILDCARD"],
    # Stage 3: Hot Unlocked (d20)
    3: ["SOUL", "SOUL", "FUN", "FUN", "HEART", "HEART", "HEART", "HEART", "HOT", "HOT", "HOT", "HOT", "ASSUMPTION", "ASSUMPTION", "COLD", "COLD", "FREE", "FREE", "WILDCARD", "WILDCARD"],
}

REDRAW_ON_SKIP_DECKS = {"ASSUMPTION", "COLD", "FREE", "HOT"}

# -----------------------------
# Icon drawing (procedural placeholders)
# Replace later with your final PNG icons.
# -----------------------------

# --- PNG icon helpers (cached, PyInstaller-safe) ---
_icon_cache = {}

def _load_icon_png(filename: str):
    # Cache the raw loaded surface
    if filename in _icon_cache:
        return _icon_cache[filename]
    path = resource_path(filename)
    surf = pygame.image.load(path).convert_alpha()
    _icon_cache[filename] = surf
    return surf

def _crop_alpha(surf: pygame.Surface) -> pygame.Surface:
    # Crop to bounding box of non-transparent pixels to remove padding
    mask = pygame.mask.from_surface(surf)
    rects = mask.get_bounding_rects()
    if not rects:
        return surf
    # Union all rects
    r = rects[0].copy()
    for rr in rects[1:]:
        r.union_ip(rr)
    cropped = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
    cropped.blit(surf, (0, 0), area=r)
    return cropped

def _fit_to_square(surf: pygame.Surface, square_px: int, fill: float = 0.95) -> pygame.Surface:
    # Scale surf to fit inside square_px x square_px, filling 'fill' proportion of the limiting dimension.
    w, h = surf.get_size()
    if w <= 0 or h <= 0:
        return surf
    target = int(square_px * fill)
    scale = target / max(w, h)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    return pygame.transform.smoothscale(surf, (new_w, new_h))

def icon_surface(key, size=64):
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size//2, size//2

    if key == "CASUAL":
        # CASUAL icon (Leaf.png) — authoritative art asset
        global _LEAF_IMG
        if _LEAF_IMG is None:
            try:
                _LEAF_IMG = pygame.image.load(resource_path("Leaf.png")).convert_alpha()
            except Exception:
                _LEAF_IMG = False  # sentinel: failed to load

        if _LEAF_IMG:
            # Scale to visually fill the icon square (crop transparent padding first),
            # keep aspect ratio, keep original orientation.
            global _LEAF_CROP
            if _LEAF_CROP is None:
                try:
                    mask = pygame.mask.from_surface(_LEAF_IMG)
                    rects = mask.get_bounding_rects()
                    if rects:
                        u = rects[0].copy()
                        for rr in rects[1:]:
                            u.union_ip(rr)
                        _LEAF_CROP = _LEAF_IMG.subsurface(u).copy()
                    else:
                        _LEAF_CROP = _LEAF_IMG
                except Exception:
                    _LEAF_CROP = _LEAF_IMG

            base = _LEAF_CROP if _LEAF_CROP else _LEAF_IMG
            target = max(2, int(size * 0.95))
            iw, ih = base.get_width(), base.get_height()
            scale = target / max(iw, ih)
            tw, th = max(2, int(iw * scale)), max(2, int(ih * scale))
            img = pygame.transform.smoothscale(base, (tw, th))
            r = img.get_rect(center=(cx, cy))
            s.blit(img, r)
        else:
            # Fallback
            # Fallback (should not happen in production): simple leaf placeholder
            leaf_fill = (95, 220, 145)
            leaf_edge = (55, 155, 105)
            pygame.draw.ellipse(s, leaf_fill, (12, 10, size-24, size-18))
            pygame.draw.ellipse(s, leaf_edge, (12, 10, size-24, size-18), 3)
    elif key == "SOUL":
        # SOUL icon uses Sapphire.png (cropped to alpha bounds, then fitted to fill the icon square)
        raw = _load_icon_png("Sapphire.png")
        cropped = _crop_alpha(raw)  # keeps gold frame because it is non-transparent
        fitted = _fit_to_square(cropped, size, fill=0.95)
        s.blit(fitted, fitted.get_rect(center=(cx, cy)))

    elif key == "FUN":
        # FUN icon uses Sun.png (cropped to alpha bounds, then fitted to fill the icon square)
        raw = _load_icon_png("Sun.png")
        cropped = _crop_alpha(raw)
        fitted = _fit_to_square(cropped, s.get_width(), fill=1.2)
        s.blit(fitted, fitted.get_rect(center=(s.get_width() // 2, s.get_height() // 2)))

    elif key == "HEART":
        # HEART icon uses Heart.png (cropped to alpha bounds, then fitted to fill the icon square)
        # Used on the heart deck (after unlock) and on the die (including the unlock ceremony swap).
        raw = _load_icon_png("Heart.png")
        cropped = _crop_alpha(raw)
        fitted = _fit_to_square(cropped, size, fill=0.95)
        s.blit(fitted, fitted.get_rect(center=(cx, cy)))


    elif key == "HOT":
        # HOT icon extracted from GameTable_BG_3.png.
        raw = _load_icon_png("dice_icon_hot.png")
        cropped = _crop_alpha(raw)
        fitted = _fit_to_square(cropped, size, fill=0.95)
        s.blit(fitted, fitted.get_rect(center=(cx, cy)))

    elif key == "ASSUMPTION":
        # ASSUMPTION icon extracted from GameTable_BG_3.png.
        raw = _load_icon_png("dice_icon_assumption.png")
        cropped = _crop_alpha(raw)
        fitted = _fit_to_square(cropped, size, fill=0.95)
        s.blit(fitted, fitted.get_rect(center=(cx, cy)))

    elif key == "COLD":
        # COLD icon extracted from GameTable_BG_3.png.
        raw = _load_icon_png("dice_icon_cold.png")
        cropped = _crop_alpha(raw)
        fitted = _fit_to_square(cropped, size, fill=0.95)
        s.blit(fitted, fitted.get_rect(center=(cx, cy)))

    elif key == "FREE":
        # FREE butterfly deck icon extracted from GameTable_BG_3.png.
        raw = _load_icon_png("dice_icon_free.png")
        cropped = _crop_alpha(raw)
        fitted = _fit_to_square(cropped, size, fill=0.95)
        s.blit(fitted, fitted.get_rect(center=(cx, cy)))

    elif key == "WILDCARD":
        # WILDCARD (Cloud) icon uses Cloud.png.
        # Note: WILDCARD is NOT a category deck; it only appears on the die to trigger Free Choice.
        raw = _load_icon_png("Cloud.png")
        cropped = _crop_alpha(raw)
        fitted = _fit_to_square(cropped, size, fill=0.95)
        s.blit(fitted, fitted.get_rect(center=(cx, cy)))

    return s


def wrap_lines(text, font, max_width):
    words = text.split(" ")
    lines = []
    current = ""
    for w in words:
        test = (current + " " + w).strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines

ICON_CACHE = {}

def get_icon(key, size=64):
    k = (key, size)
    if k not in ICON_CACHE:
        ICON_CACHE[k] = icon_surface(key, size)
    return ICON_CACHE[k]

def draw_wrapped(surface, text, rect, font, color, line_spacing=6, center=False):
    x,y,w,h = rect
    lines = []
    for para in text.split("\n"):
        lines.extend(wrap_lines(para, font, w))
        lines.append("")
    y_cursor = y
    for line in lines:
        if line == "":
            y_cursor += font.get_height()//2
            continue
        img = font.render(line, True, color)
        if center:
            surface.blit(img, (x + (w-img.get_width())//2, y_cursor))
        else:
            surface.blit(img, (x, y_cursor))
        y_cursor += img.get_height()+line_spacing
        if y_cursor > y + h:
            break

# -----------------------------
# Particles
# -----------------------------
class Particle:
    def __init__(self, pos):
        self.pos = pygame.Vector2(pos)
        ang = random.uniform(0, math.pi*2)
        sp = random.uniform(40, 140)
        self.vel = pygame.Vector2(math.cos(ang), math.sin(ang))*sp
        self.life = random.uniform(0.6, 1.1)
        self.t = 0.0
        self.r = random.randint(2,4)

    def update(self, dt):
        self.t += dt
        self.pos += self.vel*dt
        self.vel *= 0.92

    def draw(self, screen):
        a = max(0.0, 1 - self.t/self.life)
        col = (255, 210, 160, int(255*a))
        s = pygame.Surface((self.r*2, self.r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, col, (self.r, self.r), self.r)
        screen.blit(s, (self.pos.x-self.r, self.pos.y-self.r))

# -----------------------------
# Button
# -----------------------------
class Button:
    def __init__(self, label, rect):
        self.label = label
        self.rect = pygame.Rect(rect)
        self.enabled = True

    def draw(self, screen, font):
        s = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        a = 255 if self.enabled else 120
        pygame.draw.rect(s, (*COL_PARCH, a), s.get_rect(), border_radius=14)
        pygame.draw.rect(s, (*COL_PARCH_EDGE, a), s.get_rect().inflate(-6,-6), width=2, border_radius=12)
        txt = font.render(self.label, True, (70,50,35))
        s.blit(txt, ((s.get_width()-txt.get_width())//2, (s.get_height()-txt.get_height())//2))
        screen.blit(s, self.rect.topleft)

    def hit(self, pos):
        return self.enabled and self.rect.collidepoint(pos)

# -----------------------------
# Floating prompt
# -----------------------------
class FloatingPrompt:
    def __init__(self):
        self.text = ""
        self.alpha = 0.0
        self.target = 0.0
        self.active = False

    def show(self, text):
        self.text = text
        self.target = 1.0
        self.active = True

    def hide(self):
        self.target = 0.0

    def update(self, dt):
        if not self.active and self.target == 0:
            return
        # Smooth fade in/out for WILDCARD deck choice prompt.
        speed = 5.8
        self.alpha += (self.target - self.alpha) * clamp(dt * speed, 0, 1)
        if self.alpha < 0.01 and self.target == 0:
            self.alpha = 0
            self.active = False

    def draw(self, screen, pos=None, font=None):
        if not self.active:
            return

        # WILDCARD prompt: plain, table-integrated text only.
        # No plaque/frame and no stacked outline/glow layers. It fades in when
        # the cloud is rolled and fades away after a deck is chosen.
        alpha = max(0, min(255, int(self.alpha * 255)))
        if alpha <= 0:
            return

        cx, cy = W // 2, 1082
        prompt_font = pygame.font.SysFont("georgia", 34, bold=True)
        if prompt_font is None:
            prompt_font = font or pygame.font.SysFont(None, 34, bold=True)

        layer_w, layer_h = 360, 70
        layer = pygame.Surface((layer_w, layer_h), pygame.SRCALPHA)
        center = (layer_w // 2, layer_h // 2)

        # Warm carved-wood text color with a single soft shadow.
        shadow_col = (18, 10, 5)
        text_col = (55, 31, 14)

        shadow = prompt_font.render(self.text, True, shadow_col)
        main = prompt_font.render(self.text, True, text_col)
        rect = main.get_rect(center=center)

        layer.blit(shadow, rect.move(2, 3))
        layer.blit(main, rect)

        layer.set_alpha(alpha)
        screen.blit(layer, layer.get_rect(center=(cx, cy)).topleft)

# -----------------------------
# Card actor
# -----------------------------
class CardActor:
    def __init__(self):
        self.visible = False
        self.size = (360, 240)
        self.pos = pygame.Vector2(W//2, H//2+5)
        self.rot = 0.0
        self.scale_x = 1.0
        self.face_up = False
        self.category = "CASUAL"
        self.supported_categories = ["CASUAL","SOUL","FUN","HEART","HOT","ASSUMPTION","COLD","FREE"]
        self.text = ""
        self.state = "idle"
        self.t = 0.0
        self.dur = 1.0
        self.particles = []
        self.is_consequence = False

    def configure(self, category, text, is_consequence=False):
        self.category = category
        self.text = text
        self.face_up = False
        self.is_consequence = is_consequence
        self.visible = True
        self.state = "idle"
        self.t = 0.0
        self.rot = 0.0
        self.scale_x = 1.0
        self.particles.clear()

    def fly_in_and_flip(self, start_pos, end_pos):
        self.start = pygame.Vector2(start_pos)
        self.end = pygame.Vector2(end_pos)
        self.pos = pygame.Vector2(start_pos)
        self.state = "fly"
        self.t = 0.0
        self.dur = 0.65
        self.rot = -6.0
        self.scale_x = 1.0
        self.face_up = False

    def start_flip(self):
        self.state = "flip"
        self.t = 0.0
        self.dur = 0.20
        self.face_up = False

    def slide_out(self):
        self.state = "out"
        self.t = 0.0
        self.dur = 0.50
        self.out_start = pygame.Vector2(self.pos)
        self.out_end = pygame.Vector2(self.pos.x + 360, self.pos.y + 10)
        self.out_rot = random.choice([8, -8])

    def mirror_shimmer(self):
        self.state = "mirror"
        self.t = 0.0
        self.dur = 0.90

    def dissolve_to_consequence(self):
        self.state = "dissolve"
        self.t = 0.0
        self.dur = 0.70
        self.particles = []
        for _ in range(70):
            px = self.pos.x + random.uniform(-140, 140)
            py = self.pos.y + random.uniform(-90, 90)
            self.particles.append(Particle((px, py)))

    def update(self, dt):
        if not self.visible:
            return

        self.t += dt
        p = clamp(self.t / self.dur, 0, 1)
        e = ease_out_cubic(p)

        if self.state == "fly":
            self.pos = self.start.lerp(self.end, e)
            self.rot = lerp(-6, 0, e)
            if p >= 1:
                self.start_flip()

        elif self.state == "flip":
            if p < 0.5:
                self.scale_x = lerp(1.0, 0.05, p*2)
            else:
                if not self.face_up:
                    self.face_up = True
                self.scale_x = lerp(0.05, 1.0, (p-0.5)*2)
            if p >= 1:
                self.state = "idle"
                self.t = 0
                self.dur = 1

        elif self.state == "out":
            self.pos = self.out_start.lerp(self.out_end, e)
            self.rot = lerp(0, self.out_rot, e)
            if p >= 1:
                self.visible = False
                self.state = "idle"

        elif self.state == "mirror":
            if p >= 1:
                self.state = "idle"

        elif self.state == "dissolve":
            for part in self.particles:
                part.update(dt)
            if p >= 1:
                self.visible = False
                self.state = "idle"

    def _make_shimmer_overlay(self, size, progress, strength=140):
        w, h = size
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        cx = int(-w*0.3 + progress*(w*1.6))
        band = int(w*0.22)
        soft = int(w*0.08)
        for i in range(-band, band, 2):
            d = abs(i)
            a = max(0, strength - int((d/(band+soft))*strength))
            if a <= 0:
                continue
            col = (255, 245, 230, a)
            x1, y1 = cx+i, 0
            x2, y2 = cx+i-int(w*0.55), h
            pygame.draw.line(overlay, col, (x1,y1), (x2,y2), 3)
        return overlay

    def draw(self, screen, font):
        for part in self.particles:
            part.draw(screen)

        if not self.visible:
            return

        w, h = self.size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        if not self.face_up:
            col = THEME[self.category]["rgb"]
            draw_round_rect(surf, surf.get_rect(), col, radius=20)
            draw_round_rect(surf, surf.get_rect().inflate(-10,-10), (255,255,255,60), radius=18, width=2)
            ic = pygame.transform.smoothscale(get_icon(self.category, 72), (72,72))
            r = ic.get_rect(center=(w//2, h//2))
            surf.blit(ic, r)
        else:
            draw_round_rect(surf, surf.get_rect(), COL_PARCH, radius=20)
            draw_round_rect(surf, surf.get_rect().inflate(-8,-8), COL_PARCH_EDGE, radius=18, width=2)
            ic = pygame.transform.smoothscale(get_icon(self.category, 48), (48,48))
            r = ic.get_rect(center=(w//2, 40))
            surf.blit(ic, r)

            title = self.category if not self.is_consequence else f"{self.category} — Consequence"
            timg = font.render(title, True, (85, 60, 45))
            surf.blit(timg, ((w-timg.get_width())//2, 72))

            body_font = pygame.font.SysFont(None, 31)
            draw_wrapped(surf, self.text, (28, 105, w-56, h-130), body_font, COL_TEXT, line_spacing=6, center=True)

        if self.state == "mirror" and self.face_up:
            p = clamp(self.t / self.dur, 0, 1)
            strength = 130 + int(30*math.sin(p*math.pi))
            overlay = self._make_shimmer_overlay((w,h), p, strength=strength)
            surf.blit(overlay, (0,0))

        scaled_w = max(1, int(w*self.scale_x))
        scaled = pygame.transform.smoothscale(surf, (scaled_w, h))
        rotated = pygame.transform.rotate(scaled, self.rot)
        rect = rotated.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        screen.blit(rotated, rect.topleft)

# -----------------------------
# Dice actor
# -----------------------------
class DiceActor:
    def __init__(self):
        self.base_pos = pygame.Vector2(W//2, H//2+190)
        self.pos = pygame.Vector2(self.base_pos)
        self.size = 84
        self.state = "idle"
        self.t = 0.0
        self.dur = 1.2
        self.jump = 70
        self.vertical = 0.0
        self.rot = 0.0
        self.spin = 0.0
        self.decay = 0.94
        self.bounce = False
        self.bounce_t = 0.0

        self.stage = 1
        self.faces = list(DICE_STAGES[self.stage])
        self.current_face = self.faces[0]

        self.face_alpha = 255
        self.replacing = False
        self.new_face = None

    def set_stage(self, stage):
        stage = int(stage)
        if stage not in DICE_STAGES:
            stage = 1
        self.stage = stage
        self.faces = list(DICE_STAGES[self.stage])
        if self.current_face not in self.faces:
            self.current_face = self.faces[0]

    def roll(self):
        self.state = "rolling"
        self.t = 0.0
        self.spin = random.uniform(900, 1300)
        self.bounce = False
        self.current_face = random.choice(self.faces)

    def enable_heart_faces(self):
        # Heart unlock promotes the internal selector from 8 faces to 10 faces.
        self.set_stage(2)

    def enable_hot_faces(self):
        # Hot unlock promotes the internal selector from 10 faces to 12 faces.
        self.set_stage(3)

    def replace_face_magic(self, new_face):
        self.replacing = True
        self.new_face = new_face
        self.face_alpha = 255

    def update(self, dt):
        if self.state == "idle":
            if self.replacing:
                self.face_alpha -= 420*dt
                if self.face_alpha <= 0:
                    self.current_face = self.new_face
                    self.replacing = False
                    self.face_alpha = 255
            return

        self.t += dt
        p = clamp(self.t / self.dur, 0, 1)

        if not self.bounce:
            self.vertical = math.sin(p*math.pi)*self.jump
            self.rot += self.spin*dt
            self.spin *= self.decay
            if p >= 1:
                self.bounce = True
                self.bounce_t = 0.0
        else:
            self.bounce_t += dt
            bp = clamp(self.bounce_t / 0.35, 0, 1)
            self.vertical = math.sin(bp*math.pi)*18*(1-bp)
            self.rot *= 0.85
            if bp >= 1:
                self.state = "idle"
                self.vertical = 0
                self.rot = 0

        self.pos.y = self.base_pos.y - self.vertical

        if self.replacing:
            self.face_alpha -= 420*dt
            if self.face_alpha <= 0:
                self.current_face = self.new_face
                self.replacing = False
                self.face_alpha = 255

    def draw(self, screen):
        s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        draw_round_rect(s, s.get_rect(), (250, 244, 232), radius=14)
        draw_round_rect(s, s.get_rect().inflate(-8,-8), (210, 195, 170), radius=12, width=2)

        icon = pygame.transform.smoothscale(get_icon(self.current_face, 56), (56,56))
        ir = icon.get_rect(center=(self.size//2, self.size//2))
        icon.set_alpha(int(self.face_alpha))
        s.blit(icon, ir)

        tilt = min(abs(self.vertical)*0.15, 12)
        final_rot = self.rot + tilt
        rr = pygame.transform.rotate(s, final_rot)
        rect = rr.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        screen.blit(rr, rect.topleft)

# -----------------------------
# Heart unlock ceremony
# -----------------------------
class HeartUnlock:
    def __init__(self):
        self.active = False
        self.phase = 0
        self.t = 0.0
        self.deck_x = W + 200
        self.deck_target = None
        self.sparkles = []
        self.done = False
        self.fade_alpha = 255
        self.bg_swapped = False
        self.swap_at_p = 0.72

        # Painterly Heart deck artwork (transparent), used so the table background
        # stays identical before/after unlock (only an overlay slides in).
        self._deck_img = None
        self._deck_img_scaled = None
        self._deck_img = _load_alpha_candidate(["Heart 1.0.png", "HeartDeck.png"])

    def start(self, target_x):
        self.active = True
        self.done = False
        self.phase = 1
        self.t = 0.0
        self.deck_target = target_x
        self.fade_alpha = 255
        self.bg_swapped = False
        self.swap_at_p = 0.72
        # Start fully off-screen to the right (based on art width, not a magic constant)
        self._ensure_scaled()
        start_off = W + (self._deck_img_scaled.get_width()//2 if self._deck_img_scaled else 240) + 40
        self.deck_x = start_off
        self.sparkles = []

    def _ensure_scaled(self):
        """Cache a scaled version that visually matches the baked deck stacks.

        NOTE:
        The HeartDeck.png source is a large canvas with lots of transparent padding.
        If we scale the whole canvas, the deck appears tiny. So we:
          1) trim transparent margins to the tight bounding box
          2) scale the trimmed art to the Board deck_size
          3) center it on a deck_size surface (keeps consistent positioning)
        """
        if not self._deck_img or self._deck_img_scaled:
            return

        # 1) Trim transparent padding (tight bbox around visible pixels)
        # Trim very faint transparent padding so the deck scales to the same
        # visual footprint as the baked Fun deck, while preserving the real
        # painted card/shadow silhouette.
        try:
            bbox = self._deck_img.get_bounding_rect(min_alpha=5)
        except TypeError:
            bbox = self._deck_img.get_bounding_rect()
        trimmed = self._deck_img.subsurface(bbox).copy()

        target_layout = _get_heart_deck_row_layout()
        if target_layout:
            target_w, target_h = target_layout["surface"].get_size()
        else:
            target_w, target_h = board.deck_size

        heart_cfg = DECK_RENDER_CONFIG.get("HEART", {"scale": 1.0})
        target_w = int(target_w * heart_cfg.get("scale", 1.0) * 1.075)
        target_h = int(target_h * heart_cfg.get("scale", 1.0) * 1.075)

        # 2) Scale to fit inside target while preserving aspect ratio
        cw, ch = trimmed.get_width(), trimmed.get_height()
        if cw == 0 or ch == 0:
            # Fallback: shouldn't happen, but avoid crashes
            self._deck_img_scaled = pygame.transform.smoothscale(self._deck_img, (target_w, target_h))
            return

        scale = min(target_w / cw, target_h / ch)
        sw = max(1, int(cw * scale))
        sh = max(1, int(ch * scale))
        scaled = pygame.transform.smoothscale(trimmed, (sw, sh))

        # 3) Center on a fixed-size surface so rect math stays consistent
        out = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
        out.blit(scaled, scaled.get_rect(center=(target_w // 2, target_h // 2)))
        self._deck_img_scaled = out

    def update(self, dt, dice: DiceActor):
        global heart_unlocked
        if not self.active:
            return
        self.t += dt

        if self.phase == 1:
            # Slide the independent Heart stack all the way into the baked
            # deck position. Do NOT fade it during the slide: keeping the
            # moving deck fully visible prevents a blank window before the
            # unlocked background is shown.
            dur = 1.35
            p = clamp(self.t/dur, 0, 1)
            e = p * p * p * (p * (p * 6 - 15) + 10)
            self._ensure_scaled()
            start_off = W + (self._deck_img_scaled.get_width()//2 if self._deck_img_scaled else 240) + 40
            self.deck_x = lerp(start_off, self.deck_target, e)
            self.fade_alpha = 255

            if p >= 1:
                # Do not reveal the baked Heart deck yet. First let the deck
                # arrive and begin its masking glow/pulse; the unlocked table
                # swaps underneath later while the independent deck is still
                # fully opaque. This avoids the baked deck showing too early.
                self.deck_x = self.deck_target
                self.phase = 2
                self.t = 0.0
                self.fade_alpha = 255
                dice.enable_heart_faces()
                for _ in range(46):
                    self.sparkles.append({
                        "ang": random.uniform(0, math.pi*2),
                        "r": random.uniform(12, 78),
                        "sp": random.uniform(40, 90),
                    })

        elif self.phase == 2:
            # Dice-like arrival effect for the Heart deck. The moving overlay
            # stays on top briefly, pulses/wiggles, then fades out only while
            # the baked deck is already visible beneath it.
            dur = 1.28
            p = clamp(self.t/dur, 0, 1)

            # Reveal the unlocked baked table late, under cover of the deck
            # being fully visible plus the Heart glow. Fade the independent
            # deck only after the baked background is already underneath it.
            if (not self.bg_swapped) and p >= self.swap_at_p:
                heart_unlocked = True
                board.heart_visible = True
                self.bg_swapped = True

            # Keep the independent Heart deck opaque much longer. The baked deck
            # is visually close but not identical, so an early fade makes the
            # handoff readable. A very late fade plus a denser glow veil hides it.
            fade_start = 0.965
            if p >= fade_start:
                fp = clamp((p - fade_start) / (1.0 - fade_start), 0, 1)
                fe = fp * fp * (3 - 2 * fp)
                self.fade_alpha = int(255 * (1.0 - fe))
            else:
                self.fade_alpha = 255

            if 0.52 < p < 0.56:
                dice.replace_face_magic("HEART")
            for s in self.sparkles:
                s["r"] -= dt*s["sp"]
                if s["r"] < 0:
                    s["r"] = random.uniform(50, 80)
                    s["ang"] = random.uniform(0, math.pi*2)
            if p >= 1:
                self.phase = 3
                self.t = 0.0
                self.fade_alpha = 0

        elif self.phase == 3:
            if self.t > 0.24:
                self.active = False
                self.done = True

    def draw(self, screen, dice: DiceActor):
        if not self.active:
            return

        # Draw the sliding Heart deck artwork during the ceremony.
        # (Other decks are baked into the background.)
        self._ensure_scaled()
        if self._deck_img_scaled and self.fade_alpha > 0:
            target_center = board.heart_center()
            heart_center = pygame.Vector2(self.deck_x - 10, target_center.y)
            img = self._deck_img_scaled

            # Arrival pulse/wiggle: small enough to feel like the deck settles
            # into place, large enough to cover the visual handoff to the baked
            # table artwork.
            if self.phase == 2:
                p2 = clamp(self.t/1.28, 0, 1)
                pulse = math.sin(p2 * math.pi)
                scale = 1.015 + 0.045 * pulse
                rot = math.sin(p2 * math.pi * 4.0) * (2.0 * (1.0 - p2))
                sw = max(1, int(img.get_width() * scale))
                sh = max(1, int(img.get_height() * scale))
                img = pygame.transform.smoothscale(img, (sw, sh))
                if abs(rot) > 0.05:
                    img = pygame.transform.rotate(img, rot)

            if self.fade_alpha < 255:
                img = img.copy()
                img.set_alpha(self.fade_alpha)
            r = img.get_rect(center=(int(heart_center.x), int(heart_center.y)))
            screen.blit(img, r.topleft)

        if self.phase >= 2:
            # Subtle Heart-colored settling glow, placed over the Heart deck
            # itself (not the dice). This masks the exact moment the moving
            # overlay hands off to the baked-in deck underneath. The palette
            # stays warm/red/peach to match the Heart icon and table lighting.
            p = clamp(self.t/1.28, 0, 1)
            # Stronger masking veil: still warm and painterly, but opaque
            # enough at the exact swap/fade window to hide the handoff.
            pulse_peak = math.sin(p * math.pi)
            # Opacity peaks exactly around the handoff: it can begin translucent,
            # but at the swap/fade window it becomes a real veil over the deck.
            cover_in = clamp((p - 0.56) / 0.10, 0, 1)
            cover_out = 1.0 - clamp((p - 0.985) / 0.015, 0, 1)
            swap_cover = cover_in * cover_out
            # The glow is now treated as a solid magical veil during the handoff,
            # not just a translucent bloom. This prevents the table/card art shift
            # from showing through while the independent deck fades away.
            glow_strength = max(pulse_peak * 0.90, swap_cover * 1.22)
            a = max(0, min(255, int(255 * glow_strength)))
            center = pygame.Vector2(self.deck_target - 10, board.heart_center().y)
            glow_w, glow_h = 430, 356
            glow = pygame.Surface((glow_w, glow_h), pygame.SRCALPHA)

            # Soft outer bloom in Heart-icon colors.
            for i in range(14):
                t = i / 13
                alpha = max(0, min(255, int(a * (1.0 - t) * 0.88)))
                rect = pygame.Rect(0, 0, int(glow_w * (0.34 + t * 0.66)), int(glow_h * (0.30 + t * 0.70)))
                rect.center = (glow_w // 2, glow_h // 2)
                pygame.draw.ellipse(glow, (255, 70, 86, alpha), rect)

            # Denser center veil: warm, painterly, and deliberately opaque at
            # the exact handoff so the baked deck cannot visibly pop through.
            veil_alpha = min(255, int(a * 1.26))
            veil = pygame.Rect(58, 50, glow_w - 116, glow_h - 100)
            pygame.draw.ellipse(glow, (255, 82, 96, veil_alpha), veil)
            pygame.draw.ellipse(glow, (255, 124, 112, min(255, int(a * 1.04))), pygame.Rect(78, 66, glow_w - 156, glow_h - 132))
            pygame.draw.ellipse(glow, (255, 186, 138, min(245, int(a * 0.92))), pygame.Rect(106, 88, glow_w - 212, glow_h - 176))
            pygame.draw.ellipse(glow, (255, 225, 178, min(210, int(a * 0.72))), pygame.Rect(138, 112, glow_w - 276, glow_h - 224))
            pygame.draw.ellipse(glow, (255, 226, 196, min(255, int(a * 0.90))), pygame.Rect(46, 40, glow_w - 92, glow_h - 80), width=7)
            pygame.draw.ellipse(glow, (255, 244, 216, min(205, int(a * 0.70))), pygame.Rect(78, 66, glow_w - 156, glow_h - 132), width=5)
            screen.blit(glow, glow.get_rect(center=(int(center.x), int(center.y))).topleft)

            for s in self.sparkles:
                x = center.x + math.cos(s["ang"])*s["r"]
                y = center.y + math.sin(s["ang"])*s["r"]
                pygame.draw.circle(screen, (255, 210, 170), (int(x), int(y)), 3)


# -----------------------------
# Hot unlock ceremony
# -----------------------------
class HotUnlock:
    """Procedural ember-to-fire reveal for the Hot deck.

    The Hot deck is baked into GameTable_BG_3.png. During the ceremony we keep
    GameTable_BG_2 visible while a fire veil grows over the Hot slot. At peak
    opacity the veil fully covers the Hot deck area; then the table swaps to
    GameTable_BG_3 underneath and the fire fades, revealing the baked Hot deck.
    """
    def __init__(self):
        self.active = False
        self.done = False
        self.t = 0.0
        self.duration = 3.10
        self.bg_swapped = False
        self.flames = []
        self.embers = []
        self.rect = BACKGROUND_DECK_HIT_RECTS.get("HOT", pygame.Rect(603, 410, 182, 164)).copy()
        # The fire is a wide painterly veil, so its visual weight reads too far right
        # if it is centered exactly on the Hot slot. Offset only the ceremony effect
        # to the right so the visual flame mass sits over the Hot stack; the real Hot deck hitbox/background position remains unchanged.
        self.fire_x_offset = 36
        self.center = pygame.Vector2(self.rect.centerx + self.fire_x_offset, self.rect.centery)

    def start(self):
        self.active = True
        self.done = False
        self.t = 0.0
        self.bg_swapped = False
        self.rect = BACKGROUND_DECK_HIT_RECTS.get("HOT", pygame.Rect(603, 410, 182, 164)).copy()
        # The fire is a wide painterly veil, so its visual weight reads too far right
        # if it is centered exactly on the Hot slot. Offset only the ceremony effect
        # to the right so the visual flame mass sits over the Hot stack; the real Hot deck hitbox/background position remains unchanged.
        self.fire_x_offset = 36
        self.center = pygame.Vector2(self.rect.centerx + self.fire_x_offset, self.rect.centery)
        self.flames = []
        self.embers = []
        base_x = self.center.x
        base_y = self.rect.bottom - 8
        for i in range(34):
            self.flames.append({
                "phase": random.uniform(0, math.pi * 2),
                "xoff": random.uniform(-0.46, 0.46),
                "width": random.uniform(0.22, 0.52),
                "height": random.uniform(0.72, 1.18),
                "speed": random.uniform(2.0, 4.6),
                "color": random.choice([
                    (255, 64, 18),
                    (255, 93, 20),
                    (255, 130, 28),
                    (255, 190, 54),
                    (255, 226, 130),
                ]),
                "base": pygame.Vector2(base_x, base_y),
            })
        for i in range(42):
            self.embers.append({
                "x": random.uniform(self.rect.left + 20, self.rect.right - 20),
                "y": random.uniform(self.rect.bottom - 16, self.rect.bottom + 16),
                "vy": random.uniform(34, 95),
                "vx": random.uniform(-28, 28),
                "life": random.uniform(0.45, 1.35),
                "age": random.uniform(0.0, 1.0),
                "r": random.uniform(1.5, 4.2),
            })

    def update(self, dt, dice: DiceActor):
        global hot_unlocked
        if not self.active:
            return
        self.t += dt
        p = clamp(self.t / self.duration, 0, 1)

        # Fire coverage is strongest near the middle. Swap the background only
        # when the flames are fully opaque, so the Hot deck never visibly pops in.
        if (not self.bg_swapped) and p >= 0.52:
            hot_unlocked = True
            dice.enable_hot_faces()
            # Hot unlock is communicated by the fire reveal itself; no text prompt.
            self.bg_swapped = True

        # Ember drift update. Recycle while the fire is present, then let them fade.
        for e in self.embers:
            e["age"] += dt
            e["x"] += e["vx"] * dt
            e["y"] -= e["vy"] * dt
            if e["age"] >= e["life"] and p < 0.82:
                e["x"] = random.uniform(self.rect.left + 20, self.rect.right - 20)
                e["y"] = random.uniform(self.rect.bottom - 10, self.rect.bottom + 18)
                e["vx"] = random.uniform(-30, 30)
                e["vy"] = random.uniform(40, 110)
                e["life"] = random.uniform(0.45, 1.25)
                e["age"] = 0.0
                e["r"] = random.uniform(1.5, 4.5)

        if p >= 1.0:
            self.active = False
            self.done = True

    def _coverage(self):
        p = clamp(self.t / self.duration, 0, 1)
        if p < 0.18:
            return 0.10 + (p / 0.18) * 0.18
        if p < 0.52:
            q = (p - 0.18) / 0.34
            return 0.28 + (q * q * (3 - 2*q)) * 0.96
        if p < 0.66:
            return 1.24
        q = clamp((p - 0.66) / 0.34, 0, 1)
        return 1.24 * (1.0 - q * q * (3 - 2*q))

    def draw(self, screen):
        if not self.active:
            return

        p = clamp(self.t / self.duration, 0, 1)
        cov = self._coverage()
        # Opacity ramps to fully opaque at peak, then fades away after the swap.
        if p < 0.52:
            alpha_mult = clamp(p / 0.52, 0, 1)
        elif p < 0.66:
            alpha_mult = 1.0
        else:
            alpha_mult = 1.0 - clamp((p - 0.66) / 0.34, 0, 1)
        alpha_mult = clamp(alpha_mult, 0, 1)

        if alpha_mult <= 0:
            return

        # Draw on a generous transparent layer so glow can spill beyond the slot.
        layer_w = int(self.rect.width * 2.25)
        layer_h = int(self.rect.height * 2.30)
        layer = pygame.Surface((layer_w, layer_h), pygame.SRCALPHA)
        cx = layer_w // 2
        base_y = int(layer_h * 0.74)

        # Warm bloom around the Hot slot. This grows with the fire and helps hide
        # the exact BG swap while keeping the effect painterly.
        glow_a = int(150 * alpha_mult * min(1.0, cov))
        for i in range(16):
            t = i / 15
            a = int(glow_a * (1 - t) * 0.75)
            rw = int(layer_w * (0.22 + 0.78 * t) * max(0.45, cov))
            rh = int(layer_h * (0.18 + 0.58 * t) * max(0.45, cov))
            r = pygame.Rect(0, 0, rw, rh)
            r.center = (cx, int(base_y - rh * 0.18))
            pygame.draw.ellipse(layer, (255, 92, 24, a), r)

        # At peak, draw an intentionally opaque central veil covering the exact
        # Hot deck area. This is the visual mask that lets BG_3 appear seamlessly.
        peak_cover = 0.0
        if 0.48 <= p <= 0.72:
            peak_cover = 1.0 - abs(p - 0.60) / 0.12
            peak_cover = clamp(peak_cover, 0, 1)
        if peak_cover > 0:
            cover = pygame.Rect(0, 0, int(self.rect.width * 1.18), int(self.rect.height * 1.12))
            cover.center = (cx, int(layer_h * 0.48))
            pygame.draw.ellipse(layer, (255, 78, 18, int(255 * peak_cover)), cover)
            inner = cover.inflate(-34, -38)
            pygame.draw.ellipse(layer, (255, 184, 50, int(245 * peak_cover)), inner)
            core = cover.inflate(-70, -78)
            pygame.draw.ellipse(layer, (255, 238, 160, int(230 * peak_cover)), core)

        # Flame tongues. They start as embers, grow to cover the full Hot slot,
        # then collapse and fade.
        for f in self.flames:
            flicker = 0.82 + 0.18 * math.sin(self.t * f["speed"] * 4.0 + f["phase"])
            local_cov = cov * flicker
            fw = max(8, int(self.rect.width * f["width"] * local_cov))
            fh = max(10, int(self.rect.height * f["height"] * local_cov))
            x = cx + int(self.rect.width * f["xoff"] * min(1.0, local_cov))
            y = base_y
            tip_y = y - fh
            left = x - fw // 2
            right = x + fw // 2
            ctrl1 = (left + random.randint(-3, 3), y - int(fh * 0.30))
            ctrl2 = (right + random.randint(-3, 3), y - int(fh * 0.36))
            tip = (x + int(math.sin(self.t * f["speed"] + f["phase"]) * fw * 0.18), tip_y)
            points = [(x, y), ctrl1, tip, ctrl2]
            col = f["color"]
            a = int(255 * alpha_mult * min(1.0, 0.26 + local_cov))
            pygame.draw.polygon(layer, (col[0], col[1], col[2], a), points)

        # Hot white/yellow core at the base.
        core_w = int(self.rect.width * 0.88 * max(0.10, cov))
        core_h = int(self.rect.height * 0.42 * max(0.10, cov))
        core = pygame.Rect(0, 0, core_w, core_h)
        core.center = (cx, int(base_y - core_h * 0.30))
        pygame.draw.ellipse(layer, (255, 236, 150, int(210 * alpha_mult * min(1.0, cov))), core)

        # Embers drifting upward.
        for e in self.embers:
            life_p = clamp(e["age"] / max(0.001, e["life"]), 0, 1)
            a = int(230 * alpha_mult * (1 - life_p))
            if a <= 0:
                continue
            lx = int(e["x"] - (self.center.x - layer_w // 2))
            ly = int(e["y"] - (self.center.y - layer_h // 2))
            pygame.draw.circle(layer, (255, 190, 70, a), (lx, ly), max(1, int(e["r"] * (1-life_p*0.4))))

        screen.blit(layer, layer.get_rect(center=(int(self.center.x), int(self.center.y))).topleft)

# -----------------------------
# Board
# -----------------------------
class Board:
    def __init__(self):
        # Casual/Soul/Fun are now baked directly into GameTable_BG_1.png.
        # Their visuals do not move; these fixed regions provide click logic
        # and card fly-in origins on top of the background artwork.
        self.deck_size = DECK_SLOT_RECTS[1].size
        self.casual_fallback = pygame.Vector2(BACKGROUND_DECK_HIT_RECTS["CASUAL"].center)
        self.soul   = pygame.Vector2(BACKGROUND_DECK_HIT_RECTS["SOUL"].center)
        self.fun    = pygame.Vector2(BACKGROUND_DECK_HIT_RECTS["FUN"].center)
        self.heart  = pygame.Vector2(DECK_SLOT_RECTS[4].center)
        self.heart_visible = False
        self.heart_x = W + 240
        self.center = pygame.Vector2(W//2, H//2+5)

    def _layout_for_key(self, key):
        # Heart remains the only independent deck asset.
        if key == "HEART":
            return _get_heart_deck_row_layout()
        return None

    def _fallback_center_for_key(self, key):
        if key == "CASUAL":
            return pygame.Vector2(self.casual_fallback)
        if key == "SOUL":
            return pygame.Vector2(self.soul)
        if key == "FUN":
            return pygame.Vector2(self.fun)
        if key == "HEART":
            return pygame.Vector2(self.heart_x, self.heart.y)
        return pygame.Vector2(self.center)

    def deck_asset_rect(self, key):
        if key in BACKGROUND_DECK_HIT_RECTS:
            return BACKGROUND_DECK_HIT_RECTS[key].copy()

        layout = self._layout_for_key(key)
        if not layout:
            rect = pygame.Rect(0, 0, *self.deck_size)
            rect.center = self._fallback_center_for_key(key)
            return rect

        surf = heart_unlock._deck_img_scaled if (key == "HEART" and heart_unlock and getattr(heart_unlock, "_deck_img_scaled", None)) else layout["surface"]
        return surf.get_rect(center=(int(self.heart_center().x), int(self.heart_center().y)))

    def deck_asset_mask(self, key):
        if key in BACKGROUND_DECK_HIT_RECTS:
            return None
        if key == "HEART" and heart_unlock and getattr(heart_unlock, "_deck_img_scaled", None):
            return pygame.mask.from_surface(heart_unlock._deck_img_scaled)
        layout = self._layout_for_key(key)
        if layout:
            return layout["mask"]
        return None

    def deck_asset_center(self, key):
        if key in BACKGROUND_DECK_HIT_RECTS:
            return pygame.Vector2(BACKGROUND_DECK_HIT_RECTS[key].center)
        if key == "HEART":
            return pygame.Vector2(self.heart_center())
        return self._fallback_center_for_key(key)

    def casual_center(self):
        return self.deck_asset_center("CASUAL")

    def soul_center(self):
        return self.deck_asset_center("SOUL")

    def fun_center(self):
        return self.deck_asset_center("FUN")

    def heart_center(self):
        layout = self._layout_for_key("HEART")
        base_y = layout["center"].y if layout else self.heart.y

        offset_y = 0
        try:
            if heart_unlock and getattr(heart_unlock, "_deck_img_scaled", None):
                heart_cfg = DECK_RENDER_CONFIG.get("HEART", {"y_offset_ratio": 0.0})
                offset_y = int(heart_unlock._deck_img_scaled.get_height() * heart_cfg.get("y_offset_ratio", 0.0))
        except Exception:
            offset_y = 0

        return pygame.Vector2(self.heart_x, base_y + offset_y)

    def deck_centers(self):
        return {key: self.deck_asset_center(key) for key in unlocked_deck_keys()}

    def hit_deck(self, pos):
        # Only currently visible/unlocked decks can be selected. This gates
        # Heart before Stage 2 and Hot before Stage 3, including WILDCARD picks.
        for key in unlocked_deck_keys():
            rect = self.deck_asset_rect(key)
            if not rect.collidepoint(pos):
                continue

            mask = self.deck_asset_mask(key)
            if not mask:
                return key

            local_x = int(pos[0] - rect.x)
            local_y = int(pos[1] - rect.y)
            if 0 <= local_x < rect.width and 0 <= local_y < rect.height and mask.get_at((local_x, local_y)):
                return key

        return None


def draw_deck_stack(screen, center, key, stack=4):
    w,h = (130,170)
    ox, oy = (6, -5)
    col = THEME[key]["rgb"]
    icon = pygame.transform.smoothscale(get_icon(key, 72), (66,66))
    for i in range(stack-1, -1, -1):
        dx, dy = ox*i, oy*i
        rect = pygame.Rect(0,0,w,h)
        rect.center = (int(center.x+dx), int(center.y+dy))
        sh = pygame.Surface((w,h), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0,0,0,35), sh.get_rect(), border_radius=18)
        screen.blit(sh, (rect.x+4, rect.y+6))
        card = pygame.Surface((w,h), pygame.SRCALPHA)
        pygame.draw.rect(card, (*col,255), card.get_rect(), border_radius=18)
        pygame.draw.rect(card, (255,255,255,70), pygame.Rect(6,6,w-12,h-12), width=2, border_radius=16)
        if i == 0:
            ir = icon.get_rect(center=(w//2, h//2))
            card.blit(icon, ir)
        screen.blit(card, rect.topleft)

# -----------------------------
# Player panel
# -----------------------------
class PlayerPanel:
    def __init__(self):
        self.names = ["Player 1", "Player 2"]
        self.active = 0
        self.glow_t = 1.0
        self.pos = (-52, 585)
        self.target_w = int(298 * 1.2)
        self._scaled = None
        self._scaled_size = None

    def _get_image(self):
        global _PLAYER_PANEL_IMG
        if _PLAYER_PANEL_IMG is None:
            img = _load_alpha_image("PlayerNamePanel.png")
            if img is None:
                img = _load_embedded_player_panel()
            _PLAYER_PANEL_IMG = img or False
        return _PLAYER_PANEL_IMG if _PLAYER_PANEL_IMG is not False else None

    def _scaled_panel(self):
        img = self._get_image()
        if img is None:
            return None
        iw, ih = img.get_size()
        if iw <= 0 or ih <= 0:
            return None
        target_w = self.target_w
        target_h = max(1, int(ih * (target_w / iw)))
        if self._scaled is None or self._scaled_size != (target_w, target_h):
            self._scaled = pygame.transform.smoothscale(img, (target_w, target_h))
            self._scaled_size = (target_w, target_h)
        return self._scaled

    def set_names(self, a, b):
        self.names = [a or "Player 1", b or "Player 2"]

    def swap_turn(self):
        self.active = 1 - self.active
        self.glow_t = 0.0

    def update(self, dt):
        self.glow_t = min(1.0, self.glow_t + dt*2.5)

    def draw(self, screen, font):
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
            draw_font = font
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

# -----------------------------
# Background
# -----------------------------
# Backgrounds
# NOTE: Start Screen and Game Table backgrounds are intentionally separated so we can
# swap the Start Screen background image without affecting the in-game table.

_START_BG_IMG = None
_TABLE_BG_IMG = None
_TABLE_BG_UNLOCKED_IMG = None
_TABLE_BG_HOT_IMG = None
_BG_COVER_CACHE = {}
_CASUAL_DECK_OVERLAY_IMG = None
_CASUAL_DECK_OVERLAY_LAYOUT = None
_SOUL_DECK_OVERLAY_IMG = None
_SOUL_DECK_OVERLAY_LAYOUT = None
_FUN_DECK_OVERLAY_IMG = None
_FUN_DECK_OVERLAY_LAYOUT = None
_HEART_DECK_ROW_IMG = None
_PLAYER_PANEL_IMG = None
_HEART_DECK_ROW_LAYOUT = None

# Fixed table card-stack slots, traced from the white guide rectangles the user
# painted over the table mockup. These are the logical/visual anchors for the
# first 8 stack positions on the game table.
# Casual keeps its original artwork placement/scale locked in exactly as it was
# before the slot refactor because that original position already matched slot 1.
CASUAL_DECK_OVERLAY_TOPLEFT = (44, 70)
CASUAL_DECK_OVERLAY_TARGET_WIDTH = 282
# Soul uses 5/6 of Casual's locked size while preserving its prior center in slot 2.
SOUL_DECK_OVERLAY_TARGET_WIDTH = int(CASUAL_DECK_OVERLAY_TARGET_WIDTH * 5 / 6)
SOUL_DECK_OVERLAY_TOPLEFT = (235, 106)
DECK_SLOT_RECTS = {
    1: pygame.Rect(110, 169, 154, 185),
    2: pygame.Rect(277, 169, 156, 185),
    3: pygame.Rect(446, 170, 162, 187),
    4: pygame.Rect(636, 155, 180, 179),
    5: pygame.Rect(109, 410, 155, 194),
    6: pygame.Rect(277, 411, 162, 192),
    7: pygame.Rect(449, 411, 163, 193),
    8: pygame.Rect(620, 411, 154, 194),
}

# Invisible click regions for card stacks that are baked into the new 900x1350
# GameTable_BG_1.png. These can be tuned if the background artwork shifts.
BACKGROUND_DECK_HIT_RECTS = {
    # Top row
    "CASUAL": pygame.Rect(104, 168, 182, 164),
    "SOUL":   pygame.Rect(286, 168, 182, 164),
    "FUN":    pygame.Rect(468, 168, 182, 164),
    "HEART":  pygame.Rect(603, 168, 182, 164),
    # Bottom row
    "ASSUMPTION": pygame.Rect(104, 410, 182, 164),
    "COLD":       pygame.Rect(286, 410, 182, 164),
    "FREE":       pygame.Rect(468, 410, 182, 164),
    "HOT":        pygame.Rect(603, 410, 182, 164),
}
DECK_SLOT_PADDING = 6

# Locked-in deck render rules for the game table.
# If new card stacks are added later, add them here so size, placement,
# click area, and card spawn origin all stay tied to the same deck asset.
DECK_RENDER_CONFIG = {
    "CASUAL": {"slot_index": 0, "scale": 1.0,  "y_offset_ratio": 0.0},
    "SOUL":   {"slot_index": 1, "scale": 1.0,  "y_offset_ratio": 0.0},
    "FUN":    {"slot_index": 3, "scale": 1.65, "y_offset_ratio": 0.25},
    "HEART":  {"slot_index": 4, "scale": 1.0,  "y_offset_ratio": 0.0},
}

SLOT_INDEX_TO_DECK_KEY = {
    cfg["slot_index"]: key for key, cfg in DECK_RENDER_CONFIG.items()
}


def _load_bg_image(filename: str):
    """Load a background image if it exists (PyInstaller-safe). Returns Surface or None."""
    path = resource_path(filename)
    if not os.path.exists(path):
        return None
    try:
        return pygame.image.load(path).convert()
    except Exception:
        return None

def _blit_cover(dst: pygame.Surface, img: pygame.Surface):
    """Draw a background onto dst.

    Replacement table art may not be exactly DESIGN_SIZE. Smooth-scaling that
    large art every frame can create a hitch, especially at the Heart unlock
    handoff when the unlocked background becomes visible. Cache the covered
    version once per source/destination size, then only blit during gameplay.
    """
    dw, dh = dst.get_size()
    iw, ih = img.get_size()
    if iw <= 0 or ih <= 0:
        return
    if (iw, ih) == (dw, dh):
        dst.blit(img, (0, 0))
        return

    key = (id(img), iw, ih, dw, dh)
    cached = _BG_COVER_CACHE.get(key)
    if cached is None:
        scale = max(dw / iw, dh / ih)
        sw, sh = int(iw * scale), int(ih * scale)
        scaled = pygame.transform.smoothscale(img, (sw, sh))
        covered = pygame.Surface((dw, dh)).convert()
        x = (dw - sw) // 2
        y = (dh - sh) // 2
        covered.blit(scaled, (x, y))
        _BG_COVER_CACHE[key] = covered
        cached = covered
    dst.blit(cached, (0, 0))

def _prepare_cover_cache(dst: pygame.Surface, img: pygame.Surface):
    """Warm up the cover-scale cache without changing the current frame."""
    if not img:
        return
    dw, dh = dst.get_size()
    iw, ih = img.get_size()
    if (iw, ih) == (dw, dh):
        return
    key = (id(img), iw, ih, dw, dh)
    if key in _BG_COVER_CACHE:
        return
    temp = pygame.Surface((dw, dh)).convert()
    _blit_cover(temp, img)


def _draw_gradient_background():
    """Fallback background (original gradient)."""
    for y in range(H):
        t = y / (H-1)
        r = int(lerp(18, 32, t))
        g = int(lerp(24, 40, t))
        b = int(lerp(34, 54, t))
        pygame.draw.line(screen, (r, g, b), (0, y), (W, y))

def draw_start_background():
    global _START_BG_IMG
    if _START_BG_IMG is None:
        _START_BG_IMG = _load_bg_image("StartScreen_BG.png") or False
    if _START_BG_IMG:
        _blit_cover(screen, _START_BG_IMG)
    else:
        _draw_gradient_background()

def draw_table_background():
    global _TABLE_BG_IMG, _TABLE_BG_UNLOCKED_IMG, _TABLE_BG_HOT_IMG
    if _TABLE_BG_IMG is None:
        _TABLE_BG_IMG = _load_bg_image("GameTable_BG_1.png") or False
    if _TABLE_BG_UNLOCKED_IMG is None:
        _TABLE_BG_UNLOCKED_IMG = _load_bg_image("GameTable_BG_2.png") or False
    if _TABLE_BG_HOT_IMG is None:
        _TABLE_BG_HOT_IMG = _load_bg_image("GameTable_BG_3.png") or False

    # Warm all large table images once so unlock handoffs are blits, not
    # first-time smoothscales during unlock handoffs.
    _prepare_cover_cache(screen, _TABLE_BG_IMG)
    _prepare_cover_cache(screen, _TABLE_BG_UNLOCKED_IMG)
    _prepare_cover_cache(screen, _TABLE_BG_HOT_IMG)

    stage = current_table_stage()
    if stage >= 3 and _TABLE_BG_HOT_IMG:
        bg = _TABLE_BG_HOT_IMG
    elif stage >= 2 and _TABLE_BG_UNLOCKED_IMG:
        bg = _TABLE_BG_UNLOCKED_IMG
    else:
        bg = _TABLE_BG_IMG

    if bg:
        _blit_cover(screen, bg)
        return

    # Last-resort fallback only if GameTable_BG_1.png itself is missing.
    _draw_gradient_background()

    table_rect = pygame.Rect(140, 70, W-200, H-130)
    pygame.draw.rect(screen, COL_TABLE_DARK, table_rect.inflate(14,14), border_radius=26)
    pygame.draw.rect(screen, COL_TABLE, table_rect, border_radius=26)

    for i in range(7):
        yy = table_rect.y + 60 + i*70
        pygame.draw.line(screen, (110, 86, 60), (table_rect.x+20, yy), (table_rect.right-20, yy), 2)


def _build_slot_deck_layout(source_img, slot_index):
    if not source_img:
        return None

    slot_rect = DECK_SLOT_RECTS[slot_index]
    bbox = source_img.get_bounding_rect()
    trimmed = source_img.subsurface(bbox).copy() if bbox.width and bbox.height else source_img.copy()

    target_w = max(1, slot_rect.width - DECK_SLOT_PADDING * 2)
    target_h = max(1, slot_rect.height - DECK_SLOT_PADDING * 2)

    deck_key = SLOT_INDEX_TO_DECK_KEY.get(slot_index)
    deck_cfg = DECK_RENDER_CONFIG.get(deck_key, {"scale": 1.0, "y_offset_ratio": 0.0})
    deck_scale_multiplier = deck_cfg.get("scale", 1.0)
    y_offset_ratio = deck_cfg.get("y_offset_ratio", 0.0)

    cw, ch = trimmed.get_size()
    if cw <= 0 or ch <= 0:
        scaled_w = max(1, int(target_w * deck_scale_multiplier))
        scaled_h = max(1, int(target_h * deck_scale_multiplier))
        scaled = pygame.transform.smoothscale(source_img, (scaled_w, scaled_h))
    else:
        scale = min(target_w / cw, target_h / ch) * deck_scale_multiplier
        sw = max(1, int(cw * scale))
        sh = max(1, int(ch * scale))
        scaled = pygame.transform.smoothscale(trimmed, (sw, sh))

    out = pygame.Surface(slot_rect.size, pygame.SRCALPHA)
    if deck_key == "FUN":
        center_y = slot_rect.height // 2 + int(slot_rect.height * y_offset_ratio)
    else:
        center_y = slot_rect.height // 2 + int(scaled.get_height() * y_offset_ratio)
    inner_rect = scaled.get_rect(center=(slot_rect.width // 2, center_y))
    out.blit(scaled, inner_rect)
    rect = out.get_rect(topleft=slot_rect.topleft)
    mask = pygame.mask.from_surface(out)
    visible = mask.get_bounding_rects()
    visible_rect = visible[0].copy() if visible else out.get_rect()
    return {
        "surface": out,
        "rect": rect,
        "mask": mask,
        "visible_rect": visible_rect,
        "center": pygame.Vector2(rect.x + visible_rect.centerx, rect.y + visible_rect.centery),
        "deck_key": deck_key,
        "scale": deck_scale_multiplier,
        "y_offset_ratio": y_offset_ratio,
    }


def _get_casual_deck_overlay_layout():
    """Return the scaled Casual overlay plus the geometry derived from it.

    This makes the overlay art the single source of truth for the CASUAL deck's:
      - screen position
      - animation origin
      - logical deck center
      - click area during WILDCARD choice
    """
    global _CASUAL_DECK_OVERLAY_IMG, _CASUAL_DECK_OVERLAY_LAYOUT

    if _CASUAL_DECK_OVERLAY_IMG is None:
        path = resource_path("CasualLeafDeck_overlay.png")
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                # Treat solid black as transparent background from the placeholder render.
                try:
                    img.set_colorkey((0, 0, 0))
                except Exception:
                    pass
                _CASUAL_DECK_OVERLAY_IMG = img
            except Exception:
                _CASUAL_DECK_OVERLAY_IMG = False
        else:
            _CASUAL_DECK_OVERLAY_IMG = False

    if _CASUAL_DECK_OVERLAY_IMG and _CASUAL_DECK_OVERLAY_LAYOUT is None:
        iw, ih = _CASUAL_DECK_OVERLAY_IMG.get_size()
        scale = CASUAL_DECK_OVERLAY_TARGET_WIDTH / max(1, iw)
        target_h = max(1, int(ih * scale))
        scaled = pygame.transform.smoothscale(
            _CASUAL_DECK_OVERLAY_IMG,
            (CASUAL_DECK_OVERLAY_TARGET_WIDTH, target_h),
        )
        rect = scaled.get_rect(topleft=CASUAL_DECK_OVERLAY_TOPLEFT)
        mask = pygame.mask.from_surface(scaled)
        visible = mask.get_bounding_rects()
        visible_rect = visible[0].copy() if visible else scaled.get_rect()
        _CASUAL_DECK_OVERLAY_LAYOUT = {
            "surface": scaled,
            "rect": rect,
            "mask": mask,
            "visible_rect": visible_rect,
            "center": pygame.Vector2(rect.center),
        }

    return _CASUAL_DECK_OVERLAY_LAYOUT if _CASUAL_DECK_OVERLAY_IMG else None


def _load_alpha_candidate(filenames):
    for filename in filenames:
        path = resource_path(filename)
        if not os.path.exists(path):
            continue
        try:
            img = pygame.image.load(path).convert_alpha()
            # The supplied deck renders use a solid black background rather than
            # transparent pixels. Treat black as transparent so spacing, hitboxes,
            # and row alignment are driven by the visible painted deck itself.
            try:
                img.set_colorkey((0, 0, 0))
            except Exception:
                pass
            return img
        except Exception:
            continue
    return False


def _build_row_deck_layout(source_img, slot_index):
    return _build_slot_deck_layout(source_img, slot_index)


def _get_soul_deck_overlay_layout():
    """Return the Soul overlay using the same locked size treatment as Casual."""
    global _SOUL_DECK_OVERLAY_IMG, _SOUL_DECK_OVERLAY_LAYOUT

    if _SOUL_DECK_OVERLAY_IMG is None:
        _SOUL_DECK_OVERLAY_IMG = _load_alpha_candidate([
            "Soul 1.0.png",
        ])

    if _SOUL_DECK_OVERLAY_IMG and _SOUL_DECK_OVERLAY_LAYOUT is None:
        iw, ih = _SOUL_DECK_OVERLAY_IMG.get_size()
        scale = SOUL_DECK_OVERLAY_TARGET_WIDTH / max(1, iw)
        target_h = max(1, int(ih * scale))
        scaled = pygame.transform.smoothscale(
            _SOUL_DECK_OVERLAY_IMG,
            (SOUL_DECK_OVERLAY_TARGET_WIDTH, target_h),
        )
        rect = scaled.get_rect(topleft=SOUL_DECK_OVERLAY_TOPLEFT)
        mask = pygame.mask.from_surface(scaled)
        visible = mask.get_bounding_rects()
        visible_rect = visible[0].copy() if visible else scaled.get_rect()
        _SOUL_DECK_OVERLAY_LAYOUT = {
            "surface": scaled,
            "rect": rect,
            "mask": mask,
            "visible_rect": visible_rect,
            "center": pygame.Vector2(rect.center),
        }

    return _SOUL_DECK_OVERLAY_LAYOUT if _SOUL_DECK_OVERLAY_IMG else None


def _get_fun_deck_overlay_layout():
    global _FUN_DECK_OVERLAY_IMG, _FUN_DECK_OVERLAY_LAYOUT

    if _FUN_DECK_OVERLAY_IMG is None:
        _FUN_DECK_OVERLAY_IMG = _load_alpha_candidate([
            "Fun 1.0.png",
            "Sun 1.0.png",
        ])

    if _FUN_DECK_OVERLAY_IMG and _FUN_DECK_OVERLAY_LAYOUT is None:
        _FUN_DECK_OVERLAY_LAYOUT = _build_row_deck_layout(_FUN_DECK_OVERLAY_IMG, 3)

    return _FUN_DECK_OVERLAY_LAYOUT if _FUN_DECK_OVERLAY_IMG else None


def _get_heart_deck_row_layout():
    global _HEART_DECK_ROW_IMG, _HEART_DECK_ROW_LAYOUT

    if _HEART_DECK_ROW_IMG is None:
        _HEART_DECK_ROW_IMG = _load_alpha_candidate([
            "Heart 1.0.png",
            "HeartDeck.png",
        ])

    if _HEART_DECK_ROW_IMG and _HEART_DECK_ROW_LAYOUT is None:
        _HEART_DECK_ROW_LAYOUT = _build_row_deck_layout(_HEART_DECK_ROW_IMG, 4)

    return _HEART_DECK_ROW_LAYOUT if _HEART_DECK_ROW_IMG else None

# -----------------------------
# States
# -----------------------------
TITLE = "title"
GAME  = "game"
state = TITLE

title_font = pygame.font.SysFont(None, 31)
sub_font = pygame.font.SysFont(None, 31)
ui_font = pygame.font.SysFont(None, 31)
btn_font = pygame.font.SysFont(None, 31)

name_a = ""
name_b = ""
active_field = 0

# Title screen name box layout (aligned to StartScreen_BG 900x1350 artwork)
TITLE_NAME_BOX_W = 526
TITLE_NAME_BOX_H = 54
TITLE_NAME_BOX1_POS = (186, 486)
TITLE_NAME_BOX2_POS = (189, 650)

def get_title_name_boxes():
    box1 = pygame.Rect(TITLE_NAME_BOX1_POS[0], TITLE_NAME_BOX1_POS[1], TITLE_NAME_BOX_W, TITLE_NAME_BOX_H)
    box2 = pygame.Rect(TITLE_NAME_BOX2_POS[0], TITLE_NAME_BOX2_POS[1], TITLE_NAME_BOX_W, TITLE_NAME_BOX_H)
    return box1, box2

# Mirror coins per player (set on title screen)
title_mirror_coins = 3  # shared for both players (set on title screen)
TITLE_MIRROR_MIN = 0
TITLE_MIRROR_MAX = 5
# Cached title button rects for mouse hit tests
title_coin_rects = {}
playing_online_enabled = False

# Online toggle area in the 900x1350 title-screen coordinate system.
# The unchecked parchment banner is baked into StartScreen_BG.png; the X is drawn dynamically.
ONLINE_TOGGLE_POS = (168, 850)
# Preserve the actual parchment banner aspect ratio so it does not become a generic flat box.
ONLINE_TOGGLE_SIZE = (430, 97)
# Exact checkbox rectangle in the 900x1350 title-screen coordinate system.
# The checkbox is baked into StartScreen_BG.png, so the dynamic X must align to
# the visible square rather than to the old standalone asset proportions.
ONLINE_TOGGLE_CHECK_RECT = pygame.Rect(218, 899, 45, 45)
# Smaller inner rect used only for drawing the X so it stays centered inside the baked checkbox.
ONLINE_TOGGLE_X_RECT = pygame.Rect(226, 907, 30, 30)


board = Board()
dice = DiceActor()
card = CardActor()
prompt = FloatingPrompt()
players = PlayerPanel()
heart_unlock = HeartUnlock()
hot_unlock = HotUnlock()

# Action button hit areas aligned to the baked button row in GameTable_BG_1.png
BTN_W = 160
BTN_H = 70
BTN_GAP = 14
# Invisible button hit areas aligned to the baked button row in the new table art.
# Tuned from user-marked button extents so clicks land across the whole visible button art.
BTN_Y = 1216

_btn_row_w = 5 * BTN_W + 4 * BTN_GAP
_btn_row_x0 = 21

buttons = {
    "ROLL":   Button("Roll",   (_btn_row_x0 + 0*(BTN_W+BTN_GAP), BTN_Y, BTN_W, BTN_H)),
    "DRAW":   Button("Draw",   (_btn_row_x0 + 1*(BTN_W+BTN_GAP), BTN_Y, BTN_W, BTN_H)),
    "NEXT":   Button("Next",   (_btn_row_x0 + 2*(BTN_W+BTN_GAP), BTN_Y, BTN_W, BTN_H)),
    "SKIP":   Button("Skip",   (_btn_row_x0 + 3*(BTN_W+BTN_GAP), BTN_Y, BTN_W, BTN_H)),
    "MIRROR": Button("Mirror", (_btn_row_x0 + 4*(BTN_W+BTN_GAP), BTN_Y, BTN_W, BTN_H)),
}

def relayout_after_resize():
    """Recompute positions that depend on W/H after a set_resolution()."""
    global BTN_Y, _btn_row_x0, _btn_row_w

    board.center = pygame.Vector2(W//2, H//2 + 5)
    dice.base_pos = pygame.Vector2(W//2, H//2 + 190)
    dice.pos = pygame.Vector2(dice.base_pos)

    if not card.visible:
        card.pos = pygame.Vector2(board.center)

    if not board.heart_visible:
        board.heart_x = W + 240

    if not heart_unlock.active:
        heart_unlock.deck_x = W + 240

    BTN_Y = 1216
    _btn_row_w = 5 * BTN_W + 4 * BTN_GAP
    _btn_row_x0 = 21
    for i, key in enumerate(["ROLL","DRAW","NEXT","SKIP","MIRROR"]):
        buttons[key].rect = pygame.Rect(_btn_row_x0 + i*(BTN_W+BTN_GAP), BTN_Y, BTN_W, BTN_H)

mirror_coins = [2,2]

rolled_face = None
waiting_draw = False
free_choice = False
in_mirror = False
in_consequence = False

progress_total = {"CASUAL":0, "SOUL":0, "FUN":0}
heart_unlocked = False
hot_unlocked = False

# Heart tier demo progression based on heart draws
heart_draws = 0
heart_cards_completed = 0
HOT_UNLOCK_HEART_COMPLETIONS = 6

def current_heart_tier():
    # Simple demo pacing: 0-2 Soft, 3-5 Warm, 6+ Flirty
    if heart_draws >= 6:
        return "FLIRTY"
    if heart_draws >= 3:
        return "WARM"
    return "SOFT"


def current_table_stage():
    """Return the active table/progression stage.

    Stage 1: base table.
    Stage 2: Heart deck visible/unlocked.
    Stage 3: Hot deck visible/unlocked.
    """
    if globals().get("hot_unlocked", False):
        return 3
    if globals().get("heart_unlocked", False):
        return 2
    return 1


def unlocked_deck_keys():
    """Deck categories that are currently visible/selectable on the table."""
    keys = ["CASUAL", "SOUL", "FUN", "ASSUMPTION", "COLD", "FREE"]
    if current_table_stage() >= 2:
        keys.insert(3, "HEART")
    if current_table_stage() >= 3:
        keys.append("HOT")
    return keys

# Content
content = ContentManager("content")
content.load_all()

def set_button_states():
    global waiting_draw, free_choice, in_mirror, in_consequence
    can_roll = (not waiting_draw) and (not card.visible) and (not heart_unlock.active) and (not hot_unlock.active) and (not free_choice)
    can_draw = waiting_draw and (not heart_unlock.active) and (not hot_unlock.active) and (not free_choice)
    can_next = card.visible and card.face_up and (not heart_unlock.active) and (not hot_unlock.active)
    can_skip = card.visible and card.face_up and (not in_mirror) and (not in_consequence) and (not heart_unlock.active) and (not hot_unlock.active)
    cur = players.active
    can_mirror = card.visible and card.face_up and (not in_consequence) and (mirror_coins[cur] > 0) and (not heart_unlock.active) and (not hot_unlock.active)

    buttons["ROLL"].enabled = can_roll
    buttons["DRAW"].enabled = can_draw
    buttons["NEXT"].enabled = can_next
    buttons["SKIP"].enabled = can_skip
    buttons["MIRROR"].enabled = can_mirror

def start_game():
    global state, waiting_draw, mirror_coins
    # Switch to landscape for gameplay
    set_resolution(LANDSCAPE_SIZE)
    relayout_after_resize()
    state = GAME
    players.set_names(name_a.strip() or "Player 1", name_b.strip() or "Player 2")
    # apply title-selected mirror coins
    mirror_coins = [title_mirror_coins, title_mirror_coins]
    content.set_online_fun_enabled(playing_online_enabled)
    dice.set_stage(current_table_stage())
    waiting_draw = False

def handle_roll():
    global waiting_draw, rolled_face, free_choice
    dice.roll()
    rolled_face = dice.current_face
    waiting_draw = True
    free_choice = (rolled_face == "WILDCARD")
    if free_choice:
        prompt.show("Choose a Card")

def handle_draw():
    global waiting_draw, free_choice, rolled_face, in_mirror, in_consequence, heart_draws
    if free_choice:
        return
    waiting_draw = False
    in_mirror = False
    in_consequence = False

    category = rolled_face
    if category == "HEART":
        heart_draws += 1
        txt = content.get_question("HEART", heart_tier=current_heart_tier())
    else:
        txt = content.get_question(category)

    card.configure(category, txt, is_consequence=False)
    start_pos = board.deck_asset_center(category)
    card.fly_in_and_flip(start_pos, board.center)

def handle_skip():
    global in_consequence, in_mirror
    if not card.visible or not card.face_up:
        return
    in_consequence = True
    in_mirror = False
    card.dissolve_to_consequence()

def spawn_consequence_after_dissolve(category):
    global in_consequence

    # New player-authored/expanded decks skip into a fresh card from the same deck,
    # rather than drawing a consequence card. Mirror behavior remains unchanged.
    if category in REDRAW_ON_SKIP_DECKS:
        txt = content.get_question(category)
        card.configure(category, txt, is_consequence=False)
        in_consequence = False
    else:
        if category == "HEART":
            txt = content.get_consequence("HEART", heart_tier=current_heart_tier())
        else:
            txt = content.get_consequence(category)
        card.configure(category, txt, is_consequence=True)

    start_pos = board.deck_asset_center(category)
    card.fly_in_and_flip(start_pos, board.center)

def handle_mirror():
    global in_mirror
    cur = players.active
    mirror_coins[cur] -= 1
    in_mirror = True
    card.mirror_shimmer()
    players.swap_turn()

def handle_next():
    global rolled_face, waiting_draw, free_choice, in_mirror, in_consequence
    global heart_unlocked, hot_unlocked, progress_total, heart_cards_completed
    if not card.visible or not card.face_up:
        return

    completed_category = rolled_face
    completed_was_consequence = in_consequence

    card.slide_out()
    players.swap_turn()

    # Consequence cards count as completed category interactions too.
    # A skipped Soul card still becomes Soul progression toward Heart, and a
    # skipped Heart card still becomes Heart progression toward Hot. Mirrored
    # cards remain normal completions and are counted by the same category path.
    if completed_category in ("CASUAL", "SOUL", "FUN"):
        progress_total[completed_category] += 1
    elif completed_category == "HEART":
        heart_cards_completed += 1

    rolled_face = None
    waiting_draw = False
    free_choice = False
    in_mirror = False
    in_consequence = False

    if (not heart_unlocked):
        total = progress_total["CASUAL"] + progress_total["FUN"] + progress_total["SOUL"]
        if total >= 6 and progress_total["SOUL"] >= 2:
            # Start the visual unlock ceremony. The table background swaps only
            # when the sliding Heart stack reaches the baked-in stack position.
            board.heart_visible = False
            board.heart_x = BACKGROUND_DECK_HIT_RECTS["HEART"].centerx
            heart_unlock.start(BACKGROUND_DECK_HIT_RECTS["HEART"].centerx)
    elif (not hot_unlocked) and (not hot_unlock.active) and heart_cards_completed >= HOT_UNLOCK_HEART_COMPLETIONS:
        # Start the Hot unlock ceremony. GameTable_BG_3 and Stage 3 dice activate
        # only at peak flame coverage so the reveal is hidden by the fire veil.
        hot_unlock.start()

def draw_title():
    draw_start_background()

    box1, box2 = get_title_name_boxes()

    # Name boxes are part of the background artwork now.
    # We keep the interactive hit areas, but only draw a subtle focus outline.
    for idx, box in enumerate([box1, box2]):
        if idx == active_field:
            s = pygame.Surface(box.size, pygame.SRCALPHA)
            pygame.draw.rect(s, (255, 200, 120, 120), s.get_rect(), width=3, border_radius=14)
            screen.blit(s, box.topleft)

    t1 = ui_font.render(name_a, True, (70,50,35))
    t2 = ui_font.render(name_b, True, (70,50,35))
    pad_x = 22
    screen.blit(t1, (box1.x + pad_x, box1.y + (box1.h - t1.get_height())//2))
    screen.blit(t2, (box2.x + pad_x, box2.y + (box2.h - t2.get_height())//2))


        # --- Mirror Coins (shared selector embedded into the parchment ribbon) ---
    # We do NOT show any per-player mirror coin UI on the title screen anymore.
    # One shared value (0–5) is chosen here and applied to BOTH players at game start.
    global title_coin_rects
    title_coin_rects = {}

    # Ribbon placement (tuned for 900×1350 portrait title screen)
    ribbon_w = int(W * 0.78)
    ribbon_h = int(H * 0.085)
    ribbon_x = (W - ribbon_w) // 2
    ribbon_y = int(H * 0.595)

    # Wood-style +/- buttons that match the ENTER/QUIT aesthetic
    btn_w = int(ribbon_h * 0.90)
    btn_h = int(ribbon_h * 0.70)
    gap = int(btn_w * 0.28)
    right_pad = int(ribbon_h * 0.22)

    plus_rect  = pygame.Rect(ribbon_x + ribbon_w - right_pad - btn_w, ribbon_y + (ribbon_h - btn_h)//2, btn_w, btn_h)
    minus_rect = pygame.Rect(plus_rect.x - gap - btn_w, ribbon_y + (ribbon_h - btn_h)//2, btn_w, btn_h)
    # Cache anchor X so buttons don't shift when the number changes width
    plus_anchor_cx = plus_rect.centerx
    minus_anchor_cx = minus_rect.centerx

    title_coin_rects["minus_shared"] = minus_rect
    title_coin_rects["plus_shared"] = plus_rect

    # --- Mirror Coins +/- buttons (art buttons) ---
    global _MIRROR_MINUS_IMG, _MIRROR_PLUS_IMG
    if _MIRROR_MINUS_IMG is None:
        _MIRROR_MINUS_IMG = _load_alpha_image("MirrorMinus.png") or False
    if _MIRROR_PLUS_IMG is None:
        _MIRROR_PLUS_IMG = _load_alpha_image("MirrorPlus.png") or False

    mx, my = design_mouse_pos()

    # --- Mirror Coins value (only the number changes) ---
    # The background art already contains the 'Mirror Coins:' label.
    # We only render the number, in-place, matching the ribbon's vibe.
    num_str = str(title_mirror_coins)

    # Position tuned to match the baked StartScreen_BG.png artwork.
    # The user-provided red guideline (through the ribbon) corresponds to y=1243 on the
    # source art which is 2048px tall -> ratio 1243/2048.
    # We anchor the NUMBER (and therefore the +/- buttons, which follow num_rect.centery)
    # to this same visual centerline.
    num_x = 551
    centerline_y = int(H * (1243 / 2048))
    NUM_OPTICAL_OFFSET_Y = -8  # move digits slightly up for better optical centering
    num_y = centerline_y + NUM_OPTICAL_OFFSET_Y

    # Match the baked ribbon number style
    num_font = pygame.font.SysFont("georgia", 54, bold=False)
    num_color = (55, 25, 5)
    shadow_color = (25, 12, 3)

    num_surf = num_font.render(num_str, True, num_color)
    sh_surf  = num_font.render(num_str, True, shadow_color)

    # Center the glyph on the target point
    nx = num_x - num_surf.get_width() // 2
    ny = num_y - num_surf.get_height() // 2

    # Subtle shadow for carved-ink feel
    screen.blit(sh_surf, (nx + 1, ny + 1))
    screen.blit(num_surf, (nx, ny))

    # --- Mirror Coins +/- buttons (positioned relative to the number) ---
    # Keep the same Rect objects (tech), just move them to fit the art perfectly.
    num_rect = pygame.Rect(nx, ny, num_surf.get_width(), num_surf.get_height())

    # Size buttons relative to the rendered number (so they match the ribbon typography)
    pad_from_num = 10
    gap = 8

    # Target height slightly smaller than the number height
    target_h = max(24, int(num_rect.h * 0.90))

    # Preserve each image's aspect ratio
    if _MIRROR_MINUS_IMG and _MIRROR_PLUS_IMG:
        minus_aspect = _MIRROR_MINUS_IMG.get_width() / max(1, _MIRROR_MINUS_IMG.get_height())
        plus_aspect  = _MIRROR_PLUS_IMG.get_width()  / max(1, _MIRROR_PLUS_IMG.get_height())
    else:
        minus_aspect = plus_aspect = 1.0

    minus_w = max(24, int(target_h * minus_aspect))
    plus_w  = max(24, int(target_h * plus_aspect))

    minus_rect.size = (minus_w, target_h)
    plus_rect.size  = (plus_w,  target_h)

    # Keep the BUTTON PAIR fixed on the ribbon regardless of digit width,
    # while also keeping the - and + close together as a single cluster.
    # We anchor the *pair's center* to the original art-tuned anchors, then lay out
    # minus + gap + plus around that center. This prevents "walking" and avoids
    # splitting the buttons apart when their scaled widths change.
    pair_center_x = int((minus_anchor_cx + plus_anchor_cx) / 2)
    pair_gap = 6  # compact spacing between - and + (pixels)

    total_w = minus_rect.w + pair_gap + plus_rect.w
    minus_rect.left = pair_center_x - (total_w // 2)
    minus_rect.centery = centerline_y
    plus_rect.left = minus_rect.right + pair_gap
    plus_rect.centery = centerline_y

    # Clamp inside the ribbon so it never spills over the right edge
    ribbon_right = ribbon_x + ribbon_w - int(ribbon_h * 0.10)
    if plus_rect.right > ribbon_right:
        shift = plus_rect.right - ribbon_right
        minus_rect.x -= shift
        plus_rect.x  -= shift

    # Draw the art buttons last so they sit cleanly on top of the ribbon.
    if _MIRROR_MINUS_IMG and _MIRROR_PLUS_IMG:
        minus_img = pygame.transform.smoothscale(_MIRROR_MINUS_IMG, (minus_rect.w, minus_rect.h))
        plus_img  = pygame.transform.smoothscale(_MIRROR_PLUS_IMG,  (plus_rect.w, plus_rect.h))
        screen.blit(minus_img, minus_rect.topleft)
        screen.blit(plus_img,  plus_rect.topleft)
    else:
        # Fallback if images are missing
        pygame.draw.rect(screen, (90,60,40), minus_rect, border_radius=10)
        pygame.draw.rect(screen, (90,60,40), plus_rect, border_radius=10)
        screen.blit(ui_font.render("−", True, (255,240,220)), (minus_rect.x+minus_rect.w//2-6, minus_rect.y+minus_rect.h//2-10))
        screen.blit(ui_font.render("+", True, (255,240,220)), (plus_rect.x+plus_rect.w//2-6, plus_rect.y+plus_rect.h//2-10))


    # --- Online / environment prompt toggle ---
    global playing_online_enabled

    # The unchecked parchment banner is baked into StartScreen_BG.png so it is
    # always visible and perfectly integrated with the title artwork. Only the
    # interactive hit area and the dynamic X are drawn here.
    online_rect = pygame.Rect(ONLINE_TOGGLE_POS, ONLINE_TOGGLE_SIZE)
    title_coin_rects["online_toggle"] = online_rect

    # Subtle hover outline over the checkbox area only.
    # The clickable/hover rect covers the whole baked checkbox. The X itself is
    # drawn in a smaller inner rect so it cannot sit above or outside the box.
    check_rect = ONLINE_TOGGLE_CHECK_RECT.copy()
    x_rect = ONLINE_TOGGLE_X_RECT.copy()
    if online_rect.collidepoint((mx, my)):
        hover = pygame.Surface(check_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(hover, (255, 225, 145, 75), hover.get_rect(), width=3, border_radius=6)
        screen.blit(hover, check_rect.topleft)

    # Draw the hand-marked X dynamically so the base asset remains unchecked.
    if playing_online_enabled:
        xsurf = pygame.Surface(x_rect.size, pygame.SRCALPHA)
        pad = max(4, int(min(x_rect.w, x_rect.h) * 0.16))
        ink = (98, 48, 10, 235)
        glow = (255, 185, 70, 55)
        pygame.draw.line(xsurf, glow, (pad, pad), (x_rect.w - pad, x_rect.h - pad), 7)
        pygame.draw.line(xsurf, glow, (x_rect.w - pad, pad), (pad, x_rect.h - pad), 7)
        pygame.draw.line(xsurf, ink, (pad, pad), (x_rect.w - pad, x_rect.h - pad), 4)
        pygame.draw.line(xsurf, ink, (x_rect.w - pad, pad), (pad, x_rect.h - pad), 4)
        screen.blit(xsurf, x_rect.topleft)



# --- ENTER / QUIT clickable areas (aligned to the baked artwork buttons) ---
    # These are invisible hit zones; we only draw a subtle hover outline for feedback.
    enter_rect = pygame.Rect(153, 1000, 286, 68)
    quit_rect  = pygame.Rect(462, 1000, 282, 72)
    title_coin_rects["enter"] = enter_rect
    title_coin_rects["quit"] = quit_rect

    mx, my = design_mouse_pos()
    for key, rect in [("enter", enter_rect), ("quit", quit_rect)]:
        if rect.collidepoint((mx,my)):
            s = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(s, (255, 220, 150, 90), s.get_rect(), width=3, border_radius=16)
            screen.blit(s, rect.topleft)

def draw_game():
    draw_table_background()

    # All visible deck stacks are baked into the current table background.
    # We keep the deck hit areas and spawn centers in Board, but draw no
    # independent deck sprites here.

    # Prompt + gameplay elements (positions tuned for portrait table)
    prompt.draw(screen, (140, 280), pygame.font.SysFont(None, 31))

    dice.draw(screen)
    heart_unlock.draw(screen, dice)
    hot_unlock.draw(screen)
    card.draw(screen, pygame.font.SysFont(None, 31))
    # Game-table player names only: keep start-screen text untouched
    players.draw(screen, pygame.font.SysFont(None, 31))

    # Action buttons are baked into the background; keep hit logic but don't draw overlays.

async def main():
    global state, active_field, name_a, name_b, waiting_draw, free_choice, rolled_face
    global in_consequence, in_mirror, window, window_size, _present_rect

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.VIDEORESIZE:
                if not IS_WEB:
                    window_size = (max(320, event.w), max(480, event.h))
                    window = pygame.display.set_mode(window_size, pygame.RESIZABLE)
                    _present_rect = _compute_present_rect(window_size)
                continue

            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                if state == TITLE:
                    if event.key == pygame.K_RETURN:
                        start_game()
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

                elif state == GAME:
                    if event.key == pygame.K_r and buttons["ROLL"].enabled:
                        handle_roll()
                    if event.key == pygame.K_d and buttons["DRAW"].enabled:
                        handle_draw()
                    if event.key == pygame.K_n and buttons["NEXT"].enabled:
                        handle_next()
                    if event.key == pygame.K_s and buttons["SKIP"].enabled:
                        handle_skip()
                    if event.key == pygame.K_m and buttons["MIRROR"].enabled:
                        handle_mirror()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click_pos = window_to_design(event.pos)
                if state == TITLE:
                    global title_mirror_coins, playing_online_enabled
                    box1, box2 = get_title_name_boxes()
                    if box1.collidepoint(click_pos):
                        active_field = 0
                    elif box2.collidepoint(click_pos):
                        active_field = 1

                    # Shared Mirror Coins selector (applies to both players)
                    if title_coin_rects.get("minus_shared") and title_coin_rects["minus_shared"].collidepoint(click_pos):
                        title_mirror_coins = max(TITLE_MIRROR_MIN, title_mirror_coins - 1)
                    if title_coin_rects.get("plus_shared") and title_coin_rects["plus_shared"].collidepoint(click_pos):
                        title_mirror_coins = min(TITLE_MIRROR_MAX, title_mirror_coins + 1)

                    # Online/environment prompt toggle
                    if title_coin_rects.get("online_toggle") and title_coin_rects["online_toggle"].collidepoint(click_pos):
                        playing_online_enabled = not playing_online_enabled

                    # ENTER / QUIT baked-button hit zones
                    if title_coin_rects.get("enter") and title_coin_rects["enter"].collidepoint(click_pos):
                        start_game()
                    if title_coin_rects.get("quit") and title_coin_rects["quit"].collidepoint(click_pos):
                        pygame.quit()
                        sys.exit(0)

                elif state == GAME:
                    if buttons["ROLL"].hit(click_pos):
                        handle_roll()
                    elif buttons["DRAW"].hit(click_pos):
                        handle_draw()
                    elif buttons["NEXT"].hit(click_pos):
                        handle_next()
                    elif buttons["SKIP"].hit(click_pos):
                        handle_skip()
                    elif buttons["MIRROR"].hit(click_pos):
                        handle_mirror()
                    else:
                        if free_choice:
                            chosen = board.hit_deck(click_pos)
                            if chosen:
                                rolled_face = chosen
                                free_choice = False
                                prompt.hide()
                                handle_draw()

        # Updates
        if state == GAME:
            prompt.update(dt)
            players.update(dt)

            if heart_unlock.active:
                heart_unlock.update(dt, dice)
                board.heart_x = heart_unlock.deck_x

            if hot_unlock.active:
                hot_unlock.update(dt, dice)

            dice.update(dt)
            card.update(dt)

            if in_consequence and (not card.visible) and (card.state == "idle"):
                spawn_consequence_after_dissolve(rolled_face)

            set_button_states()

        # Draw
        if state == TITLE:
            draw_title()
        else:
            draw_game()

        present_frame()
        await asyncio.sleep(0)

    pygame.quit()
    sys.exit(0)

asyncio.run(main())
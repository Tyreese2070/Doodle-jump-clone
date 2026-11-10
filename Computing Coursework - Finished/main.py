"""
Jumping Man - an endless vertical platformer.

Controls
    A / D or Left / Right   move (gamepad stick / d-pad also works)
    Esc or P                pause
    F11                     toggle fullscreen
    F3                      toggle FPS counter
    Menus                   mouse, or Up/Down + Enter

The original coursework version is kept in main_original.py.
"""

import array
import json
import math
import os
import pickle
import random
import sys
import time

import pygame

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, "Assets")
SAVE_PATH = os.path.join(BASE_DIR, "save.json")
LEGACY_LEADERBOARD = os.path.join(BASE_DIR, "leaderboard.txt")

W, H = 480, 720
FPS = 60
STEP = 1.0 / FPS

# Physics, all values are per fixed 60 Hz step
GRAVITY = 0.55
MAX_FALL = 20.0
JUMP_VEL = -15.5
SPRING_VEL = -25.0
STOMP_VEL = -17.0
SHIELD_SAVE_VEL = -24.0
ROCKET_VEL = -19.0
MOVE_ACCEL = 0.95
FRICTION = 0.86
MAX_SPEED = 7.8

ROCKET_TIME = 1.6
SHIELD_TIME = 8.0
MAGNET_TIME = 10.0
COMBO_WINDOW = 90  # steps

PLAYER_W, PLAYER_H = 38, 50   # drawn size
HIT_W, HIT_H = 26, 44         # collision box (feet at y)
PLAT_H = 16
MILESTONE_EVERY = 500
LEADERBOARD_SIZE = 10
MAX_NAME = 12

# Palette
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
INK = (28, 38, 56)
INK_SOFT = (90, 104, 128)
ACCENT = (61, 186, 110)
ACCENT_DARK = (34, 128, 72)
GOLD = (255, 196, 54)
SILVER = (200, 210, 222)
BRONZE = (214, 140, 82)
RED = (232, 72, 72)
PANEL = (250, 252, 255)

# Sky zones: (altitude in px, top colour, bottom colour)
SKY_ZONES = [
    (0, (110, 190, 245), (190, 232, 250)),
    (6000, (96, 120, 210), (250, 176, 120)),
    (13000, (30, 34, 92), (120, 70, 140)),
    (22000, (6, 8, 24), (24, 20, 60)),
]

PLATFORM_COLOURS = {
    "normal": (92, 196, 92),
    "moving": (74, 163, 223),
    "vanish": (236, 242, 255),
    "crumble": (176, 122, 74),
    "ground": (92, 196, 92),
}


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_col(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def shade(col, amount):
    """amount > 0 lightens, < 0 darkens."""
    if amount >= 0:
        return lerp_col(col, (255, 255, 255), amount)
    return lerp_col(col, (0, 0, 0), -amount)


def wrap_dx(x_from, x_to):
    """Shortest horizontal distance on a wrapping screen."""
    dx = x_to - x_from
    if dx > W / 2:
        dx -= W
    elif dx < -W / 2:
        dx += W
    return dx


# ---------------------------------------------------------------------------
# Pygame setup
# ---------------------------------------------------------------------------
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
try:
    if not pygame.mixer.get_init():
        pygame.mixer.init()
except pygame.error:
    pass

try:
    SCREEN = pygame.display.set_mode((W, H), pygame.SCALED, vsync=1)
except pygame.error:
    SCREEN = pygame.display.set_mode((W, H), pygame.SCALED)
pygame.display.set_caption("Jumping Man")
CLOCK = pygame.time.Clock()


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------
def load_image(name, size=None, smooth=True):
    try:
        img = pygame.image.load(os.path.join(ASSET_DIR, name)).convert_alpha()
    except (pygame.error, FileNotFoundError):
        img = pygame.Surface(size or (32, 32), pygame.SRCALPHA)
        img.fill((255, 0, 255))
    if size:
        img = (pygame.transform.smoothscale if smooth else pygame.transform.scale)(img, size)
    return img


PLAYER_FRAMES = [load_image("playerjump0%d.png" % i, (PLAYER_W, PLAYER_H), smooth=False) for i in range(1, 6)]
PLAYER_ICON = load_image("PlayerSprite.png", (64, 80))
pygame.display.set_icon(PLAYER_ICON)
APPLE_IMG = load_image("AppleSprite.png", (24, 27))
APPLE_ICON = load_image("AppleSprite.png", (20, 22))
ROCKET_IMG = load_image("jumpboost.png", (18, 34), smooth=False)
SHIELD_IMG = load_image("forcefield.png", (30, 30))
LOGO_IMG = load_image("gameLogo.png", (400, 77))
CLOUD_IMGS = [load_image("cloud%d.png" % i) for i in range(1, 6)]


def make_magnet_image(size=30):
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    r = pygame.Rect(3, 4, size - 6, size - 6)
    pygame.draw.arc(surf, (40, 40, 60), r.inflate(2, 2), math.pi, 2 * math.pi, 9)
    pygame.draw.arc(surf, (226, 58, 58), r, math.pi, 2 * math.pi, 7)
    leg_w = 7
    for x in (r.left, r.right - leg_w):
        pygame.draw.rect(surf, (226, 58, 58), (x, 6, leg_w, r.centery - 5))
        pygame.draw.rect(surf, (220, 224, 232), (x, 3, leg_w, 6))
        pygame.draw.rect(surf, (40, 40, 60), (x, 3, leg_w, r.centery - 2), 1)
    return surf


MAGNET_IMG = make_magnet_image()
ITEM_IMAGES = {"apple": APPLE_IMG, "rocket": ROCKET_IMG, "shield": SHIELD_IMG, "magnet": MAGNET_IMG}
HUD_ICONS = {"rocket": pygame.transform.scale(ROCKET_IMG, (12, 22)),
             "shield": pygame.transform.smoothscale(SHIELD_IMG, (22, 22)),
             "magnet": pygame.transform.smoothscale(MAGNET_IMG, (22, 22))}
ITEM_GLOW = {"apple": (255, 90, 90), "rocket": (255, 200, 60), "shield": (90, 200, 255), "magnet": (255, 120, 200)}

_glow_cache = {}


def glow_surface(radius, colour):
    key = (radius, colour)
    surf = _glow_cache.get(key)
    if surf is None:
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for i in range(radius, 0, -2):
            a = int(70 * (1 - i / radius) ** 1.6)
            pygame.draw.circle(surf, (*colour, a), (radius, radius), i)
        _glow_cache[key] = surf
    return surf


_plat_cache = {}


def platform_surface(kind, w):
    key = (kind, w)
    surf = _plat_cache.get(key)
    if surf is not None:
        return surf
    col = PLATFORM_COLOURS[kind]
    surf = pygame.Surface((w, PLAT_H + 4), pygame.SRCALPHA)
    pygame.draw.rect(surf, (0, 0, 0, 45), (2, 4, w - 2, PLAT_H), border_radius=8)       # drop shadow
    pygame.draw.rect(surf, shade(col, -0.45), (0, 0, w, PLAT_H), border_radius=8)       # outline
    pygame.draw.rect(surf, shade(col, -0.18), (2, 2, w - 4, PLAT_H - 4), border_radius=6)
    pygame.draw.rect(surf, col, (2, 2, w - 4, PLAT_H - 7), border_radius=6)
    pygame.draw.rect(surf, shade(col, 0.45), (7, 3, w - 14, 3), border_radius=2)        # highlight
    if kind == "crumble":
        dark = shade(col, -0.5)
        for cx in range(14, w - 8, 18):
            pygame.draw.lines(surf, dark, False, [(cx, 2), (cx + 4, 7), (cx - 2, 10), (cx + 2, PLAT_H - 2)], 2)
    elif kind == "vanish":
        for cx in range(8, w - 6, 12):
            pygame.draw.circle(surf, (200, 214, 240), (cx, PLAT_H - 5), 2)
    elif kind == "moving":
        mid = PLAT_H // 2
        for d in (-1, 1):
            cx = w // 2 + d * (w // 2 - 12)
            pygame.draw.polygon(surf, shade(col, 0.6), [(cx + d * 4, mid), (cx - d * 2, mid - 4), (cx - d * 2, mid + 4)])
    _plat_cache[key] = surf
    return surf


# Text -----------------------------------------------------------------------
_font_cache = {}
_text_cache = {}


def get_font(size, bold=False):
    key = (size, bold)
    f = _font_cache.get(key)
    if f is None:
        f = pygame.font.Font(None, size)  # bundled font: identical on every machine
        f.bold = bold
        _font_cache[key] = f
    return f


def render_text(text, size, colour, bold=False):
    key = (text, size, colour, bold)
    surf = _text_cache.get(key)
    if surf is None:
        if len(_text_cache) > 800:
            _text_cache.clear()
        surf = get_font(size, bold).render(text, True, colour)
        _text_cache[key] = surf
    return surf


def draw_text(surf, text, size, colour, pos, anchor="topleft", bold=False, shadow=True, alpha=255):
    img = render_text(text, size, colour, bold)
    rect = img.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    if shadow:
        sh = render_text(text, size, (10, 16, 30), bold)
        sh.set_alpha(int(alpha * 0.45))
        surf.blit(sh, rect.move(2, 2))
    img.set_alpha(alpha)
    surf.blit(img, rect)
    return rect


# Audio ----------------------------------------------------------------------
def synth(f0, f1, dur, vol=0.3, wave="sine", noise=0.0):
    """Generate a short sweep sound effect without any extra assets."""
    init = pygame.mixer.get_init()
    if not init or abs(init[1]) != 16:
        return None
    rate, _, channels = init
    n = int(rate * dur)
    buf = array.array("h")
    phase = 0.0
    attack = rate * 0.004
    for i in range(n):
        t = i / n
        phase += 2 * math.pi * lerp(f0, f1, t) / rate
        if wave == "square":
            s = 1.0 if math.sin(phase) > 0 else -1.0
        elif wave == "tri":
            s = 2 / math.pi * math.asin(math.sin(phase))
        else:
            s = math.sin(phase)
        if noise:
            s = s * (1 - noise) + random.uniform(-1, 1) * noise
        env = min(1.0, i / attack) * (1 - t) ** 2
        v = int(clamp(s * env * vol, -1, 1) * 32767)
        buf.extend([v] * channels)
    return pygame.mixer.Sound(buffer=buf)


def synth_seq(notes, note_dur, vol=0.25, wave="square"):
    init = pygame.mixer.get_init()
    if not init or abs(init[1]) != 16:
        return None
    parts = [synth(f, f, note_dur, vol, wave) for f in notes]
    raw = b"".join(p.get_raw() for p in parts)
    return pygame.mixer.Sound(buffer=raw)


class Audio:
    FILES = {
        "jump": ("jumpsound.wav", 0.55),
        "boost": ("bigjumpsound.wav", 0.8),
        "gameover": ("gameoversound.wav", 0.8),
        "shield_up": ("shieldupsound.wav", 0.8),
        "shield_down": ("shielddownsound.wav", 0.8),
        "apple": ("applesound.wav", 0.6),
    }

    def __init__(self, volume):
        self.volume = volume
        self.sounds = {}
        self.enabled = bool(pygame.mixer.get_init())
        if not self.enabled:
            return
        for key, (fname, gain) in self.FILES.items():
            try:
                self.sounds[key] = (pygame.mixer.Sound(os.path.join(ASSET_DIR, fname)), gain)
            except (pygame.error, FileNotFoundError):
                pass
        generated = {
            "spring": (synth(260, 1100, 0.22, 0.22, "square"), 1.0),
            "break": (synth(220, 50, 0.25, 0.5, "sine", noise=0.75), 1.0),
            "stomp": (synth(520, 110, 0.16, 0.3, "square"), 1.0),
            "hurt": (synth(330, 70, 0.45, 0.32, "square", noise=0.25), 1.0),
            "vanish": (synth(900, 1500, 0.12, 0.18, "tri"), 1.0),
            "magnet": (synth(300, 900, 0.3, 0.25, "tri"), 1.0),
            "click": (synth(700, 900, 0.05, 0.18, "square"), 1.0),
            "tick": (synth(1300, 1300, 0.025, 0.08, "tri"), 1.0),
            "milestone": (synth_seq([523, 659, 784, 1047], 0.08), 1.0),
            "best": (synth_seq([784, 988, 1175, 1568, 1568], 0.09, 0.2), 1.0),
        }
        for key, (snd, gain) in generated.items():
            if snd is not None:
                self.sounds[key] = (snd, gain)

    def play(self, name, vol=1.0):
        if not self.enabled or self.volume <= 0:
            return
        entry = self.sounds.get(name)
        if entry:
            snd, gain = entry
            snd.set_volume(clamp(self.volume * gain * vol, 0, 1))
            snd.play()


# ---------------------------------------------------------------------------
# Save data (JSON, replaces the pickle leaderboard)
# ---------------------------------------------------------------------------
class _NoClassUnpickler(pickle.Unpickler):
    """Only allows plain data, so an old leaderboard.txt can be migrated safely.

    find_class is refused outright, so the pickle can only build lists, tuples,
    strings and numbers; it can't import or call anything. Used once, to convert
    the legacy file to save.json.
    """

    def find_class(self, module, name):
        raise pickle.UnpicklingError("blocked %s.%s" % (module, name))


class SaveData:
    def __init__(self):
        self.data = {
            "leaderboard": [],
            "settings": {"volume": 0.7, "shake": True, "particles": True, "fullscreen": False, "show_fps": False},
            "best": 0,
            "last_name": "",
            "stats": {"games": 0, "apples": 0, "stomps": 0, "best_height": 0},
        }
        self.load()

    @property
    def settings(self):
        return self.data["settings"]

    @property
    def leaderboard(self):
        return self.data["leaderboard"]

    def load(self):
        if os.path.exists(SAVE_PATH):
            try:
                with open(SAVE_PATH, encoding="utf-8") as f:
                    loaded = json.load(f)
                for k, v in loaded.items():
                    if isinstance(v, dict) and isinstance(self.data.get(k), dict):
                        self.data[k].update(v)
                    else:
                        self.data[k] = v
            except (OSError, ValueError):
                pass
        else:
            self.migrate_legacy()
            self.write()

    def migrate_legacy(self):
        try:
            with open(LEGACY_LEADERBOARD, "rb") as f:
                old = _NoClassUnpickler(f).load()
            for name, score in old:
                if isinstance(name, str) and isinstance(score, (int, float)) and score > 0 and name != "---":
                    self.add_score(name, int(score), 0, write=False)
            if self.leaderboard:
                self.data["best"] = self.leaderboard[0]["score"]
        except Exception:
            pass

    def write(self):
        tmp = SAVE_PATH + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            os.replace(tmp, SAVE_PATH)
        except OSError:
            pass

    def qualifies(self, score):
        lb = self.leaderboard
        return score > 0 and (len(lb) < LEADERBOARD_SIZE or score > lb[-1]["score"])

    def add_score(self, name, score, height, write=True):
        entry = {"name": name, "score": int(score), "height": int(height), "date": time.strftime("%Y-%m-%d")}
        lb = self.leaderboard
        lb.append(entry)
        lb.sort(key=lambda e: e["score"], reverse=True)
        del lb[LEADERBOARD_SIZE:]
        if write:
            self.write()
        return lb.index(entry) if entry in lb else None


# ---------------------------------------------------------------------------
# World entities
# ---------------------------------------------------------------------------
class Player:
    def __init__(self, x, y):
        self.x = x          # centre x
        self.y = y          # feet y (world)
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1
        self.squash = 0.0
        self.squash_v = 0.0
        self.anim = 0.0
        self.spin = 0.0
        self.alive = True
        self.rocket = 0.0
        self.shield = 0.0
        self.magnet = 0.0
        self.trail = []

    @property
    def centre(self):
        return self.x, self.y - HIT_H / 2

    def rect_at(self, x):
        return pygame.Rect(int(x - HIT_W / 2), int(self.y - HIT_H), HIT_W, HIT_H)


class Platform:
    def __init__(self, x, y, w, kind="normal", vx=0.0):
        self.x = x
        self.y = y          # top surface
        self.w = w
        self.kind = kind
        self.vx = vx
        self.spring = None  # x offset of spring
        self.spring_t = 0.0
        self.broken = False
        self.fall_v = 0.0
        self.break_t = 0
        self.used = False
        self.alpha = 255.0
        self.dead = False
        self.squish = 0.0

    def update(self):
        if self.kind == "moving" and not self.broken:
            self.x += self.vx
            if self.x < 4 or self.x + self.w > W - 4:
                self.vx = -self.vx
                self.x = clamp(self.x, 4, W - 4 - self.w)
        if self.broken:
            self.fall_v += 0.45
            self.y += self.fall_v
            self.break_t += 1
            self.alpha -= 6
        if self.kind == "vanish" and self.used:
            self.alpha -= 14
        if self.alpha <= 0:
            self.dead = True
        self.squish *= 0.8
        self.spring_t = max(0.0, self.spring_t - STEP * 3)

    @property
    def solid(self):
        return not (self.broken or self.dead or (self.kind == "vanish" and self.used))


class Item:
    def __init__(self, kind, x, y, plat=None):
        self.kind = kind
        self.x = x
        self.y = y
        self.plat = plat
        self.ox = (x - plat.x) if plat else 0
        self.t = random.uniform(0, 6.28)
        self.dead = False
        self.free = plat is None
        self.vx = 0.0
        self.vy = 0.0

    def update(self, player, magnet_on):
        self.t += 0.08
        if self.plat is not None and not self.free:
            if self.plat.dead or self.plat.broken or (self.plat.kind == "vanish" and self.plat.used):
                self.free = True
            else:
                self.x = self.plat.x + self.ox
                self.y = self.plat.y - 18
        if magnet_on and self.kind == "apple":
            px, py = player.centre
            dx, dy = wrap_dx(self.x, px), py - self.y
            dist = math.hypot(dx, dy)
            if dist < 230:
                self.free = True
                pull = 1.4 + (230 - dist) / 30
                self.vx = lerp(self.vx, dx / max(dist, 1) * pull * 4, 0.25)
                self.vy = lerp(self.vy, dy / max(dist, 1) * pull * 4, 0.25)
                self.x = (self.x + self.vx) % W
                self.y += self.vy

    @property
    def draw_y(self):
        return self.y + math.sin(self.t) * 3


class Enemy:
    def __init__(self, x, y, kind):
        self.x = x
        self.base_y = y
        self.y = y
        self.kind = kind
        self.r = 19
        self.t = random.uniform(0, 6.28)
        self.speed = random.choice((-1, 1)) * random.uniform(1.0, 2.2) if kind == "flyer" else 0.0
        self.dying = False
        self.vy = 0.0
        self.rot = 0.0
        self.dead = False

    def update(self):
        self.t += 0.05
        if self.dying:
            self.vy += 0.6
            self.y += self.vy
            self.rot += 9
            return
        if self.kind == "flyer":
            self.x += self.speed
            if self.x < self.r or self.x > W - self.r:
                self.speed = -self.speed
                self.x = clamp(self.x, self.r, W - self.r)
        self.y = self.base_y + math.sin(self.t * 1.6) * 8


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "colour", "size", "grav", "drag")

    def __init__(self, x, y, vx, vy, life, colour, size, grav=0.15, drag=0.98):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.colour = colour
        self.size = size
        self.grav = grav
        self.drag = drag


class Popup:
    __slots__ = ("text", "x", "y", "life", "colour", "size")

    def __init__(self, text, x, y, colour=WHITE, size=26):
        self.text, self.x, self.y, self.colour, self.size = text, x, y, colour, size
        self.life = 55


class BgCloud:
    def __init__(self, randomise_y=True):
        img = random.choice(CLOUD_IMGS)
        scale = random.uniform(0.9, 1.9)
        self.img = pygame.transform.smoothscale(img, (int(img.get_width() * scale), int(img.get_height() * scale)))
        self.par = 0.12 + scale * 0.12
        self.x = random.uniform(-100, W)
        self.y = random.uniform(0, H + 200)
        self.speed = random.uniform(0.1, 0.35) * random.choice((-1, 1))


# ---------------------------------------------------------------------------
# World: one run of the game (also used for the attract-mode demo on menus)
# ---------------------------------------------------------------------------
class World:
    def __init__(self, game, demo=False):
        self.game = game
        self.demo = demo
        self.settings = game.save.settings
        self.player = Player(W / 2, 0)
        self.platforms = [Platform(0, 0, W, "ground")]
        self.items = []
        self.enemies = []
        self.particles = []
        self.popups = []
        self.cam_y = -H + 110
        self.next_y = -110
        self.last_enemy_y = -2000
        self.time = 0
        self.max_height = 0
        self.apples = 0
        self.apple_points = 0
        self.stomps = 0
        self.stomp_points = 0
        self.combo = 0
        self.last_apple_t = -999
        self.milestone = 0
        self.banner = None
        self.shake = 0.0
        self.flash = 0.0
        self.dead_timer = 0
        self.finished = False
        self.best_score = 0 if demo else game.save.data["best"]
        self.beat_best = False
        self.stars = [(random.uniform(0, W), random.uniform(0, H), random.choice((1, 1, 1, 2)), random.uniform(0.02, 0.08),
                       random.uniform(0, 6.28)) for _ in range(110)]
        self.clouds = [BgCloud() for _ in range(7)]
        self._sky_key = None
        self._sky = None
        self.generate()

    # -- helpers ----------------------------------------------------------
    @property
    def score(self):
        return int(self.max_height / 10) + self.apple_points + self.stomp_points

    @property
    def height_m(self):
        return int(self.max_height / 10)

    def sfx(self, name, vol=1.0):
        if not self.demo:
            self.game.audio.play(name, vol)

    def add_shake(self, amount):
        self.shake = max(self.shake, amount)

    def burst(self, x, y, n, colours, speed=3.0, life=30, size=4, grav=0.15, spread=math.tau, angle=0.0, drag=0.97):
        if not self.settings.get("particles", True):
            n = max(1, n // 4)
        if len(self.particles) > 600:
            return
        for _ in range(n):
            a = angle + random.uniform(-spread / 2, spread / 2)
            s = random.uniform(speed * 0.3, speed)
            self.particles.append(Particle(x, y, math.cos(a) * s, math.sin(a) * s, random.randint(int(life * 0.6), life),
                                           random.choice(colours), random.uniform(size * 0.6, size), grav, drag))

    def popup(self, text, x, y, colour=WHITE, size=26):
        self.popups.append(Popup(text, x, y, colour, size))

    def difficulty(self, y):
        return clamp(-y / 16000, 0.0, 1.0)

    # -- level generation -------------------------------------------------
    def generate(self):
        while self.next_y > self.cam_y - 260:
            self.spawn_row()

    def spawn_row(self):
        y = self.next_y
        alt = -y
        d = self.difficulty(y)
        gap = random.uniform(48 + 55 * d, 92 + 98 * d)
        w = int(random.uniform(66, 82) - 20 * d)
        x = random.uniform(6, W - w - 6)

        kind, vx = "normal", 0.0
        r = random.random()
        p_move = 0.06 + 0.32 * d if alt > 700 else 0.0
        p_vanish = 0.04 + 0.16 * d if alt > 1800 else 0.0
        if r < p_move:
            kind = "moving"
            vx = random.choice((-1, 1)) * random.uniform(1.0, 1.3 + 2.4 * d)
        elif r < p_move + p_vanish:
            kind = "vanish"
        plat = Platform(x, y, w, kind, vx)
        self.platforms.append(plat)

        # Something on top of the platform
        if kind != "vanish" and random.random() < 0.075:
            plat.spring = random.uniform(6, w - 26)
        elif random.random() < 0.14:
            choices = [("apple", 60), ("shield", 12), ("magnet", 12)]
            if alt > 600:
                choices.append(("rocket", 9 + 6 * d))
            total = sum(c[1] for c in choices)
            pick = random.uniform(0, total)
            for name, weight in choices:
                pick -= weight
                if pick <= 0:
                    break
            self.items.append(Item(name, x + w / 2, y - 18, plat))

        # A trail of apples floating above
        if alt > 300 and random.random() < 0.06:
            cx = x + w / 2
            amp = random.uniform(20, 60)
            for i in range(5):
                ax = cx + math.sin(i / 4 * math.pi) * amp
                self.items.append(Item("apple", ax % W, y - 60 - i * 30))

        # Decoy crumbling platform in the gap
        if alt > 350 and gap > 85 and random.random() < 0.12 + 0.3 * d:
            cw = random.randint(60, 76)
            for _ in range(6):
                cx = random.uniform(6, W - cw - 6)
                if abs((cx + cw / 2) - (x + w / 2)) > 110:
                    break
            self.platforms.append(Platform(cx, y - gap * random.uniform(0.35, 0.65), cw, "crumble"))

        # Enemy hovering in the gap
        if alt > 2500 and y < self.last_enemy_y - 650 and random.random() < 0.05 + 0.12 * d:
            ex = random.uniform(30, W - 30)
            for _ in range(8):
                if abs(ex - (x + w / 2)) > 120:
                    break
                ex = random.uniform(30, W - 30)
            kind_e = "flyer" if alt > 6000 and random.random() < 0.45 else "blob"
            self.enemies.append(Enemy(ex, y - gap / 2 - 30, kind_e))
            self.last_enemy_y = y

        self.next_y -= gap

    # -- simulation -------------------------------------------------------
    def update(self, move):
        p = self.player
        self.time += 1

        if p.alive:
            if move:
                p.vx += move * MOVE_ACCEL
                p.facing = 1 if move > 0 else -1
            else:
                p.vx *= FRICTION
            p.vx = clamp(p.vx, -MAX_SPEED, MAX_SPEED)
            if abs(p.vx) < 0.05:
                p.vx = 0.0
        p.x = (p.x + p.vx) % W

        prev_feet = p.y
        if p.rocket > 0:
            p.rocket -= STEP
            p.vy = ROCKET_VEL
            if p.rocket <= 0:
                p.vy = -9
            if self.time % 2 == 0:
                self.burst(p.x - p.facing * 4, p.y - 6, 3, [(255, 220, 90), (255, 140, 40), (255, 80, 40)],
                           speed=4, life=22, size=6, grav=0.05, spread=0.8, angle=math.pi / 2)
        else:
            p.vy = min(p.vy + GRAVITY, MAX_FALL)
        p.y += p.vy

        if p.alive and p.vy > 0 and p.rocket <= 0:
            self.check_landing(prev_feet)

        # Timers
        if p.shield > 0:
            p.shield -= STEP
            if p.shield <= 0:
                self.sfx("shield_down")
        if p.magnet > 0:
            p.magnet -= STEP

        # Squash & stretch spring
        p.squash_v += -p.squash * 0.28
        p.squash_v *= 0.72
        p.squash += p.squash_v
        if p.spin > 0:
            p.spin = max(0.0, p.spin - 14)
        p.anim += 0.12 + abs(p.vx) * 0.03

        # Afterimage trail when moving fast
        if p.vy < -17 or p.rocket > 0:
            p.trail.append((p.x, p.y))
        elif p.trail:
            p.trail.pop(0)
        if len(p.trail) > 6:
            p.trail.pop(0)

        for pl in self.platforms:
            pl.update()
        for e in self.enemies:
            e.update()
        magnet_on = p.magnet > 0 and p.alive
        for it in self.items:
            it.update(p, magnet_on)

        if p.alive:
            self.check_items()
            self.check_enemies()

        # Camera
        if p.alive:
            target = p.y - H * 0.45
            if target < self.cam_y:
                self.cam_y += (target - self.cam_y) * 0.22
            self.cam_y = min(self.cam_y, p.y - HIT_H - 70)
        else:
            self.dead_timer += 1
            if self.death_by_fall:
                self.cam_y += (p.y - H * 0.5 - self.cam_y) * 0.12
            if self.dead_timer > 75:
                self.finished = True

        # Scoring and milestones
        if p.alive:
            self.max_height = max(self.max_height, -p.y)
            m = self.height_m // MILESTONE_EVERY
            if m > self.milestone:
                self.milestone = m
                self.banner = ["%dm!" % (m * MILESTONE_EVERY), 0]
                self.sfx("milestone")
                self.burst(W / 2, self.cam_y + H * 0.3, 40, [GOLD, ACCENT, (90, 200, 255), RED, WHITE],
                           speed=7, life=60, size=5, grav=0.12)
            if not self.demo and not self.beat_best and self.best_score > 0 and self.score > self.best_score:
                self.beat_best = True
                self.sfx("best")
                self.popup("NEW BEST!", p.x, p.y - 70, GOLD, 34)
                self.flash = 0.6

        # Death by falling
        if p.alive and p.y - HIT_H > self.cam_y + H + 10:
            if p.shield > 0:
                p.shield = 0
                p.vy = SHIELD_SAVE_VEL
                p.y = self.cam_y + H + HIT_H
                self.sfx("shield_down")
                self.add_shake(10)
                self.flash = 0.5
                self.burst(p.x, self.cam_y + H - 10, 40, [(120, 210, 255), WHITE], speed=8, life=40, size=5,
                           spread=math.pi, angle=-math.pi / 2)
                self.popup("SAVED!", p.x, self.cam_y + H - 80, (140, 220, 255), 32)
            else:
                self.kill(fell=True)

        # Generation & cleanup
        if p.alive:
            self.generate()
        bottom = self.cam_y + H + 320
        self.platforms = [pl for pl in self.platforms if not pl.dead and pl.y < bottom]
        self.items = [it for it in self.items if not it.dead and it.y < bottom]
        self.enemies = [e for e in self.enemies if not e.dead and e.y < bottom + 400]

        for pt in self.particles:
            pt.vx *= pt.drag
            pt.vy = pt.vy * pt.drag + pt.grav
            pt.x += pt.vx
            pt.y += pt.vy
            pt.life -= 1
        self.particles = [pt for pt in self.particles if pt.life > 0]
        for pu in self.popups:
            pu.y -= 1.1
            pu.life -= 1
        self.popups = [pu for pu in self.popups if pu.life > 0]

        if self.banner:
            self.banner[1] += 1
            if self.banner[1] > 110:
                self.banner = None
        self.shake *= 0.86
        self.flash = max(0.0, self.flash - 0.04)

    death_by_fall = False

    def check_landing(self, prev_feet):
        p = self.player
        left, right = p.x - HIT_W / 2 + 3, p.x + HIT_W / 2 - 3
        best, best_off = None, 0
        for pl in self.platforms:
            if not pl.solid or not (prev_feet <= pl.y + 1 and p.y >= pl.y):
                continue
            for off in (0, W, -W):
                if right + off > pl.x and left + off < pl.x + pl.w:
                    if best is None or pl.y < best.y:
                        best, best_off = pl, off
                    break
        if best is not None:
            self.land(best, best_off)

    def land(self, pl, off):
        p = self.player
        if pl.kind == "crumble":
            pl.broken = True
            self.sfx("break")
            self.burst(pl.x + pl.w / 2, pl.y + 6, 16, [(176, 122, 74), (120, 80, 46), (210, 160, 110)],
                       speed=4, life=40, size=5, grav=0.3)
            p.vy *= 0.6
            return
        p.y = pl.y
        feet_x = p.x + off
        if pl.spring is not None and pl.x + pl.spring - 4 <= feet_x <= pl.x + pl.spring + 24:
            p.vy = SPRING_VEL
            pl.spring_t = 1.0
            p.spin = 360
            self.sfx("spring")
            self.add_shake(4)
            self.burst(feet_x, pl.y, 14, [WHITE, (255, 240, 160)], speed=5, life=26, size=4,
                       spread=math.pi, angle=-math.pi / 2)
        else:
            p.vy = JUMP_VEL
            self.sfx("jump")
            self.burst(feet_x, pl.y, 8, [WHITE, shade(PLATFORM_COLOURS[pl.kind], 0.4)], speed=2.4, life=22,
                       size=4, grav=0.02, spread=math.pi * 0.7, angle=-math.pi / 2)
        p.squash = 0.32
        p.squash_v = 0.0
        pl.squish = 1.0
        if pl.kind == "vanish":
            pl.used = True
            self.sfx("vanish")
            self.burst(pl.x + pl.w / 2, pl.y + 6, 18, [WHITE, (220, 230, 255)], speed=3, life=34, size=6, grav=-0.02)

    def check_items(self):
        p = self.player
        px, py = p.centre
        for it in self.items:
            if it.dead:
                continue
            if abs(wrap_dx(px, it.x)) < 26 and abs(py - it.draw_y) < 32:
                it.dead = True
                self.collect(it)

    def collect(self, it):
        p = self.player
        colour = ITEM_GLOW[it.kind]
        self.burst(it.x, it.y, 14, [colour, WHITE], speed=4, life=28, size=4, grav=0.05)
        if it.kind == "apple":
            if self.time - self.last_apple_t <= COMBO_WINDOW:
                self.combo = min(self.combo + 1, 5)
            else:
                self.combo = 1
            self.last_apple_t = self.time
            pts = 10 * self.combo
            self.apples += 1
            self.apple_points += pts
            self.sfx("apple", 0.7 + 0.08 * self.combo)
            self.popup("+%d" % pts + (" x%d" % self.combo if self.combo > 1 else ""), it.x, it.y - 10,
                       (255, 236, 120) if self.combo > 1 else WHITE, 22 + self.combo * 2)
        elif it.kind == "rocket":
            p.rocket = ROCKET_TIME
            p.vy = ROCKET_VEL
            self.sfx("boost")
            self.add_shake(6)
            self.popup("ROCKET!", it.x, it.y - 20, GOLD, 30)
        elif it.kind == "shield":
            p.shield = SHIELD_TIME
            self.sfx("shield_up")
            self.popup("SHIELD", it.x, it.y - 20, (140, 220, 255), 28)
        elif it.kind == "magnet":
            p.magnet = MAGNET_TIME
            self.sfx("magnet")
            self.popup("MAGNET", it.x, it.y - 20, (255, 150, 210), 28)

    def check_enemies(self):
        p = self.player
        for e in self.enemies:
            if e.dying:
                continue
            for off in (0, W, -W):
                rect = p.rect_at(p.x + off).inflate(-6, -6)
                cx = clamp(e.x, rect.left, rect.right)
                cy = clamp(e.y, rect.top, rect.bottom)
                if (cx - e.x) ** 2 + (cy - e.y) ** 2 < (e.r - 2) ** 2:
                    break
            else:
                continue
            if p.rocket > 0 or p.shield > 0:
                self.defeat_enemy(e, 100)
            elif p.vy > 0 and p.y < e.y + 4:
                p.vy = STOMP_VEL
                p.squash = 0.3
                self.defeat_enemy(e, 50)
            else:
                self.kill(fell=False)
                return

    def defeat_enemy(self, e, pts):
        e.dying = True
        e.vy = -4
        self.stomps += 1
        self.stomp_points += pts
        self.sfx("stomp")
        self.add_shake(6)
        self.burst(e.x, e.y, 20, [(160, 90, 220), (90, 40, 150), WHITE], speed=5, life=30, size=5)
        self.popup("+%d" % pts, e.x, e.y - 30, (220, 170, 255), 28)

    def kill(self, fell):
        p = self.player
        if not p.alive:
            return
        p.alive = False
        p.rocket = p.shield = p.magnet = 0
        self.death_by_fall = fell
        self.add_shake(14 if not fell else 8)
        self.flash = 0.7 if not fell else 0.3
        if fell:
            self.sfx("gameover")
        else:
            self.sfx("hurt")
            self.sfx("gameover", 0.7)
            p.vy = -10
            p.vx = 0
            p.spin = 720
            self.burst(p.x, p.y - HIT_H / 2, 26, [RED, WHITE, (255, 200, 80)], speed=6, life=34, size=5)

    # -- drawing ----------------------------------------------------------
    def draw_sky(self, surf):
        alt = max(0.0, -self.cam_y)
        key = int(alt // 40)
        if key != self._sky_key:
            self._sky_key = key
            z0 = SKY_ZONES[0]
            z1 = SKY_ZONES[-1]
            t = 1.0
            for a, b in zip(SKY_ZONES, SKY_ZONES[1:]):
                if a[0] <= alt < b[0]:
                    z0, z1 = a, b
                    t = (alt - a[0]) / (b[0] - a[0])
                    t = t * t * (3 - 2 * t)
                    break
            else:
                z0 = z1 = SKY_ZONES[-1]
            top = lerp_col(z0[1], z1[1], t)
            bot = lerp_col(z0[2], z1[2], t)
            grad = pygame.Surface((1, 2))
            grad.set_at((0, 0), top)
            grad.set_at((0, 1), bot)
            self._sky = pygame.transform.smoothscale(grad, (W, H))
        surf.blit(self._sky, (0, 0))

        star_a = clamp((alt - 9000) / 9000, 0, 1)
        if star_a > 0:
            for (sx, sy, size, par, ph) in self.stars:
                y = (sy + alt * par) % H
                tw = 0.6 + 0.4 * math.sin(self.time * 0.05 + ph)
                c = int(255 * star_a * tw)
                if size == 1:
                    surf.fill((c, c, min(255, c + 20)), (int(sx), int(y), 2, 2))
                else:
                    pygame.draw.circle(surf, (c, c, min(255, c + 30)), (int(sx), int(y)), 2)

        cloud_a = int(255 * clamp(1 - (alt - 8000) / 10000, 0.15, 1))
        span = H + 240
        for c in self.clouds:
            c.x += c.speed
            if c.x > W + 20:
                c.x = -c.img.get_width() - 20
            elif c.x < -c.img.get_width() - 20:
                c.x = W + 20
            y = (c.y + alt * c.par) % span - 120
            c.img.set_alpha(cloud_a)
            surf.blit(c.img, (int(c.x), int(y)))

    def draw(self, surf):
        ox = oy = 0
        if self.shake > 0.3 and self.settings.get("shake", True):
            ox = random.uniform(-self.shake, self.shake)
            oy = random.uniform(-self.shake, self.shake)
        cam = self.cam_y - oy
        self.draw_sky(surf)

        # Best height marker
        if not self.demo and self.best_score > 0 and not self.beat_best:
            by = -self.best_score * 10 - cam
            if -20 < by < H + 20:
                for x in range(0, W, 24):
                    pygame.draw.line(surf, GOLD, (x + ox, by), (x + 12 + ox, by), 3)
                draw_text(surf, "BEST", 20, GOLD, (W - 8, by - 4), "bottomright", bold=True)

        for pl in self.platforms:
            self.draw_platform(surf, pl, ox, cam)
        for it in self.items:
            self.draw_item(surf, it, ox, cam)
        for e in self.enemies:
            self.draw_enemy(surf, e, ox, cam)
        self.draw_player(surf, ox, cam)

        for pt in self.particles:
            t = pt.life / pt.max_life
            r = max(1, int(pt.size * t))
            pygame.draw.circle(surf, pt.colour, (int(pt.x + ox), int(pt.y - cam)), r)
        for pu in self.popups:
            a = int(255 * clamp(pu.life / 20, 0, 1))
            draw_text(surf, pu.text, pu.size, pu.colour, (pu.x + ox, pu.y - cam), "center", bold=True, alpha=a)

        if self.flash > 0:
            fl = pygame.Surface((W, H))
            fl.fill(WHITE)
            fl.set_alpha(int(150 * self.flash))
            surf.blit(fl, (0, 0))

    def draw_platform(self, surf, pl, ox, cam):
        sy = pl.y - cam
        if sy < -40 or sy > H + 40:
            return
        if pl.kind == "ground":
            gy = int(sy)
            pygame.draw.rect(surf, (120, 84, 52), (0, gy + 14, W, H))
            pygame.draw.rect(surf, (92, 196, 92), (0, gy, W, 16))
            pygame.draw.rect(surf, (150, 230, 140), (0, gy, W, 4))
            for x in range(6, W, 22):
                pygame.draw.circle(surf, (100, 70, 44), (x + (x * 7) % 9, gy + 34 + (x * 13) % 30), 3)
            return
        img = platform_surface(pl.kind, pl.w)
        sx = pl.x + ox
        dip = pl.squish * 4
        if pl.broken:
            half = pl.w // 2
            for i, sign in enumerate((-1, 1)):
                piece = img.subsurface((i * half, 0, half if i == 0 else pl.w - half, PLAT_H + 4))
                rot = pygame.transform.rotate(piece, -sign * pl.break_t * 3)
                rot.set_alpha(int(clamp(pl.alpha, 0, 255)))
                cx = sx + i * half + half / 2 + sign * pl.break_t * 1.2
                surf.blit(rot, rot.get_rect(center=(cx, sy + PLAT_H / 2)))
            return
        if pl.alpha < 255:
            img = img.copy()
            img.set_alpha(int(clamp(pl.alpha, 0, 255)))
        surf.blit(img, (sx, sy + dip))
        if pl.spring is not None:
            self.draw_spring(surf, sx + pl.spring, sy + dip, pl.spring_t)

    def draw_spring(self, surf, x, y, t):
        ext = 10 + 14 * t
        base = y + 2
        top = base - ext
        coils = 4
        pts = []
        for i in range(coils * 2 + 1):
            py = base - ext * i / (coils * 2)
            px = x + (4 if i % 2 else 16)
            pts.append((px, py))
        pygame.draw.lines(surf, (70, 76, 90), False, pts, 3)
        pygame.draw.lines(surf, (200, 206, 220), False, pts, 1)
        pygame.draw.rect(surf, (60, 20, 20), (x - 1, top - 6, 22, 7), border_radius=3)
        pygame.draw.rect(surf, RED, (x, top - 5, 20, 5), border_radius=3)

    def draw_item(self, surf, it, ox, cam):
        sy = it.draw_y - cam
        if sy < -40 or sy > H + 40:
            return
        img = ITEM_IMAGES[it.kind]
        pulse = 0.85 + 0.15 * math.sin(it.t * 2)
        g = glow_surface(26, ITEM_GLOW[it.kind])
        g.set_alpha(int(255 * pulse))
        surf.blit(g, g.get_rect(center=(it.x + ox, sy)))
        surf.blit(img, img.get_rect(center=(it.x + ox, sy)))

    def draw_enemy(self, surf, e, ox, cam):
        sx, sy = e.x + ox, e.y - cam
        if sy < -60 or sy > H + 60:
            return
        size = 64
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size // 2
        body = (130, 70, 200) if e.kind == "blob" else (210, 70, 110)
        dark = shade(body, -0.45)
        if e.kind == "flyer":
            flap = math.sin(self.time * 0.5) * 6
            for d in (-1, 1):
                pygame.draw.ellipse(s, (235, 240, 255), (c + d * 18 - 9, c - 16 - flap, 18, 12))
                pygame.draw.ellipse(s, dark, (c + d * 18 - 9, c - 16 - flap, 18, 12), 2)
        spikes = 9
        for i in range(spikes):
            a = i / spikes * math.tau + e.t * 0.6
            p1 = (c + math.cos(a) * (e.r + 8), c + math.sin(a) * (e.r + 8))
            p2 = (c + math.cos(a + 0.3) * (e.r - 2), c + math.sin(a + 0.3) * (e.r - 2))
            p3 = (c + math.cos(a - 0.3) * (e.r - 2), c + math.sin(a - 0.3) * (e.r - 2))
            pygame.draw.polygon(s, dark, (p1, p2, p3))
        pygame.draw.circle(s, dark, (c, c), e.r + 1)
        pygame.draw.circle(s, body, (c, c), e.r - 1)
        pygame.draw.circle(s, shade(body, 0.35), (c - 6, c - 7), 5)
        # Eyes track the player
        p = self.player
        dx, dy = wrap_dx(e.x, p.x), (p.y - HIT_H / 2) - e.y
        dist = max(1.0, math.hypot(dx, dy))
        lx, ly = dx / dist * 2.5, dy / dist * 2.5
        for d in (-1, 1):
            ex, ey = c + d * 7, c - 1
            pygame.draw.circle(s, WHITE, (ex, ey), 6)
            pygame.draw.circle(s, INK, (int(ex + lx), int(ey + ly)), 3)
            pygame.draw.line(s, INK, (ex - 6 * d, ey - 9), (ex + 4 * d, ey - 5), 3)
        pygame.draw.arc(s, INK, (c - 6, c + 5, 12, 8), 0.2, math.pi - 0.2, 2)
        if e.dying:
            s = pygame.transform.rotozoom(s, e.rot, 1.0)
            s.set_alpha(200)
        surf.blit(s, s.get_rect(center=(sx, sy)))

    def player_image(self):
        p = self.player
        if p.alive and (abs(p.vx) > 0.6):
            frame = PLAYER_FRAMES[int(p.anim) % len(PLAYER_FRAMES)]
        else:
            frame = PLAYER_FRAMES[0]
        if p.facing < 0:
            frame = pygame.transform.flip(frame, True, False)
        stretch = clamp(abs(p.vy) / 70, 0, 0.14) if p.alive else 0
        sx = 1 + p.squash - stretch * 0.6
        sy = 1 - p.squash + stretch
        img = pygame.transform.scale(frame, (max(4, int(PLAYER_W * sx)), max(4, int(PLAYER_H * sy))))
        angle = -p.vx * 1.6 + (p.spin * -p.facing if p.spin else 0)
        if angle:
            img = pygame.transform.rotate(img, angle)
        return img

    def draw_player(self, surf, ox, cam):
        p = self.player
        img = self.player_image()
        sy = p.y - cam
        # Afterimages
        for i, (tx, ty) in enumerate(p.trail):
            ghost = img.copy()
            ghost.set_alpha(30 + i * 18)
            surf.blit(ghost, ghost.get_rect(midbottom=(tx + ox, ty - cam + 2)))
        offsets = [0]
        if p.x < PLAYER_W:
            offsets.append(W)
        elif p.x > W - PLAYER_W:
            offsets.append(-W)
        for off in offsets:
            x = p.x + ox + off
            if p.magnet > 0 and (p.magnet > 2 or int(p.magnet * 8) % 2):
                ring = int(40 + (self.time % 30) * 2)
                pygame.draw.circle(surf, (255, 130, 210), (int(x), int(sy - HIT_H / 2)), ring, 1)
                surf.blit(MAGNET_IMG, MAGNET_IMG.get_rect(center=(x, sy - PLAYER_H - 14)))
            if p.rocket > 0:
                surf.blit(ROCKET_IMG, ROCKET_IMG.get_rect(center=(x - p.facing * 14, sy - 22)))
            surf.blit(img, img.get_rect(midbottom=(x, sy + 2)))
            if p.shield > 0 and (p.shield > 2 or int(p.shield * 8) % 2):
                r = 34 + int(math.sin(self.time * 0.15) * 2)
                bubble = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(bubble, (120, 210, 255, 55), (r + 2, r + 2), r)
                pygame.draw.circle(bubble, (180, 235, 255, 200), (r + 2, r + 2), r, 3)
                pygame.draw.arc(bubble, (255, 255, 255, 220), (8, 8, r * 2 - 12, r * 2 - 12), 1.9, 2.8, 3)
                surf.blit(bubble, bubble.get_rect(center=(x, sy - HIT_H / 2)))


# ---------------------------------------------------------------------------
# UI widgets
# ---------------------------------------------------------------------------
class Button:
    def __init__(self, label, action, w=260, h=54, style="primary", hint=""):
        self.label = label          # str or callable returning str
        self.action = action
        self.rect = pygame.Rect(0, 0, w, h)
        self.style = style
        self.hint = hint
        self.hover = 0.0
        self.enabled = True

    def text(self):
        return self.label() if callable(self.label) else self.label

    def update(self, active):
        self.hover += ((1.0 if active and self.enabled else 0.0) - self.hover) * 0.3

    def draw(self, surf):
        base = {"primary": ACCENT, "secondary": (82, 112, 160), "danger": (210, 80, 80)}[self.style]
        if not self.enabled:
            base = (150, 156, 168)
        scale = 1 + 0.05 * self.hover
        r = self.rect.copy()
        r.width, r.height = int(r.width * scale), int(r.height * scale)
        r.center = self.rect.center
        lift = int(3 * self.hover)
        r.y -= lift
        shadow = r.move(0, 5 + lift)
        pygame.draw.rect(surf, shade(base, -0.5), shadow, border_radius=14)
        pygame.draw.rect(surf, shade(base, 0.12 * self.hover), r, border_radius=14)
        pygame.draw.rect(surf, shade(base, 0.35), (r.x + 8, r.y + 4, r.width - 16, 6), border_radius=3)
        if self.hover > 0.05:
            pygame.draw.rect(surf, WHITE, r.inflate(4, 4), 2, border_radius=16)
        draw_text(surf, self.text(), 32, WHITE, r.center, "center", bold=True)
        if self.hint:
            draw_text(surf, self.hint, 18, shade(base, 0.6), (r.right - 10, r.centery), "midright", shadow=False)


class ButtonList:
    """Vertical list of buttons with mouse + keyboard + gamepad navigation."""

    def __init__(self, game, buttons, top, gap=14):
        self.game = game
        self.buttons = buttons
        self.selected = 0
        self.top = top
        self.gap = gap
        self.layout()

    def layout(self):
        y = self.top
        for b in self.buttons:
            b.rect.midtop = (W // 2, y)
            y += b.rect.height + self.gap

    def move(self, d):
        n = len(self.buttons)
        for _ in range(n):
            self.selected = (self.selected + d) % n
            if self.buttons[self.selected].enabled:
                break
        self.game.audio.play("tick")

    def handle(self, event):
        if event.type == pygame.MOUSEMOTION:
            for i, b in enumerate(self.buttons):
                if b.rect.collidepoint(event.pos) and b.enabled and i != self.selected:
                    self.selected = i
                    self.game.audio.play("tick")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, b in enumerate(self.buttons):
                if b.rect.collidepoint(event.pos) and b.enabled:
                    self.selected = i
                    self.activate(b)
                    return True
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.move(-1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.move(1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                b = self.buttons[self.selected]
                if b.enabled:
                    self.activate(b)
                    return True
        elif event.type == pygame.JOYHATMOTION:
            if event.value[1]:
                self.move(-event.value[1])
        elif event.type == pygame.JOYBUTTONDOWN and event.button == 0:
            b = self.buttons[self.selected]
            if b.enabled:
                self.activate(b)
                return True
        return False

    def activate(self, b):
        self.game.audio.play("click")
        b.action()

    def update(self):
        for i, b in enumerate(self.buttons):
            b.update(i == self.selected)

    def draw(self, surf):
        for b in self.buttons:
            b.draw(surf)


def draw_panel(surf, rect, alpha=235):
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, (0, 0, 0, 60), panel.get_rect().move(0, 6), border_radius=22)
    pygame.draw.rect(panel, (*PANEL, alpha), panel.get_rect().inflate(0, -6).move(0, -3), border_radius=22)
    pygame.draw.rect(panel, (*INK, 40), panel.get_rect().inflate(0, -6).move(0, -3), 2, border_radius=22)
    surf.blit(panel, rect.topleft)


def dim(surf, alpha=120, colour=(10, 16, 34)):
    d = pygame.Surface((W, H))
    d.fill(colour)
    d.set_alpha(alpha)
    surf.blit(d, (0, 0))


# ---------------------------------------------------------------------------
# Game: state machine for menus and play
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        self.save = SaveData()
        self.audio = Audio(self.save.settings.get("volume", 0.7))
        self.running = True
        self.state = "menu"
        self.prev_state = "menu"
        self.world = World(self, demo=True)
        self.demo_ai_target = None
        self.fade = 1.0
        self.time = 0
        self.joy = None
        self.reset_confirm = 0
        self.highlight_rank = None
        self.result = None
        self.name_input = ""
        self.entering_name = False
        self.submit_rect = pygame.Rect(0, 0, 0, 0)
        if self.save.settings.get("fullscreen"):
            self.toggle_fullscreen(save=False)
        self.init_joystick()
        self.build_menus()

    # -- setup ------------------------------------------------------------
    def init_joystick(self):
        try:
            if pygame.joystick.get_count() > 0:
                self.joy = pygame.joystick.Joystick(0)
        except pygame.error:
            self.joy = None

    def build_menus(self):
        s = self.save.settings
        self.main_menu = ButtonList(self, [
            Button("Play", self.start_game, hint="Enter"),
            Button("Leaderboard", lambda: self.goto("leaderboard"), style="secondary"),
            Button("How to Play", lambda: self.goto("help"), style="secondary"),
            Button("Options", lambda: self.goto("options"), style="secondary"),
            Button("Quit", self.quit, style="danger"),
        ], top=300)
        self.pause_menu = ButtonList(self, [
            Button("Resume", self.resume, hint="Esc"),
            Button("Restart", self.start_game, style="secondary"),
            Button("Options", lambda: self.goto("options"), style="secondary"),
            Button("Main Menu", self.to_menu, style="danger"),
        ], top=290)
        self.options_menu = ButtonList(self, [
            Button(lambda: "Sound  < %d%% >" % round(self.audio.volume * 100), self.cycle_volume, w=320),
            Button(lambda: "Screen Shake: %s" % ("On" if s["shake"] else "Off"), lambda: self.toggle("shake"), w=320),
            Button(lambda: "Particles: %s" % ("High" if s["particles"] else "Low"), lambda: self.toggle("particles"), w=320),
            Button(lambda: "Fullscreen: %s" % ("On" if s["fullscreen"] else "Off"), self.toggle_fullscreen, w=320),
            Button(lambda: "Show FPS: %s" % ("On" if s["show_fps"] else "Off"), lambda: self.toggle("show_fps"), w=320),
            Button(lambda: "Click again to confirm" if self.reset_confirm > 0 else "Reset Scores", self.reset_scores,
                   w=320, style="danger"),
            Button("Back", self.back, w=320, style="secondary", hint="Esc"),
        ], top=170, gap=10)
        for b in self.options_menu.buttons:
            b.rect.height = 50
        self.options_menu.layout()
        self.back_only = ButtonList(self, [Button("Back", self.back, style="secondary", hint="Esc")], top=H - 92)
        self.gameover_menu = ButtonList(self, [
            Button("Play Again", self.start_game, hint="R"),
            Button("Main Menu", self.to_menu, style="secondary", hint="M"),
        ], top=H - 170)

    # -- actions ----------------------------------------------------------
    def goto(self, state):
        if state in ("options", "leaderboard", "help"):
            self.prev_state = self.state
        if state == "options":
            self.options_menu.selected = 0
        self.state = state

    def back(self):
        self.state = self.prev_state if self.prev_state in ("menu", "pause") else "menu"

    def start_game(self):
        self.world = World(self)
        self.state = "play"
        self.fade = 1.0
        self.result = None
        self.entering_name = False
        self.highlight_rank = None

    def resume(self):
        self.state = "play"

    def pause(self):
        if self.state == "play":
            self.state = "pause"
            self.pause_menu.selected = 0
            self.audio.play("click")

    def to_menu(self):
        self.world = World(self, demo=True)
        self.state = "menu"
        self.fade = 1.0
        self.main_menu.selected = 0

    def quit(self):
        self.running = False

    def toggle(self, key):
        self.save.settings[key] = not self.save.settings[key]
        self.save.write()

    def cycle_volume(self, step=0.1, wrap=True):
        v = round(self.audio.volume + step, 2)
        if wrap and v > 1.001:
            v = 0.0
        self.audio.volume = clamp(v, 0.0, 1.0)
        self.save.settings["volume"] = self.audio.volume
        self.save.write()
        self.audio.play("apple")

    def toggle_fullscreen(self, save=True):
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            return
        if save:
            self.save.settings["fullscreen"] = not self.save.settings["fullscreen"]
            self.save.write()

    def reset_scores(self):
        if self.reset_confirm > 0:
            self.save.data["leaderboard"] = []
            self.save.data["best"] = 0
            self.save.write()
            self.reset_confirm = 0
            self.audio.play("break")
        else:
            self.reset_confirm = 180

    def finish_run(self):
        w = self.world
        save = self.save
        score = w.score
        stats = save.data["stats"]
        stats["games"] += 1
        stats["apples"] += w.apples
        stats["stomps"] += w.stomps
        stats["best_height"] = max(stats["best_height"], w.height_m)
        new_best = score > save.data["best"]
        if new_best:
            save.data["best"] = score
        save.write()
        self.result = {"score": score, "height": w.height_m, "apples": w.apples, "stomps": w.stomps,
                       "new_best": new_best, "best": save.data["best"], "t": 0}
        self.entering_name = save.qualifies(score)
        self.name_input = save.data.get("last_name", "")
        self.gameover_menu.selected = 0
        self.state = "gameover"

    def submit_name(self):
        name = self.name_input.strip() or "Player"
        self.save.data["last_name"] = name
        self.highlight_rank = self.save.add_score(name, self.result["score"], self.result["height"])
        self.entering_name = False
        self.audio.play("milestone")

    # -- input ------------------------------------------------------------
    def move_input(self):
        keys = pygame.key.get_pressed()
        move = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move += 1
        if self.joy is not None:
            try:
                ax = self.joy.get_axis(0)
                if abs(ax) > 0.25:
                    move = ax
                if self.joy.get_numhats():
                    hx = self.joy.get_hat(0)[0]
                    if hx:
                        move = hx
            except pygame.error:
                pass
        return move

    def demo_move(self):
        """Simple autopilot so the menu background plays itself."""
        w = self.world
        p = w.player
        rise = (p.vy * p.vy) / (2 * GRAVITY) if p.vy < 0 else 0
        target = None
        for pl in w.platforms:
            if not pl.solid or pl.kind == "crumble" or pl.kind == "ground":
                continue
            if p.vy < 0:
                ok = p.y - rise + 15 <= pl.y < p.y - 10
            else:
                ok = pl.y >= p.y
            if ok and (target is None or (pl.y < target.y if p.vy < 0 else pl.y < target.y)):
                target = pl
        if target is None:
            return 0
        dx = wrap_dx(p.x, target.x + target.w / 2)
        if abs(dx) < 10:
            return 0
        return 1 if dx > 0 else -1

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue
            if event.type == pygame.JOYDEVICEADDED and self.joy is None:
                self.init_joystick()
            if event.type == pygame.WINDOWFOCUSLOST and self.state == "play":
                self.pause()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                    continue
                if event.key == pygame.K_F3:
                    self.toggle("show_fps")
                    continue

            st = self.state
            if st == "menu":
                self.main_menu.handle(event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.quit()
            elif st == "play":
                if (event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p)) or \
                        (event.type == pygame.JOYBUTTONDOWN and event.button in (6, 7)):
                    self.pause()
            elif st == "pause":
                if (event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p)) or \
                        (event.type == pygame.JOYBUTTONDOWN and event.button in (1, 6, 7)):
                    self.resume()
                else:
                    self.pause_menu.handle(event)
            elif st == "options":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.back()
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d) \
                        and self.options_menu.selected == 0:
                    self.cycle_volume(0.1 if event.key in (pygame.K_RIGHT, pygame.K_d) else -0.1, wrap=False)
                else:
                    self.options_menu.handle(event)
            elif st in ("leaderboard", "help"):
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    self.back()
                else:
                    self.back_only.handle(event)
            elif st == "gameover":
                self.handle_gameover_event(event)

    def handle_gameover_event(self, event):
        if self.result is None or self.result["t"] < 40:
            return
        if self.entering_name:
            if event.type == pygame.TEXTINPUT:
                for ch in event.text:
                    if (ch.isalnum() or ch in " _-") and len(self.name_input) < MAX_NAME:
                        self.name_input += ch
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    self.name_input = self.name_input[:-1]
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.submit_name()
                elif event.key == pygame.K_ESCAPE:
                    self.entering_name = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.submit_rect.collidepoint(event.pos):
                self.submit_name()
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self.start_game()
                return
            if event.key in (pygame.K_m, pygame.K_ESCAPE):
                self.to_menu()
                return
            if event.key == pygame.K_l:
                self.to_menu()
                self.goto("leaderboard")
                return
        self.gameover_menu.handle(event)

    # -- update -----------------------------------------------------------
    def update(self):
        self.time += 1
        self.fade = max(0.0, self.fade - 0.06)
        if self.reset_confirm > 0:
            self.reset_confirm -= 1
        st = self.state
        if st in ("menu", "leaderboard", "help") or (st == "options" and self.world.demo):
            self.world.update(self.demo_move())
            if self.world.finished or self.world.player.y > 400:
                self.world = World(self, demo=True)
        elif st == "play":
            self.world.update(self.move_input())
            if self.world.finished:
                self.finish_run()
        elif st == "gameover":
            self.world.update(0)
            self.result["t"] += 1

        menus = {"menu": self.main_menu, "pause": self.pause_menu, "options": self.options_menu,
                 "leaderboard": self.back_only, "help": self.back_only, "gameover": self.gameover_menu}
        if st in menus:
            menus[st].update()

    # -- drawing ----------------------------------------------------------
    def draw(self):
        surf = SCREEN
        st = self.state
        self.world.draw(surf)

        if st == "play":
            self.draw_hud(surf)
        elif st == "menu":
            self.draw_menu(surf)
        elif st == "pause":
            self.draw_hud(surf)
            dim(surf, 150)
            draw_text(surf, "PAUSED", 64, WHITE, (W / 2, 200), "center", bold=True)
            draw_text(surf, "Height %dm   Score %d" % (self.world.height_m, self.world.score), 26, (210, 220, 240),
                      (W / 2, 245), "center")
            self.pause_menu.draw(surf)
        elif st == "options":
            dim(surf, 150)
            draw_text(surf, "OPTIONS", 56, WHITE, (W / 2, 110), "center", bold=True)
            self.options_menu.draw(surf)
            draw_text(surf, "Left/Right adjusts sound  -  F11 fullscreen", 20, (190, 200, 220), (W / 2, H - 24),
                      "center")
        elif st == "leaderboard":
            self.draw_leaderboard(surf)
        elif st == "help":
            self.draw_help(surf)
        elif st == "gameover":
            self.draw_gameover(surf)

        if self.save.settings.get("show_fps"):
            draw_text(surf, "%d FPS" % CLOCK.get_fps(), 20, WHITE, (W - 8, H - 8), "bottomright")
        if self.fade > 0:
            dim(surf, int(255 * self.fade), (0, 0, 0))
        pygame.display.flip()

    def draw_hud(self, surf):
        w = self.world
        p = w.player
        draw_text(surf, str(w.score), 52, WHITE, (16, 10), bold=True)
        draw_text(surf, "%dm" % w.height_m, 24, (230, 240, 255), (18, 54))
        surf.blit(APPLE_ICON, (16, 80))
        draw_text(surf, str(w.apples), 26, WHITE, (42, 82), bold=True)
        best = max(w.best_score, w.score)
        draw_text(surf, "BEST %d" % best, 22, GOLD if w.beat_best else (230, 240, 255), (W - 14, 14), "topright",
                  bold=True)

        # Power-up timers
        y = 44
        for active, total, img, colour in ((p.rocket, ROCKET_TIME, HUD_ICONS["rocket"], (255, 200, 60)),
                                           (p.shield, SHIELD_TIME, HUD_ICONS["shield"], (90, 200, 255)),
                                           (p.magnet, MAGNET_TIME, HUD_ICONS["magnet"], (255, 120, 200))):
            if active > 0:
                bar = pygame.Rect(W - 120, y + 10, 80, 10)
                pygame.draw.rect(surf, (0, 0, 0), bar.inflate(4, 4), border_radius=6)
                fill = bar.copy()
                fill.width = int(bar.width * clamp(active / total, 0, 1))
                pygame.draw.rect(surf, colour, fill, border_radius=5)
                surf.blit(img, img.get_rect(center=(W - 24, y + 15)))
                y += 36

        # Combo meter
        if w.combo > 1 and w.time - w.last_apple_t <= COMBO_WINDOW:
            t = 1 - (w.time - w.last_apple_t) / COMBO_WINDOW
            draw_text(surf, "COMBO x%d" % w.combo, 26, (255, 236, 120), (16, 110), bold=True, alpha=int(255 * min(1, t * 2)))
            pygame.draw.rect(surf, (255, 236, 120), (16, 134, int(100 * t), 4), border_radius=2)

        if w.banner:
            text, t = w.banner
            scale = 1 + max(0, (10 - t)) * 0.06
            a = int(255 * clamp((110 - t) / 25, 0, 1))
            draw_text(surf, text, int(72 * scale), GOLD, (W / 2, H * 0.3), "center", bold=True, alpha=a)

    def draw_menu(self, surf):
        dim(surf, 70)
        bob = math.sin(self.time * 0.04) * 6
        surf.blit(LOGO_IMG, LOGO_IMG.get_rect(center=(W / 2, 120 + bob)))
        icon = pygame.transform.rotate(PLAYER_ICON, math.sin(self.time * 0.05) * 8)
        surf.blit(icon, icon.get_rect(center=(W / 2, 222 + bob * 0.5)))
        self.main_menu.draw(surf)
        best = self.save.data["best"]
        stats = self.save.data["stats"]
        footer = "Best %d   -   Games %d   -   Apples %d" % (best, stats["games"], stats["apples"])
        draw_text(surf, footer, 22, WHITE, (W / 2, H - 22), "center")

    def draw_leaderboard(self, surf):
        dim(surf, 150)
        panel = pygame.Rect(24, 40, W - 48, H - 150)
        draw_panel(surf, panel)
        draw_text(surf, "LEADERBOARD", 50, INK, (W / 2, panel.y + 40), "center", bold=True, shadow=False)
        lb = self.save.leaderboard
        if not lb:
            draw_text(surf, "No scores yet.", 30, INK_SOFT, (W / 2, panel.centery - 10), "center", shadow=False)
            draw_text(surf, "Go set the first one!", 26, INK_SOFT, (W / 2, panel.centery + 22), "center", shadow=False)
        else:
            draw_text(surf, "NAME", 20, INK_SOFT, (panel.x + 72, panel.y + 80), shadow=False, bold=True)
            draw_text(surf, "HEIGHT", 20, INK_SOFT, (panel.right - 120, panel.y + 80), "topright", shadow=False, bold=True)
            draw_text(surf, "SCORE", 20, INK_SOFT, (panel.right - 24, panel.y + 80), "topright", shadow=False, bold=True)
            for i, e in enumerate(lb):
                y = panel.y + 106 + i * 44
                row = pygame.Rect(panel.x + 12, y, panel.width - 24, 38)
                if i == self.highlight_rank:
                    glow = 0.5 + 0.5 * math.sin(self.time * 0.12)
                    pygame.draw.rect(surf, lerp_col((255, 240, 190), (255, 220, 120), glow), row, border_radius=10)
                elif i % 2 == 0:
                    pygame.draw.rect(surf, (236, 242, 250), row, border_radius=10)
                medal = [GOLD, SILVER, BRONZE][i] if i < 3 else (214, 222, 234)
                pygame.draw.circle(surf, shade(medal, -0.3), (row.x + 26, row.centery + 1), 15)
                pygame.draw.circle(surf, medal, (row.x + 26, row.centery), 14)
                draw_text(surf, str(i + 1), 24, INK, (row.x + 26, row.centery + 1), "center", bold=True, shadow=False)
                draw_text(surf, e["name"], 28, INK, (row.x + 60, row.centery), "midleft", shadow=False)
                h = e.get("height", 0)
                draw_text(surf, ("%dm" % h) if h else "-", 24, INK_SOFT, (row.right - 108, row.centery), "midright",
                          shadow=False)
                draw_text(surf, str(e["score"]), 28, INK, (row.right - 12, row.centery), "midright", bold=True,
                          shadow=False)
        self.back_only.draw(surf)

    def draw_help(self, surf):
        dim(surf, 150)
        panel = pygame.Rect(24, 30, W - 48, H - 140)
        draw_panel(surf, panel)
        x = panel.x + 28
        y = panel.y + 22
        draw_text(surf, "HOW TO PLAY", 46, INK, (W / 2, y + 18), "center", bold=True, shadow=False)
        y += 54
        for line in ("Move with A / D, arrow keys or a gamepad.",
                     "Walk off one side to appear on the other.",
                     "Climb as high as you can. Don't fall!"):
            draw_text(surf, line, 23, INK, (x, y), shadow=False)
            y += 23
        y += 6
        draw_text(surf, "POWER-UPS", 26, ACCENT_DARK, (x, y), bold=True, shadow=False)
        y += 30
        for img, name, desc in ((APPLE_IMG, "Apple", "+10 points. Chain them for combos up to x5"),
                                (ROCKET_IMG, "Rocket", "Blast upward, smashing enemies"),
                                (SHIELD_IMG, "Shield", "Survive one fall and squash enemies"),
                                (MAGNET_IMG, "Magnet", "Pulls nearby apples to you")):
            surf.blit(img, img.get_rect(center=(x + 16, y + 14)))
            draw_text(surf, name, 24, INK, (x + 44, y), bold=True, shadow=False)
            draw_text(surf, desc, 20, INK_SOFT, (x + 44, y + 20), shadow=False)
            y += 42
        draw_text(surf, "PLATFORMS", 26, ACCENT_DARK, (x, y), bold=True, shadow=False)
        y += 30
        for kind, desc in (("normal", "Solid and dependable"), ("moving", "Slides side to side"),
                           ("vanish", "Disappears after one bounce"), ("crumble", "Breaks - you'll fall through!")):
            img = platform_surface(kind, 56)
            if kind == "vanish":
                pygame.draw.rect(surf, (170, 190, 220), (x - 2, y + 2, 60, PLAT_H + 2), border_radius=8)
            surf.blit(img, (x, y + 4))
            draw_text(surf, desc, 22, INK, (x + 72, y + 4), shadow=False)
            y += 27
        y += 4
        self.draw_spring_icon(surf, x + 10, y + 16)
        draw_text(surf, "Springs launch you sky-high", 22, INK, (x + 72, y + 4), shadow=False)
        y += 30
        pygame.draw.circle(surf, (90, 40, 150), (x + 28, y + 12), 13)
        pygame.draw.circle(surf, (130, 70, 200), (x + 28, y + 12), 11)
        draw_text(surf, "Enemies: stomp them from above!", 22, INK, (x + 72, y + 4), shadow=False)
        self.back_only.draw(surf)

    def draw_spring_icon(self, surf, x, y):
        self.world.draw_spring(surf, x, y, 0.3)

    def draw_gameover(self, surf):
        r = self.result
        t = r["t"]
        dim(surf, int(min(160, t * 5)))
        slide = (1 - clamp(t / 30, 0, 1)) ** 3
        panel = pygame.Rect(36, 60 + int(slide * H), W - 72, H - 250)
        draw_panel(surf, panel)
        cx = W / 2
        y = panel.y + 40
        title = "NEW BEST!" if r["new_best"] else "GAME OVER"
        col = GOLD if r["new_best"] else INK
        if r["new_best"]:
            pulse = 1 + 0.04 * math.sin(self.time * 0.15)
            draw_text(surf, title, int(56 * pulse), shade(GOLD, -0.2), (cx, y), "center", bold=True, shadow=False)
        else:
            draw_text(surf, title, 56, col, (cx, y), "center", bold=True, shadow=False)
        # Count-up score
        shown = int(r["score"] * clamp((t - 20) / 40, 0, 1))
        draw_text(surf, str(shown), 84, ACCENT_DARK, (cx, y + 70), "center", bold=True, shadow=False)
        draw_text(surf, "SCORE", 20, INK_SOFT, (cx, y + 110), "center", bold=True, shadow=False)

        stats = (("Height", "%dm" % r["height"]), ("Apples", str(r["apples"])), ("Stomps", str(r["stomps"])),
                 ("Best", str(r["best"])))
        sy = y + 140
        for i, (label, val) in enumerate(stats):
            col_x = panel.x + 40 + (i % 2) * (panel.width / 2 - 20)
            row_y = sy + (i // 2) * 52
            draw_text(surf, label.upper(), 18, INK_SOFT, (col_x, row_y), bold=True, shadow=False)
            draw_text(surf, val, 32, INK, (col_x, row_y + 18), bold=True, shadow=False)

        ny = sy + 112
        self.submit_rect = pygame.Rect(0, 0, 0, 0)
        if self.entering_name:
            draw_text(surf, "You made the leaderboard! Enter your name:", 22, INK, (cx, ny), "center", shadow=False)
            box = pygame.Rect(panel.x + 30, ny + 16, panel.width - 140, 44)
            pygame.draw.rect(surf, WHITE, box, border_radius=10)
            pygame.draw.rect(surf, ACCENT, box, 3, border_radius=10)
            caret = "|" if (self.time // 30) % 2 == 0 else ""
            draw_text(surf, self.name_input + caret, 32, INK, (box.x + 12, box.centery), "midleft", shadow=False)
            self.submit_rect = pygame.Rect(box.right + 10, box.y, 70, 44)
            pygame.draw.rect(surf, ACCENT, self.submit_rect, border_radius=10)
            draw_text(surf, "OK", 30, WHITE, self.submit_rect.center, "center", bold=True)
            draw_text(surf, "Enter to save  -  Esc to skip", 18, INK_SOFT, (cx, box.bottom + 14), "center", shadow=False)
        elif self.highlight_rank is not None:
            draw_text(surf, "Saved as #%d on the leaderboard!  (L to view)" % (self.highlight_rank + 1), 22, ACCENT_DARK,
                      (cx, ny + 20), "center", bold=True, shadow=False)

        if t > 30:
            for b in self.gameover_menu.buttons:
                b.enabled = not self.entering_name
            self.gameover_menu.draw(surf)

    # -- main loop --------------------------------------------------------
    def run(self):
        acc = 0.0
        while self.running:
            dt = CLOCK.tick(FPS) / 1000.0
            acc += min(dt, 0.25)
            self.handle_events()
            steps = 0
            while acc >= STEP and steps < 5:
                self.update()
                acc -= STEP
                steps += 1
            if steps == 5:
                acc = 0.0
            self.draw()
        self.save.write()
        pygame.quit()


if __name__ == "__main__":
    Game().run()
    sys.exit()

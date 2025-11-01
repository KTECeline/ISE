import pygame
import sys
import os
import json
import subprocess
import math
from pygame import mixer
from random import uniform, randint

# -------------------------
# Configuration
# -------------------------
BG_PATH = r"C:\Users\Xdimt\Downloads\background.img.png"  # user-specified
STORY_BG_PATH = r"C:\Users\Xdimt\Downloads\story_background.png"  # story background
FONT_PATH = os.path.join("assets", "fonts", "skooled_serif.ttf")  # optional
HOVER_SFX = r"C:\Users\Xdimt\Downloads\Hover.mp3"  # Updated path
CLICK_SFX = r"C:\Users\Xdimt\Downloads\Click.mp3"  # Updated path
MUSIC_PATH = r"C:\Users\Xdimt\Downloads\Background_music.mp3"  # Updated path

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
NEON_GREEN = (0, 255, 136)           # hover glow color
DARK_MOSS_OUTLINE = (26, 46, 26)     # title outline (#1a2e1a)
BUTTON_BASE = (42, 61, 42)           # darker base (#2a3d2a)
BUTTON_TOP = (70, 92, 70)
BUTTON_BOTTOM = (40, 58, 40)
BUTTON_BORDER = (20, 36, 20)
STATS_COLOR = (220, 230, 220)
STORY_TEXT_COLOR = (220, 240, 220)   # Light green for story text

# Buttons layout
BUTTON_W = 420
BUTTON_H = 80
BUTTON_X = (SCREEN_WIDTH - BUTTON_W) // 2
BUTTON_START_Y = 330
BUTTON_SPACING = 96

# Particles (spores)
NUM_SPORES = 70
SPORE_COLOR = (200, 255, 170)

# Story text
STORY_LINES = [
    "You awaken in the Fungal Wastes — the air thick with spores and echoes of lost souls.",
    "The mushrooms pulse faintly, whispering of secrets buried deep below.",
    "To survive here, you must learn to listen... to the forest, and to yourself.",
    "Your journey begins now."
]

# -------------------------
# Initialization
# -------------------------
pygame.init()
mixer_ok = True
try:
    mixer.init()
except Exception as e:
    print("[WARN] Audio mixer init failed:", e)
    mixer_ok = False

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Fungal Wastes")
clock = pygame.time.Clock()

# ensure asset dirs
for d in ['assets/sounds', 'assets/music', 'assets/fonts', 'assets/menu']:
    os.makedirs(d, exist_ok=True)

# -------------------------
# Load background safely
# -------------------------
def load_background(path):
    if os.path.exists(path):
        try:
            img = pygame.image.load(path)
            return pygame.transform.smoothscale(img, (SCREEN_WIDTH, SCREEN_HEIGHT)).convert()
        except Exception as e:
            print("[WARN] Failed to load background:", e)
    # fallback subtle vertical gradient
    surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    for y in range(SCREEN_HEIGHT):
        g = int(12 + 24 * (y / SCREEN_HEIGHT))
        surf.fill((8, g, 10), rect=pygame.Rect(0, y, SCREEN_WIDTH, 1))
    return surf

background = load_background(BG_PATH)
story_background = load_background(STORY_BG_PATH)

# -------------------------
# Fonts
# -------------------------
def load_font(path, size, fallback_name=None):
    if os.path.exists(path):
        try:
            return pygame.font.Font(path, size)
        except Exception as e:
            print("[WARN] custom font load failed:", e)
    try:
        return pygame.font.SysFont(fallback_name or "Georgia", size)
    except Exception:
        return pygame.font.Font(None, size)

title_font = load_font(FONT_PATH, 86, fallback_name="Georgia")
button_font = load_font(FONT_PATH, 36, fallback_name="Arial")
small_font = load_font(FONT_PATH, 18, fallback_name="Arial")
story_font = load_font(FONT_PATH, 32, fallback_name="Georgia")  # Font for story text

# -------------------------
# Sounds (optional)
# -------------------------
hover_sfx = None
click_sfx = None
if mixer_ok:
    try:
        if os.path.exists(HOVER_SFX):
            hover_sfx = mixer.Sound(HOVER_SFX)
        if os.path.exists(CLICK_SFX):
            click_sfx = mixer.Sound(CLICK_SFX)
        if os.path.exists(MUSIC_PATH):
            mixer.music.load(MUSIC_PATH)
            mixer.music.set_volume(0.45)
            mixer.music.play(-1)
    except Exception as e:
        print("[WARN] Sound load/play failed:", e)

# -------------------------
# Game data load/save
# -------------------------
GAME_DATA_FILE = "game_data.json"
def load_game_data():
    if os.path.exists(GAME_DATA_FILE):
        try:
            with open(GAME_DATA_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print("[WARN] Could not read game_data.json:", e)
    return {"score":0,"lives":3,"mushrooms":0,"current_level":1,"inventory":{},"unlocked_levels":[1]}

def save_game_data(data):
    try:
        with open(GAME_DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print("[WARN] Could not save game data:", e)

game_data = load_game_data()

# -------------------------
# Spore particle class
# -------------------------
class Spore:
    def __init__(self):
        self.reset(first=True)
    def reset(self, first=False):
        self.x = uniform(0, SCREEN_WIDTH)
        self.y = uniform(SCREEN_HEIGHT * 0.4, SCREEN_HEIGHT) if first else SCREEN_HEIGHT + uniform(0,200)
        self.vy = -uniform(5/60.0, 28/60.0)
        self.vx = uniform(-0.12, 0.12)
        self.size = uniform(1.0, 3.5)
        self.alpha = randint(80, 230)
        self.life = uniform(3.0, 12.0)
    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt/60.0
        if self.y < -10 or self.life <= 0:
            self.reset()
    def draw(self, surf):
        s = max(1, int(self.size))
        tmp = pygame.Surface((s*3, s*3), pygame.SRCALPHA)
        col = (*SPORE_COLOR, int(self.alpha))
        pygame.draw.circle(tmp, col, (s+1, s+1), s)
        surf.blit(tmp, (int(self.x)-s-1, int(self.y)-s-1), special_flags=pygame.BLEND_ADD)

spores = [Spore() for _ in range(NUM_SPORES)]

# -------------------------
# Procedural stone texture generator
# -------------------------
def generate_stone_texture(w, h):
    surf = pygame.Surface((w, h))
    surf.fill(BUTTON_BASE)
    for y in range(0, h, 6):
        for x in range(0, w, 6):
            shade_off = randint(-12, 18)
            r = max(0, min(255, BUTTON_BASE[0] + shade_off))
            g = max(0, min(255, BUTTON_BASE[1] + shade_off))
            b = max(0, min(255, BUTTON_BASE[2] + shade_off))
            rect = pygame.Rect(x + randint(-1,1), y + randint(-1,1), 6, 6)
            pygame.draw.rect(surf, (r,g,b), rect)
    for _ in range(10):
        sx = randint(0, w-1); sy = randint(0, h-1)
        ex = randint(0, w-1); ey = randint(0, h-1)
        pygame.draw.line(surf, (BUTTON_TOP[0]-8, BUTTON_TOP[1]-8, BUTTON_TOP[2]-8), (sx,sy), (ex,ey), 1)
    return surf

STONE_TILE = generate_stone_texture(BUTTON_W, BUTTON_H)

# -------------------------
# Button class
# -------------------------
class Button:
    def __init__(self, text, rect, callback=None):
        self.text = text
        self.rect = pygame.Rect(rect)
        self.callback = callback
        self.hovered = False
        self.pulse = 0.0
    def update(self, dt, mouse_pos):
        was = self.hovered
        self.hovered = self.rect.collidepoint(mouse_pos)
        if self.hovered and not was and hover_sfx:
            try: hover_sfx.play()
            except: pass
        target = 1.0 if self.hovered else 0.0
        self.pulse += (target - self.pulse) * min(1.0, dt * 0.02)
    def draw(self, surf):
        # tile stone texture
        tile = STONE_TILE
        tw, th = tile.get_width(), tile.get_height()
        for y in range(self.rect.y, self.rect.y + self.rect.height, th):
            for x in range(self.rect.x, self.rect.x + self.rect.width, tw):
                surf.blit(tile, (x, y))
        # top and bottom shading overlay
        top_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.rect.height//2)
        bot_rect = pygame.Rect(self.rect.x, self.rect.y + self.rect.height//2, self.rect.width, self.rect.height - self.rect.height//2)
        top_col = tuple(max(0,min(255,int(BUTTON_TOP[i] + (NEON_GREEN[i]-BUTTON_TOP[i])*self.pulse*0.05))) for i in range(3))
        bot_col = tuple(max(0,min(255,int(BUTTON_BOTTOM[i] + (BUTTON_TOP[i]-BUTTON_BOTTOM[i])*self.pulse*0.03))) for i in range(3))
        pygame.draw.rect(surf, top_col, top_rect, border_radius=8)
        pygame.draw.rect(surf, bot_col, bot_rect, border_radius=8)
        # border
        border_col = tuple(max(0,min(255,int(BUTTON_BORDER[i] + (NEON_GREEN[i]-BUTTON_BORDER[i])*self.pulse*0.06))) for i in range(3))
        pygame.draw.rect(surf, border_col, self.rect, 3, border_radius=8)
        # hover glow
        if self.pulse > 0.01:
            glow_alpha = int(60 + 140 * self.pulse)
            glow_surf = pygame.Surface((self.rect.width + 22, self.rect.height + 22), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (NEON_GREEN[0], NEON_GREEN[1], NEON_GREEN[2], glow_alpha), glow_surf.get_rect(), border_radius=10)
            surf.blit(glow_surf, (self.rect.x - 11, self.rect.y - 11), special_flags=pygame.BLEND_ADD)
        # text
        offset = int(6 * self.pulse)
        txt = button_font.render(self.text, True, WHITE)
        tr = txt.get_rect(center=(self.rect.centerx, self.rect.centery - offset))
        surf.blit(txt, tr)
    def click(self):
        if click_sfx:
            try: click_sfx.play()
            except: pass
        if self.callback:
            self.callback()

# -------------------------
# Story scene typing effect
# -------------------------
class StoryTypingEffect:
    def __init__(self, lines):
        self.lines = lines
        self.current_line = 0
        self.current_char = 0
        self.last_update_time = 0
        self.char_delay = 35  # ms between characters
        self.line_delay = 1200  # ms between lines
        self.finished = False
        self.waiting_for_next = False
        
    def update(self, current_time):
        if self.finished or self.waiting_for_next:
            return
            
        if current_time - self.last_update_time > self.char_delay:
            self.last_update_time = current_time
            self.current_char += 1
            
            # Check if current line is complete
            if self.current_char >= len(self.lines[self.current_line]):
                self.waiting_for_next = True
                
    def skip_or_next(self):
        if self.waiting_for_next:
            # Move to next line
            self.current_line += 1
            self.current_char = 0
            self.waiting_for_next = False
            
            # Check if all lines are done
            if self.current_line >= len(self.lines):
                self.finished = True
        else:
            # Skip to end of current line
            self.current_char = len(self.lines[self.current_line])
            self.waiting_for_next = True
            
    def get_current_text(self):
        if self.finished:
            return None
            
        current_text = self.lines[self.current_line][:self.current_char]
        return current_text
        
    def is_complete(self):
        return self.finished

# -------------------------
# Scenes & callbacks
# -------------------------
def start_game_cb():
    set_scene_with_fade("story")

def start_level_1():
    if os.path.exists("level_1.py"):
        try:
            subprocess.run([sys.executable, "level_1.py"])
            # If we return from level_1, go back to main menu
            set_scene_with_fade("menu")
        except Exception as e:
            print("[WARN] launching level_1.py failed:", e)
            set_scene_with_fade("menu")
    else:
        print("[INFO] level_1.py not found — placeholder start.")
        set_scene_with_fade("menu")

def set_scene_with_fade(target):
    global scene_fade
    scene_fade = {"active": True, "alpha": 0, "dir": 1, "target": target}

def open_options_cb():
    set_scene_with_fade("options")

def open_marketplace_cb():
    set_scene_with_fade("marketplace")

def open_level2_cb():
    set_scene_with_fade("level2")

def exit_cb():
    save_game_data(game_data)
    pygame.quit()
    sys.exit()

# buttons
main_buttons = [
    Button("Start Game", (BUTTON_X, BUTTON_START_Y, BUTTON_W, BUTTON_H), callback=start_game_cb),
    Button("Options", (BUTTON_X, BUTTON_START_Y + BUTTON_SPACING, BUTTON_W, BUTTON_H), callback=open_options_cb),
    Button("Exit", (BUTTON_X, BUTTON_START_Y + BUTTON_SPACING*2, BUTTON_W, BUTTON_H), callback=exit_cb),
]

opt_buttons = [
    Button("Marketplace", (BUTTON_X, BUTTON_START_Y, BUTTON_W, BUTTON_H), callback=open_marketplace_cb),
    Button("Level 2", (BUTTON_X, BUTTON_START_Y + BUTTON_SPACING, BUTTON_W, BUTTON_H), callback=open_level2_cb),
    Button("Back", (BUTTON_X, BUTTON_START_Y + BUTTON_SPACING*2, BUTTON_W, BUTTON_H), callback=lambda: set_scene_with_fade("menu")),
]

market_buttons = [
    Button("Back", (BUTTON_X, BUTTON_START_Y + 2*BUTTON_SPACING, BUTTON_W, BUTTON_H), callback=lambda: set_scene_with_fade("menu")),
]

level2_buttons = [
    Button("Back to Menu", (BUTTON_X, BUTTON_START_Y + 2*BUTTON_SPACING, BUTTON_W, BUTTON_H), callback=lambda: set_scene_with_fade("menu")),
]

# scene state
current_scene = "menu"
scene_fade = {"active": False, "alpha": 0, "dir": 0, "target": None}
story_typing = StoryTypingEffect(STORY_LINES)

# -------------------------
# Drawing helpers
# -------------------------
def draw_centered_title(surf, text, font, color, outline_color, x_center, y):
    txt = font.render(text, True, color)
    tr = txt.get_rect(center=(x_center, y))
    outline = font.render(text, True, outline_color)
    # draw 4 outline offsets
    for ox, oy in [(-2,-2),(2,-2),(-2,2),(2,2)]:
        surf.blit(outline, (tr.x + ox, tr.y + oy))
    surf.blit(txt, tr)

def visible_buttons_list():
    if current_scene == "menu":
        return main_buttons
    if current_scene == "options":
        return opt_buttons
    if current_scene == "marketplace":
        return market_buttons
    if current_scene == "level2":
        return level2_buttons
    return []

# -------------------------
# Scene render functions
# -------------------------
title_phase = 0.0
fade_alpha = 255
fade_speed = 2

def render_menu(dt, mouse_pos):
    for b in main_buttons:
        b.update(dt, mouse_pos)
    screen.blit(background, (0,0))
    v = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(v, (0,0,0,60), v.get_rect())
    screen.blit(v, (0,0), special_flags=pygame.BLEND_RGBA_SUB)
    for s in spores: s.draw(screen)
    global title_phase
    title_phase += 0.02 * (dt/16.0)
    draw_centered_title(screen, "FUNGAL WASTES", title_font, (200,245,200), DARK_MOSS_OUTLINE, SCREEN_WIDTH//2, 160)
    # stats
    stats = [
        f"Score: {game_data.get('score',0)}",
        f"Lives: {game_data.get('lives',0)}",
        f"Mushrooms: {game_data.get('mushrooms',0)}",
        f"Level: {game_data.get('current_level',1)}"
    ]
    for i, t in enumerate(stats):
        screen.blit(small_font.render(t, True, STATS_COLOR), (48, 220 + i*28))
    for b in main_buttons: b.draw(screen)
    footer = small_font.render("Developed by G23", True, WHITE)  # Updated
    screen.blit(footer, footer.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT-28)))

def render_options(dt, mouse_pos):
    for b in opt_buttons: b.update(dt, mouse_pos)
    screen.blit(background, (0,0))
    v = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(v, (0,0,0,60), v.get_rect())
    screen.blit(v, (0,0), special_flags=pygame.BLEND_RGBA_SUB)
    for s in spores: s.draw(screen)
    draw_centered_title(screen, "OPTIONS", title_font, (210,240,210), DARK_MOSS_OUTLINE, SCREEN_WIDTH//2, 140)
    for b in opt_buttons: b.draw(screen)
    footer = small_font.render("Developed by G23", True, WHITE)  # Updated
    screen.blit(footer, footer.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT-28)))

def render_marketplace(dt, mouse_pos):
    for b in market_buttons: b.update(dt, mouse_pos)
    screen.blit(background, (0,0))
    for s in spores: s.draw(screen)
    draw_centered_title(screen, "MARKETPLACE", title_font, (210,240,210), DARK_MOSS_OUTLINE, SCREEN_WIDTH//2, 140)
    info = small_font.render("Marketplace coming soon. Use Back to return.", True, STATS_COLOR)
    screen.blit(info, info.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))
    for b in market_buttons: b.draw(screen)
    footer = small_font.render("Developed by G23", True, WHITE)  # Updated
    screen.blit(footer, footer.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT-28)))

def render_level2(dt, mouse_pos):
    for b in level2_buttons: b.update(dt, mouse_pos)
    screen.fill((8,14,10))
    draw_centered_title(screen, "LEVEL 2 - WASTELAND", title_font, (200,230,200), DARK_MOSS_OUTLINE, SCREEN_WIDTH//2, 140)
    info = small_font.render("Level 2 placeholder. Press Back to return.", True, STATS_COLOR)
    screen.blit(info, info.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))
    for b in level2_buttons: b.draw(screen)
    footer = small_font.render("Developed by G23", True, WHITE)  # Updated
    screen.blit(footer, footer.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT-28)))

def render_story(dt, mouse_pos, current_time):
    screen.blit(story_background, (0,0))
    
    # Add dark overlay for better text readability
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))  # Semi-transparent black
    screen.blit(overlay, (0, 0))
    
    # Update typing effect
    global story_typing
    story_typing.update(current_time)
    
    # Draw current text
    current_text = story_typing.get_current_text()
    if current_text:
        # Render text with word wrapping
        text_surface = render_text_with_wrapping(current_text, story_font, STORY_TEXT_COLOR, SCREEN_WIDTH - 200)
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        screen.blit(text_surface, text_rect)
        
        # Show "Continue" prompt if waiting for next line
        if story_typing.waiting_for_next and not story_typing.finished:
            prompt = small_font.render("Click or press any key to continue...", True, (200, 200, 200))
            prompt_rect = prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100))
            screen.blit(prompt, prompt_rect)
    
    # If story is complete, show final prompt and transition after delay
    if story_typing.is_complete():
        prompt = small_font.render("Click or press any key to begin your journey...", True, (200, 200, 200))
        prompt_rect = prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100))
        screen.blit(prompt, prompt_rect)

def render_text_with_wrapping(text, font, color, max_width):
    words = text.split(' ')
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        test_width = font.size(test_line)[0]
        
        if test_width <= max_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    # Create a surface with the total height needed
    line_height = font.get_linesize()
    total_height = line_height * len(lines)
    surface = pygame.Surface((max_width, total_height), pygame.SRCALPHA)
    
    # Render each line
    y = 0
    for line in lines:
        line_surface = font.render(line, True, color)
        surface.blit(line_surface, (0, y))
        y += line_height
    
    return surface

# -------------------------
# Main loop
# -------------------------
def main_loop():
    global fade_alpha, current_scene, scene_fade, story_typing
    running = True
    last = pygame.time.get_ticks()
    while running:
        now = pygame.time.get_ticks()
        dt = now - last
        last = now

        # events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_game_data(game_data)
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()
                if current_scene == "story":
                    # Handle story scene click
                    if story_typing.is_complete():
                        # Story finished, start the game
                        start_level_1()
                    else:
                        # Skip to next line or complete current line
                        story_typing.skip_or_next()
                else:
                    # Handle button clicks in other scenes
                    for b in visible_buttons_list():
                        if b.rect.collidepoint(mouse_pos):
                            b.click()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    save_game_data(game_data)
                    running = False
                elif current_scene == "story":
                    # Handle story scene key press
                    if story_typing.is_complete():
                        # Story finished, start the game
                        start_level_1()
                    else:
                        # Skip to next line or complete current line
                        story_typing.skip_or_next()
                else:
                    # Handle keyboard navigation in other scenes
                    if event.key in (pygame.K_UP, pygame.K_w):
                        btns = visible_buttons_list()
                        if btns:
                            sel = next((i for i,b in enumerate(btns) if b.hovered), 0)
                            sel = (sel - 1) % len(btns)
                            for i,b in enumerate(btns): b.hovered = (i==sel)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        btns = visible_buttons_list()
                        if btns:
                            sel = next((i for i,b in enumerate(btns) if b.hovered), 0)
                            sel = (sel + 1) % len(btns)
                            for i,b in enumerate(btns): b.hovered = (i==sel)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        btns = visible_buttons_list()
                        if btns:
                            sel = next((i for i,b in enumerate(btns) if b.hovered), 0)
                            btns[sel].click()

        mouse_pos = pygame.mouse.get_pos()

        # update spores
        for s in spores:
            s.update(dt)

        # handle scene fade transitions
        if scene_fade.get("active", False):
            if scene_fade["dir"] == 1:
                scene_fade["alpha"] = min(255, scene_fade["alpha"] + 8)
                if scene_fade["alpha"] >= 255:
                    # switch scene now
                    current_scene = scene_fade.get("target", current_scene)
                    # Reset story typing if entering story scene
                    if current_scene == "story":
                        story_typing = StoryTypingEffect(STORY_LINES)
                    scene_fade["dir"] = -1
            elif scene_fade["dir"] == -1:
                scene_fade["alpha"] = max(0, scene_fade["alpha"] - 8)
                if scene_fade["alpha"] <= 0:
                    scene_fade["active"] = False

        # update & render scene
        if current_scene == "menu":
            for b in main_buttons: b.update(dt, mouse_pos)
            render_menu(dt, mouse_pos)
        elif current_scene == "options":
            for b in opt_buttons: b.update(dt, mouse_pos)
            render_options(dt, mouse_pos)
        elif current_scene == "marketplace":
            for b in market_buttons: b.update(dt, mouse_pos)
            render_marketplace(dt, mouse_pos)
        elif current_scene == "level2":
            for b in level2_buttons: b.update(dt, mouse_pos)
            render_level2(dt, mouse_pos)
        elif current_scene == "story":
            render_story(dt, mouse_pos, now)

        # draw fade overlays (initial menu fade or scene transitions)
        if scene_fade.get("active", False):
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.fill((0,0,0))
            overlay.set_alpha(int(scene_fade["alpha"]))
            screen.blit(overlay, (0,0))
        elif fade_alpha > 0:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.fill((0,0,0))
            overlay.set_alpha(int(fade_alpha))
            screen.blit(overlay, (0,0))
            fade_alpha = max(0, fade_alpha - fade_speed)

        pygame.display.flip()
        clock.tick(FPS)

    save_game_data(game_data)
    pygame.quit()
    sys.exit()

# Ensure there is an entry
if __name__ == "__main__":
    main_loop()


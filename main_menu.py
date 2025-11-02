"""
main_menu.py - MYCELIUM'S LAMENT
Updated with multiple story backgrounds and smooth fade transitions
"""

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
BG_PATH = r"assets/images/background.img.png"
STORY_BG_PATHS = [
    r"assets/images/story_Background1.png",
    r"assets/images/story_Background2.png", 
    r"assets/images/story_Background3.png",
    r"assets/images/story_Background4.png"
]
FONT_PATH = os.path.join("assets", "fonts", "skooled_serif.ttf")
HOVER_SFX = r"assets/sounds/Hover.mp3"
CLICK_SFX = r"assets/sounds/Click.mp3"
MUSIC_PATH = r"assets/sounds/Background_music.mp3"

# Voice audio paths
# Map individual intro scene voices (Intro_1..Intro_5) and other dialogue
VOICE_PATHS = {
    "intro_1": r"assets/voice/Intro_1.mp3",
    "intro_2": r"assets/voice/Intro_2.mp3",
    "intro_3": r"assets/voice/Intro_3.mp3",
    "intro_4": r"assets/voice/Intro_4.mp3",
    "intro_5": r"assets/voice/Intro_5.mp3",
    "story_intro": r"assets/sounds/intro.mpeg",
    "wm_greeting": r"assets/sounds/greeting.mpeg"
}
# Greeting voice files for Wise Mushroom (per-line)
VOICE_PATHS.update({
    "greeting_1": r"assets/voice/Greeting_1.mp3",
    "greeting_2": r"assets/voice/Greeting_2.mp3",
    "greeting_3": r"assets/voice/Greeting_3.mp3",
    "greeting_4": r"assets/voice/Greeting_4.mp3",
    "greeting_5": r"assets/voice/Greeting_5.mp3",
})

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
NEON_GREEN = (0, 255, 136)
DARK_MOSS_OUTLINE = (26, 46, 26)
BUTTON_BASE = (42, 61, 42)
BUTTON_TOP = (70, 92, 70)
BUTTON_BOTTOM = (40, 58, 40)
BUTTON_BORDER = (20, 36, 20)
STATS_COLOR = (220, 230, 220)
STORY_TEXT_COLOR = (220, 240, 220)
LORE_TEXT_COLOR = (180, 220, 180)

# Buttons layout
BUTTON_W = 420
BUTTON_H = 80
BUTTON_X = (SCREEN_WIDTH - BUTTON_W) // 2
BUTTON_START_Y = 330
BUTTON_SPACING = 96

# Particles (spores)
NUM_SPORES = 70
SPORE_COLOR = (200, 255, 170)

# Improved Story text - combined sentences for better flow
STORY_LINES = [
    "In the ancient fungal realm of Echofungus, a vast underground world woven from mycelial threads and spore-veiled caverns, life pulses through symbiotic cycles of decay and rebirth.",
    "But a cataclysmic Blightstorm—a spore plague—fractured the realm, starving the guardian monsters that hold back the encroaching void.",
    "You are a Surface Echo, a rare wanderer from the barren above-world, drawn by Hyphara's call to restore balance.",
    "Your journey involves collecting and feeding sacred mushrooms to these monstrous guardians, awakening their strength and mending the mycelial web.", 
    "Failure means the Blightstorm consumes all; success earns Hyphara's gratitude and ascension to the Sporelit Heavens.",
    "Your journey begins now."
]

# Improved Wise Mushroom dialogue - combined sentences
WM_DIALOGUE = [
    "Is that a visitor I see? A rare sight indeed... We haven't had one in a while.",
    "A quiet one, hmm. Mind if you tell me your name? Or at least write it down.",
    "I am Eldergill, last of the Rootbound Sages. The Blightstorm rages below—our guardians starve, and the web unravels. Hyphara dreams of a feeder from above. Will you descend? Prove your weave?",
    "The soil hungers, young Echo. Gather the gifts of decay—feed the maws to pass. Fail, and the void claims us all.",
    "Go now... the Fungal Waste awaits."
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
pygame.display.set_caption("Mycelium's Lament")
clock = pygame.time.Clock()

# ensure asset dirs
for d in ['assets/sounds', 'assets/music', 'assets/fonts', 'assets/menu', 'assets/voice']:
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

# Load all story backgrounds
story_backgrounds = []
for path in STORY_BG_PATHS:
    bg = load_background(path)
    story_backgrounds.append(bg)

# If no story backgrounds loaded, use the main background as fallback
if not story_backgrounds:
    story_backgrounds = [background]

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
story_font = load_font(FONT_PATH, 32, fallback_name="Georgia")
dialogue_font = load_font(FONT_PATH, 28, fallback_name="Georgia")

# -------------------------
# Sounds (optional)
# -------------------------
hover_sfx = None
click_sfx = None
voice_sounds = {}  # Dictionary to hold voice audio

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
        
        # Load voice sounds if they exist
        for voice_key, voice_path in VOICE_PATHS.items():
            if os.path.exists(voice_path):
                try:
                    voice_sounds[voice_key] = mixer.Sound(voice_path)
                    print(f"[INFO] Loaded voice: {voice_key}")
                except Exception as e:
                    print(f"[WARN] Could not load voice {voice_path}: {e}")
            else:
                print(f"[INFO] Voice file not found: {voice_path}")
    except Exception as e:
        print("[WARN] Sound load/play failed:", e)


def stop_all_voice():
    """Stop any currently playing voice sounds."""
    if not mixer_ok:
        return
    try:
        for v in list(voice_sounds.values()):
            try:
                v.stop()
            except Exception:
                pass
    except Exception:
        pass

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
    return {
        "player_name": "",
        "score": 0,
        "lives": 3,
        "mushrooms": 0,
        "current_level": 1,
        "inventory": {},
        "unlocked_levels": [1],
        "symbiote_shrooms": 0,
        "spore_credits": 0
    }

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
# Story scene typing effect with audio support and background transitions
# -------------------------
class StoryTypingEffect:
    def __init__(self, lines, font, color=STORY_TEXT_COLOR, voice_key=None, voice_keys=None, backgrounds=None):
        """
        lines: list of strings
        voice_key: legacy single voice key (kept for compatibility)
        voice_keys: optional list of voice keys, one per line (preferred)
        """
        self.lines = lines
        self.font = font
        self.color = color
        self.current_line = 0
        self.current_char = 0
        self.last_update_time = 0
        self.char_delay = 40  # ms between characters
        self.line_delay = 1500  # ms between lines
        self.finished = False
        self.waiting_for_next = False
        # track which lines' voice we've already played
        self.voice_played_lines = set()
        # legacy single key
        self.voice_key = voice_key
        # per-line keys preferred
        self.voice_keys = voice_keys or []
        self.backgrounds = backgrounds or []
        self.current_bg_index = 0
        self.bg_transition_alpha = 0
        self.bg_transitioning = False
        self.bg_transition_speed = 3  # Higher = slower transition
        
    def update(self, current_time):
        if self.finished or self.waiting_for_next:
            return
            
        if current_time - self.last_update_time > self.char_delay:
            self.last_update_time = current_time
            self.current_char += 1
            
            # Play per-line voice when the first character appears for that line
            if self.current_char == 1:
                self.play_voice_for_current_line()
            
            # Handle background transitions based on line progress
            self.update_background_transitions()
            
            # Check if current line is complete
            if self.current_char >= len(self.lines[self.current_line]):
                self.waiting_for_next = True
                
    def update_background_transitions(self):
        # Change background every 2 lines (approximately)
        target_bg_index = min(len(self.backgrounds) - 1, self.current_line // 2)
        
        if target_bg_index != self.current_bg_index and not self.bg_transitioning:
            self.bg_transitioning = True
            self.bg_transition_alpha = 0
            
        if self.bg_transitioning:
            self.bg_transition_alpha += self.bg_transition_speed
            if self.bg_transition_alpha >= 255:
                self.current_bg_index = int(target_bg_index)  # Ensure it's an integer
                self.bg_transitioning = False
                self.bg_transition_alpha = 0
                
    def play_voice(self):
        # Legacy single-key playback
        if self.voice_key and self.voice_key in voice_sounds:
            try:
                voice_sounds[self.voice_key].play()
                print(f"[INFO] Playing voice: {self.voice_key}")
            except Exception as e:
                print(f"[WARN] Could not play voice {self.voice_key}: {e}")

    def play_voice_for_current_line(self):
        """Play the voice corresponding to the current line (if available).
        Stops any currently playing voice for this line if user skips.
        """
        # Determine key: prefer voice_keys list, fall back to single voice_key
        key = None
        if self.current_line < len(self.voice_keys):
            key = self.voice_keys[self.current_line]
        elif self.voice_key:
            key = self.voice_key

        if not key:
            return

        # Avoid replaying the same line's voice
        if self.current_line in self.voice_played_lines:
            return

        # Try to stop any previous voice (best-effort)
        try:
            stop_all_voice()
        except Exception:
            pass

        if key in voice_sounds:
            try:
                voice_sounds[key].play()
                print(f"[INFO] Playing voice: {key} for line {self.current_line}")
            except Exception as e:
                print(f"[WARN] Could not play voice {key}: {e}")

        self.voice_played_lines.add(self.current_line)
                
    def skip_or_next(self):
        if self.waiting_for_next:
            # Move to next line
            # stop current line voice when advancing
            try:
                if self.current_line < len(self.voice_keys):
                    k = self.voice_keys[self.current_line]
                    if k in voice_sounds:
                        voice_sounds[k].stop()
            except Exception:
                pass
            self.current_line += 1
            self.current_char = 0
            self.waiting_for_next = False
            
            # Check if all lines are done
            if self.current_line >= len(self.lines):
                self.finished = True
        else:
            # Skip to end of current line
            # Stop any voice for the current line when user forces skip
            try:
                if self.current_line < len(self.voice_keys):
                    k = self.voice_keys[self.current_line]
                    if k in voice_sounds:
                        voice_sounds[k].stop()
                elif self.voice_key and self.voice_key in voice_sounds:
                    voice_sounds[self.voice_key].stop()
            except Exception:
                pass
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
# Name input system
# -------------------------
class NameInput:
    def __init__(self):
        self.text = ""
        self.active = True
        self.cursor_visible = True
        self.cursor_timer = 0
        
    def update(self, dt):
        self.cursor_timer += dt
        if self.cursor_timer > 500:  # Blink every 500ms
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = 0
            
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self.text.strip():
                    self.active = False
                    return True
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                # Limit name length and only allow alphanumeric + spaces
                if len(self.text) < 16 and (event.unicode.isalnum() or event.unicode == ' '):
                    self.text += event.unicode
        return False
        
    def draw(self, surf, position):
        # Draw input box
        input_rect = pygame.Rect(position[0] - 150, position[1] - 20, 300, 40)
        pygame.draw.rect(surf, (40, 60, 40), input_rect, border_radius=5)
        pygame.draw.rect(surf, (80, 120, 80), input_rect, 2, border_radius=5)
        
        # Draw text
        if self.text:
            name_text = dialogue_font.render(self.text, True, WHITE)
            surf.blit(name_text, (input_rect.x + 10, input_rect.y + 5))
        else:
            prompt_text = small_font.render("Enter your name...", True, (150, 150, 150))
            surf.blit(prompt_text, (input_rect.x + 10, input_rect.y + 10))
            
        # Draw cursor
        if self.active and self.cursor_visible:
            cursor_x = input_rect.x + 10 + (dialogue_font.size(self.text)[0] if self.text else 0)
            pygame.draw.rect(surf, WHITE, (cursor_x, input_rect.y + 5, 2, 30))

# -------------------------
# Scenes & callbacks
# -------------------------
def start_game_cb():
    set_scene_with_fade("story_intro")

def start_level_1():
    """Close the menu process and replace it with level_1.py so the menu
    does not remain running in the background.
    """
    if not os.path.exists("level_1.py"):
        print("[INFO] level_1.py not found — returning to menu.")
        set_scene_with_fade("menu")
        return

    try:
        # Update game data before starting level
        game_data["current_level"] = 1
        save_game_data(game_data)

        # Try to cleanly shutdown pygame and exec into level_1.py so this
        # process is replaced (no lingering menu process).
        try:
            pygame.quit()
        except Exception:
            pass

        script = os.path.abspath("level_1.py")
        os.execv(sys.executable, [sys.executable, script])
    except Exception as e:
        # Exec failed — fallback to launching as subprocess then exit.
        print("[WARN] execv failed, falling back to subprocess.run:", e)
        try:
            subprocess.run([sys.executable, "level_1.py"])
        except Exception as e2:
            print("[ERROR] Failed to launch level_1.py:", e2)
        finally:
            # Ensure the menu process exits after attempting fallback
            try:
                pygame.quit()
            except Exception:
                pass
            sys.exit(0)

def set_scene_with_fade(target):
    global scene_fade
    scene_fade = {"active": True, "alpha": 0, "dir": 1, "target": target}

def open_options_cb():
    set_scene_with_fade("options")

def open_marketplace_cb():
    # Save and fully close the menu, then replace the current process with
    # the marketplace Python process. Using os.execv ensures the menu process
    # is replaced (no background menu left running). Falls back to subprocess
    # if execv fails.
    save_game_data(game_data)
    try:
        pygame.quit()
    except Exception:
        pass

    try:
        script = os.path.abspath("marketplace.py")
        os.execv(sys.executable, [sys.executable, script])
    except Exception as e:
        # Exec failed; fallback to launching marketplace then exiting.
        print("[WARN] execv failed, falling back to subprocess.run:", e)
        try:
            subprocess.run([sys.executable, "marketplace.py"])
        except Exception as e2:
            print("[ERROR] Failed to launch marketplace:", e2)
        finally:
            sys.exit(0)

def open_level2_cb():
    # Save and fully close the menu, then replace the current process with
    # the Level 2 Python process so the menu is not left running in background.
    save_game_data(game_data)
    try:
        pygame.quit()
    except Exception:
        pass

    try:
        script = os.path.abspath("level_2.py")
        os.execv(sys.executable, [sys.executable, script])
    except Exception as e:
        # Exec failed; fallback to launching level_2 then exiting.
        print("[WARN] execv failed, falling back to subprocess.run:", e)
        try:
            subprocess.run([sys.executable, "level_2.py"])
        except Exception as e2:
            print("[ERROR] Failed to launch level_2.py:", e2)
        finally:
            sys.exit(0)

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
story_typing = StoryTypingEffect(STORY_LINES, story_font, voice_key="story_intro", backgrounds=story_backgrounds)
# Provide per-line greeting voice keys for WM dialogue (one per WM_DIALOGUE line)
wm_greeting_keys = ["greeting_1", "greeting_2", "greeting_3", "greeting_4", "greeting_5"]
wm_dialogue = StoryTypingEffect(WM_DIALOGUE, dialogue_font, LORE_TEXT_COLOR, voice_keys=wm_greeting_keys)
name_input = NameInput()

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
    draw_centered_title(screen, "MYCELIUM'S LAMENT", title_font, (200,245,200), DARK_MOSS_OUTLINE, SCREEN_WIDTH//2, 160)
    # stats
    stats = [
        f"Score: {game_data.get('score',0)}",
        f"Lives: {game_data.get('lives',0)}",
        f"Mushrooms: {game_data.get('mushrooms',0)}",
        f"Level: {game_data.get('current_level',1)}",
        f"Player: {game_data.get('player_name', 'Unknown')}"
    ]
    for i, t in enumerate(stats):
        screen.blit(small_font.render(t, True, STATS_COLOR), (48, 220 + i*28))
    for b in main_buttons: b.draw(screen)
    footer = small_font.render("Developed by G23", True, WHITE)
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
    footer = small_font.render("Developed by G23", True, WHITE)
    screen.blit(footer, footer.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT-28)))

def render_marketplace(dt, mouse_pos):
    for b in market_buttons: b.update(dt, mouse_pos)
    screen.blit(background, (0,0))
    for s in spores: s.draw(screen)
    draw_centered_title(screen, "MARKETPLACE", title_font, (210,240,210), DARK_MOSS_OUTLINE, SCREEN_WIDTH//2, 140)
    # Marketplace now launched via callback; keep simple UI while subprocess runs/returns
    info = small_font.render("Launching Marketplace... (will return when closed)", True, STATS_COLOR)
    screen.blit(info, info.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))
    for b in market_buttons: b.draw(screen)
    footer = small_font.render("Developed by G23", True, WHITE)
    screen.blit(footer, footer.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT-28)))

def render_level2(dt, mouse_pos):
    for b in level2_buttons: b.update(dt, mouse_pos)
    screen.fill((8,14,10))
    draw_centered_title(screen, "LEVEL 2 - CITY OF TEARS", title_font, (200,230,200), DARK_MOSS_OUTLINE, SCREEN_WIDTH//2, 140)
    info = small_font.render("The City of Tears awaits... Press Back to return.", True, STATS_COLOR)
    screen.blit(info, info.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))
    for b in level2_buttons: b.draw(screen)
    footer = small_font.render("Developed by G23", True, WHITE)
    screen.blit(footer, footer.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT-28)))

def render_story_intro(dt, mouse_pos, current_time):
    # Update typing effect
    global story_typing
    story_typing.update(current_time)
    
    # Draw current background with transition
    if story_typing.backgrounds and len(story_typing.backgrounds) > 0:
        current_bg_index = int(story_typing.current_bg_index)  # Ensure it's an integer
        if current_bg_index < len(story_typing.backgrounds):
            current_bg = story_typing.backgrounds[current_bg_index]
            screen.blit(current_bg, (0, 0))
            
            # If transitioning, draw the next background with alpha
            if story_typing.bg_transitioning and current_bg_index < len(story_typing.backgrounds) - 1:
                next_bg_index = current_bg_index + 1
                if next_bg_index < len(story_typing.backgrounds):
                    next_bg = story_typing.backgrounds[next_bg_index]
                    transition_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                    transition_surf.blit(next_bg, (0, 0))
                    transition_surf.set_alpha(story_typing.bg_transition_alpha)
                    screen.blit(transition_surf, (0, 0))
    
    # Add dark overlay for better text readability
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    screen.blit(overlay, (0, 0))
    
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
        prompt = small_font.render("Click or press any key to meet Eldergill...", True, (200, 200, 200))
        prompt_rect = prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100))
        screen.blit(prompt, prompt_rect)

def render_wm_dialogue(dt, mouse_pos, current_time):
    # Use the last story background for WM dialogue
    if story_backgrounds and len(story_backgrounds) > 0:
        screen.blit(story_backgrounds[-1], (0,0))
    else:
        screen.blit(background, (0,0))
    
    # Add dark overlay for better text readability
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    screen.blit(overlay, (0, 0))
    
    # Draw Wise Mushroom title
    wm_title = story_font.render("Eldergill - The Rootbound Sage", True, LORE_TEXT_COLOR)
    screen.blit(wm_title, wm_title.get_rect(center=(SCREEN_WIDTH // 2, 100)))
    
    # Update typing effect
    global wm_dialogue, name_input
    if not name_input.active:
        wm_dialogue.update(current_time)
    
    # Handle name input
    if name_input.active:
        name_input.update(dt)
        
        # Draw prompt for name
        name_prompt = dialogue_font.render("What shall we call you, Surface Echo?", True, LORE_TEXT_COLOR)
        screen.blit(name_prompt, name_prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60)))
        
        # Draw name input box
        name_input.draw(screen, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        
        # Draw instruction
        instruction = small_font.render("Press ENTER when finished", True, (200, 200, 200))
        screen.blit(instruction, instruction.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40)))
    else:
        # Draw current dialogue text
        current_text = wm_dialogue.get_current_text()
        if current_text:
            # Render text with word wrapping
            text_surface = render_text_with_wrapping(current_text, dialogue_font, LORE_TEXT_COLOR, SCREEN_WIDTH - 200)
            text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(text_surface, text_rect)
            
            # Show "Continue" prompt if waiting for next line
            if wm_dialogue.waiting_for_next and not wm_dialogue.finished:
                prompt = small_font.render("Click or press any key to continue...", True, (200, 200, 200))
                prompt_rect = prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100))
                screen.blit(prompt, prompt_rect)
    
    # If dialogue is complete, show final prompt to start the game
    if wm_dialogue.is_complete():
        prompt = small_font.render("Click or press any key to begin your journey in the Fungal Waste...", True, (200, 200, 200))
        prompt_rect = prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100))
        screen.blit(prompt, prompt_rect)

# -------------------------
# Main loop
# -------------------------
def main_loop():
    global fade_alpha, current_scene, scene_fade, story_typing, wm_dialogue, name_input, game_data
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
                if current_scene == "story_intro":
                    # Handle story scene click
                    if story_typing.is_complete():
                        # Story finished, transition to WM dialogue
                        set_scene_with_fade("wm_dialogue")
                    else:
                        # Skip to next line or complete current line
                        story_typing.skip_or_next()
                elif current_scene == "wm_dialogue":
                    if name_input.active:
                        # Name input is active, don't advance dialogue on click
                        pass
                    elif wm_dialogue.is_complete():
                        # Dialogue finished, start the game
                        start_level_1()
                    else:
                        # Skip to next line or complete current line
                        wm_dialogue.skip_or_next()
                else:
                    # Handle button clicks in other scenes
                    for b in visible_buttons_list():
                        if b.rect.collidepoint(mouse_pos):
                            b.click()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    save_game_data(game_data)
                    running = False
                elif current_scene == "story_intro":
                    # Handle story scene key press
                    if story_typing.is_complete():
                        # Story finished, transition to WM dialogue
                        set_scene_with_fade("wm_dialogue")
                    else:
                        # Skip to next line or complete current line
                        story_typing.skip_or_next()
                elif current_scene == "wm_dialogue":
                    if name_input.active:
                        # Handle name input
                        if name_input.handle_event(event):
                            # Name submitted, save it
                            game_data["player_name"] = name_input.text
                            save_game_data(game_data)
                    elif wm_dialogue.is_complete():
                        # Dialogue finished, start the game
                        start_level_1()
                    else:
                        # Skip to next line or complete current line
                        wm_dialogue.skip_or_next()
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
                    # stop any playing voice before switching scenes
                    try:
                        stop_all_voice()
                    except Exception:
                        pass
                    current_scene = scene_fade.get("target", current_scene)
                    # Reset story typing if entering story scene
                    if current_scene == "story_intro":
                        # Provide per-line voice keys for the first five intro scenes
                        intro_voice_keys = ["intro_1", "intro_2", "intro_3", "intro_4", "intro_5"]
                        # If there are fewer lines than voice keys, it's fine — constructor handles it
                        story_typing = StoryTypingEffect(STORY_LINES, story_font, voice_keys=intro_voice_keys, backgrounds=story_backgrounds)
                    elif current_scene == "wm_dialogue":
                        # Recreate WM dialogue with per-line greeting voices
                        wm_greeting_keys = ["greeting_1", "greeting_2", "greeting_3", "greeting_4", "greeting_5"]
                        wm_dialogue = StoryTypingEffect(WM_DIALOGUE, dialogue_font, LORE_TEXT_COLOR, voice_keys=wm_greeting_keys)
                        name_input = NameInput()
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
        elif current_scene == "story_intro":
            render_story_intro(dt, mouse_pos, now)
        elif current_scene == "wm_dialogue":
            render_wm_dialogue(dt, mouse_pos, now)

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

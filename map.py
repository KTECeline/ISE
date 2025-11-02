import pygame
import sys
import os
import random
import math
import json
from level2.goal import walking_frames_right, hit_frames_right
from level2.particles import SporeParticle, FireworkParticle
from level2.ui import ScorePopup, draw_minimap
import charactermove as char_move
# Initialize Pygame
pygame.init()
# Initialize audio mixer (safe if system doesn't have audio — catch failures)
try:
    # try to reduce latency on some systems then init mixer
    try:
        pygame.mixer.pre_init(44100, -16, 2, 512)
    except Exception:
        pass
    try:
        pygame.mixer.init()
    except Exception:
        pass
except Exception:
    # audio not available — continue silently
    pass
# Load optional SFX (missing files won't crash the game)
bubble_pop = None
scored_sound = None
try:
    try:
        bubble_pop = pygame.mixer.Sound('assets/sounds/bubble_pop.mp3')
    except Exception:
        try:
            bubble_pop = pygame.mixer.Sound('assets/sounds/bubble_pop.wav')
        except Exception:
            bubble_pop = None
    try:
        scored_sound = pygame.mixer.Sound('assets/sounds/scored.mp3')
    except Exception:
        try:
            scored_sound = pygame.mixer.Sound('assets/sounds/scored.wav')
        except Exception:
            scored_sound = None
except Exception:
    bubble_pop = scored_sound = None
# Create a dummy display mode first to allow image loading (fixes "No video mode" error)
dummy_screen = pygame.display.set_mode((1, 1), pygame.NOFRAME)
# Try loading character assets (safe if assets missing)
try:
    char_move.load_assets()
except Exception:
    pass
# Constants
SCREEN_WIDTH = 1024  # Fixed screen size for viewing
SCREEN_HEIGHT = 768
FPS = 60
PLAYER_SPEED = 10  # was 5 — increase base walking speed
BALL_SPEED = 15   # was 10 — increase shoot speed so shots feel snappier
BALL_FRICTION = 0.98  # Slow down over time
COLLISION_COLOR = (255, 0, 0)  # Red for walls; tolerance for slight variations
TOLERANCE = 50  # Allow minor RGB variations in red detection
GOAL_RADIUS = 30  # Size of goal zones
NUM_GOALS = 8  # More goals scattered across map
PARTICLE_COUNT = 20  # Burst on hit
MINIMAP_SIZE = (200, 150)  # Small minimap dimensions
MINIMAP_ZOOM = 1.5  # >1 zooms in (shows smaller world area magnified); 1.0 = full world
BASE_SCORE = 10  # Points per hit
COMBO_MULTIPLIER = 2  # Double score on streak/multi-hit (one strike gets two = x2 more marks)
POPUP_LIFETIME = 60  # Frames for score pop-up fade
FORBIDDEN_Y_MAX = 4215  # No goals above this y-line (higher y = above, so spawn y > 4215)
MUSHROOM_ANIM_SCALE = 2.0  # Multiplier for animated mushroom frame size (1.0 = base ball size)
FIREWORK_PARTICLE_COUNT = 28  # How many firework sparks to spawn per goal
# Prefer strongly red fireworks so they stand out
FIREWORK_COLORS = [(255, 40, 40), (255, 80, 60), (200, 30, 30), (255, 100, 80)]
SCREEN_SHAKE_FRAMES = 12  # frames of camera shake when hit
screen_shake_timer = 0
SHOW_HIT_DEBUG = False  # This flag is no longer needed; removing it.
# Aura settings
AURA_RADIUS = 150  # world units radius of the aura around the player
# Rolling / squish animation settings for the sporeball
ROLL_VELOCITY_THRESHOLD = 1.2  # start roll animation when speed exceeds this
ROLL_FRAME_SPEED = 0.5  # how quickly to advance roll frames
SQUISH_FRAMES = 4  # number of keyframes for squash/stretch
SQUISH_DURATION = 10  # frames that the squish animation plays
# Trail / motion blur for ball
BALL_TRAIL_MAX = 12  # max trail copies kept
BALL_TRAIL_ALPHA = 160  # max alpha for the newest trail copy
BALL_TRAIL_SCALE_DECAY = 0.95  # each older trail image is this scale of the next
# Paths to your files (update if needed)
MAP_PATH = 'assets/textures/map/Level_2_map.png'
COLLISION_PATH = 'assets/textures/map/Level_2_collision.png'
# ---------------- Inventory helpers & powerup config ----------------
def load_inventory():
    try:
        with open('inventory.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
def save_inventory(inv):
    try:
        with open('inventory.json', 'w') as f:
            json.dump(inv, f)
    except Exception:
        pass
# Mapping of powerup keys to asset icons and display names
POWERUP_INFO = {
    'velocity_vial': {'img': 'speed1.png', 'name': 'Velocity Vial'},
    'golden_gleam': {'img': 'gold1.png', 'name': 'Golden Gleam'},
    'cluster_cap': {'img': 'magnet1.png', 'name': 'Cluster Cap'},
    'aura_alembic': {'img': 'circle1.png', 'name': 'Aura Alembic'},
}
# Powerup runtime state (timers measured in frames)
POWERUP_DURATION_FRAMES = int(6 * FPS)  # 6 seconds
powerup_timers = {k: 0 for k in POWERUP_INFO.keys()}  # active effect timers
# Allow per-powerup duration overrides (frames). Keep default at 6s above.
POWERUP_DURATIONS = {
    'velocity_vial': int(10 * FPS),  # velocity lasts 10 seconds
}
# Temporary goals spawned by cluster_cap
temp_goal_timers = {}
# Full-screen cluster overlay timer (frames)
cluster_overlay_timer = 0
# shoot speed multiplier used when velocity active
shoot_speed_multiplier = 1.0
# player movement speed multiplier (1.0 = normal)
player_speed_multiplier = 1.0
# score multiplier when golden is active
score_multiplier_active = 1
# aura active flag handled via timer
# cluster cap spawns extra goals immediately when used; timer kept for visual UI
# Transport sequence state: when all goals are completed we teleport the player
# to a start position then smoothly move them up a tunnel (Y descends) over
# TRANSPORT_DURATION_MS milliseconds. While transporting, input & shooting are
# disabled and a small "Transporting..." message is shown.
transporting = False
transport_start_ticks = 0
TRANSPORT_DURATION_MS = int(3 * 1000)
TRANSPORT_START_POS = (5200.0, 4400.0)
TRANSPORT_END_POS = (5200.0, 860.0)
# Level flow states
level_cleared = False
level_cleared_start = 0
LEVEL_CLEARED_DISPLAY_MS = 1500
# New: level-failed state (when health hits zero)
level_failed = False
level_failed_start = 0
LEVEL_FAILED_DISPLAY_MS = 1500
# After transport ends player can explore
post_transport = False
# Load persisted inventory
inventory = load_inventory()
# Load images (now safe after dummy display)
try:
    map_image = pygame.image.load(MAP_PATH)
    collision_surface = pygame.image.load(COLLISION_PATH)
    # Convert after loading to optimize
    map_image = map_image.convert()
    collision_surface = collision_surface.convert_alpha()
except pygame.error as e:
    sys.exit(1)
# Load goal animation frames from level2 (do this after a video mode is set)
try:
    import level2.goal as goal_module
    try:
        goal_module.load_assets()
    except Exception as e:
        print("Warning: failed to load level2 goal assets:", e)
except Exception:
    goal_module = None
# Load ball animation frames from level2.hit
try:
    import level2.hit as hit_module
    try:
        hit_module.load_assets()
        ball_frames = hit_module.ball_frames
    except Exception as e:
        print("Warning: failed to load level2 hit assets:", e)
        ball_frames = []
except Exception:
    hit_module = None
    ball_frames = []
# Sound played when chest is first opened
drop_sound = None
try:
    drop_sound = pygame.mixer.Sound('assets/sounds/drop.mp3')
except Exception:
    drop_sound = None
# Tunnel transport sound: try several common extensions and fall back to the
# music channel if needed. Support both pygame.mixer.Sound and pygame.mixer.music
# so we can handle formats the Sound loader doesn't support.
tunnel_sound = None
tunnel_is_music = False
def _load_tunnel_sound():
    global tunnel_sound, tunnel_is_music
    candidates = [
        'assets/sounds/tunnel.mp3',
        'assets/sounds/tunnel.ogg',
        'assets/sounds/tunnel.wav',
        'assets/sounds/tunnel1.mp3',
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        # First try to load as a Sound (small files)
        try:
            s = pygame.mixer.Sound(path)
            tunnel_sound = s
            tunnel_is_music = False
            return
        except Exception:
            # If Sound can't load, try loading into the music channel
            try:
                pygame.mixer.music.load(path)
                tunnel_sound = path
                tunnel_is_music = True
                return
            except Exception:
                # Not loadable; try next candidate
                continue
    # If nothing worked, keep tunnel_sound = None
_load_tunnel_sound()
# World dimensions from map
WORLD_WIDTH = map_image.get_width()
WORLD_HEIGHT = map_image.get_height()
# --- Performance: build a coarse collision grid once to avoid frequent get_at() scans ---
# Cell size controls precision vs. speed; 8 is a good tradeoff on large maps.
_COLLISION_CELL = 8
_collision_grid_w = (WORLD_WIDTH + _COLLISION_CELL - 1) // _COLLISION_CELL
_collision_grid_h = (WORLD_HEIGHT + _COLLISION_CELL - 1) // _COLLISION_CELL
# bytearray for compactness: 0 = empty, 1 = any red-like pixel present in the cell
collision_grid = bytearray(_collision_grid_w * _collision_grid_h)
# scan each cell once at startup (sample every 2 pixels inside the cell for speed)
_sample_step = 2
for cy in range(_collision_grid_h):
    y0 = cy * _COLLISION_CELL
    y1 = min(WORLD_HEIGHT, y0 + _COLLISION_CELL)
    for cx in range(_collision_grid_w):
        x0 = cx * _COLLISION_CELL
        x1 = min(WORLD_WIDTH, x0 + _COLLISION_CELL)
        marked = 0
        for yy in range(y0, y1, _sample_step):
            found = False
            for xx in range(x0, x1, _sample_step):
                pixel = collision_surface.get_at((xx, yy))
                if (abs(pixel[0] - COLLISION_COLOR[0]) < TOLERANCE and
                    abs(pixel[1] - COLLISION_COLOR[1]) < TOLERANCE and
                    abs(pixel[2] - COLLISION_COLOR[2]) < TOLERANCE and
                    pixel[3] > 0):
                    marked = 1
                    found = True
                    break
            if found:
                break
        collision_grid[cy * _collision_grid_w + cx] = marked
# Now set real screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Level 2: Sporeball Gauntlet - Goals Only Below y=4215!")
clock = pygame.time.Clock()
# Precreate full-screen overlay surfaces to avoid allocating new surfaces each frame.
_cluster_overlay_base = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
_cluster_overlay_base.fill((60, 200, 80, 255))
_gold_overlay_base = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
_gold_overlay_base.fill((255, 220, 100, 255))
_velocity_overlay_base = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
_velocity_overlay_base.fill((100, 150, 255, 255))
# Load small icon images for powerups (used in bottom-left UI)
powerup_images = {}
for key, info in POWERUP_INFO.items():
    path = f"assets/characters/{info['img']}"
    try:
        surf = pygame.image.load(path).convert_alpha()
        # scale to a consistent icon size
        surf = pygame.transform.smoothscale(surf, (48, 48))
    except Exception:
        surf = pygame.Surface((48, 48), pygame.SRCALPHA)
        surf.fill((100, 100, 100, 200))
    powerup_images[key] = surf
# Player setup in WORLD coordinates (start near ball for convenience)
player_pos = [730.0, 8230.0]  # Near ball start
player_radius = 20  # Simple circle for testing
# Instantiate character sprite for on-screen player (rendered at screen center)
try:
    character_sprite = char_move.Player(pos=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + player_radius))
    character_group = pygame.sprite.Group(character_sprite)
except Exception:
    character_sprite = None
    character_group = pygame.sprite.Group()
# Lock flag to prevent player movement after level completion/transport
player_locked = False
# Player health
player_max_health = 100
player_health = player_max_health
# Frames of temporary invulnerability after taking a bubble hit
HIT_COOLDOWN_FRAMES = int(0.8 * FPS)
player_hit_cooldown = 0
# Chest setup (placed in post-transport area)
CHEST_POS = (5800.0, 895.0)
CHEST_RADIUS = 48
try:
    chest_closed_img = pygame.image.load('assets/images/chest_closed.png').convert_alpha()
except Exception:
    chest_closed_img = pygame.Surface((64, 48), pygame.SRCALPHA)
    pygame.draw.rect(chest_closed_img, (100,60,20), chest_closed_img.get_rect())
try:
    chest_open_img = pygame.image.load('assets/images/chest_open.png').convert_alpha()
except Exception:
    chest_open_img = pygame.Surface((64, 48), pygame.SRCALPHA)
    pygame.draw.rect(chest_open_img, (200,180,80), chest_open_img.get_rect())
chest_opened = False
# Track previous chest state so we only play the open sound once on transition
prev_chest_opened = False
# Piles to decorate the post-transport area
PILE_POSITIONS = [(5780.0, 905.0), (5840.0, 905.0)]
try:
    pile_img = pygame.image.load('assets/images/pile1.png').convert_alpha()
except Exception:
    pile_img = pygame.Surface((48, 32), pygame.SRCALPHA)
    pygame.draw.ellipse(pile_img, (120, 90, 60), pile_img.get_rect())
# Camera setup (follows player, keeps player centered)
cam_x = player_pos[0] - SCREEN_WIDTH // 2
cam_y = player_pos[1] - SCREEN_HEIGHT // 2
cam_target_x, cam_target_y = cam_x, cam_y  # For lerping to ball
# Scoring
score = 0
streak = 0  # For combo (one strike = double next score)
# Use the ScorePopup from `level2.ui` (imported at top) so drawing can take a font
popups = []  # List of active pop-ups
particles = pygame.sprite.Group()
# simple timer used to animate goal sprite glow/frames
goal_timer = 0
# --- enemy projectiles (goal bubbles) ---
class GoalBubble(pygame.sprite.Sprite):
    """Small bubble shot by goals toward the player/ball."""
    def __init__(self, world_x, world_y, vx, vy, radius=8, lifetime=180):
        super().__init__()
        self.world_x = float(world_x)
        self.world_y = float(world_y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.radius = int(radius)
        self.lifetime = int(lifetime)  # frames
        # simple circular bubble image (alpha)
        d = self.radius * 2
        surf = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(surf, (150, 200, 255, 200), (self.radius, self.radius), self.radius)
        pygame.draw.circle(surf, (255, 255, 255, 120), (self.radius-1, self.radius-1), max(1, self.radius//3))
        self.image = surf
        self.rect = surf.get_rect()
    def update(self):
        # Move
        self.world_x += self.vx
        self.world_y += self.vy
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()
            return
        # Destroy if out of world bounds (cheap early-out)
        if (self.world_x < -100 or self.world_x > WORLD_WIDTH + 100 or
            self.world_y < -100 or self.world_y > WORLD_HEIGHT + 100):
            self.kill()
            return
        # collision with player (simple circle)
        try:
            dx = self.world_x - player_pos[0]
            dy = self.world_y - player_pos[1]
            if dx*dx + dy*dy <= (self.radius + player_radius) ** 2:
                # small knockback
                dist = math.hypot(dx, dy) or 1.0
                push = 22.0
                player_pos[0] += (dx / dist) * push
                player_pos[1] += (dy / dist) * push
                # damage the player (with brief invuln cooldown so one burst doesn't insta-kill)
                try:
                    global player_health, player_hit_cooldown
                    if player_hit_cooldown <= 0:
                        damage = 5
                        player_health = max(0, player_health - damage)
                        player_hit_cooldown = HIT_COOLDOWN_FRAMES
                        # show a small negative popup to indicate damage (reuse ScorePopup)
                        try:
                            popups.append(ScorePopup(player_pos[0], player_pos[1], -damage))
                        except Exception:
                            pass
                except Exception:
                    pass
                # spawn pop particles and remove the bubble
                for _ in range(6):
                    particles.add(SporeParticle(self.world_x, self.world_y))
                # play bubble-pop sound if available
                try:
                    if 'bubble_pop' in globals() and bubble_pop:
                        bubble_pop.play()
                except Exception:
                    pass
                self.kill()
                return
        except Exception:
            pass
        # collision with mushroom ball (pop)
        try:
            if mushroom_ball and getattr(mushroom_ball, 'pos', None):
                bx, by = mushroom_ball.pos[0], mushroom_ball.pos[1]
                dx = self.world_x - bx
                dy = self.world_y - by
                if dx*dx + dy*dy <= (self.radius + mushroom_ball.radius) ** 2:
                    for _ in range(8):
                        particles.add(SporeParticle(self.world_x, self.world_y))
                    # optional: nudge the ball slightly
                    try:
                        mushroom_ball.vx += (dx / (math.hypot(dx, dy) or 1.0)) * 0.8
                        mushroom_ball.vy += (dy / (math.hypot(dx, dy) or 1.0)) * 0.8
                    except Exception:
                        pass
                    # play bubble-pop sound if available
                    try:
                        if 'bubble_pop' in globals() and bubble_pop:
                            bubble_pop.play()
                    except Exception:
                        pass
                    self.kill()
                    return
        except Exception:
            pass
    def draw(self, surf, cam_x, cam_y):
        try:
            screen_x = int(self.world_x - cam_x - self.image.get_width() // 2)
            screen_y = int(self.world_y - cam_y - self.image.get_height() // 2)
            surf.blit(self.image, (screen_x, screen_y))
        except Exception:
            pass
# Group for active goal bubbles
enemy_projectiles = pygame.sprite.Group()
# Mushroom Ball moved to level2.ball (parameterized to avoid circular imports)
from level2.ball import MushroomBall
from level2.goals import GoalSprite, generate_goals, goals, goal_sprites, goal_sprite_map, pop_goals_hit_by_point, pop_goals_in_radius

# generate_goals implemented in level2.goals.generate_goals (imported above)
def check_goal_hit(ball_pos, ball_radius):
    # Use helper in level2.goals to remove goals hit by the ball. Return True if any removed.
    global score, streak, screen_shake_timer
    # aura_extra increases effective goal radius when aura is active
    aura_extra = 20 if powerup_timers.get('aura_alembic', 0) > 0 else 0
    removed = pop_goals_hit_by_point(ball_pos, ball_radius, GOAL_RADIUS, aura_extra=aura_extra)
    hits_this_shot = len(removed)
    if hits_this_shot == 0:
        return False
    # Spawn particles and fireworks and compute points as before
    for gx, gy in removed:
        for _ in range(PARTICLE_COUNT):
            particles.add(SporeParticle(gx, gy))
    # scoring
    if hits_this_shot == 1:
        if streak > 0:
            points = int(BASE_SCORE * COMBO_MULTIPLIER)
        else:
            points = BASE_SCORE
    else:
        points = int(BASE_SCORE * hits_this_shot * COMBO_MULTIPLIER)
    if powerup_timers.get('golden_gleam', 0) > 0:
        points = int(points * 2)
    score += points
    streak += hits_this_shot
    mushroom_ball.hit_this_shot = True
    for gx, gy in removed:
        for _ in range(FIREWORK_PARTICLE_COUNT):
            particles.add(FireworkParticle(gx, gy, color=random.choice(FIREWORK_COLORS)))
    screen_shake_timer = SCREEN_SHAKE_FRAMES
    try:
        if scored_sound:
            scored_sound.play()
    except Exception:
        pass
    popups.append(ScorePopup(ball_pos[0], ball_pos[1], points))
    return True

def aura_collect():
    """Auto-collect goals that are within AURA_RADIUS of the player.
    This function removes goals, spawns particles/fireworks, awards points, and
    schedules popups similar to check_goal_hit.
    """
    # Delegate goal removal to level2.goals and then perform the same
    # scoring/particle/popup effects that `check_goal_hit` does.
    global score, streak, screen_shake_timer
    # Remove goals within the aura radius and get the removed coords
    removed = pop_goals_in_radius(player_pos, AURA_RADIUS, GOAL_RADIUS)
    if not removed:
        return False
    # Spawn smaller spore bursts at each removed goal and clear temp timers
    for gx, gy in removed:
        for _ in range(PARTICLE_COUNT // 2):
            particles.add(SporeParticle(gx, gy))
        temp_goal_timers.pop((int(gx), int(gy)), None)
    # Compute points: treat all removed this frame as a single strike
    n = len(removed)
    if n == 1:
        pts = BASE_SCORE if streak == 0 else int(BASE_SCORE * COMBO_MULTIPLIER)
    else:
        pts = int(BASE_SCORE * n * COMBO_MULTIPLIER)
    # golden gleam doubles points if active
    if powerup_timers.get('golden_gleam', 0) > 0:
        pts = int(pts * 2)
    score += pts
    streak += n
    mushroom_ball.hit_this_shot = True
    # Fireworks (smaller burst for aura-collected goals)
    for gx, gy in removed:
        for _ in range(FIREWORK_PARTICLE_COUNT // 2):
            particles.add(FireworkParticle(gx, gy, color=random.choice(FIREWORK_COLORS)))
    # camera shake
    screen_shake_timer = SCREEN_SHAKE_FRAMES
    # popup at player position
    popups.append(ScorePopup(player_pos[0], player_pos[1], pts))
    try:
        if scored_sound:
            scored_sound.play()
    except Exception:
        pass

    # --- ensure we start the transport sequence if that was the last goal ---
    try:
        # mark level cleared so the transport block later will begin after the short delay
        if len(goals) == 0 and not level_cleared:
            level_cleared = True
            level_cleared_start = pygame.time.get_ticks()
            print("All goals cleared by aura — beginning transport delay")
    except Exception:
        pass

    return True
# Placeholder for the mushroom ball instance. The real instance is created
# after the collision helper is defined so we can pass it as a callback.
mushroom_ball = None
def update_camera():
    """Update camera to center on player, but lerp toward ball if active."""
    global cam_x, cam_y, cam_target_x, cam_target_y
    global screen_shake_timer
    # Target: Midpoint between player and ball if active
    # Guard against mushroom_ball being None during early init
    if mushroom_ball and getattr(mushroom_ball, 'active', False):
        mid_x = (player_pos[0] + mushroom_ball.pos[0]) / 2
        mid_y = (player_pos[1] + mushroom_ball.pos[1]) / 2
        cam_target_x = mid_x - SCREEN_WIDTH // 2
        cam_target_y = mid_y - SCREEN_HEIGHT // 2
    else:
        cam_target_x = player_pos[0] - SCREEN_WIDTH // 2
        cam_target_y = player_pos[1] - SCREEN_HEIGHT // 2
    
    # Lerp camera (smooth follow)
    lerp_speed = 0.1
    cam_x += (cam_target_x - cam_x) * lerp_speed
    cam_y += (cam_target_y - cam_y) * lerp_speed
    
    # Clamp camera so edges don't show outside world
    cam_x = max(0, min(cam_x, WORLD_WIDTH - SCREEN_WIDTH))
    cam_y = max(0, min(cam_y, WORLD_HEIGHT - SCREEN_HEIGHT))
    # Apply screen shake if active
    if screen_shake_timer and screen_shake_timer > 0:
        # Shake magnitude fades with timer
        frac = screen_shake_timer / float(max(1, SCREEN_SHAKE_FRAMES))
        shake_amount = 6 * frac
        sx = random.uniform(-shake_amount, shake_amount)
        sy = random.uniform(-shake_amount, shake_amount)
        cam_x += sx
        cam_y += sy
        screen_shake_timer -= 1

def ease_in_out_cubic(t: float) -> float:
    """Smooth cubic ease-in/out. t in [0,1]."""
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - pow(-2 * t + 2, 3) / 2
# The minimap drawing is handled by level2.ui.draw_minimap which is imported
# at module top. The original in-file implementation was removed to avoid
# shadowing the cleaner, parameterized helper in `level2.ui`.
def check_collision(world_x, world_y, radius):
    """
    Check if position overlaps red pixels in collision map.
    Uses a precomputed coarse collision_grid to avoid scanning every pixel each frame.
    """
    # Convert circle bounds to collision-grid cell indices
    min_cx = max(0, int((world_x - radius) // _COLLISION_CELL))
    max_cx = min(_collision_grid_w - 1, int((world_x + radius) // _COLLISION_CELL))
    min_cy = max(0, int((world_y - radius) // _COLLISION_CELL))
    max_cy = min(_collision_grid_h - 1, int((world_y + radius) // _COLLISION_CELL))
    # small step for precise check inside marked cells (keeps checks low)
    step = 2
    for cy in range(min_cy, max_cy + 1):
        base_row = cy * _collision_grid_w
        for cx in range(min_cx, max_cx + 1):
            if collision_grid[base_row + cx] == 0:
                continue  # this cell has no red-like pixels (fast skip)
            # cell may contain collision — do a precise but sparse scan restricted to the intersection
            cell_x0 = cx * _COLLISION_CELL
            cell_y0 = cy * _COLLISION_CELL
            x0 = max(int(world_x - radius), cell_x0)
            x1 = min(int(world_x + radius), min(cell_x0 + _COLLISION_CELL - 1, WORLD_WIDTH - 1))
            y0 = max(int(world_y - radius), cell_y0)
            y1 = min(int(world_y + radius), min(cell_y0 + _COLLISION_CELL - 1, WORLD_HEIGHT - 1))
            for px in range(x0, x1 + 1, step):
                for py in range(y0, y1 + 1, step):
                    if (px - world_x) ** 2 + (py - world_y) ** 2 > radius * radius:
                        continue
                    pixel = collision_surface.get_at((px, py))
                    if (abs(pixel[0] - COLLISION_COLOR[0]) < TOLERANCE and
                        abs(pixel[1] - COLLISION_COLOR[1]) < TOLERANCE and
                        abs(pixel[2] - COLLISION_COLOR[2]) < TOLERANCE and
                        pixel[3] > 0):
                        return True
    return False
# Ensure starting position is safe (move if on wall)
if check_collision(player_pos[0], player_pos[1], player_radius):
    player_pos[0] = 50.0
    player_pos[1] = 50.0
    while check_collision(player_pos[0], player_pos[1], player_radius) and player_pos[0] < WORLD_WIDTH - 100:
        player_pos[0] += 50
        player_pos[1] += 50
# Generate goals SCATTERED ACROSS MAP (before user moves, only y > 4215)
generate_goals(WORLD_WIDTH, WORLD_HEIGHT, FORBIDDEN_Y_MAX, NUM_GOALS, check_collision, goal_radius=GOAL_RADIUS, sprite_scale=1.8)
update_camera()  # Initial cam
# Instantiate the mushroom ball now that helper functions (like check_collision)
# and world sizes are defined. We used a placeholder above so this assignment
# can override it after the definitions are available.
mushroom_ball = MushroomBall(
    initial_pos=[730.0, 8230.0],
    radius=15,
    frames=ball_frames,
    get_shoot_speed_multiplier=lambda: shoot_speed_multiplier,
    check_collision_fn=check_collision,
    BALL_SPEED=BALL_SPEED,
    BALL_FRICTION=BALL_FRICTION,
    MUSHROOM_ANIM_SCALE=MUSHROOM_ANIM_SCALE,
    ROLL_VELOCITY_THRESHOLD=ROLL_VELOCITY_THRESHOLD,
    ROLL_FRAME_SPEED=ROLL_FRAME_SPEED,
    SQUISH_DURATION=SQUISH_DURATION,
    BALL_TRAIL_MAX=BALL_TRAIL_MAX,
    BALL_TRAIL_ALPHA=BALL_TRAIL_ALPHA,
    WORLD_WIDTH=WORLD_WIDTH,
    WORLD_HEIGHT=WORLD_HEIGHT,
)
# small timer (frames) used to delay auto-return after a hit (set when a shot hits)
mushroom_ball.return_timer = 0

# --- NEW: reset_level helper (keeps player in this level, does NOT quit to menu) ---
def reset_level():
    global player_pos, player_health, score, streak
    global particles, enemy_projectiles, popups
    global powerup_timers, temp_goal_timers, cluster_overlay_timer
    global goals, goal_sprites, goal_sprite_map
    global level_cleared, transporting, post_transport, player_locked
    global chest_opened, prev_chest_opened, level_failed, level_failed_start
    global mushroom_ball, player_speed_multiplier, shoot_speed_multiplier

    # restore basic actor state
    player_pos = [730.0, 8230.0]
    player_health = player_max_health
    score = 0
    streak = 0

    # clear transient effects
    try:
        particles.empty()
    except Exception:
        particles = pygame.sprite.Group()
    try:
        enemy_projectiles.empty()
    except Exception:
        enemy_projectiles = pygame.sprite.Group()
    popups = []

    # reset powerups / temp goals / overlays
    for k in powerup_timers.keys():
        powerup_timers[k] = 0
    temp_goal_timers.clear()
    cluster_overlay_timer = 0

    # clear and re-generate goals (keep same constraints as initial generation)
    try:
        goals[:] = []
        try:
            for gs in list(goal_sprites):
                try:
                    gs.kill()
                except Exception:
                    pass
            goal_sprites.empty()
        except Exception:
            pass
        goal_sprite_map.clear()
    except Exception:
        pass
    generate_goals(WORLD_WIDTH, WORLD_HEIGHT, FORBIDDEN_Y_MAX, NUM_GOALS, check_collision, goal_radius=GOAL_RADIUS, sprite_scale=1.8)

    # reset ball to player
    try:
        mushroom_ball.reset(player_pos)
        mushroom_ball.active = False
        mushroom_ball.stopped = True
        mushroom_ball.return_timer = 0
        mushroom_ball.hit_this_shot = False
    except Exception:
        pass

    # restore flow flags
    level_cleared = False
    transporting = False
    post_transport = False
    player_locked = False
    chest_opened = False
    prev_chest_opened = False

    # reset failed flag
    level_failed = False
    level_failed_start = 0

    # reset runtime multipliers
    player_speed_multiplier = 1.0
    shoot_speed_multiplier = 1.0

    # update camera to new player pos
    try:
        update_camera()
    except Exception:
        pass
# Main loop
running = True
mouse_world_pos = [0, 0]  # Track mouse in world coords
level_complete = False
font = pygame.font.SysFont(None, 24)
big_font = pygame.font.SysFont(None, 48)
while running:
    # Build powerup slots (bottom-left) based on purchased counts
    powerup_slots = []  # list of dicts: {key, rect, count}
    base_x = 10
    base_y = SCREEN_HEIGHT - 70
    spacing = 64
    idx = 0
    for key in POWERUP_INFO.keys():
        cnt = int(inventory.get(key, 0)) if inventory.get(key, 0) is not None else 0
        if cnt > 0:
            x = base_x + idx * spacing
            r = pygame.Rect(x, base_y, 56, 56)
            powerup_slots.append({'key': key, 'rect': r, 'count': cnt})
            idx += 1
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        # Click on powerup slot to use it
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for slot in powerup_slots:
                if slot['rect'].collidepoint((mx, my)):
                    k = slot['key']
                    if inventory.get(k, 0) > 0 and powerup_timers.get(k, 0) == 0:
                        # consume one
                        inventory[k] = inventory.get(k, 0) - 1
                        save_inventory(inventory)
                        # activate effect using per-powerup override if present
                        powerup_timers[k] = POWERUP_DURATIONS.get(k, POWERUP_DURATION_FRAMES)
                        # apply immediate behaviors if needed
                        if k == 'cluster_cap':
                            # spawn up to 3 temporary goals near ball (or player if ball not active)
                            spawned = 0
                            # choose center: prefer ball if active, otherwise player
                            if mushroom_ball and getattr(mushroom_ball, 'pos', None) and mushroom_ball.active:
                                center_x, center_y = int(mushroom_ball.pos[0]), int(mushroom_ball.pos[1])
                            else:
                                center_x, center_y = int(player_pos[0]), int(player_pos[1])
                            # try to place exactly 3 goals, with multiple attempts per placement
                            for goal_i in range(3):
                                placed = False
                                for _try in range(12):
                                    gx = center_x + random.randint(-100, 100)
                                    gy = center_y + random.randint(-100, 100)
                                    gx = max(GOAL_RADIUS, min(WORLD_WIDTH - GOAL_RADIUS, gx))
                                    gy = max(GOAL_RADIUS, min(WORLD_HEIGHT - GOAL_RADIUS, gy))
                                    if gy > FORBIDDEN_Y_MAX and not check_collision(gx, gy, GOAL_RADIUS):
                                        goals.append([gx, gy])
                                        gs = GoalSprite(gx, gy, index=len(goals))
                                        goal_sprites.add(gs)
                                        goal_sprite_map[(int(gx), int(gy))] = gs
                                        # mark temporary so it will be removed later
                                        temp_goal_timers[(int(gx), int(gy))] = POWERUP_DURATION_FRAMES
                                        # spawn some particles so player notices
                                        for _p in range(10):
                                            particles.add(SporeParticle(gx, gy))
                                        spawned += 1
                                        placed = True
                                        break
                                if not placed:
                                    # couldn't place this one; continue to next
                                    continue
                            # Activate full-screen soft green overlay for the duration
                            globals()['cluster_overlay_timer'] = POWERUP_DURATION_FRAMES
                            if spawned == 0:
                                print("Cluster cap used but no safe spawn locations found near", center_x, center_y)
                            else:
                                print(f"Cluster cap spawned {spawned} temporary goals near ({center_x},{center_y})")
                        # immediate feedback print
                        print(f"Used {k}; remaining: {inventory.get(k,0)}")
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and mushroom_ball.stopped and not player_locked:  # Shoot if stopped
                # Get mouse world pos
                mouse_screen = pygame.mouse.get_pos()
                mouse_world_pos[0] = mouse_screen[0] + cam_x
                mouse_world_pos[1] = mouse_screen[1] + cam_y
                mushroom_ball.shoot(player_pos, mouse_world_pos)
            if event.key == pygame.K_r:  # Reset ball manually
                if not mushroom_ball.hit_this_shot:
                    streak = 0
                mushroom_ball.reset(player_pos)
            if event.key == pygame.K_e:
                # If chest is opened and player presses E, exit back to main menu
                if post_transport and chest_opened:
                    try:
                        save_inventory(inventory)
                    except Exception:
                        pass
                    pygame.quit()
                    sys.exit()
        # Optional: Zoom with mouse wheel (basic)
        if event.type == pygame.MOUSEWHEEL:
            pass  # Expand if needed
    if level_complete:
        # Flash screen on win
        flash_alpha = int(128 * math.sin(pygame.time.get_ticks() * 0.01))
        flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        flash_surf.fill((0, 255, 0))
        flash_surf.set_alpha(flash_alpha)
        screen.blit(flash_surf, (0, 0))
    else:
        # If we're transporting the player, animate the tunnel movement and
        # skip standard input / ball updates. Otherwise handle input normally.
        # If level was just cleared, show a short "LEVEL CLEARED" message
        # then teleport the player to the transport start and begin the tunnel.
        if level_cleared and (not transporting) and (not post_transport):
            now = pygame.time.get_ticks()
            if now - level_cleared_start >= LEVEL_CLEARED_DISPLAY_MS:
                # teleport player to transport start and begin transport
                try:
                    player_pos[0] = TRANSPORT_START_POS[0]
                    player_pos[1] = TRANSPORT_START_POS[1]
                    transporting = True
                    transport_start_ticks = pygame.time.get_ticks()
                    player_locked = True
                    # play tunnel sound (when available)
                    try:
                        if tunnel_sound:
                            if tunnel_is_music:
                                pygame.mixer.music.play(-1)
                            else:
                                tunnel_sound.play(-1)
                    except Exception:
                        pass
                except Exception:
                    # if teleport fails, just mark as post_transport so player can move
                    post_transport = True
                    player_locked = False
        if transporting:
            now = pygame.time.get_ticks()
            elapsed = now - transport_start_ticks
            t_raw = min(1.0, elapsed / float(TRANSPORT_DURATION_MS))
            t = ease_in_out_cubic(t_raw)
            # Lock X to transport start X and ease Y from start -> end
            player_pos[0] = TRANSPORT_START_POS[0]
            player_pos[1] = TRANSPORT_START_POS[1] + (TRANSPORT_END_POS[1] - TRANSPORT_START_POS[1]) * t
            # Once transport finishes, mark level complete so the win screen shows
            if t_raw >= 1.0:
                transporting = False
                post_transport = True
                player_locked = False
                # stop tunnel sound gracefully if playing
                try:
                    if tunnel_sound:
                        if tunnel_is_music:
                            try:
                                pygame.mixer.music.fadeout(400)
                            except Exception:
                                try:
                                    pygame.mixer.music.stop()
                                except Exception:
                                    pass
                        else:
                            try:
                                tunnel_sound.fadeout(400)
                            except Exception:
                                try:
                                    tunnel_sound.stop()
                                except Exception:
                                    pass
                except Exception:
                    pass
            # Still allow particle updates and timers below; skip movement/ball logic
            keys = pygame.key.get_pressed()  # dummy read to keep input state consistent
        else:
            # Handle input (arrow keys or WASD for player)
            keys = pygame.key.get_pressed()
        # If not transporting and not locked, apply runtime movement, ball updates and goal checks.
        if (not transporting) and (not player_locked):
            # Apply runtime player movement multiplier (allows velocity powerup to speed player)
            cur_speed = PLAYER_SPEED * (player_speed_multiplier if player_speed_multiplier else 1.0)
            new_x, new_y = player_pos[0], player_pos[1]
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                new_x -= cur_speed
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                new_x += cur_speed
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                new_y -= cur_speed
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                new_y += cur_speed
            # Clamp proposed move to world bounds
            new_x = max(player_radius, min(new_x, WORLD_WIDTH - player_radius))
            new_y = max(player_radius, min(new_y, WORLD_HEIGHT - player_radius))
            # Test collision at new world position (silent)
            if not check_collision(new_x, new_y, player_radius):
                player_pos[0] = new_x
                player_pos[1] = new_y
            # Update ball
            mushroom_ball.update()

            # decrement automatic-return timer (frames). When it reaches 0 the existing
            # stopped-check will allow the ball to reset back to the player.
            try:
                if getattr(mushroom_ball, 'return_timer', 0) > 0:
                    mushroom_ball.return_timer -= 1
                    if mushroom_ball.return_timer < 0:
                        mushroom_ball.return_timer = 0
            except Exception:
                pass
            hit_during_shot = False
            if mushroom_ball.active and not level_complete:
                if check_goal_hit(mushroom_ball.pos, mushroom_ball.radius):
                    hit_during_shot = True
                    # play scored sound if available
                    try:
                        if 'scored_sound' in globals() and scored_sound:
                            scored_sound.play()
                    except Exception:
                        pass

                    # immediately return the ball to the player
                    mushroom_ball.active = False
                    mushroom_ball.stopped = True
                    mushroom_ball.reset(player_pos)
                    mushroom_ball.return_timer = 0

                    # If that was the last goal, enter the cleared state (same behavior)
                    if len(goals) == 0 and not level_cleared:
                        level_cleared = True
                        level_cleared_start = pygame.time.get_ticks()
                        try:
                            mushroom_ball.active = False
                            mushroom_ball.stopped = True
                        except Exception:
                            pass

                # If ball has stopped, only auto-reset immediately if no return_timer is pending.
                if mushroom_ball.stopped:
                    if getattr(mushroom_ball, 'return_timer', 0) > 0:
                        # Hold the stopped state until the return timer expires.
                        pass
                    else:
                        if not mushroom_ball.hit_this_shot:
                            streak = 0
                        mushroom_ball.reset(player_pos)  # Auto-reset after stop (no pending timer)
        # Update particles (always run so effects continue during transport)
        particles.update()
        # Update goal bubbles
        enemy_projectiles.update()
        # Update pop-ups (always run)
        popups = [p for p in popups if p.update()]
        # Update powerup timers and apply runtime flags (always run)
        # Decrement timers
        for k in list(powerup_timers.keys()):
            if powerup_timers[k] > 0:
                powerup_timers[k] -= 1

        # APPLY runtime effects for active powerups (fix: actually change movement/shoot speed)
        # Make velocity_vial noticeably faster while active
        if powerup_timers.get('velocity_vial', 0) > 0:
            # increase player movement and shooting speed while active
            player_speed_multiplier = 2.5  # faster walking
            shoot_speed_multiplier = 1.6   # faster ball shooting
        else:
            player_speed_multiplier = 1.0
            shoot_speed_multiplier = 1.0
        # player's hit cooldown tick-down
        if player_hit_cooldown > 0:
            player_hit_cooldown -= 1
        # Decrement temporary goal timers and remove expired temporary goals
        for key in list(temp_goal_timers.keys()):
            temp_goal_timers[key] -= 1
            if temp_goal_timers[key] <= 0:
                gx, gy = key
                # remove matching goal from goals list
                goals[:] = [g for g in goals if not (int(g[0]) == gx and int(g[1]) == gy)]
                gs = goal_sprite_map.pop((gx, gy), None)
                if gs:
                    try:
                        gs.kill()
                    except Exception:
                        pass
                del temp_goal_timers[key]

        # --- If temporary-goal expiry removed the last goal, make sure we mark the level cleared ---
        try:
            if len(goals) == 0 and not level_cleared:
                level_cleared = True
                level_cleared_start = pygame.time.get_ticks()
                print("All goals cleared by temp-goal expiry — beginning transport delay")
        except Exception:
            pass
        # Decrement cluster overlay timer
        if globals().get('cluster_overlay_timer', 0) > 0:
            globals()['cluster_overlay_timer'] -= 1
        # Aura auto-collect: if aura is active, collect nearby goals once per frame
        if powerup_timers.get('aura_alembic', 0) > 0:
            aura_collect()

        # --- New: handle player death / level failure ---
        if player_health <= 0 and not level_failed:
            level_failed = True
            level_failed_start = pygame.time.get_ticks()
            player_locked = True
            try:
                mushroom_ball.active = False
                mushroom_ball.stopped = True
            except Exception:
                pass

        if level_failed:
            # wait a short display time then reset the level
            now = pygame.time.get_ticks()
            if now - level_failed_start >= LEVEL_FAILED_DISPLAY_MS:
                reset_level()
    # Update camera to follow player/ball
    update_camera()
    # Draw: Viewport from world
    src_rect = pygame.Rect(cam_x, cam_y, SCREEN_WIDTH, SCREEN_HEIGHT)
    screen.blit(map_image, (0, 0), src_rect)  # Background map viewport ONLY
    # If cluster overlay active, draw a soft green tint over the entire screen
    if globals().get('cluster_overlay_timer', 0) > 0:
        # alpha pulses slightly for visual interest
        rem = globals().get('cluster_overlay_timer', 0)
        frac = rem / float(POWERUP_DURATION_FRAMES)
        # alpha ranges 120 -> 60 as it expires
        alpha = int(120 * frac + 60 * (1 - frac))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((60, 200, 80, max(30, min(180, alpha))))
        screen.blit(overlay, (0, 0))
    # If golden gleam active, draw a soft yellow tint over the screen
    if powerup_timers.get('golden_gleam', 0) > 0:
        rem = powerup_timers.get('golden_gleam', 0)
        frac = rem / float(POWERUP_DURATION_FRAMES)
        # alpha ranges 100 -> 40 as it expires
        alpha = int(100 * frac + 40 * (1 - frac))
        y_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        y_overlay.fill((255, 220, 100, max(20, min(180, alpha))))
        screen.blit(y_overlay, (0, 0))
        # small 'DOUBLE' label top-center while active
        try:
            lbl = big_font.render("DOUBLE SCORE", True, (255, 240, 180))
            lbl_rect = lbl.get_rect(center=(SCREEN_WIDTH//2, 40))
            # draw faint dark outline
            outline = pygame.Surface((lbl_rect.width+8, lbl_rect.height+8), pygame.SRCALPHA)
            outline.fill((0,0,0,100))
            screen.blit(outline, (lbl_rect.x-4, lbl_rect.y-4))
            screen.blit(lbl, lbl_rect)
        except Exception:
            pass
    # If velocity vial active, draw a soft blue tint over the screen
    if powerup_timers.get('velocity_vial', 0) > 0:
        rem = powerup_timers.get('velocity_vial', 0)
        # Use the per-powerup duration so visuals match runtime
        vel_dur = POWERUP_DURATIONS.get('velocity_vial', POWERUP_DURATION_FRAMES)
        frac = rem / float(vel_dur)
        # alpha ranges 140 -> 50 as it expires
        alpha = int(140 * frac + 50 * (1 - frac))
        b_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        b_overlay.fill((100, 150, 255, max(20, min(220, alpha))))
        screen.blit(b_overlay, (0, 0))
        # small 'SPEED' label top-center while active
        try:
            lbl = big_font.render("SPEED", True, (220, 240, 255))
            lbl_rect = lbl.get_rect(center=(SCREEN_WIDTH//2, 40))
            # faint outline
            outline = pygame.Surface((lbl_rect.width+8, lbl_rect.height+8), pygame.SRCALPHA)
            outline.fill((0,0,0,80))
            screen.blit(outline, (lbl_rect.x-4, lbl_rect.y-4))
            screen.blit(lbl, lbl_rect)
        except Exception:
            pass
    # If aura alembic active, draw a soft purple tint + lavender aura circle around player
    # Add a faint pulse (subtle radius + alpha modulation) to make the aura more visible
    if powerup_timers.get('aura_alembic', 0) > 0:
        rem = powerup_timers.get('aura_alembic', 0)
        frac = rem / float(POWERUP_DURATION_FRAMES)
        alpha = int(110 * frac + 40 * (1 - frac))
        p_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        p_overlay.fill((160, 120, 200, max(20, min(200, alpha))))
        screen.blit(p_overlay, (0, 0))
        # draw lavender aura circle around player (screen center) with stronger visibility + pulsing
        try:
            aura_screen_x = SCREEN_WIDTH // 2
            aura_screen_y = SCREEN_HEIGHT // 2
            # base pixel radius scaled from world radius, increase scale so it's larger on screen
            # previous scaling could be very small on large maps; amplify by 1.6
            base_px = int(AURA_RADIUS * (SCREEN_WIDTH / float(WORLD_WIDTH)) * 1.6)
            # time-based pulse (seconds)
            t = pygame.time.get_ticks() / 1000.0
            # pulse frequency in Hz and amplitude scaled by remaining fraction
            freq = 0.9  # ~0.9 Hz (one pulse ~1.1s)
            amp = 0.12 * frac  # larger amplitude (~±12% radius) when fresh, fades with timer
            pulse = math.sin(t * 2.0 * math.pi * freq)
            # modulated radius (keep subtle but more visible)
            aura_radius_px = max(6, int(base_px * (1.0 + amp * pulse)))
            # stronger base alphas to improve visibility
            fill_base = 90
            outline_base = 220
            # modulate alpha slightly with pulse and remaining timer
            fill_alpha = int(max(12, min(230, fill_base * (1.0 + 0.28 * pulse) * frac)))
            outline_alpha = int(max(50, min(255, outline_base * (1.0 + 0.45 * pulse) * frac)))
            # Create aura surface sized for the current pulsed radius
            aura_surf = pygame.Surface((aura_radius_px * 2 + 20, aura_radius_px * 2 + 20), pygame.SRCALPHA)
            center = (aura_radius_px + 10, aura_radius_px + 10)
            # soft filled circle (higher alpha)
            pygame.draw.circle(aura_surf, (220, 200, 255, fill_alpha), center, aura_radius_px)
            # outer glow: larger, faint but more visible
            glow_r = int(aura_radius_px * 1.3)
            try:
                glow_alpha = int(max(10, min(200, fill_alpha * 0.6)))
                pygame.draw.circle(aura_surf, (230, 210, 255, glow_alpha), center, glow_r)
            except Exception:
                pass
            # main strong outline
            pygame.draw.circle(aura_surf, (200, 180, 255, outline_alpha), center, aura_radius_px, 4)
            # Add a faint expanding/contracting outer ring to draw attention
            ring_amp = 0.06 * frac
            ring_r = int(aura_radius_px * (1.0 + ring_amp * math.cos(t * 2.0 * math.pi * (freq * 0.6))))
            ring_alpha = int(max(8, min(120, 80 * frac * (1.0 + 0.8 * pulse))))
            try:
                pygame.draw.circle(aura_surf, (210, 190, 255, ring_alpha), center, ring_r, 2)
            except Exception:
                pass
            # blit centered on player screen position
            screen.blit(aura_surf, (aura_screen_x - aura_radius_px - 10, aura_screen_y - aura_radius_px - 10))
        except Exception:
            pass
    # Draw 'Level Cleared' message right after clearing goals and before teleport
    if level_cleared and (not transporting) and (not post_transport):
        now = pygame.time.get_ticks()
        if now - level_cleared_start < LEVEL_CLEARED_DISPLAY_MS:
            try:
                msg = big_font.render("LEVEL CLEARED", True, (255, 215, 120))
                r = msg.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 120))
                screen.blit(msg, r)
            except Exception:
                pass

    # New: display failure message when health reaches zero
    if level_failed:
        try:
            msg = big_font.render("level failed, pls try again", True, (255, 80, 80))
            r = msg.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 60))
            # faint outline
            outline = pygame.Surface((r.width+8, r.height+8), pygame.SRCALPHA)
            outline.fill((0,0,0,140))
            screen.blit(outline, (r.x-4, r.y-4))
            screen.blit(msg, r)
        except Exception:
            pass
    # If post-transport state active, draw chest and handle proximity
    if post_transport:
        try:
            cx, cy = CHEST_POS
            screen_x = int(cx - cam_x - chest_closed_img.get_width()//2)
            screen_y = int(cy - cam_y - chest_closed_img.get_height()//2)
            # Draw decorative piles near the chest (behind the chest)
            try:
                for px, py in PILE_POSITIONS:
                    p_screen_x = int(px - cam_x - (pile_img.get_width() // 2))
                    p_screen_y = int(py - cam_y - (pile_img.get_height() // 2))
                    screen.blit(pile_img, (p_screen_x, p_screen_y))
            except Exception:
                pass
            
            # collision / proximity check
            dist_sq = (player_pos[0] - cx) ** 2 + (player_pos[1] - cy) ** 2
            # Determine new opened state and play drop sound only on transition
            new_opened = dist_sq <= CHEST_RADIUS ** 2
            if new_opened:
                # Play drop/open sound the moment chest transitions from closed -> open
                if not prev_chest_opened:
                    try:
                        if drop_sound:
                            drop_sound.play()
                    except Exception:
                        pass
                chest_opened = True
                screen.blit(chest_open_img, (screen_x, screen_y))
                # show prompt
                try:
                    prompt = font.render("Press E to exit", True, (240, 240, 240))
                    pr = prompt.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 60))
                    screen.blit(prompt, pr)
                except Exception:
                    pass
            else:
                chest_opened = False
                screen.blit(chest_closed_img, (screen_x, screen_y))
            prev_chest_opened = new_opened
        except Exception:
            pass
    # Draw particles (world -> screen offset)
    for p in list(particles):
        try:
            # p.rect stores world coordinates; offset by camera
            screen_x = int(p.rect.x - cam_x)
            screen_y = int(p.rect.y - cam_y)
            screen.blit(p.image, (screen_x, screen_y))
        except Exception:
            # Fallback to default draw if anything goes wrong
            try:
                particles.draw(screen)
            except Exception:
                pass
    # Draw active goal bubbles
    for b in list(enemy_projectiles):
        try:
            b.draw(screen, cam_x, cam_y)
        except Exception:
            try:
                enemy_projectiles.remove(b)
            except Exception:
                pass
    # end draw goal bubbles
    
    # Draw goal sprites (animated). Update and blit each sprite relative to camera.
    goal_timer += 1
    for gs in list(goal_sprites):
        gs.step()
        gs.sync_to_camera(cam_x, cam_y)
        # --- Goal shooting behavior: each goal has a shot timer and will fire a bubble at the player/ball ---
        try:
            # initialize per-sprite shot timer if missing
            if getattr(gs, 'shot_timer', None) is None:
                # initial delay randomized so not all fire at once (frames)
                gs.shot_timer = random.randint(int(0.5 * FPS), int(3.0 * FPS))
            gs.shot_timer -= 1
            if gs.shot_timer <= 0:
                # reset timer (random cadence)
                gs.shot_timer = random.randint(int(0.8 * FPS), int(2.6 * FPS))
                # determine world spawn position for the bubble (use synced rect + cam)
                try:
                    spawn_x = gs.rect.centerx + cam_x
                    spawn_y = gs.rect.centery + cam_y
                except Exception:
                    # fallback to stored goal coords if available
                    spawn_x = getattr(gs, 'x', getattr(gs, 'world_x', spawn_x))
                    spawn_y = getattr(gs, 'y', getattr(gs, 'world_y', spawn_y))
                # choose target: prefer active mushroom_ball, otherwise player
                if mushroom_ball and getattr(mushroom_ball, 'active', False):
                    target = mushroom_ball.pos
                else:
                    target = player_pos
                dx = target[0] - spawn_x
                dy = target[1] - spawn_y
                dist = math.hypot(dx, dy) or 1.0
                # bubble speed tuned to be noticeable but dodgeable
                # faster bubbles per request
                speed = random.uniform(5.0, 9.0)
                vx = dx / dist * speed
                vy = dy / dist * speed
                enemy_projectiles.add(GoalBubble(spawn_x, spawn_y, vx, vy))
        except Exception:
            pass
        try:
            # Lazily build a soft radial glow surface per-goal to avoid per-frame allocations.
            if getattr(gs, 'glow_image', None) is None:
                gw = max(64, int(max(gs.rect.width, gs.rect.height) * 2.4))
                glow = pygame.Surface((gw, gw), pygame.SRCALPHA)
                cx, cy = gw // 2, gw // 2
                # Draw a few concentric circles for a soft gradient glow (cheap)
                radii = [int(gw * f) for f in (0.72, 0.52, 0.36, 0.22, 0.12)]
                alphas = [180, 120, 80, 48, 20]
                # warm yellowish glow; change color if you want different tint
                for r, a in zip(radii, alphas):
                    pygame.draw.circle(glow, (255, 210, 120, a), (cx, cy), r)
                gs.glow_image = glow
            # Pulse the glow alpha over time (per-goal phase uses index if available)
            t = pygame.time.get_ticks() / 1000.0
            phase = (getattr(gs, 'index', 0) * 0.37)
            pulse = 0.78 + 0.28 * math.sin(t * 2.0 * math.pi * 0.55 + phase)
            alpha = int(220 * max(0.0, min(1.0, pulse)))
            try:
                gs.glow_image.set_alpha(alpha)
            except Exception:
                pass
            # Center glow on the goal's screen rect center
            glow_pos = (gs.rect.centerx - gs.glow_image.get_width() // 2,
                        gs.rect.centery - gs.glow_image.get_height() // 2)
            screen.blit(gs.glow_image, glow_pos)
            # Finally draw the goal sprite itself
            screen.blit(gs.image, gs.rect)
        except Exception:
            pass
    # Draw player (always centered since cam follows)
    # Update & draw character sprite centered at the player screen position.
    # We let the sprite update its animation state (reads input) but keep it anchored
    # to the screen center by resetting midbottom each frame.
    try:
        if character_sprite:
            character_sprite.update()  # advances animation / facing based on input
            character_sprite.rect.midbottom = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + player_radius)
            screen.blit(character_sprite.image, character_sprite.rect)
        else:
            # fallback to simple circle if sprite missing
            pygame.draw.circle(screen, (0, 0, 255), (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), player_radius)
    except Exception:
        try:
            pygame.draw.circle(screen, (0, 0, 255), (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), player_radius)
        except Exception:
            pass
    # Draw mushroom ball only when not transporting
    if not transporting:
        mushroom_ball.draw(screen, cam_x, cam_y)
    else:
        # Dim the view slightly and show a centered transporting label
        try:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            screen.blit(overlay, (0, 0))
            t_txt = big_font.render("Transporting...", True, (255, 255, 255))
            t_rect = t_txt.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 40))
            # faint outline for readability
            outline = pygame.Surface((t_rect.width+8, t_rect.height+8), pygame.SRCALPHA)
            outline.fill((0,0,0,120))
            screen.blit(outline, (t_rect.x-4, t_rect.y-4))
            screen.blit(t_txt, t_rect)
        except Exception:
            pass
    # Draw score pop-ups
    for popup in popups:
        # ScorePopup.draw now requires a font argument
        popup.draw(screen, cam_x, cam_y, font)
    # Aim line (from player to mouse, if not shooting and not transporting or locked)
    if (not transporting) and (not player_locked) and mushroom_ball.stopped and not level_complete:
        mouse_screen = pygame.mouse.get_pos()
        mouse_world_pos[0] = mouse_screen[0] + cam_x
        mouse_world_pos[1] = mouse_screen[1] + cam_y
        # Line in screen coords — start from the character sprite center (middle of character)
        try:
            if character_sprite:
                start_screen = character_sprite.rect.center
            else:
                start_screen = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        except Exception:
            start_screen = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        end_screen = (mouse_screen[0], mouse_screen[1])
        pygame.draw.line(screen, (255, 255, 0), start_screen, end_screen, 2)
    # Draw minimap with real map texture
    # draw_minimap has been moved to level2.ui and is parameterized to avoid globals
    draw_minimap(screen, player_pos, map_image, mushroom_ball, cam_x, cam_y,
                 WORLD_WIDTH, WORLD_HEIGHT, MINIMAP_SIZE, MINIMAP_ZOOM, goals)
    # Info/UI with score (don't display the word 'Streak' at the top; streak counter still used internally)
    info = font.render(f"Pos: ({int(player_pos[0])}, {int(player_pos[1])}) | Score: {score} | Goals left: {len(goals)} | SPACE to shoot! R to reset", True, (255, 255, 255))
    screen.blit(info, (10, 10))
    # Draw player health bar
    try:
        hb_x, hb_y = 10, 36
        hb_w, hb_h = 220, 18
        # background
        pygame.draw.rect(screen, (30, 30, 30), (hb_x, hb_y, hb_w, hb_h))
        # current health fill
        frac = max(0.0, min(1.0, float(player_health) / float(player_max_health)))
        pygame.draw.rect(screen, (50, 180, 70), (hb_x + 2, hb_y + 2, int((hb_w - 4) * frac), hb_h - 4))
        # border
        pygame.draw.rect(screen, (160, 160, 160), (hb_x, hb_y, hb_w, hb_h), 2)
        # numeric text
        try:
            hp_txt = font.render(f"HP: {int(player_health)} / {int(player_max_health)}", True, (240, 240, 240))
            screen.blit(hp_txt, (hb_x + hb_w + 8, hb_y - 2))
        except Exception:
            pass
    except Exception:
        pass
    # Draw purchased powerups as icons at bottom-left; clicking uses them
    # powerup_slots was computed at top of loop
    for slot in powerup_slots:
        r = slot['rect']
        # background card
        pygame.draw.rect(screen, (40, 40, 40), r)
        pygame.draw.rect(screen, (120, 120, 120), r, 2)
        # icon
        key = slot['key']
        img = powerup_images.get(key)
        if img:
            img_r = img.get_rect(center=(r.x + 28, r.y + 28))
            screen.blit(img, img_r)
        # count badge
        cnt = slot['count']
        badge_pos = (r.right - 10, r.y + 10)
        pygame.draw.circle(screen, (0, 200, 0), badge_pos, 10)
        ct = font.render(str(cnt), True, (0, 0, 0))
        ct_r = ct.get_rect(center=badge_pos)
        screen.blit(ct, ct_r)
        # if active, draw remaining seconds indicator (small bar)
        t = powerup_timers.get(key, 0)
        if t > 0:
            secs = int(math.ceil(t / float(FPS)))
            sec_text = font.render(f"{secs}s", True, (255, 255, 0))
            st_r = sec_text.get_rect(center=(r.centerx, r.y - 10))
            screen.blit(sec_text, st_r)
    if level_complete:
        win_text = big_font.render("LEVEL COMPLETE! Final Score: " + str(score), True, (255, 255, 0))
        screen.blit(win_text, (SCREEN_WIDTH//2 - win_text.get_width()//2, SCREEN_HEIGHT//2))
    pygame.display.flip()
    clock.tick(FPS)
pygame.quit()
sys.exit()

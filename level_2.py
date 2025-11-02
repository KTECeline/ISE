import pygame
import sys
import os
import random
import math
import json
from level2.goal import walking_frames_right, hit_frames_right
from level2.particles import SporeParticle, FireworkParticle
from level2.ui import ScorePopup, draw_minimap

# Initialize Pygame
pygame.init()

# Initialize audio mixer (safe if system doesn't have audio — catch failures)
try:
    pygame.mixer.init()
except Exception:
    pass

# Create a dummy display mode first to allow image loading (fixes "No video mode" error)
dummy_screen = pygame.display.set_mode((1, 1), pygame.NOFRAME)

# Constants
SCREEN_WIDTH = 1024  # Fixed screen size for viewing
SCREEN_HEIGHT = 768
FPS = 60
PLAYER_SPEED = 5
BALL_SPEED = 10  # Initial shoot speed
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

# Load sound effects (optional — game continues if missing)
scored_sound = None
try:
    scored_sound = pygame.mixer.Sound('assets/sounds/scored.mp3')
except Exception:
    scored_sound = None

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

# Now set real screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Level 2: Sporeball Gauntlet - Goals Only Below y=4215!")
clock = pygame.time.Clock()

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
# Lock flag to prevent player movement after level completion/transport
player_locked = False

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
    Scans a circle around (world_x, world_y) for red.
    Returns True if hit (collision).
    """
    hit = False
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if dx**2 + dy**2 > radius**2:  # Skip outside circle
                continue
            check_x = int(world_x + dx)
            check_y = int(world_y + dy)
            if 0 <= check_x < WORLD_WIDTH and 0 <= check_y < WORLD_HEIGHT:
                pixel = collision_surface.get_at((check_x, check_y))
                # Check if close to red (with tolerance)
                if (abs(pixel[0] - COLLISION_COLOR[0]) < TOLERANCE and
                    abs(pixel[1] - COLLISION_COLOR[1]) < TOLERANCE and
                    abs(pixel[2] - COLLISION_COLOR[2]) < TOLERANCE and
                    pixel[3] > 0):  # Not transparent
                    hit = True
                    break
        if hit:
            break
    return hit

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
            hit_during_shot = False
            if mushroom_ball.active and not level_complete:
                if check_goal_hit(mushroom_ball.pos, mushroom_ball.radius):
                    hit_during_shot = True
                    # If that was the last goal, enter the cleared state and show the
                    # 'Level Cleared' message briefly before teleporting to the
                    # transport start area.
                    if len(goals) == 0 and not level_cleared:
                        level_cleared = True
                        level_cleared_start = pygame.time.get_ticks()
                        # deactivate the ball so it doesn't continue moving
                        try:
                            mushroom_ball.active = False
                            mushroom_ball.stopped = True
                        except Exception:
                            pass
                if mushroom_ball.stopped:
                    if not mushroom_ball.hit_this_shot:
                        streak = 0
                    mushroom_ball.reset(player_pos)  # Auto-reset after stop

        # Update particles (always run so effects continue during transport)
        particles.update()

        # Update pop-ups (always run)
        popups = [p for p in popups if p.update()]

        # Update powerup timers and apply runtime flags (always run)
        # Decrement timers
        for k in list(powerup_timers.keys()):
            if powerup_timers[k] > 0:
                powerup_timers[k] -= 1

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

        # Decrement cluster overlay timer
        if globals().get('cluster_overlay_timer', 0) > 0:
            globals()['cluster_overlay_timer'] -= 1
        # Aura auto-collect: if aura is active, collect nearby goals once per frame
        if powerup_timers.get('aura_alembic', 0) > 0:
            aura_collect()

        # Apply shoot & movement speed multipliers if velocity_vial active
        if powerup_timers.get('velocity_vial', 0) > 0:
            shoot_speed_multiplier = 2.0
            player_speed_multiplier = 2.0
        else:
            shoot_speed_multiplier = 1.0
            player_speed_multiplier = 1.0

        # golden_gleam is handled inside check_goal_hit via powerup_timers

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

    # Draw goal sprites (animated). Update and blit each sprite relative to camera.
    goal_timer += 1
    for gs in list(goal_sprites):
        gs.step()
        gs.sync_to_camera(cam_x, cam_y)
        # Only blit if on screen
        if -100 <= gs.rect.right and gs.rect.left <= SCREEN_WIDTH + 100 and -100 <= gs.rect.bottom and gs.rect.top <= SCREEN_HEIGHT + 100:
            # Draw a soft glow under the goal if available
            try:
                if getattr(gs, 'glow_image', None) is not None:
                    # Pulse the glow slowly using the global ticks. The per-pixel alpha
                    # in glow_image is modulated by a per-surface alpha to create a soft pulse.
                    t = pygame.time.get_ticks() / 1000.0
                    # frequency: 0.5 Hz (one full pulse every 2 seconds)
                    pulse = 0.75 + 0.25 * math.sin(t * 2 * math.pi * 0.5 + (gs.index * 0.5))
                    glow_copy = gs.glow_image.copy()
                    # Max overall alpha of the glow: 200 (will multiply with per-pixel alpha)
                    glow_copy.set_alpha(int(200 * max(0.0, min(1.0, pulse))))
                    glow_rect = glow_copy.get_rect(center=gs.rect.center)
                    screen.blit(glow_copy, glow_rect)
            except Exception:
                pass
            screen.blit(gs.image, gs.rect)
            # Draw numbering if the sprite still corresponds to an active goal coordinate
            # We stored an index when creating sprites
            try:
                label = font.render(str(gs.index + 1), True, (255, 0, 0))
                screen.blit(label, (gs.rect.centerx - 5, gs.rect.top - 15))
            except Exception:
                pass

    # Draw player (always centered since cam follows)
    pygame.draw.circle(screen, (0, 0, 255), (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), player_radius)

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
        # Line in screen coords
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
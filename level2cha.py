# full_game_with_kirby_player.py
import pygame
import sys
import random
import math
import json
from level2.goal import walking_frames_right, hit_frames_right
from level2.particles import SporeParticle, FireworkParticle
from level2.ui import ScorePopup, draw_minimap

# Initialize Pygame
pygame.init()
try:
    pygame.mixer.init()
except Exception:
    pass

# Create a dummy display mode first to allow image loading (fixes "No video mode" error)
dummy_screen = pygame.display.set_mode((1, 1), pygame.NOFRAME)

# Constants
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60
PLAYER_SPEED = 5
BALL_SPEED = 10
BALL_FRICTION = 0.98
COLLISION_COLOR = (255, 0, 0)
TOLERANCE = 50
GOAL_RADIUS = 30
NUM_GOALS = 8
PARTICLE_COUNT = 20
MINIMAP_SIZE = (200, 150)
MINIMAP_ZOOM = 1.5
BASE_SCORE = 10
COMBO_MULTIPLIER = 2
POPUP_LIFETIME = 60
FORBIDDEN_Y_MAX = 4215
MUSHROOM_ANIM_SCALE = 2.0
FIREWORK_PARTICLE_COUNT = 28
FIREWORK_COLORS = [(255, 40, 40), (255, 80, 60), (200, 30, 30), (255, 100, 80)]
SCREEN_SHAKE_FRAMES = 12
screen_shake_timer = 0

# Aura & animation settings
AURA_RADIUS = 150
ROLL_VELOCITY_THRESHOLD = 1.2
ROLL_FRAME_SPEED = 0.5
SQUISH_FRAMES = 4
SQUISH_DURATION = 10
BALL_TRAIL_MAX = 12
BALL_TRAIL_ALPHA = 160
BALL_TRAIL_SCALE_DECAY = 0.95

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

POWERUP_INFO = {
    'velocity_vial': {'img': 'speed1.png', 'name': 'Velocity Vial'},
    'golden_gleam': {'img': 'gold1.png', 'name': 'Golden Gleam'},
    'cluster_cap': {'img': 'magnet1.png', 'name': 'Cluster Cap'},
    'aura_alembic': {'img': 'circle1.png', 'name': 'Aura Alembic'},
}

POWERUP_DURATION_FRAMES = int(6 * FPS)
powerup_timers = {k: 0 for k in POWERUP_INFO.keys()}
POWERUP_DURATIONS = {'velocity_vial': int(10 * FPS)}
temp_goal_timers = {}
cluster_overlay_timer = 0
shoot_speed_multiplier = 1.0
player_speed_multiplier = 1.0
score_multiplier_active = 1

inventory = load_inventory()

# Load images (now safe after dummy display)
try:
    map_image = pygame.image.load(MAP_PATH)
    collision_surface = pygame.image.load(COLLISION_PATH)
    map_image = map_image.convert()
    collision_surface = collision_surface.convert_alpha()
except pygame.error as e:
    print("Failed loading map or collision. Exiting.", e)
    sys.exit(1)

# Load other level assets
try:
    import level2.goal as goal_module
    try:
        goal_module.load_assets()
    except Exception as e:
        print("Warning: failed to load level2 goal assets:", e)
except Exception:
    goal_module = None

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

scored_sound = None
try:
    scored_sound = pygame.mixer.Sound('assets/sounds/scored.mp3')
except Exception:
    pass

WORLD_WIDTH = map_image.get_width()
WORLD_HEIGHT = map_image.get_height()

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Level 2: Sporeball Gauntlet - Goals Only Below y=4215!")
clock = pygame.time.Clock()

powerup_images = {}
for key, info in POWERUP_INFO.items():
    path = f"assets/characters/{info['img']}"
    try:
        surf = pygame.image.load(path).convert_alpha()
        surf = pygame.transform.smoothscale(surf, (48, 48))
    except Exception:
        surf = pygame.Surface((48, 48), pygame.SRCALPHA)
        surf.fill((100, 100, 100, 200))
    powerup_images[key] = surf

# Player setup (world coords)
player_pos = [730.0, 8230.0]

# ------------------ KIRBY SPRITE (1 row x 9 columns) ------------------
KIRBY_PATH = 'character/kirbWalk.png'  # your sprite sheet path

def load_spritesheet(path, rows=1, cols=9):
    surf = pygame.image.load(path).convert_alpha()
    w, h = surf.get_size()
    frame_w = w // cols
    frame_h = h // rows
    frames = []
    for r in range(rows):
        for c in range(cols):
            rect = pygame.Rect(c*frame_w, r*frame_h, frame_w, frame_h)
            frame = surf.subsurface(rect).copy()
            frames.append(frame)
    return frames, frame_w, frame_h

try:
    kirby_frames, kirb_fw, kirb_fh = load_spritesheet(KIRBY_PATH, rows=1, cols=9)
except Exception as e:
    print("Failed to load kirbWalk.png:", e)
    kirby_frames = []
    kirb_fw = 40
    kirb_fh = 40

# Scale frames to match player visual scale if you want
SPRITE_SCALE = 1.0  # change if you want to scale the sprite up/down
if SPRITE_SCALE != 1.0 and kirby_frames:
    kirby_frames = [pygame.transform.smoothscale(f, (int(kirb_fw * SPRITE_SCALE), int(kirb_fh * SPRITE_SCALE))) for f in kirby_frames]
    kirb_fw = int(kirb_fw * SPRITE_SCALE)
    kirb_fh = int(kirb_fh * SPRITE_SCALE)

# Compute player_radius from sprite height so feet align (avoid "floating")
# We'll set the collision radius to roughly 40-50% of sprite height so sprite bottom meets the collision center:
player_radius = max(12, int(kirb_fh * 0.45))

# Animation indices
walk_frames = list(range(len(kirby_frames))) if kirby_frames else [0]
idle_frame_index = 0
jump_frame_index = min(4, len(kirby_frames)-1)  # choose a mid-frame as jump pose
dash_frame_index = min(2, len(kirby_frames)-1)  # choose an arbitrary frame for dash pose

anim_index = 0
anim_timer = 0.0
ANIM_FPS = 12.0

# ------------------ END KIRBY SPRITE ------------------

# Camera setup
cam_x = player_pos[0] - SCREEN_WIDTH // 2
cam_y = player_pos[1] - SCREEN_HEIGHT // 2
cam_target_x, cam_target_y = cam_x, cam_y

# Scoring
score = 0
streak = 0
popups = []
particles = pygame.sprite.Group()
goal_timer = 0

from level2.ball import MushroomBall
from level2.goals import GoalSprite, generate_goals, goals, goal_sprites, goal_sprite_map, pop_goals_hit_by_point, pop_goals_in_radius

def check_goal_hit(ball_pos, ball_radius):
    global score, streak, screen_shake_timer
    aura_extra = 20 if powerup_timers.get('aura_alembic', 0) > 0 else 0
    removed = pop_goals_hit_by_point(ball_pos, ball_radius, GOAL_RADIUS, aura_extra=aura_extra)
    hits_this_shot = len(removed)
    if hits_this_shot == 0:
        return False
    for gx, gy in removed:
        for _ in range(PARTICLE_COUNT):
            particles.add(SporeParticle(gx, gy))
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
    global score, streak, screen_shake_timer
    removed = pop_goals_in_radius(player_pos, AURA_RADIUS, GOAL_RADIUS)
    if not removed:
        return False
    for gx, gy in removed:
        for _ in range(PARTICLE_COUNT // 2):
            particles.add(SporeParticle(gx, gy))
        temp_goal_timers.pop((int(gx), int(gy)), None)
    n = len(removed)
    if n == 1:
        pts = BASE_SCORE if streak == 0 else int(BASE_SCORE * COMBO_MULTIPLIER)
    else:
        pts = int(BASE_SCORE * n * COMBO_MULTIPLIER)
    if powerup_timers.get('golden_gleam', 0) > 0:
        pts = int(pts * 2)
    score += pts
    streak += n
    mushroom_ball.hit_this_shot = True
    for gx, gy in removed:
        for _ in range(FIREWORK_PARTICLE_COUNT // 2):
            particles.add(FireworkParticle(gx, gy, color=random.choice(FIREWORK_COLORS)))
    screen_shake_timer = SCREEN_SHAKE_FRAMES
    popups.append(ScorePopup(player_pos[0], player_pos[1], pts))
    try:
        if scored_sound:
            scored_sound.play()
    except Exception:
        pass
    return True

mushroom_ball = None

def update_camera():
    global cam_x, cam_y, cam_target_x, cam_target_y, screen_shake_timer
    if mushroom_ball and getattr(mushroom_ball, 'active', False):
        mid_x = (player_pos[0] + mushroom_ball.pos[0]) / 2
        mid_y = (player_pos[1] + mushroom_ball.pos[1]) / 2
        cam_target_x = mid_x - SCREEN_WIDTH // 2
        cam_target_y = mid_y - SCREEN_HEIGHT // 2
    else:
        cam_target_x = player_pos[0] - SCREEN_WIDTH // 2
        cam_target_y = player_pos[1] - SCREEN_HEIGHT // 2
    lerp_speed = 0.1
    cam_x += (cam_target_x - cam_x) * lerp_speed
    cam_y += (cam_target_y - cam_y) * lerp_speed
    cam_x = max(0, min(cam_x, WORLD_WIDTH - SCREEN_WIDTH))
    cam_y = max(0, min(cam_y, WORLD_HEIGHT - SCREEN_HEIGHT))
    if screen_shake_timer and screen_shake_timer > 0:
        frac = screen_shake_timer / float(max(1, SCREEN_SHAKE_FRAMES))
        shake_amount = 6 * frac
        sx = random.uniform(-shake_amount, shake_amount)
        sy = random.uniform(-shake_amount, shake_amount)
        cam_x += sx
        cam_y += sy
        screen_shake_timer -= 1

def check_collision(world_x, world_y, radius):
    hit = False
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if dx**2 + dy**2 > radius**2:
                continue
            check_x = int(world_x + dx)
            check_y = int(world_y + dy)
            if 0 <= check_x < WORLD_WIDTH and 0 <= check_y < WORLD_HEIGHT:
                pixel = collision_surface.get_at((check_x, check_y))
                if (abs(pixel[0] - COLLISION_COLOR[0]) < TOLERANCE and
                    abs(pixel[1] - COLLISION_COLOR[1]) < TOLERANCE and
                    abs(pixel[2] - COLLISION_COLOR[2]) < TOLERANCE and
                    pixel[3] > 0):
                    hit = True
                    break
        if hit:
            break
    return hit

if check_collision(player_pos[0], player_pos[1], player_radius):
    player_pos[0] = 50.0
    player_pos[1] = 50.0
    while check_collision(player_pos[0], player_pos[1], player_radius) and player_pos[0] < WORLD_WIDTH - 100:
        player_pos[0] += 50
        player_pos[1] += 50

generate_goals(WORLD_WIDTH, WORLD_HEIGHT, FORBIDDEN_Y_MAX, NUM_GOALS, check_collision, goal_radius=GOAL_RADIUS, sprite_scale=1.8)
update_camera()

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

# Movement & physics variables
velocity = [0.0, 0.0]  # not used for player here except simple
mushroom_ball_stopped_prev = True

# Player animation state flags
is_moving = False
is_jumping = False
is_dashing = False
dash_timer = 0.0
DASH_DURATION = 0.25
can_dash = True
dash_cooldown_timer = 0.0

# Helper to draw player sprite centered with feet aligned to player collision center:
def draw_player_sprite(screen, cam_x, cam_y, frame_surf):
    """
    Draw the sprite at screen center so that the bottom center of the sprite
    aligns with the player's collision center (where we previously drew the circle).
    """
    if not frame_surf:
        return
    screen_center_x = SCREEN_WIDTH // 2
    screen_center_y = SCREEN_HEIGHT // 2
    # Player collision "center" was at screen center; we want sprite bottom to be player_center + player_radius
    sprite_bottom_y = screen_center_y + player_radius
    sprite_top_y = sprite_bottom_y - frame_surf.get_height()
    sprite_left_x = screen_center_x - frame_surf.get_width() // 2
    screen.blit(frame_surf, (sprite_left_x, int(sprite_top_y)))

# Main loop
running = True
mouse_world_pos = [0, 0]
level_complete = False
font = pygame.font.SysFont(None, 24)
big_font = pygame.font.SysFont(None, 48)

# Animation helper
def advance_anim(dt, fps=ANIM_FPS, frames=walk_frames, loop=True):
    global anim_index, anim_timer
    anim_timer += dt
    frame_time = 1.0 / fps if fps > 0 else 0.1
    if anim_timer >= frame_time:
        steps = int(anim_timer / frame_time)
        anim_timer -= steps * frame_time
        anim_index += steps
        if loop:
            anim_index %= len(frames)
        else:
            anim_index = min(anim_index, len(frames)-1)
    return frames[anim_index % len(frames)]

# main
while running:
    powerup_slots = []
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

    dt = clock.get_time() / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for slot in powerup_slots:
                if slot['rect'].collidepoint((mx, my)):
                    k = slot['key']
                    if inventory.get(k, 0) > 0 and powerup_timers.get(k, 0) == 0:
                        inventory[k] = inventory.get(k, 0) - 1
                        save_inventory(inventory)
                        powerup_timers[k] = POWERUP_DURATIONS.get(k, POWERUP_DURATION_FRAMES)
                        if k == 'cluster_cap':
                            spawned = 0
                            if mushroom_ball and getattr(mushroom_ball, 'pos', None) and mushroom_ball.active:
                                center_x, center_y = int(mushroom_ball.pos[0]), int(mushroom_ball.pos[1])
                            else:
                                center_x, center_y = int(player_pos[0]), int(player_pos[1])
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
                                        temp_goal_timers[(int(gx), int(gy))] = POWERUP_DURATION_FRAMES
                                        for _p in range(10):
                                            particles.add(SporeParticle(gx, gy))
                                        spawned += 1
                                        placed = True
                                        break
                                if not placed:
                                    continue
                            globals()['cluster_overlay_timer'] = POWERUP_DURATION_FRAMES
                            if spawned == 0:
                                print("Cluster cap used but no safe spawn locations found near", center_x, center_y)
                            else:
                                print(f"Cluster cap spawned {spawned} temporary goals near ({center_x},{center_y})")
                        print(f"Used {k}; remaining: {inventory.get(k,0)}")
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and mushroom_ball.stopped and not level_complete:
                mouse_screen = pygame.mouse.get_pos()
                mouse_world_pos[0] = mouse_screen[0] + cam_x
                mouse_world_pos[1] = mouse_screen[1] + cam_y
                mushroom_ball.shoot(player_pos, mouse_world_pos)
            if event.key == pygame.K_r:
                if not mushroom_ball.hit_this_shot:
                    streak = 0
                mushroom_ball.reset(player_pos)

    if level_complete:
        pass
    else:
        keys = pygame.key.get_pressed()
        cur_speed = PLAYER_SPEED * (player_speed_multiplier if player_speed_multiplier else 1.0)
        new_x, new_y = player_pos[0], player_pos[1]
        is_moving = False
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            new_x -= cur_speed
            is_moving = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            new_x += cur_speed
            is_moving = True
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            new_y -= cur_speed
            is_moving = True
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            new_y += cur_speed
            is_moving = True

        new_x = max(player_radius, min(new_x, WORLD_WIDTH - player_radius))
        new_y = max(player_radius, min(new_y, WORLD_HEIGHT - player_radius))

        if check_collision(new_x, new_y, player_radius):
            pass
        else:
            player_pos[0] = new_x
            player_pos[1] = new_y

        # Update ball and goals
        mushroom_ball.update()
        hit_during_shot = False
        if mushroom_ball.active and not level_complete:
            if check_goal_hit(mushroom_ball.pos, mushroom_ball.radius):
                hit_during_shot = True
                if len(goals) == 0:
                    level_complete = True
            if mushroom_ball.stopped:
                if not mushroom_ball.hit_this_shot:
                    streak = 0
                mushroom_ball.reset(player_pos)

        particles.update()
        popups = [p for p in popups if p.update()]

        for k in list(powerup_timers.keys()):
            if powerup_timers[k] > 0:
                powerup_timers[k] -= 1

        for key in list(temp_goal_timers.keys()):
            temp_goal_timers[key] -= 1
            if temp_goal_timers[key] <= 0:
                gx, gy = key
                goals[:] = [g for g in goals if not (int(g[0]) == gx and int(g[1]) == gy)]
                gs = goal_sprite_map.pop((gx, gy), None)
                if gs:
                    try:
                        gs.kill()
                    except Exception:
                        pass
                del temp_goal_timers[key]

        if globals().get('cluster_overlay_timer', 0) > 0:
            globals()['cluster_overlay_timer'] -= 1

        if powerup_timers.get('aura_alembic', 0) > 0:
            aura_collect()

        if powerup_timers.get('velocity_vial', 0) > 0:
            shoot_speed_multiplier = 2.0
            player_speed_multiplier = 2.0
        else:
            shoot_speed_multiplier = 1.0
            player_speed_multiplier = 1.0

    # Update camera
    update_camera()

    # Draw background
    src_rect = pygame.Rect(cam_x, cam_y, SCREEN_WIDTH, SCREEN_HEIGHT)
    screen.blit(map_image, (0, 0), src_rect)

    if globals().get('cluster_overlay_timer', 0) > 0:
        rem = globals().get('cluster_overlay_timer', 0)
        frac = rem / float(POWERUP_DURATION_FRAMES)
        alpha = int(120 * frac + 60 * (1 - frac))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((60, 200, 80, max(30, min(180, alpha))))
        screen.blit(overlay, (0, 0))
    if powerup_timers.get('golden_gleam', 0) > 0:
        rem = powerup_timers.get('golden_gleam', 0)
        frac = rem / float(POWERUP_DURATION_FRAMES)
        alpha = int(100 * frac + 40 * (1 - frac))
        y_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        y_overlay.fill((255, 220, 100, max(20, min(180, alpha))))
        screen.blit(y_overlay, (0, 0))
        try:
            lbl = big_font.render("DOUBLE SCORE", True, (255, 240, 180))
            lbl_rect = lbl.get_rect(center=(SCREEN_WIDTH//2, 40))
            outline = pygame.Surface((lbl_rect.width+8, lbl_rect.height+8), pygame.SRCALPHA)
            outline.fill((0,0,0,100))
            screen.blit(outline, (lbl_rect.x-4, lbl_rect.y-4))
            screen.blit(lbl, lbl_rect)
        except Exception:
            pass
    if powerup_timers.get('velocity_vial', 0) > 0:
        rem = powerup_timers.get('velocity_vial', 0)
        vel_dur = POWERUP_DURATIONS.get('velocity_vial', POWERUP_DURATION_FRAMES)
        frac = rem / float(vel_dur)
        alpha = int(140 * frac + 50 * (1 - frac))
        b_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        b_overlay.fill((100, 150, 255, max(20, min(220, alpha))))
        screen.blit(b_overlay, (0, 0))
        try:
            lbl = big_font.render("SPEED", True, (220, 240, 255))
            lbl_rect = lbl.get_rect(center=(SCREEN_WIDTH//2, 40))
            outline = pygame.Surface((lbl_rect.width+8, lbl_rect.height+8), pygame.SRCALPHA)
            outline.fill((0,0,0,80))
            screen.blit(outline, (lbl_rect.x-4, lbl_rect.y-4))
            screen.blit(lbl, lbl_rect)
        except Exception:
            pass
    if powerup_timers.get('aura_alembic', 0) > 0:
        rem = powerup_timers.get('aura_alembic', 0)
        frac = rem / float(POWERUP_DURATION_FRAMES)
        alpha = int(110 * frac + 40 * (1 - frac))
        p_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        p_overlay.fill((160, 120, 200, max(20, min(200, alpha))))
        screen.blit(p_overlay, (0, 0))
        try:
            aura_screen_x = SCREEN_WIDTH // 2
            aura_screen_y = SCREEN_HEIGHT // 2
            base_px = int(AURA_RADIUS * (SCREEN_WIDTH / float(WORLD_WIDTH)) * 1.6)
            t = pygame.time.get_ticks() / 1000.0
            freq = 0.9
            amp = 0.12 * frac
            pulse = math.sin(t * 2.0 * math.pi * freq)
            aura_radius_px = max(6, int(base_px * (1.0 + amp * pulse)))
            fill_base = 90
            outline_base = 220
            fill_alpha = int(max(12, min(230, fill_base * (1.0 + 0.28 * pulse) * frac)))
            outline_alpha = int(max(50, min(255, outline_base * (1.0 + 0.45 * pulse) * frac)))
            aura_surf = pygame.Surface((aura_radius_px * 2 + 20, aura_radius_px * 2 + 20), pygame.SRCALPHA)
            center = (aura_radius_px + 10, aura_radius_px + 10)
            pygame.draw.circle(aura_surf, (220, 200, 255, fill_alpha), center, aura_radius_px)
            glow_r = int(aura_radius_px * 1.3)
            try:
                glow_alpha = int(max(10, min(200, fill_alpha * 0.6)))
                pygame.draw.circle(aura_surf, (230, 210, 255, glow_alpha), center, glow_r)
            except Exception:
                pass
            pygame.draw.circle(aura_surf, (200, 180, 255, outline_alpha), center, aura_radius_px, 4)
            ring_amp = 0.06 * frac
            ring_r = int(aura_radius_px * (1.0 + ring_amp * math.cos(t * 2.0 * math.pi * (freq * 0.6))))
            ring_alpha = int(max(8, min(120, 80 * frac * (1.0 + 0.8 * pulse))))
            try:
                pygame.draw.circle(aura_surf, (210, 190, 255, ring_alpha), center, ring_r, 2)
            except Exception:
                pass
            screen.blit(aura_surf, (aura_screen_x - aura_radius_px - 10, aura_screen_y - aura_radius_px - 10))
        except Exception:
            pass

    # Draw particles
    for p in list(particles):
        try:
            screen_x = int(p.rect.x - cam_x)
            screen_y = int(p.rect.y - cam_y)
            screen.blit(p.image, (screen_x, screen_y))
        except Exception:
            try:
                particles.draw(screen)
            except Exception:
                pass

    # Goals
    goal_timer += 1
    for gs in list(goal_sprites):
        gs.step()
        gs.sync_to_camera(cam_x, cam_y)
        if -100 <= gs.rect.right and gs.rect.left <= SCREEN_WIDTH + 100 and -100 <= gs.rect.bottom and gs.rect.top <= SCREEN_HEIGHT + 100:
            try:
                if getattr(gs, 'glow_image', None) is not None:
                    t = pygame.time.get_ticks() / 1000.0
                    pulse = 0.75 + 0.25 * math.sin(t * 2 * math.pi * 0.5 + (gs.index * 0.5))
                    glow_copy = gs.glow_image.copy()
                    glow_copy.set_alpha(int(200 * max(0.0, min(1.0, pulse))))
                    glow_rect = glow_copy.get_rect(center=gs.rect.center)
                    screen.blit(glow_copy, glow_rect)
            except Exception:
                pass
            screen.blit(gs.image, gs.rect)
            try:
                label = font.render(str(gs.index + 1), True, (255, 0, 0))
                screen.blit(label, (gs.rect.centerx - 5, gs.rect.top - 15))
            except Exception:
                pass

    # ------------------ DRAW PLAYER SPRITE (centered with feet aligned) ------------------
    # choose animation frame based on state:
    cur_frame = None
    # prefer dash pose
    if is_dashing:
        if dash_timer < DASH_DURATION:
            cur_frame = kirby_frames[dash_frame_index] if kirby_frames else None
        else:
            is_dashing = False
    elif not mushroom_ball.stopped:
        # if ball shot we still show idle/walk depending on movement? show idle
        cur_frame = kirby_frames[idle_frame_index] if kirby_frames else None
    else:
        # On ground / moving -> walk; if moving animate walking frames
        # Simple jumping detection: if player's y changed quickly or there is no ground under (not using physics here),
        # But we don't have vertical velocity for player: use movement-only: if moving -> walk, else idle.
        if is_moving:
            # advance walk animation
            anim_timer += dt
            frame_time = 1.0 / ANIM_FPS
            if anim_timer >= frame_time:
                steps = int(anim_timer / frame_time)
                anim_timer -= steps * frame_time
                anim_index = (anim_index + steps) % len(walk_frames) if walk_frames else 0
            cur_frame = kirby_frames[walk_frames[anim_index]] if kirby_frames else None
        else:
            cur_frame = kirby_frames[idle_frame_index] if kirby_frames else None

    # If player's 'in air' (ball reset earlier code ensures auto reset), we can attempt a fall test:
    # We'll detect "in air" by testing collision slightly below the player's world pos:
    in_air = False
    below_y = player_pos[1] + player_radius + 2
    if not check_collision(player_pos[0], below_y, player_radius):
        in_air = True
    if in_air:
        # prefer jump frame
        if kirby_frames:
            cur_frame = kirby_frames[jump_frame_index]

    # Draw sprite aligned to feet
    draw_player_sprite(screen, cam_x, cam_y, cur_frame)
    # --------------------------------------------------------------------------------------

    # Draw ball
    mushroom_ball.draw(screen, cam_x, cam_y)

    # Draw popups
    for popup in popups:
        popup.draw(screen, cam_x, cam_y, font)

    # Aim line
    if mushroom_ball.stopped and not level_complete:
        mouse_screen = pygame.mouse.get_pos()
        mouse_world_pos[0] = mouse_screen[0] + cam_x
        mouse_world_pos[1] = mouse_screen[1] + cam_y
        start_screen = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        end_screen = (mouse_screen[0], mouse_screen[1])
        pygame.draw.line(screen, (255, 255, 0), start_screen, end_screen, 2)

    # Minimap
    draw_minimap(screen, player_pos, map_image, mushroom_ball, cam_x, cam_y, WORLD_WIDTH, WORLD_HEIGHT, MINIMAP_SIZE, MINIMAP_ZOOM, goals)

    # UI / Info
    info = font.render(f"Pos: ({int(player_pos[0])}, {int(player_pos[1])}) | Score: {score} | Goals left: {len(goals)} | SPACE to shoot! R to reset", True, (255, 255, 255))
    screen.blit(info, (10, 10))

    # Draw powerup icons
    for slot in powerup_slots:
        r = slot['rect']
        pygame.draw.rect(screen, (40, 40, 40), r)
        pygame.draw.rect(screen, (120, 120, 120), r, 2)
        key = slot['key']
        img = powerup_images.get(key)
        if img:
            img_r = img.get_rect(center=(r.x + 28, r.y + 28))
            screen.blit(img, img_r)
        cnt = slot['count']
        badge_pos = (r.right - 10, r.y + 10)
        pygame.draw.circle(screen, (0, 200, 0), badge_pos, 10)
        ct = font.render(str(cnt), True, (0, 0, 0))
        ct_r = ct.get_rect(center=badge_pos)
        screen.blit(ct, ct_r)
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

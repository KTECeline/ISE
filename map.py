import pygame
import sys
import random
import math
import json
from level2.goal import walking_frames_right, hit_frames_right

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
# shoot speed multiplier used when velocity active
shoot_speed_multiplier = 1.0
# score multiplier when golden is active
score_multiplier_active = 1
# aura active flag handled via timer
# cluster cap spawns extra goals immediately when used; timer kept for visual UI

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

# Camera setup (follows player, keeps player centered)
cam_x = player_pos[0] - SCREEN_WIDTH // 2
cam_y = player_pos[1] - SCREEN_HEIGHT // 2
cam_target_x, cam_target_y = cam_x, cam_y  # For lerping to ball

# Scoring
score = 0
streak = 0  # For combo (one strike = double next score)

# Score pop-up effect
class ScorePopup:
    def __init__(self, x, y, points):
        self.x = x  # World x
        self.y = y  # World y
        self.points = points
        self.lifetime = POPUP_LIFETIME
        self.start_y = y

    def update(self):
        self.y -= 1  # Float up
        self.lifetime -= 1
        return self.lifetime > 0

    def draw(self, screen, cam_x, cam_y):
        if self.lifetime <= 0:
            return
        screen_x = int(self.x - cam_x)
        screen_y = int(self.y - cam_y)
        alpha = int(255 * (self.lifetime / POPUP_LIFETIME))
        text = font.render(f"+{self.points}", True, (255, 255, 0))
        text.set_alpha(alpha)
        screen.blit(text, (screen_x - 10, screen_y))

popups = []  # List of active pop-ups

# Particle for goal hit burst
class SporeParticle(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((4, 4))
        self.image.fill((0, 255, 100))
        self.rect = self.image.get_rect(center=(x, y))
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(3, 6)
        self.vel = [math.cos(angle) * speed, math.sin(angle) * speed]
        self.lifetime = 30

    def update(self):
        self.rect.x += self.vel[0]
        self.rect.y += self.vel[1]
        self.vel[1] += 0.2  # Gravity
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()


class FireworkParticle(pygame.sprite.Sprite):
    """A bright firework-style spark that fades out."""
    def __init__(self, x, y, color=None):
        super().__init__()
        # Make fireworks larger so they're visible
        self.radius = random.randint(3, 6)
        self.color = color if color is not None else random.choice(FIREWORK_COLORS)
        size = max(8, self.radius * 3)
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        # draw a filled circle plus a faint outer ring for glow
        pygame.draw.circle(self.image, self.color + (255,), (size//2, size//2), self.radius)
        try:
            glow_color = (self.color[0], self.color[1], self.color[2], 80)
            pygame.draw.circle(self.image, glow_color, (size//2, size//2), int(self.radius * 1.8))
        except Exception:
            pass
        self.orig_image = self.image.copy()
        # Rect stored in world coords (we'll offset when drawing)
        self.rect = self.image.get_rect(center=(int(x), int(y)))
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(3.0, 9.0)
        self.vel = [math.cos(angle) * speed, math.sin(angle) * speed]
        # Longer lifetime for visibility
        self.lifetime = random.randint(45, 90)
        self.age = 0

    def update(self):
        self.age += 1
        # Apply velocity and gravity-like pull
        # Move in world coordinates
        self.rect.x += self.vel[0]
        self.rect.y += self.vel[1]
        self.vel[1] += 0.08  # slight downward pull
        # Fade out and shrink
        if self.age >= self.lifetime:
            self.kill()
            return
        alpha = int(255 * (1.0 - (self.age / self.lifetime)))
        if alpha < 0:
            alpha = 0
        # Recreate image with new alpha to ensure blending
        self.image = self.orig_image.copy()
        try:
            self.image.set_alpha(alpha)
        except Exception:
            pass

particles = pygame.sprite.Group()

# Mushroom Ball (sporeball, football-like but mushroom-themed)
class MushroomBall:
    def __init__(self):
        self.pos = [730.0, 8230.0]  # Start at specified position
        self.vel = [0.0, 0.0]  # Velocity
        self.radius = 15
        self.active = False  # Not shot yet
        self.stopped = True  # For reset
        self.hit_this_shot = False  # Track if hit during this shot
        # Animation frames (from level2.hit if available)
        try:
            self.frames = list(ball_frames) if ball_frames else []
        except Exception:
            self.frames = []
        self.frame_index = 0.0
        # Rolling animation frames (use frames if available)
        self.roll_frames = self.frames if self.frames else []
        # Prepare squish/stretch keyframes: a small sequence of surfaces that simulate
        # squash (wider, shorter) and stretch (narrower, taller). We'll generate 4 keyframes.
        self.squish_frames = []
        self.squish_timer = 0
        self.squish_phase = 0
        # If we have a base frame, create squish keyframes by scaling; otherwise leave empty
        if self.frames:
            base = self.frames[0]
            bw, bh = base.get_size()
            # keyframes: [stretch_y>1, normal, squish_y<1, normal] - simple loop
            key_scales = [(0.9, 1.1), (1.0, 1.0), (1.2, 0.8), (1.0, 1.0)]
            for sx, sy in key_scales:
                nw = max(1, int(bw * sx))
                nh = max(1, int(bh * sy))
                try:
                    kf = pygame.transform.smoothscale(base, (nw, nh))
                except Exception:
                    kf = base.copy()
                self.squish_frames.append(kf)
        else:
            self.squish_frames = []
        # Trail list stores (surface, world_x, world_y)
        self.trail = []

    def shoot(self, start_pos, target_pos):
        # Aim from player to mouse (world coords)
        dx = target_pos[0] - start_pos[0]
        dy = target_pos[1] - start_pos[1]
        dist = math.sqrt(dx**2 + dy**2)
        if dist > 0:
            # respect any active velocity multiplier
            global shoot_speed_multiplier
            sp = BALL_SPEED * (shoot_speed_multiplier if shoot_speed_multiplier else 1.0)
            self.vel = [ (dx / dist) * sp, (dy / dist) * sp ]
        self.pos = start_pos[:]
        self.active = True
        self.stopped = False
        self.hit_this_shot = False

    def update(self):
        if not self.active:
            return
        # Move
        self.pos[0] += self.vel[0]
        self.pos[1] += self.vel[1]
        # Friction (top-down slide slow)
        self.vel[0] *= BALL_FRICTION
        self.vel[1] *= BALL_FRICTION
        if abs(self.vel[0]) < 0.1:
            self.vel[0] = 0
        if abs(self.vel[1]) < 0.1:
            self.vel[1] = 0
        if self.vel[0] == 0 and self.vel[1] == 0:
            self.stopped = True
        
        # Bounds clamp
        self.pos[0] = max(self.radius, min(self.pos[0], WORLD_WIDTH - self.radius))
        self.pos[1] = max(self.radius, min(self.pos[1], WORLD_HEIGHT - self.radius))
        
        # Wall collision (simple push back if hit)
        if check_collision(self.pos[0], self.pos[1], self.radius):
            # Basic bounce: reverse vel on hit
            self.vel[0] *= -0.7
            self.vel[1] *= -0.7
            # Nudge out
            self.pos[0] += self.vel[0] * 2
            self.pos[1] += self.vel[1] * 2
            # Trigger a squish/stretch animation on bounce
            if self.squish_frames:
                self.squish_timer = SQUISH_DURATION
                # phase can be used to offset which keyframe to start on; use vel to choose
                if abs(self.vel[1]) > abs(self.vel[0]):
                    # more vertical bounce -> emphasize stretch first
                    self.squish_phase = 0
                else:
                    # more horizontal -> emphasize squish
                    self.squish_phase = 2

    def draw(self, screen, cam_x, cam_y):
        if not self.active:
            return
        screen_x = int(self.pos[0] - cam_x)
        screen_y = int(self.pos[1] - cam_y)
        # Compute the frame surface to draw (frame_s). We'll handle rolling, squish,
        # and fallback drawing consistently so we can add a fading trail below.
        frame_s = None
        try:
            if self.frames:
                speed = math.hypot(self.vel[0], self.vel[1])
                # Squish animation takes precedence
                if self.squish_timer > 0 and self.squish_frames:
                    t = (SQUISH_DURATION - self.squish_timer) / float(max(1, SQUISH_DURATION))
                    idx = int(t * len(self.squish_frames))
                    idx = min(idx, len(self.squish_frames) - 1)
                    frame = self.squish_frames[(self.squish_phase + idx) % len(self.squish_frames)]
                    self.squish_timer -= 1
                    base_size = int(self.radius * 2)
                    fw = max(1, int(base_size * MUSHROOM_ANIM_SCALE))
                    fh = max(1, int(base_size * MUSHROOM_ANIM_SCALE))
                    frame_s = pygame.transform.smoothscale(frame, (fw, fh))
                elif speed > ROLL_VELOCITY_THRESHOLD and self.roll_frames:
                    # Rolling animation with rotation
                    self.frame_index = (self.frame_index + ROLL_FRAME_SPEED * (speed / 5.0)) % len(self.roll_frames)
                    frame = self.roll_frames[int(self.frame_index)]
                    angle = -math.degrees(math.atan2(self.vel[1], self.vel[0])) if speed > 0 else 0
                    base_size = int(self.radius * 2)
                    fw = max(1, int(base_size * MUSHROOM_ANIM_SCALE))
                    fh = max(1, int(base_size * MUSHROOM_ANIM_SCALE))
                    frame_s = pygame.transform.smoothscale(frame, (fw, fh))
                    try:
                        frame_s = pygame.transform.rotate(frame_s, angle)
                    except Exception:
                        pass
                else:
                    # Simple frame-cycle
                    self.frame_index = (self.frame_index + 0.2) % len(self.frames)
                    frame = self.frames[int(self.frame_index)]
                    base_size = int(self.radius * 2)
                    fw = max(1, int(base_size * MUSHROOM_ANIM_SCALE))
                    fh = max(1, int(base_size * MUSHROOM_ANIM_SCALE))
                    frame_s = pygame.transform.smoothscale(frame, (fw, fh))
        except Exception:
            frame_s = None

        # If we couldn't produce a sprite frame, fall back to procedural mushroom surface
        if frame_s is None:
            # Create a small surface representing the mushroom for the trail and main draw
            surf = pygame.Surface((self.radius * 2 + 6, self.radius * 2 + 6), pygame.SRCALPHA)
            # Cap (brown)
            pygame.draw.circle(surf, (139, 69, 19), (surf.get_width()//2, surf.get_height()//2 - 2), self.radius)
            # Stem
            pygame.draw.rect(surf, (255, 255, 255), (surf.get_width()//2 - 5, surf.get_height()//2, 10, 10))
            # small spores
            for i in range(3):
                ox = surf.get_width()//2 + (i-1) * 6
                oy = surf.get_height()//2 + 2
                pygame.draw.circle(surf, (0, 255, 0), (ox + random.randint(-2,2), oy + random.randint(-2,2)), 2)
            frame_s = surf

        # Draw trail (older snapshots) with decreasing alpha and slight size decay
        if self.trail:
            n = len(self.trail)
            for idx, (tsurf, (wx, wy)) in enumerate(self.trail):
                try:
                    # alpha grows with idx (oldest dimmest, newest brightest)
                    alpha = int(BALL_TRAIL_ALPHA * ((idx + 1) / float(n)))
                    draw_surf = tsurf.copy()
                    draw_surf.set_alpha(alpha)
                    screen_x_t = int(wx - cam_x)
                    screen_y_t = int(wy - cam_y)
                    rect = draw_surf.get_rect(center=(screen_x_t, screen_y_t))
                    screen.blit(draw_surf, rect)
                except Exception:
                    pass

        # Draw main ball
        rect = frame_s.get_rect(center=(screen_x, screen_y))
        screen.blit(frame_s, rect)

        # Append current snapshot to trail (keep copies so original frame_s can be rotated elsewhere)
        try:
            snap = frame_s.copy()
            self.trail.append((snap, (self.pos[0], self.pos[1])))
            if len(self.trail) > BALL_TRAIL_MAX:
                # remove oldest
                del self.trail[0]
        except Exception:
            pass

    def reset(self, player_pos):
        self.pos = player_pos[:]
        self.vel = [0.0, 0.0]
        self.active = False
        self.stopped = True
        self.hit_this_shot = False

# Goals (scattered across map, safe from collisions, only y > 4215)
goals = []  # list of [x,y] coordinates (world)
goal_timer = 0  # for any legacy timers
# Sprite-based visual goals
goal_sprites = pygame.sprite.Group()
goal_sprite_map = {}  # (x,y) -> GoalSprite

HIT_DISPLAY_FRAMES = 120  # frames to show hit animation before removing visual (approx 2s at 60fps)
SPRITE_SCALE = 1.8  # scale factor for goal sprites (1.0 = original size)

class GoalSprite(pygame.sprite.Sprite):
    def __init__(self, world_x, world_y, index=0):
        super().__init__()
        self.world_x = int(world_x)
        self.world_y = int(world_y)
        self.index = index
        # Create scaled copies of frames so the sprite can be larger than source
        self.walkingFrames = []
        self.hitFrames = []
        try:
            for f in walking_frames_right:
                nw = max(1, int(f.get_width() * SPRITE_SCALE))
                nh = max(1, int(f.get_height() * SPRITE_SCALE))
                self.walkingFrames.append(pygame.transform.smoothscale(f, (nw, nh)))
            for f in hit_frames_right:
                nw = max(1, int(f.get_width() * SPRITE_SCALE))
                nh = max(1, int(f.get_height() * SPRITE_SCALE))
                self.hitFrames.append(pygame.transform.smoothscale(f, (nw, nh)))
        except Exception:
            # If frames aren't available, leave lists empty and fallback later
            pass
        self.frame_index = 0.0
        self.hit = False
        self.remove_timer = None
        # initial image
        if self.walkingFrames:
            self.image = self.walkingFrames[0]
        else:
            # fallback: simple green circle surface
            s = max(8, int(GOAL_RADIUS * SPRITE_SCALE))
            surf = pygame.Surface((s, s), pygame.SRCALPHA)
            pygame.draw.circle(surf, (0, 255, 0), (s//2, s//2), s//2)
            self.image = surf
        self.rect = self.image.get_rect()

        # Precompute a soft glow surface to draw under the goal sprite.
        # Glow size is based on the image size and GOAL_RADIUS so it scales nicely.
        try:
            img_w, img_h = self.image.get_size()
            glow_w = int(max(img_w, img_h) * 1.6)
            glow_h = int(max(img_w, img_h) * 1.6)
            glow_surf = pygame.Surface((glow_w, glow_h), pygame.SRCALPHA)
            # Draw concentric circles with decreasing alpha to simulate a soft glow
            center = (glow_w // 2, glow_h // 2)
            max_radius = int(min(glow_w, glow_h) // 2)
            steps = 6
            # warm soft white glow
            base_color = (255, 255, 255)
            for i in range(steps, 0, -1):
                frac = i / float(steps)
                radius = int(max_radius * frac)
                alpha = int(80 * (frac ** 1.2))  # softer falloff
                color = (base_color[0], base_color[1], base_color[2], alpha)
                pygame.draw.circle(glow_surf, color, center, radius)
            self.glow_image = glow_surf
        except Exception:
            self.glow_image = None

    def step(self):
        # Advance animation
        if not self.hit:
            if self.walkingFrames:
                self.frame_index = (self.frame_index + 0.2) % len(self.walkingFrames)
                self.image = self.walkingFrames[int(self.frame_index)]
        else:
            if self.hitFrames:
                self.frame_index = (self.frame_index + 0.2) % len(self.hitFrames)
                self.image = self.hitFrames[int(self.frame_index)]
            if self.remove_timer is not None:
                self.remove_timer -= 1
                if self.remove_timer <= 0:
                    self.kill()

    def sync_to_camera(self, cam_x, cam_y):
        # Position sprite on screen based on camera
        screen_x = int(self.world_x - cam_x)
        screen_y = int(self.world_y - cam_y)
        # keep same midbottom alignment as Goal demo
        self.rect = self.image.get_rect(midbottom=(screen_x, screen_y))

    def mark_hit(self):
        self.hit = True
        self.remove_timer = HIT_DISPLAY_FRAMES


def generate_goals():
    global goals, goal_sprites, goal_sprite_map
    goals = []
    goal_sprites.empty()
    goal_sprite_map.clear()
    attempts = 0
    # Scatter across full map, but safe from red AND only below y=4215 (y > FORBIDDEN_Y_MAX, since higher y = above)
    min_y = FORBIDDEN_Y_MAX + 1  # Start just below the line
    index = 0
    while len(goals) < NUM_GOALS and attempts < 500:  # Broad search
        goal_x = random.randint(100, WORLD_WIDTH - 100)
        goal_y = random.randint(min_y, WORLD_HEIGHT - 100)
        if not check_collision(goal_x, goal_y, GOAL_RADIUS):
            goals.append([goal_x, goal_y])
            # create visual sprite
            gs = GoalSprite(goal_x, goal_y, index=index)
            goal_sprites.add(gs)
            goal_sprite_map[(int(goal_x), int(goal_y))] = gs
            index += 1
        attempts += 1

def check_goal_hit(ball_pos, ball_radius):
    global score, streak
    global screen_shake_timer
    hits_this_shot = 0
    hit_goals = []  # Track for multi-hit
    for i in range(len(goals)-1, -1, -1):  # Reverse to avoid index shift
        goal = goals[i]
        dx = ball_pos[0] - goal[0]
        dy = ball_pos[1] - goal[1]
        dist = math.sqrt(dx**2 + dy**2)
        # If aura powerup is active, effectively increase goal radius for auto-hit
        aura_extra = 20 if powerup_timers.get('aura_alembic', 0) > 0 else 0
        effective_goal_radius = GOAL_RADIUS + aura_extra
        if dist < effective_goal_radius + ball_radius:
            gx, gy = goals[i][0], goals[i][1]
            hit_goals.append([gx, gy])
            hits_this_shot += 1
            del goals[i]
            # Particle burst at goal
            for _ in range(PARTICLE_COUNT):
                p = SporeParticle(gx, gy)
                particles.add(p)
            # Mark visual sprite as hit (if present) and schedule its removal
            gs = goal_sprite_map.pop((int(gx), int(gy)), None)
            if gs:
                gs.mark_hit()
    if hits_this_shot > 0:
        # Scoring: give extra reward for multi-goal strikes.
        # Use an exponential combo so multi-hit strikes are worth noticeably more.
        # For n hits: points = BASE_SCORE * n * (COMBO_MULTIPLIER ** (n-1))
        # This makes 1 hit -> BASE_SCORE, 2 hits -> BASE_SCORE*2*COMBO, 3 hits -> BASE_SCORE*3*COMBO^2, etc.
        # Scoring rules:
        # - Single hit: award BASE_SCORE; if there is an active streak, double that single-hit (COMBO_MULTIPLIER).
        # - Multi-hit in a single strike: multiply the total (BASE_SCORE * hits) by COMBO_MULTIPLIER.
        if hits_this_shot == 1:
            if streak > 0:
                points = int(BASE_SCORE * COMBO_MULTIPLIER)
            else:
                points = BASE_SCORE
        else:
            # Two goals in one strike: e.g. BASE_SCORE*2*COMBO -> 10*2*2 = 40
            points = int(BASE_SCORE * hits_this_shot * COMBO_MULTIPLIER)
        # If golden gleam is active, double points while its timer > 0
        if powerup_timers.get('golden_gleam', 0) > 0:
            points = int(points * 2)

        score += points
        streak += hits_this_shot  # Build streak on hit(s)
        mushroom_ball.hit_this_shot = True
        # Spawn firework particles for a more celebratory collision effect
        spawned = 0
        for gx, gy in hit_goals:
            for _ in range(FIREWORK_PARTICLE_COUNT):
                fp = FireworkParticle(gx, gy, color=random.choice(FIREWORK_COLORS))
                particles.add(fp)
                spawned += 1
        # Short camera shake
        screen_shake_timer = SCREEN_SHAKE_FRAMES
        # Play scored sound if available
        try:
            if scored_sound:
                scored_sound.play()
        except Exception:
            pass
        # Pop-up at ball pos (average if multi)
        avg_x = ball_pos[0]
        avg_y = ball_pos[1]
        popups.append(ScorePopup(avg_x, avg_y, points))
        return True
    return False

# Ball instance (starts at (730, 8230))
mushroom_ball = MushroomBall()

def update_camera():
    """Update camera to center on player, but lerp toward ball if active."""
    global cam_x, cam_y, cam_target_x, cam_target_y
    global screen_shake_timer
    # Target: Midpoint between player and ball if active
    if mushroom_ball.active:
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

def draw_minimap(screen):
    """Draw small minimap in top-right showing scaled real map + elements."""
    minimap = pygame.Surface(MINIMAP_SIZE)

    # Choose a cropped region around the player (so the minimap is zoomed-in)
    zoom = max(1.0, MINIMAP_ZOOM)
    crop_w = max(1, int(WORLD_WIDTH / zoom))
    crop_h = max(1, int(WORLD_HEIGHT / zoom))
    # Center crop on player
    center_x = int(player_pos[0])
    center_y = int(player_pos[1])
    crop_x = max(0, min(center_x - crop_w // 2, WORLD_WIDTH - crop_w))
    crop_y = max(0, min(center_y - crop_h // 2, WORLD_HEIGHT - crop_h))
    crop_rect = pygame.Rect(crop_x, crop_y, crop_w, crop_h)
    try:
        cropped = map_image.subsurface(crop_rect).copy()
    except Exception:
        # Fallback: scale the full map if subsurface fails
        cropped = map_image.copy()
    scaled_map = pygame.transform.scale(cropped, MINIMAP_SIZE)
    minimap.blit(scaled_map, (0, 0))
    
    # World border
    pygame.draw.rect(minimap, (255, 255, 255), (0, 0, MINIMAP_SIZE[0], MINIMAP_SIZE[1]), 1)
    
    # Player dot (blue)
    # Scale from the cropped world area to minimap size
    scale_x = MINIMAP_SIZE[0] / crop_w
    scale_y = MINIMAP_SIZE[1] / crop_h
    player_map_x = int((player_pos[0] - crop_x) * scale_x)
    player_map_y = int((player_pos[1] - crop_y) * scale_y)
    pygame.draw.circle(minimap, (0, 0, 255), (player_map_x, player_map_y), 3)
    
    # Goals (green dots, larger if remaining)
    for goal in goals:
        goal_map_x = int((goal[0] - crop_x) * scale_x)
        goal_map_y = int((goal[1] - crop_y) * scale_y)
        pygame.draw.circle(minimap, (0, 255, 0), (goal_map_x, goal_map_y), 3)
    
    # Mushroom ball if active (yellow)
    if mushroom_ball.active:
        ball_map_x = int((mushroom_ball.pos[0] - crop_x) * scale_x)
        ball_map_y = int((mushroom_ball.pos[1] - crop_y) * scale_y)
        pygame.draw.circle(minimap, (255, 255, 0), (ball_map_x, ball_map_y), 2)
    
    # Camera view box (white outline)
    cam_map_x = int((cam_x - crop_x) * scale_x)
    cam_map_y = int((cam_y - crop_y) * scale_y)
    cam_map_w = int(SCREEN_WIDTH * scale_x)
    cam_map_h = int(SCREEN_HEIGHT * scale_y)
    pygame.draw.rect(minimap, (255, 255, 255), (cam_map_x, cam_map_y, cam_map_w, cam_map_h), 1)
    
    # Blit to screen top-right
    screen.blit(minimap, (SCREEN_WIDTH - MINIMAP_SIZE[0] - 10, 10))
    
    # Label
    label_font = pygame.font.SysFont(None, 18)
    label = label_font.render("Minimap: Blue=You, Green=Goals, Yellow=Ball", True, (255, 255, 255))
    screen.blit(label, (SCREEN_WIDTH - MINIMAP_SIZE[0] - 10, 10 + MINIMAP_SIZE[1] + 5))

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
generate_goals()

update_camera()  # Initial cam

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
                        # activate effect for POWERUP_DURATION_FRAMES
                        powerup_timers[k] = POWERUP_DURATION_FRAMES
                        # apply immediate behaviors if needed
                        if k == 'cluster_cap':
                            # spawn 3 extra goals around ball position if safe
                            spawned = 0
                            for _ in range(3):
                                gx = int(mushroom_ball.pos[0] + random.randint(-120, 120))
                                gy = int(mushroom_ball.pos[1] + random.randint(-120, 120))
                                if gy > FORBIDDEN_Y_MAX and not check_collision(gx, gy, GOAL_RADIUS):
                                    goals.append([gx, gy])
                                    gs = GoalSprite(gx, gy, index=len(goals))
                                    goal_sprites.add(gs)
                                    goal_sprite_map[(int(gx), int(gy))] = gs
                                    spawned += 1
                        # immediate feedback print
                        print(f"Used {k}; remaining: {inventory.get(k,0)}")
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and mushroom_ball.stopped and not level_complete:  # Shoot if stopped
                # Get mouse world pos
                mouse_screen = pygame.mouse.get_pos()
                mouse_world_pos[0] = mouse_screen[0] + cam_x
                mouse_world_pos[1] = mouse_screen[1] + cam_y
                mushroom_ball.shoot(player_pos, mouse_world_pos)
            if event.key == pygame.K_r:  # Reset ball manually
                if not mushroom_ball.hit_this_shot:
                    streak = 0
                mushroom_ball.reset(player_pos)
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
        # Handle input (arrow keys or WASD for player)
        keys = pygame.key.get_pressed()
        new_x, new_y = player_pos[0], player_pos[1]
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            new_x -= PLAYER_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            new_x += PLAYER_SPEED
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            new_y -= PLAYER_SPEED
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            new_y += PLAYER_SPEED

        # Clamp proposed move to world bounds
        new_x = max(player_radius, min(new_x, WORLD_WIDTH - player_radius))
        new_y = max(player_radius, min(new_y, WORLD_HEIGHT - player_radius))

        # Test collision at new world position (silent)
        if check_collision(new_x, new_y, player_radius):
            pass  # Silent wall hit
        else:
            player_pos[0] = new_x
            player_pos[1] = new_y

        # Update ball
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
                mushroom_ball.reset(player_pos)  # Auto-reset after stop

        # Update particles
        particles.update()

        # Update pop-ups
        popups = [p for p in popups if p.update()]

        # Update powerup timers and apply runtime flags
        # Decrement timers
        for k in list(powerup_timers.keys()):
            if powerup_timers[k] > 0:
                powerup_timers[k] -= 1

        # Apply shoot speed multiplier if velocity_vial active
        if powerup_timers.get('velocity_vial', 0) > 0:
            shoot_speed_multiplier = 1.5
        else:
            shoot_speed_multiplier = 1.0

        # golden_gleam is handled inside check_goal_hit via powerup_timers

    # Update camera to follow player/ball
    update_camera()

    # Draw: Viewport from world
    src_rect = pygame.Rect(cam_x, cam_y, SCREEN_WIDTH, SCREEN_HEIGHT)
    screen.blit(map_image, (0, 0), src_rect)  # Background map viewport ONLY

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

    # Draw mushroom ball
    mushroom_ball.draw(screen, cam_x, cam_y)

    # Draw score pop-ups
    for popup in popups:
        popup.draw(screen, cam_x, cam_y)

    # Aim line (from player to mouse, if not shooting)
    if mushroom_ball.stopped and not level_complete:
        mouse_screen = pygame.mouse.get_pos()
        mouse_world_pos[0] = mouse_screen[0] + cam_x
        mouse_world_pos[1] = mouse_screen[1] + cam_y
        # Line in screen coords
        start_screen = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        end_screen = (mouse_screen[0], mouse_screen[1])
        pygame.draw.line(screen, (255, 255, 0), start_screen, end_screen, 2)

    # Draw minimap with real map texture
    draw_minimap(screen)

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
import pygame
import sys
import random
import math

# Initialize Pygame
pygame.init()

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
BASE_SCORE = 10  # Points per hit
COMBO_MULTIPLIER = 2  # Double score on streak/multi-hit (one strike gets two = x2 more marks)
POPUP_LIFETIME = 60  # Frames for score pop-up fade
FORBIDDEN_Y_MAX = 4215  # No goals above this y-line (higher y = above, so spawn y > 4215)

# Paths to your files (update if needed)
MAP_PATH = 'assets/textures/map/Level_2_map.png'
COLLISION_PATH = 'assets/textures/map/Level_2_collision.png'

# Load images (now safe after dummy display)
try:
    map_image = pygame.image.load(MAP_PATH)
    collision_surface = pygame.image.load(COLLISION_PATH)
    # Convert after loading to optimize
    map_image = map_image.convert()
    collision_surface = collision_surface.convert_alpha()
except pygame.error as e:
    sys.exit(1)

# World dimensions from map
WORLD_WIDTH = map_image.get_width()
WORLD_HEIGHT = map_image.get_height()

# Now set real screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Level 2: Sporeball Gauntlet - Goals Only Below y=4215!")
clock = pygame.time.Clock()

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

    def shoot(self, start_pos, target_pos):
        # Aim from player to mouse (world coords)
        dx = target_pos[0] - start_pos[0]
        dy = target_pos[1] - start_pos[1]
        dist = math.sqrt(dx**2 + dy**2)
        if dist > 0:
            self.vel = [ (dx / dist) * BALL_SPEED, (dy / dist) * BALL_SPEED ]
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

    def draw(self, screen, cam_x, cam_y):
        if not self.active:
            return
        # Mushroom look: Brown cap circle + white stem + random spores
        screen_x = int(self.pos[0] - cam_x)
        screen_y = int(self.pos[1] - cam_y)
        # Cap
        pygame.draw.circle(screen, (139, 69, 19), (screen_x, screen_y - 5), self.radius)  # Brown cap
        # Stem
        pygame.draw.rect(screen, (255, 255, 255), (screen_x - 5, screen_y, 10, 10))  # White stem
        # Glowing spores (simple dots)
        for _ in range(3):
            offset_x = random.randint(-5, 5)
            offset_y = random.randint(-5, 5)
            pygame.draw.circle(screen, (0, 255, 0), (screen_x + offset_x, screen_y + offset_y), 2)

    def reset(self, player_pos):
        self.pos = player_pos[:]
        self.vel = [0.0, 0.0]
        self.active = False
        self.stopped = True
        self.hit_this_shot = False

# Goals (scattered across map, safe from collisions, only y > 4215)
goals = []
goal_timer = 0  # For pulsing
def generate_goals():
    global goals
    goals = []
    attempts = 0
    # Scatter across full map, but safe from red AND only below y=4215 (y > FORBIDDEN_Y_MAX, since higher y = above)
    min_y = FORBIDDEN_Y_MAX + 1  # Start just below the line
    while len(goals) < NUM_GOALS and attempts < 500:  # Broad search
        goal_x = random.randint(100, WORLD_WIDTH - 100)
        goal_y = random.randint(min_y, WORLD_HEIGHT - 100)
        if not check_collision(goal_x, goal_y, GOAL_RADIUS):
            goals.append([goal_x, goal_y])
        attempts += 1

def check_goal_hit(ball_pos, ball_radius):
    global score, streak
    hits_this_shot = 0
    hit_goals = []  # Track for multi-hit
    for i in range(len(goals)-1, -1, -1):  # Reverse to avoid index shift
        goal = goals[i]
        dx = ball_pos[0] - goal[0]
        dy = ball_pos[1] - goal[1]
        dist = math.sqrt(dx**2 + dy**2)
        if dist < GOAL_RADIUS + ball_radius:
            hit_goals.append(goals[i])
            hits_this_shot += 1
            del goals[i]
            # Particle burst at goal
            for _ in range(PARTICLE_COUNT):
                p = SporeParticle(goal[0], goal[1])
                particles.add(p)
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
        score += points
        streak += hits_this_shot  # Build streak on hit(s)
        mushroom_ball.hit_this_shot = True
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

def draw_minimap(screen):
    """Draw small minimap in top-right showing scaled real map + elements."""
    minimap = pygame.Surface(MINIMAP_SIZE)
    
    # Mini size real map: Scale full map to minimap size
    scaled_map = pygame.transform.scale(map_image, MINIMAP_SIZE)
    minimap.blit(scaled_map, (0, 0))
    
    # World border
    pygame.draw.rect(minimap, (255, 255, 255), (0, 0, MINIMAP_SIZE[0], MINIMAP_SIZE[1]), 1)
    
    # Player dot (blue)
    scale_x = MINIMAP_SIZE[0] / WORLD_WIDTH
    scale_y = MINIMAP_SIZE[1] / WORLD_HEIGHT
    player_map_x = int(player_pos[0] * scale_x)
    player_map_y = int(player_pos[1] * scale_y)
    pygame.draw.circle(minimap, (0, 0, 255), (player_map_x, player_map_y), 3)
    
    # Goals (green dots, larger if remaining)
    for goal in goals:
        goal_map_x = int(goal[0] * scale_x)
        goal_map_y = int(goal[1] * scale_y)
        pygame.draw.circle(minimap, (0, 255, 0), (goal_map_x, goal_map_y), 3)
    
    # Mushroom ball if active (yellow)
    if mushroom_ball.active:
        ball_map_x = int(mushroom_ball.pos[0] * scale_x)
        ball_map_y = int(mushroom_ball.pos[1] * scale_y)
        pygame.draw.circle(minimap, (255, 255, 0), (ball_map_x, ball_map_y), 2)
    
    # Camera view box (white outline)
    cam_map_x = int(cam_x * scale_x)
    cam_map_y = int(cam_y * scale_y)
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
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
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

    # Update camera to follow player/ball
    update_camera()

    # Draw: Viewport from world
    src_rect = pygame.Rect(cam_x, cam_y, SCREEN_WIDTH, SCREEN_HEIGHT)
    screen.blit(map_image, (0, 0), src_rect)  # Background map viewport ONLY

    # Draw particles
    particles.draw(screen)

    # Draw goals (pulsing with numbers)
    goal_timer += 1
    pulse = 1 + 0.2 * math.sin(goal_timer * 0.1)  # Gentle pulse
    for i, goal in enumerate(goals):
        screen_x = int(goal[0] - cam_x)
        screen_y = int(goal[1] - cam_y)
        if -GOAL_RADIUS <= screen_x <= SCREEN_WIDTH + GOAL_RADIUS and -GOAL_RADIUS <= screen_y <= SCREEN_HEIGHT + GOAL_RADIUS:  # Draw if near screen
            pulse_radius = int(GOAL_RADIUS * pulse)
            pygame.draw.circle(screen, (0, 255, 0), (screen_x, screen_y), pulse_radius)  # Green glow
            # Inner white core
            pygame.draw.circle(screen, (255, 255, 255), (screen_x, screen_y), GOAL_RADIUS // 2)
            # Number label
            label = font.render(str(i+1), True, (255, 0, 0))
            screen.blit(label, (screen_x - 5, screen_y - 5))

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
    if level_complete:
        win_text = big_font.render("LEVEL COMPLETE! Final Score: " + str(score), True, (255, 255, 0))
        screen.blit(win_text, (SCREEN_WIDTH//2 - win_text.get_width()//2, SCREEN_HEIGHT//2))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()
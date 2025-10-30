import pygame
import sys

# Initialize Pygame
pygame.init()

# Create a dummy display mode first to allow image loading (fixes "No video mode" error)
dummy_screen = pygame.display.set_mode((1, 1), pygame.NOFRAME)

# Constants
SCREEN_WIDTH = 1024  # Fixed screen size for viewing
SCREEN_HEIGHT = 768
FPS = 60
PLAYER_SPEED = 5
COLLISION_COLOR = (255, 0, 0)  # Red for walls; tolerance for slight variations
TOLERANCE = 50  # Allow minor RGB variations in red detection

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
    print(f"Loaded map size: {map_image.get_size()}")
    print(f"Loaded collision size: {collision_surface.get_size()}")
except pygame.error as e:
    print(f"Error loading images: {e}")
    print("Check file paths and ensure images exist.")
    sys.exit(1)

# World dimensions from map
WORLD_WIDTH = map_image.get_width()
WORLD_HEIGHT = map_image.get_height()

# Now set real screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Level 2 Collision Test - Clean View (No Red Overlay)")
clock = pygame.time.Clock()

# Player setup in WORLD coordinates (start near top-left, adjust if needed)
player_pos = [200.0, 200.0]  # Float for smooth movement; tweak if starting on wall
player_radius = 20  # Simple circle for testing

# Camera setup (follows player, keeps player centered)
cam_x = player_pos[0] - SCREEN_WIDTH // 2
cam_y = player_pos[1] - SCREEN_HEIGHT // 2

def update_camera():
    """Update camera to center on player, clamped to world bounds."""
    global cam_x, cam_y
    cam_x = player_pos[0] - SCREEN_WIDTH // 2
    cam_y = player_pos[1] - SCREEN_HEIGHT // 2
    # Clamp camera so edges don't show outside world
    cam_x = max(0, min(cam_x, WORLD_WIDTH - SCREEN_WIDTH))
    cam_y = max(0, min(cam_y, WORLD_HEIGHT - SCREEN_HEIGHT))

def check_collision(world_x, world_y, radius):
    """
    Check if player world position overlaps red pixels in collision map.
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
    print("Starting pos on wall! Moving to safe spot...")
    player_pos[0] = 50.0
    player_pos[1] = 50.0
    while check_collision(player_pos[0], player_pos[1], player_radius) and player_pos[0] < WORLD_WIDTH - 100:
        player_pos[0] += 50
        player_pos[1] += 50
    print(f"New start: {player_pos}")

update_camera()  # Initial cam

# Main loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        # Optional: Zoom with mouse wheel (basic, scales view but keeps collision pixel-perfect)
        if event.type == pygame.MOUSEWHEEL:
            # For now, just print; implement zoom below if wanted
            pass

    # Handle input (arrow keys or WASD)
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

    # Test collision at new world position
    if check_collision(new_x, new_y, player_radius):
        print("Hit wall! Cannot move there.")   
    else:
        player_pos[0] = new_x
        player_pos[1] = new_y

    # Update camera to follow player
    update_camera()

    # Draw: Viewport from world (efficient for large maps)
    src_rect = pygame.Rect(cam_x, cam_y, SCREEN_WIDTH, SCREEN_HEIGHT)
    screen.blit(map_image, (0, 0), src_rect)  # Background map viewport ONLY

    # Draw player (always centered since cam follows)
    pygame.draw.circle(screen, (0, 0, 255), (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), player_radius)

    # Optional: Draw world bounds info
    font = pygame.font.SysFont(None, 24)
    info = font.render(f"World: {WORLD_WIDTH}x{WORLD_HEIGHT} | Pos: ({int(player_pos[0])}, {int(player_pos[1])})", True, (255, 255, 255))
    screen.blit(info, (10, 10))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()
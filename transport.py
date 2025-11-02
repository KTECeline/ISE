import pygame
import sys
import math
import os

# Initialize Pygame
pygame.init()

# Screen setup
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Quick Transport Test")
clock = pygame.time.Clock()

# Colors
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)

# Try to load your original map
try:
    MAP_PATH = 'assets/textures/map/Level_2_map.png'
    map_image = pygame.image.load(MAP_PATH).convert()
    WORLD_WIDTH = map_image.get_width()
    WORLD_HEIGHT = map_image.get_height()
    print(f"Map loaded: {WORLD_WIDTH}x{WORLD_HEIGHT}")
except:
    print("Map not found, using placeholder")
    WORLD_WIDTH = 10000
    WORLD_HEIGHT = 10000
    map_image = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT))
    map_image.fill((50, 50, 50))
    # Draw some simple terrain
    for i in range(0, WORLD_WIDTH, 200):
        for j in range(0, WORLD_HEIGHT, 200):
            color = (70, 70, 70) if (i//200 + j//200) % 2 == 0 else (90, 90, 90)
            pygame.draw.rect(map_image, color, (i, j, 200, 200))

# Try to load character
try:
    import charactermove as char_move
    char_move.load_assets()
    character_sprite = char_move.Player(pos=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
    character_group = pygame.sprite.Group(character_sprite)
    print("Character loaded successfully")
except:
    print("Character not found, using placeholder")
    character_sprite = None
    character_group = pygame.sprite.Group()

# Transport positions (two-step movement)
START_POS = [5193.0, 4434.0]    # Starting position
MIDDLE_POS = [5193.0, 895.0]    # First target (vertical movement)
CHEST_POS = [5800.0, 895.0]     # Final target (horizontal movement)
transport_speed = 15.0  # Slower movement speed

# Transport state
TRANSPORT_STATES = {
    'IDLE': 0,
    'MOVING_TO_MIDDLE': 1,
    'MOVING_TO_CHEST': 2,
    'COMPLETE': 3
}
current_transport_state = TRANSPORT_STATES['IDLE']

# Smooth movement variables
smooth_path = []
path_index = 0

# Game state
player_pos = START_POS.copy()
player_radius = 20
end_scene_started = False

# Camera (follows player)
cam_x = player_pos[0] - SCREEN_WIDTH // 2
cam_y = player_pos[1] - SCREEN_HEIGHT // 2

# Create a semi-transparent overlay for dimming effect
overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
overlay.fill((0, 0, 0, 150))  # Black with 150 alpha (medium darkness)

def create_smooth_path(start, middle, end, num_points=10):
    """Create a smooth curved path through the points"""
    path = []
    
    # First segment: start to middle with slight curve
    for i in range(num_points):
        t = i / num_points
        # Add a slight curve to the first segment
        control_x = start[0] + (middle[0] - start[0]) * 0.5
        control_y = start[1] + (middle[1] - start[1]) * 0.8
        
        # Quadratic bezier curve
        x = (1-t)**2 * start[0] + 2*(1-t)*t * control_x + t**2 * middle[0]
        y = (1-t)**2 * start[1] + 2*(1-t)*t * control_y + t**2 * middle[1]
        path.append([x, y])
    
    # Second segment: middle to end with slight curve
    for i in range(num_points):
        t = i / num_points
        # Add a slight curve to the second segment
        control_x = middle[0] + (end[0] - middle[0]) * 0.3
        control_y = middle[1] + (end[1] - middle[1]) * 0.2
        
        # Quadratic bezier curve
        x = (1-t)**2 * middle[0] + 2*(1-t)*t * control_x + t**2 * end[0]
        y = (1-t)**2 * middle[1] + 2*(1-t)*t * control_y + t**2 * end[1]
        path.append([x, y])
    
    return path

def start_transport():
    global current_transport_state, smooth_path, path_index
    current_transport_state = TRANSPORT_STATES['MOVING_TO_MIDDLE']
    
    # Create smooth path
    smooth_path = create_smooth_path(START_POS, MIDDLE_POS, CHEST_POS)
    path_index = 0
    print("Transport started with smooth path!")

def update_transport():
    global player_pos, current_transport_state, end_scene_started, path_index
    
    if current_transport_state == TRANSPORT_STATES['IDLE']:
        return
    
    if path_index < len(smooth_path):
        # Move to next point in smooth path
        target_pos = smooth_path[path_index]
        dx = target_pos[0] - player_pos[0]
        dy = target_pos[1] - player_pos[1]
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance < transport_speed:
            # Reached this path point
            player_pos = target_pos.copy()
            path_index += 1
            
            # Check if we've reached the final destination
            if path_index >= len(smooth_path):
                current_transport_state = TRANSPORT_STATES['COMPLETE']
                end_scene_started = True
                print("Transport completed with smooth path!")
                print(f"Final position: {player_pos}")
        else:
            # Move toward next path point
            direction_x = dx / distance
            direction_y = dy / distance
            player_pos[0] += direction_x * transport_speed
            player_pos[1] += direction_y * transport_speed

def start_end_scene():
    print("=" * 50)
    print("END SCENE STARTED!")
    print("This is where your end scene communication would begin.")
    print("You can add dialogue, cutscenes, or whatever you need here.")
    print("=" * 50)

# Main game loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r and current_transport_state == TRANSPORT_STATES['IDLE']:
                start_transport()
            elif event.key == pygame.K_e and end_scene_started:
                # Start the actual end scene communication
                start_end_scene()
            elif event.key == pygame.K_ESCAPE:
                running = False
    
    # Update transport if active
    if current_transport_state != TRANSPORT_STATES['IDLE'] and current_transport_state != TRANSPORT_STATES['COMPLETE']:
        update_transport()
    
    # Start end scene immediately when transport finishes
    if end_scene_started:
        start_end_scene()
        end_scene_started = False  # Prevent repeating
    
    # Update camera to follow player
    cam_x = player_pos[0] - SCREEN_WIDTH // 2
    cam_y = player_pos[1] - SCREEN_HEIGHT // 2
    
    # Update character sprite if it exists
    if character_sprite:
        character_sprite.update()
        character_sprite.rect.midbottom = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + player_radius)
    
    # Clear screen and draw map
    screen.fill((0, 0, 0))
    
    # Draw map viewport
    src_rect = pygame.Rect(cam_x, cam_y, SCREEN_WIDTH, SCREEN_HEIGHT)
    screen.blit(map_image, (0, 0), src_rect)
    
    # NO position markers - completely removed
    
    # Draw player character
    if character_sprite:
        screen.blit(character_sprite.image, character_sprite.rect)
    else:
        # Fallback: simple player circle
        player_screen_x = int(player_pos[0] - cam_x)
        player_screen_y = int(player_pos[1] - cam_y)
        pygame.draw.circle(screen, BLUE, (player_screen_x, player_screen_y), player_radius)
    
    # Apply dim overlay and show "Transporting..." text during transport
    is_transporting = current_transport_state in [TRANSPORT_STATES['MOVING_TO_MIDDLE'], TRANSPORT_STATES['MOVING_TO_CHEST']]
    
    if is_transporting:
        # Dim the screen (like loading screen)
        screen.blit(overlay, (0, 0))
        
        # Draw "Transporting..." text in the center with pulsing effect
        big_font = pygame.font.Font(None, 72)
        
        # Create pulsing alpha effect
        pulse = (math.sin(pygame.time.get_ticks() * 0.01) + 1) * 0.5  # 0 to 1
        alpha = int(150 + 105 * pulse)  # 150 to 255 alpha
        
        # Main transporting text
        transport_text = big_font.render("TRANSPORTING...", True, (255, 255, 255))
        text_rect = transport_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        
        # Create text surface with alpha
        text_surface = pygame.Surface((text_rect.width + 20, text_rect.height + 20), pygame.SRCALPHA)
        text_surface.fill((0, 0, 0, alpha // 2))  # Semi-transparent background
        text_surface.blit(transport_text, (10, 10))
        
        screen.blit(text_surface, (text_rect.x - 10, text_rect.y - 10))
    
    # Draw UI text (always on top)
    font = pygame.font.Font(None, 36)
    
    pos_text = font.render(f"Position: ({int(player_pos[0])}, {int(player_pos[1])})", True, WHITE)
    screen.blit(pos_text, (10, 10))
    
    # Simple transport status
    if current_transport_state == TRANSPORT_STATES['IDLE']:
        help_text = font.render("Press R to start transport to chest", True, WHITE)
        screen.blit(help_text, (10, 50))
    elif current_transport_state == TRANSPORT_STATES['COMPLETE']:
        end_text = font.render("Transport complete! Press E for end scene", True, (0, 255, 0))
        screen.blit(end_text, (10, 50))
    
    # Draw minimap in corner (optional - remove if you don't want it either)
    minimap_size = 200
    minimap_surface = pygame.Surface((minimap_size, minimap_size))
    minimap_surface.fill((0, 0, 0))
    
    # Draw minimap representation of world
    scale_x = minimap_size / WORLD_WIDTH
    scale_y = minimap_size / WORLD_HEIGHT
    
    # Draw positions on minimap (optional - remove these lines if you don't want minimap markers)
    # pygame.draw.circle(minimap_surface, GREEN, (int(START_POS[0] * scale_x), int(START_POS[1] * scale_y)), 3)
    # pygame.draw.circle(minimap_surface, YELLOW, (int(MIDDLE_POS[0] * scale_x), int(MIDDLE_POS[1] * scale_y)), 3)
    # pygame.draw.circle(minimap_surface, RED, (int(CHEST_POS[0] * scale_x), int(CHEST_POS[1] * scale_y)), 3)
    
    # Draw player on minimap
    player_minimap_x = int(player_pos[0] * scale_x)
    player_minimap_y = int(player_pos[1] * scale_y)
    pygame.draw.circle(minimap_surface, BLUE, (player_minimap_x, player_minimap_y), 4)
    
    screen.blit(minimap_surface, (SCREEN_WIDTH - minimap_size - 10, 10))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
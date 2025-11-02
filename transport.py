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
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

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
transport_speed = 50.0  # Fast movement speed

# Transport state
TRANSPORT_STATES = {
    'IDLE': 0,
    'MOVING_TO_MIDDLE': 1,
    'MOVING_TO_CHEST': 2,
    'COMPLETE': 3
}
current_transport_state = TRANSPORT_STATES['IDLE']

# Try to load chest image
try:
    chest_img = pygame.image.load('assets/images/chest_closed.png').convert_alpha()
    print("Chest image loaded")
except:
    print("Chest image not found, using placeholder")
    chest_img = pygame.Surface((64, 48), pygame.SRCALPHA)
    pygame.draw.rect(chest_img, (100, 60, 20), chest_img.get_rect())

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

def start_transport():
    global current_transport_state
    current_transport_state = TRANSPORT_STATES['MOVING_TO_MIDDLE']
    print("Transport started!")

def update_transport():
    global player_pos, current_transport_state, end_scene_started
    
    if current_transport_state == TRANSPORT_STATES['IDLE']:
        return
    
    if current_transport_state == TRANSPORT_STATES['MOVING_TO_MIDDLE']:
        # Move vertically to middle position
        dx = MIDDLE_POS[0] - player_pos[0]
        dy = MIDDLE_POS[1] - player_pos[1]
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance < transport_speed:
            # Reached middle position
            player_pos = MIDDLE_POS.copy()
            current_transport_state = TRANSPORT_STATES['MOVING_TO_CHEST']
            print("Reached middle position! Moving to chest...")
        else:
            # Move toward middle position
            direction_x = dx / distance
            direction_y = dy / distance
            player_pos[0] += direction_x * transport_speed
            player_pos[1] += direction_y * transport_speed
    
    elif current_transport_state == TRANSPORT_STATES['MOVING_TO_CHEST']:
        # Move horizontally to chest position
        dx = CHEST_POS[0] - player_pos[0]
        dy = CHEST_POS[1] - player_pos[1]
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance < transport_speed:
            # Reached chest position
            player_pos = CHEST_POS.copy()
            current_transport_state = TRANSPORT_STATES['COMPLETE']
            end_scene_started = True
            print("Transport completed!")
            print(f"Final position: {player_pos}")
        else:
            # Move toward chest position
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
    
    # Draw position markers
    start_screen_x = int(START_POS[0] - cam_x)
    start_screen_y = int(START_POS[1] - cam_y)
    pygame.draw.circle(screen, GREEN, (start_screen_x, start_screen_y), 15, 3)
    
    middle_screen_x = int(MIDDLE_POS[0] - cam_x)
    middle_screen_y = int(MIDDLE_POS[1] - cam_y)
    pygame.draw.circle(screen, YELLOW, (middle_screen_x, middle_screen_y), 12, 3)
    
    chest_screen_x = int(CHEST_POS[0] - cam_x - chest_img.get_width() // 2)
    chest_screen_y = int(CHEST_POS[1] - cam_y - chest_img.get_height() // 2)
    screen.blit(chest_img, (chest_screen_x, chest_screen_y))
    
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
    small_font = pygame.font.Font(None, 24)
    
    pos_text = font.render(f"Position: ({int(player_pos[0])}, {int(player_pos[1])})", True, WHITE)
    screen.blit(pos_text, (10, 10))
    
    # Simple transport status
    if current_transport_state == TRANSPORT_STATES['IDLE']:
        help_text = font.render("Press R to start transport to chest", True, WHITE)
        screen.blit(help_text, (10, 50))
    elif current_transport_state == TRANSPORT_STATES['COMPLETE']:
        end_text = font.render("Transport complete! Press E for end scene", True, (0, 255, 0))
        screen.blit(end_text, (10, 50))
    
    # Draw position labels (only if not transporting or with higher contrast)
    label_alpha = 128 if is_transporting else 255
    start_label = small_font.render("START", True, GREEN)
    start_label.set_alpha(label_alpha)
    screen.blit(start_label, (start_screen_x - 20, start_screen_y - 25))
    
    middle_label = small_font.render("MIDDLE", True, YELLOW)
    middle_label.set_alpha(label_alpha)
    screen.blit(middle_label, (middle_screen_x - 25, middle_screen_y - 25))
    
    chest_label = small_font.render("CHEST", True, RED)
    chest_label.set_alpha(label_alpha)
    screen.blit(chest_label, (chest_screen_x + 10, chest_screen_y - 30))
    
    # Draw minimap in corner
    minimap_size = 200
    minimap_surface = pygame.Surface((minimap_size, minimap_size))
    minimap_surface.fill((0, 0, 0))
    
    # Draw minimap representation of world
    scale_x = minimap_size / WORLD_WIDTH
    scale_y = minimap_size / WORLD_HEIGHT
    
    # Draw positions on minimap
    pygame.draw.circle(minimap_surface, GREEN, (int(START_POS[0] * scale_x), int(START_POS[1] * scale_y)), 3)
    pygame.draw.circle(minimap_surface, YELLOW, (int(MIDDLE_POS[0] * scale_x), int(MIDDLE_POS[1] * scale_y)), 3)
    pygame.draw.circle(minimap_surface, RED, (int(CHEST_POS[0] * scale_x), int(CHEST_POS[1] * scale_y)), 3)
    
    # Draw player on minimap
    player_minimap_x = int(player_pos[0] * scale_x)
    player_minimap_y = int(player_pos[1] * scale_y)
    pygame.draw.circle(minimap_surface, BLUE, (player_minimap_x, player_minimap_y), 4)
    
    screen.blit(minimap_surface, (SCREEN_WIDTH - minimap_size - 10, 10))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
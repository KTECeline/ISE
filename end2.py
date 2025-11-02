import pygame
import sys
import os

# Initialize pygame
pygame.init()
pygame.mixer.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dialog Box with Sound")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (50, 50, 50)
LIGHT_BROWN = (210, 180, 140)
DARK_BROWN = (101, 67, 33)
TRANSPARENT = (0, 0, 0, 0)

# Fonts
try:
    font = pygame.font.Font(None, 28)
    name_font = pygame.font.Font(None, 24)
except:
    font = pygame.font.SysFont("Arial", 28)
    name_font = pygame.font.SysFont("Arial", 24, bold=True)

# Dialog data
dialog_lines = [
    {"text": "The rain no longer mourns—it sings.", "sound": "end2.1"},
    {"text": "So the City breathes again?", "sound": "end2.2"},
    {"text": "Aye. Every tear feeds the light that blooms anew.", "sound": "end2.3"},
    {"text": "Then... our sorrow was worth it.", "sound": "end2.4"}
]

# Load background image
try:
    background = pygame.image.load("assets/images/end2.png")
    background = pygame.transform.scale(background, (WIDTH, HEIGHT))
except pygame.error as e:
    print(f"Could not load background image: {e}")
    # Create fallback background
    background = pygame.Surface((WIDTH, HEIGHT))
    background.fill((20, 25, 40))  # Dark blue background for rainy scene
    # Add some visual elements to simulate the described scene
    for i in range(200):  # Rain drops
        x = (i * 15 + pygame.time.get_ticks() // 10) % WIDTH
        y = (i * 8) % HEIGHT
        pygame.draw.line(background, (150, 180, 220), (x, y), (x, y + 8), 1)
    for i in range(30):  # Glowing roots
        x = i * 30
        y = HEIGHT - 20 + (i % 3) * 5
        pygame.draw.line(background, (180, 220, 255), (x, y), (x + 15, y - 40), 3)

# Load sound files
sounds = {}
for i in range(1, 5):
    sound_file = f"assets/voice/end/end2.{i}.mp3"
    try:
        if os.path.exists(sound_file):
            sounds[f"end2.{i}"] = pygame.mixer.Sound(sound_file)
            print(f"Loaded sound: {sound_file}")
        else:
            print(f"Sound file not found: {sound_file}")
            # Create silent sound as fallback
            silent_sound = pygame.mixer.Sound(buffer=bytes([0] * 44100))
            sounds[f"end2.{i}"] = silent_sound
    except pygame.error as e:
        print(f"Could not load sound {sound_file}: {e}")
        # Create silent sound as fallback
        silent_sound = pygame.mixer.Sound(buffer=bytes([0] * 44100))
        sounds[f"end2.{i}"] = silent_sound

# Create dialog box with rounded corners
def create_dialog_box(width, height, color, border_color, border_width=3):
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    
    # Fill with main color
    pygame.draw.rect(surface, color, (0, 0, width, height), border_radius=15)
    
    # Draw border
    pygame.draw.rect(surface, border_color, (0, 0, width, height), border_width, border_radius=15)
    
    return surface

# Create dialog box
dialog_width, dialog_height = WIDTH - 100, 130
dialog_box = create_dialog_box(dialog_width, dialog_height, LIGHT_BROWN, DARK_BROWN)

# Game variables
current_line = 0
text_progress = 0
typing_speed = 2  # characters per frame
sound_played = False
conversation_finished = False
clock = pygame.time.Clock()

# Function to wrap text
def wrap_text(text, font, max_width):
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
    
    return lines

# Main game loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN or event.key == pygame.K_RIGHT:
                # Move to next line or advance text
                if text_progress >= len(dialog_lines[current_line]["text"]):
                    if current_line < len(dialog_lines) - 1:
                        current_line += 1
                        text_progress = 0
                        sound_played = False
                    else:
                        # This is the last line - finish conversation
                        conversation_finished = True
                        running = False
                else:
                    text_progress = len(dialog_lines[current_line]["text"])
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Click to advance
            if text_progress >= len(dialog_lines[current_line]["text"]):
                if current_line < len(dialog_lines) - 1:
                    current_line += 1
                    text_progress = 0
                    sound_played = False
                else:
                    # This is the last line - finish conversation
                    conversation_finished = True
                    running = False
            else:
                text_progress = len(dialog_lines[current_line]["text"])
    
    # Update text progress
    if text_progress < len(dialog_lines[current_line]["text"]):
        text_progress += typing_speed
    
    # Play sound when starting a new line
    if not sound_played and text_progress > 0:
        sound_key = dialog_lines[current_line]["sound"]
        if sound_key in sounds:
            sounds[sound_key].play()
        sound_played = True
    
    # Draw background
    screen.blit(background, (0, 0))
    
    # Draw dialog box
    screen.blit(dialog_box, (50, HEIGHT - dialog_height - 20))
    
    # Draw text with typing effect and wrapping
    current_text = dialog_lines[current_line]["text"][:int(text_progress)]
    wrapped_lines = wrap_text(current_text, font, dialog_width - 40)
    
    # Draw each line of text
    for i, line in enumerate(wrapped_lines):
        text_surface = font.render(line, True, BLACK)
        screen.blit(text_surface, (70, HEIGHT - dialog_height - 10 + i * 30))
    
    # Draw continue indicator if text is complete
    if text_progress >= len(dialog_lines[current_line]["text"]):
        if current_line < len(dialog_lines) - 1:
            continue_text = font.render("Press SPACE or click to continue...", True, DARK_BROWN)
            screen.blit(continue_text, (WIDTH - 300, HEIGHT - 40))
        else:
            continue_text = font.render("Press SPACE or click to end...", True, DARK_BROWN)
            screen.blit(continue_text, (WIDTH - 250, HEIGHT - 40))
    
    # Update display
    pygame.display.flip()
    clock.tick(60)

# Clean up and exit
pygame.quit()
sys.exit()
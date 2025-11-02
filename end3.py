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
    {"text": "This... is the sky beneath the soil?", "sound": "end3.1"},
    {"text": "The Sporelit Heavens—Hyphara's dream made whole.", "sound": "end3.2"},
    {"text": "Welcome, little Echo. You carried the weave well.", "sound": "end3.3"},
    {"text": "I only followed the roots.", "sound": "end3.4"},
    {"text": "And in doing so, you became one.", "sound": "end3.5"}
]

# Load background image
try:
    background = pygame.image.load("assets/images/end3.png")
    background = pygame.transform.scale(background, (WIDTH, HEIGHT))
except pygame.error as e:
    print(f"Could not load background image: {e}")
    # Create fallback background for "sky beneath the soil" / Sporelit Heavens
    background = pygame.Surface((WIDTH, HEIGHT))
    # Create a mystical underground sky gradient
    for y in range(HEIGHT):
        # Dark soil at bottom transitioning to sporelit sky at top
        r = max(10, min(80, 20 + y // 15))
        g = max(5, min(60, 15 + y // 20))
        b = max(20, min(100, 40 + y // 10))
        pygame.draw.line(background, (r, g, b), (0, y), (WIDTH, y))
    
    # Add glowing spores (stars in the underground sky)
    for i in range(100):
        x = (i * 37) % WIDTH
        y = (i * 23) % (HEIGHT // 2)  # Only in upper half for sky effect
        size = 2 + (i % 3)
        glow_color = (150 + i % 50, 180 + i % 40, 200 + i % 30)
        pygame.draw.circle(background, glow_color, (x, y), size)
        
    # Add some root-like structures at the bottom
    for i in range(20):
        x = i * 40
        base_y = HEIGHT - 30
        points = [
            (x, base_y),
            (x + 10, base_y - 50 - (i % 3) * 10),
            (x + 25, base_y - 80 - (i % 5) * 15),
            (x + 15, base_y - 120 - (i % 7) * 20)
        ]
        root_color = (80 + i % 20, 60 + i % 15, 40 + i % 10)
        pygame.draw.lines(background, root_color, False, points, 3)

# Load sound files
sounds = {}
for i in range(1, 6):
    sound_file = f"assets/voice/end/end3.{i}.mp3"
    try:
        if os.path.exists(sound_file):
            sounds[f"end3.{i}"] = pygame.mixer.Sound(sound_file)
            print(f"Loaded sound: {sound_file}")
        else:
            print(f"Sound file not found: {sound_file}")
            # Create silent sound as fallback
            silent_sound = pygame.mixer.Sound(buffer=bytes([0] * 44100))
            sounds[f"end3.{i}"] = silent_sound
    except pygame.error as e:
        print(f"Could not load sound {sound_file}: {e}")
        # Create silent sound as fallback
        silent_sound = pygame.mixer.Sound(buffer=bytes([0] * 44100))
        sounds[f"end3.{i}"] = silent_sound

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
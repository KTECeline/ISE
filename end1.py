import pygame
import sys
import os

# Initialize pygame
pygame.init()
pygame.mixer.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Echo's Complete Journey")

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

# All endings data
endings = [
    {
        "name": "end1",
        "background": "assets/images/end1.png",
        "dialog": [
            {"text": "The roots rise with you, Echo. Each pulse below remembers your gift.", "sound": "end1.1"},
            {"text": "It feels… alive.", "sound": "end1.2"},
            {"text": "All things in Hyphara's weave are. Even silence grows here.", "sound": "end1.3"}
        ]
    },
    {
        "name": "end2", 
        "background": "assets/images/end2.png",
        "dialog": [
            {"text": "The rain no longer mourns—it sings.", "sound": "end2.1"},
            {"text": "So the City breathes again?", "sound": "end2.2"},
            {"text": "Aye. Every tear feeds the light that blooms anew.", "sound": "end2.3"},
            {"text": "Then... our sorrow was worth it.", "sound": "end2.4"}
        ]
    },
    {
        "name": "end3",
        "background": "assets/images/end3.png", 
        "dialog": [
            {"text": "This... is the sky beneath the soil?", "sound": "end3.1"},
            {"text": "The Sporelit Heavens—Hyphara's dream made whole.", "sound": "end3.2"},
            {"text": "Welcome, little Echo. You carried the weave well.", "sound": "end3.3"},
            {"text": "I only followed the roots.", "sound": "end3.4"},
            {"text": "And in doing so, you became one.", "sound": "end3.5"}
        ]
    },
    {
        "name": "end4",
        "background": "assets/images/end4.png",
        "dialog": [
            {"text": "Each guardian fed, each sorrow healed—still you ascend.", "sound": "end4.1"},
            {"text": "Was this the purpose of my descent?", "sound": "end4.2"},
            {"text": "Purpose is merely a shape the soil takes. You gave it bloom.", "sound": "end4.3"},
            {"text": "Kneel, Echo. Receive the Weaver's light.", "sound": "end4.4"}
        ]
    },
    {
        "name": "end5",
        "background": "assets/images/end5.png",
        "dialog": [
            {"text": "The Blight sleeps... for now.", "sound": "end5.1"},
            {"text": "Then the weave is safe?", "sound": "end5.2"},
            {"text": "Safe enough to dream again.", "sound": "end5.3"},
            {"text": "Rest, little Echo. The mycelia remember.", "sound": "end5.4"}
        ]
    }
]

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

# Function to create fallback background
def create_fallback_background(ending_name):
    background = pygame.Surface((WIDTH, HEIGHT))
    
    if ending_name == "end1":
        background.fill((30, 15, 5))
        for i in range(100):
            x = i * 8
            y = HEIGHT - 50 + (i % 3) * 10
            pygame.draw.circle(background, (100, 70, 40), (x, y), 2)
        for i in range(50):
            x = i * 20
            y = HEIGHT // 2 + (i % 5) * 5
            pygame.draw.circle(background, (150, 200, 100), (x, y), 3, 1)
    
    elif ending_name == "end2":
        background.fill((20, 25, 40))
        for i in range(200):
            x = (i * 15) % WIDTH
            y = (i * 8) % HEIGHT
            pygame.draw.line(background, (150, 180, 220), (x, y), (x, y + 8), 1)
    
    elif ending_name == "end3":
        for y in range(HEIGHT):
            r = max(10, min(80, 20 + y // 15))
            g = max(5, min(60, 15 + y // 20))
            b = max(20, min(100, 40 + y // 10))
            pygame.draw.line(background, (r, g, b), (0, y), (WIDTH, y))
        for i in range(100):
            x = (i * 37) % WIDTH
            y = (i * 23) % (HEIGHT // 2)
            size = 2 + (i % 3)
            glow_color = (150 + i % 50, 180 + i % 40, 200 + i % 30)
            pygame.draw.circle(background, glow_color, (x, y), size)
    
    elif ending_name == "end4":
        for y in range(HEIGHT):
            r = min(255, 30 + y // 2)
            g = min(255, 40 + y // 2)
            b = min(255, 50 + y // 3)
            pygame.draw.line(background, (r, g, b), (0, y), (WIDTH, y))
        for i in range(150):
            x = (i * 29) % WIDTH
            y = (i * 17) % HEIGHT
            size = 1 + (i % 4)
            glow_intensity = 150 + (i % 105)
            glow_color = (glow_intensity, glow_intensity, 100 + glow_intensity // 2)
            pygame.draw.circle(background, glow_color, (x, y), size)
    
    elif ending_name == "end5":
        background.fill((10, 5, 20))
        for i in range(100):
            x = (i * 25) % WIDTH
            y = HEIGHT - (i * 3) % HEIGHT
            size = 2 + (i % 3)
            pygame.draw.circle(background, (200, 220, 255), (x, y), size)
    
    return background

# Main sequence loop
for ending in endings:
    # Load background image
    try:
        background = pygame.image.load(ending["background"])
        background = pygame.transform.scale(background, (WIDTH, HEIGHT))
    except pygame.error as e:
        print(f"Could not load background image {ending['background']}: {e}")
        background = create_fallback_background(ending["name"])
    
    # Load sound files for this ending
    sounds = {}
    for i, dialog_line in enumerate(ending["dialog"], 1):
        sound_file = f"assets/voice/end/{ending['name']}.{i}.mp3"
        try:
            if os.path.exists(sound_file):
                sounds[f"{ending['name']}.{i}"] = pygame.mixer.Sound(sound_file)
                print(f"Loaded sound: {sound_file}")
            else:
                print(f"Sound file not found: {sound_file}")
                # Create silent sound as fallback
                silent_sound = pygame.mixer.Sound(buffer=bytes([0] * 44100))
                sounds[f"{ending['name']}.{i}"] = silent_sound
        except pygame.error as e:
            print(f"Could not load sound {sound_file}: {e}")
            # Create silent sound as fallback
            silent_sound = pygame.mixer.Sound(buffer=bytes([0] * 44100))
            sounds[f"{ending['name']}.{i}"] = silent_sound
    
    # Game variables for this ending
    current_line = 0
    text_progress = 0
    typing_speed = 2
    sound_played = False
    clock = pygame.time.Clock()
    
    running_ending = True
    while running_ending:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN or event.key == pygame.K_RIGHT:
                    # Move to next line or advance text
                    if text_progress >= len(ending["dialog"][current_line]["text"]):
                        if current_line < len(ending["dialog"]) - 1:
                            current_line += 1
                            text_progress = 0
                            sound_played = False
                        else:
                            # This is the last line - move to next ending
                            running_ending = False
                    else:
                        text_progress = len(ending["dialog"][current_line]["text"])
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Click to advance
                if text_progress >= len(ending["dialog"][current_line]["text"]):
                    if current_line < len(ending["dialog"]) - 1:
                        current_line += 1
                        text_progress = 0
                        sound_played = False
                    else:
                        # This is the last line - move to next ending
                        running_ending = False
                else:
                    text_progress = len(ending["dialog"][current_line]["text"])
        
        # Update text progress
        if text_progress < len(ending["dialog"][current_line]["text"]):
            text_progress += typing_speed
        
        # Play sound when starting a new line
        if not sound_played and text_progress > 0:
            sound_key = ending["dialog"][current_line]["sound"]
            if sound_key in sounds:
                sounds[sound_key].play()
            sound_played = True
        
        # Draw background
        screen.blit(background, (0, 0))
        
        # Draw dialog box
        screen.blit(dialog_box, (50, HEIGHT - dialog_height - 20))
        
        # Draw text with typing effect and wrapping
        current_text = ending["dialog"][current_line]["text"][:int(text_progress)]
        wrapped_lines = wrap_text(current_text, font, dialog_width - 40)
        
        # Draw each line of text
        for i, line in enumerate(wrapped_lines):
            text_surface = font.render(line, True, BLACK)
            screen.blit(text_surface, (70, HEIGHT - dialog_height - 10 + i * 30))
        
        # Draw continue indicator if text is complete
        if text_progress >= len(ending["dialog"][current_line]["text"]):
            if current_line < len(ending["dialog"]) - 1:
                continue_text = font.render("Press SPACE or click to continue...", True, DARK_BROWN)
                screen.blit(continue_text, (WIDTH - 300, HEIGHT - 40))
            else:
                if ending["name"] != "end5":  # Not the final ending
                    continue_text = font.render("Press SPACE for next chapter...", True, DARK_BROWN)
                else:
                    continue_text = font.render("Press SPACE to end journey...", True, DARK_BROWN)
                screen.blit(continue_text, (WIDTH - 300, HEIGHT - 40))
        
        # Update display
        pygame.display.flip()
        clock.tick(60)

# Clean up and exit after all endings
pygame.quit()
sys.exit() 
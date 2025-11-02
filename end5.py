import pygame
import sys
import os

pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dialog Box with Sound")

COLORS = {
    'WHITE': (255, 255, 255),
    'BLACK': (0, 0, 0),
    'LIGHT_BROWN': (210, 180, 140),
    'DARK_BROWN': (101, 67, 33)
}

font = pygame.font.SysFont("Arial", 28)

dialog_lines = [
    {"text": "The Blight sleeps... for now.", "sound": "end5.1"},
    {"text": "Then the weave is safe?", "sound": "end5.2"},
    {"text": "Safe enough to dream again.", "sound": "end5.3"},
    {"text": "Rest, little Echo. The mycelia remember.", "sound": "end5.4"}
]

try:
    background = pygame.image.load("assets/images/end5.png")
    background = pygame.transform.scale(background, (WIDTH, HEIGHT))
except:
    background = pygame.Surface((WIDTH, HEIGHT))
    background.fill((10, 5, 20))
    for i in range(100):
        x = (i * 25) % WIDTH
        y = HEIGHT - (i * 3) % HEIGHT
        size = 2 + (i % 3)
        pygame.draw.circle(background, (200, 220, 255), (x, y), size)

sounds = {}
for i in range(1, 5):
    sound_file = f"assets/voice/end/end5.{i}.mp3"
    try:
        if os.path.exists(sound_file):
            sounds[f"end5.{i}"] = pygame.mixer.Sound(sound_file)
    except:
        silent_sound = pygame.mixer.Sound(buffer=bytes([0] * 44100))
        sounds[f"end5.{i}"] = silent_sound

def create_dialog_box(width, height):
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(surface, COLORS['LIGHT_BROWN'], (0, 0, width, height), border_radius=15)
    pygame.draw.rect(surface, COLORS['DARK_BROWN'], (0, 0, width, height), 3, border_radius=15)
    return surface

dialog_box = create_dialog_box(WIDTH - 100, 130)

current_line = 0
text_progress = 0
typing_speed = 2
sound_played = False
clock = pygame.time.Clock()

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type in [pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN]:
            if text_progress >= len(dialog_lines[current_line]["text"]):
                if current_line < len(dialog_lines) - 1:
                    current_line += 1
                    text_progress = 0
                    sound_played = False
                else:
                    running = False
            else:
                text_progress = len(dialog_lines[current_line]["text"])
    
    if text_progress < len(dialog_lines[current_line]["text"]):
        text_progress += typing_speed
    
    if not sound_played and text_progress > 0:
        sound_key = dialog_lines[current_line]["sound"]
        if sound_key in sounds:
            sounds[sound_key].play()
        sound_played = True
    
    screen.blit(background, (0, 0))
    screen.blit(dialog_box, (50, HEIGHT - 150))
    
    current_text = dialog_lines[current_line]["text"][:int(text_progress)]
    text_surface = font.render(current_text, True, COLORS['BLACK'])
    screen.blit(text_surface, (70, HEIGHT - 120))
    
    if text_progress >= len(dialog_lines[current_line]["text"]):
        continue_text = font.render("Press SPACE or click to continue...", True, COLORS['DARK_BROWN'])
        screen.blit(continue_text, (WIDTH - 300, HEIGHT - 50))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
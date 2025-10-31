import os
import random
import pygame
import sys

pygame.init()

# --- Setup ---
WIDTH, HEIGHT = 1000, 700
# NOTE: Do NOT create a display surface at import time. The demo creates a screen when
# run as a script (see _main()). This keeps the module import-safe for other files.

# --- Load assets ---
background_color = (135, 206, 250)  # light blue background

SCRIPT_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'assets', 'characters'))

# Paths (no loading at import time)
walking_sheet_path = os.path.join(ASSETS_DIR, 'villian_sprite1.png')
hit_sheet_path = os.path.join(ASSETS_DIR, 'villian_static1.png')

# Frame containers (filled by load_assets)
walking_frames_right = []
hit_frames_right = []

# --- Extract frames ---
num_walking_frames = 4
num_hit_frames = 2

def extract_frames(sheet, row, numFrames):
    width = sheet.get_width() // numFrames
    height = sheet.get_height()
    frames = []
    for i in range(numFrames):
        frame = sheet.subsurface(pygame.Rect(i * width, 0, width, height))
        frames.append(frame)
    return frames

def load_assets():
    """Load sprite sheets and populate frame lists. Call after a display has been set."""
    global walking_frames_right, hit_frames_right
    # Load images
    ws = pygame.image.load(walking_sheet_path)
    hs = pygame.image.load(hit_sheet_path)
    # convert_alpha may require a display; avoid if it fails
    try:
        ws = ws.convert_alpha()
    except Exception:
        ws = ws.convert()
    try:
        hs = hs.convert_alpha()
    except Exception:
        hs = hs.convert()
    # Extract frames
    wframes = extract_frames(ws, 0, num_walking_frames)
    hframes = extract_frames(hs, 0, num_hit_frames)
    # Mutate lists in-place so importers keep references
    walking_frames_right.clear()
    walking_frames_right.extend(wframes)
    hit_frames_right.clear()
    hit_frames_right.extend(hframes)

# --- Player Class ---
class Goal(pygame.sprite.Sprite):
    """A goal sprite that animates until marked hit; call `mark_hit()` when hit by the ball."""
    def __init__(self, pos=None):
        super().__init__()
        self.walkingRightFrames = walking_frames_right
        self.hitFrames = hit_frames_right
        self.frame_index = 0
        self.hit = False  # Hit state
        # Choose random position if not provided
        if pos is None:
            x = random.randint(50, WIDTH - 50)
            y = random.randint(100, HEIGHT - 50)
            pos = (x, y)
        self.image = self.walkingRightFrames[0]
        self.rect = self.image.get_rect(midbottom=pos)

    def update(self):
        if not self.hit:
            # Auto-animate walking frames (idle animation)
            self.frame_index = (self.frame_index + 0.2) % len(self.walkingRightFrames)
            self.image = self.walkingRightFrames[int(self.frame_index)]
        else:
            # Auto-animate hit frames (show hit sprite)
            self.frame_index = (self.frame_index + 0.2) % len(self.hitFrames)
            new_image = self.hitFrames[int(self.frame_index)]
            # Keep bottom alignment
            old_bottom = self.rect.bottom
            old_mid_x = self.rect.centerx
            self.rect = new_image.get_rect(midbottom=(old_mid_x, old_bottom))
            self.image = new_image

    def mark_hit(self):
        """Externally mark this goal as hit (switches animation to hit frames)."""
        self.hit = True

# --- Main Loop ---
def _main():
    # Create display for demo mode only
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Mushroom Auto-Animation Demo")
    clock = pygame.time.Clock()
    goal = Goal()  # Randomly placed goal sprite
    all_sprites = pygame.sprite.Group(goal)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # Toggle hit state on spacebar press (demo "hit" trigger)
                    goal.hit = not goal.hit

        # Update
        all_sprites.update()

        # Draw
        screen.fill(background_color)
        all_sprites.draw(screen)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    _main()
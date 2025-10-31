import os
import pygame
import sys

pygame.init()

# --- Config ---
WIDTH, HEIGHT = 1000, 700
background_color = (135, 206, 250)  # light blue background

SCRIPT_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'assets', 'characters'))
ball_sheet_path = os.path.join(ASSETS_DIR, 'ball1.png')
num_ball_frames = 8

# frames container (populated by load_assets)
ball_frames = []

def extract_frames(sheet, row, numFrames):
    width = sheet.get_width() // numFrames
    height = sheet.get_height()
    frames = []
    for i in range(numFrames):
        frame = sheet.subsurface(pygame.Rect(i * width, 0, width, height))
        frames.append(frame)
    return frames

def load_assets():
    """Load ball sprite sheet and populate ball_frames. Must be called after a video mode exists."""
    global ball_frames
    sheet = pygame.image.load(ball_sheet_path)
    try:
        sheet = sheet.convert_alpha()
    except Exception:
        sheet = sheet.convert()
    frames = extract_frames(sheet, 0, num_ball_frames)
    ball_frames.clear()
    ball_frames.extend(frames)


class Ball(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.ballFrames = ball_frames
        self.image = self.ballFrames[0] if self.ballFrames else pygame.Surface((16, 16))
        self.rect = self.image.get_rect(center=pos)  # Center it for ball
        self.frame_index = 0.0
        self.animating = True  # Start animating immediately, or set to False and trigger

    def update(self):
        if self.animating and self.ballFrames:
            self.frame_index = (self.frame_index + 0.133) % len(self.ballFrames)
            self.image = self.ballFrames[int(self.frame_index)]


def _main():
    # Demo runner for testing this module directly
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Ball Goal Hit Animation Demo")
    load_assets()
    clock = pygame.time.Clock()
    ball = Ball(pos=(WIDTH // 2, HEIGHT // 2))  # Center on screen
    all_sprites = pygame.sprite.Group(ball)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # Toggle animation on spacebar (simulate "hit goal" trigger)
                    ball.animating = not ball.animating

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
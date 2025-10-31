import pygame
import sys
import math

# Make this module import-safe: asset loading is lazy via load_assets()

# --- Config defaults (can be overridden by caller) ---
num_walking_frames = 7
num_down_frames = 3
num_jump_frames = 3

# Global visual scale for the character. Increase to make the on-screen
# character larger. Can be overridden by callers of load_assets via
# the `scale` parameter.
CHARACTER_SCALE = 1.8

# Asset placeholders (filled by load_assets)
walking_frames_right = []
walking_frames_left = []
standing_right = None
standing_left = None
down_frames_right = []
down_frames_left = []
jump_frames_right = []
jump_frames_left = []

_assets_loaded = False

def extract_frames(sheet, numFrames):
    width = sheet.get_width() // numFrames
    height = sheet.get_height()
    frames = []
    for i in range(numFrames):
        frame = sheet.subsurface(pygame.Rect(i * width, 0, width, height))
        frames.append(frame)
    return frames

def load_assets(base_path='character'):
    """Load sprite sheets and populate frame lists. Must be called after a pygame display is created (for convert_alpha())."""
    global walking_frames_right, walking_frames_left, standing_right, standing_left
    global down_frames_right, down_frames_left, jump_frames_right, jump_frames_left, _assets_loaded
    if _assets_loaded:
        return
    # Load sprite sheets
    standing_image = pygame.image.load(f"{base_path}/chaStanding.png").convert_alpha()
    walking_sheet = pygame.image.load(f"{base_path}/chaWalk.png").convert_alpha()
    down_sheet = pygame.image.load(f"{base_path}/chadown.png").convert_alpha()
    jump_sheet = pygame.image.load(f"{base_path}/chajump.png").convert_alpha()

    wfr = extract_frames(walking_sheet, num_walking_frames)
    wfl = [pygame.transform.flip(frame, True, False) for frame in wfr]

    dr = extract_frames(down_sheet, num_down_frames)
    dl = [pygame.transform.flip(frame, True, False) for frame in dr]

    jr = extract_frames(jump_sheet, num_jump_frames)
    jl = [pygame.transform.flip(frame, True, False) for frame in jr]

    walking_frames_right = wfr
    walking_frames_left = wfl
    standing_right = standing_image
    standing_left = pygame.transform.flip(standing_image, True, False)
    down_frames_right = dr
    down_frames_left = dl
    jump_frames_right = jr
    jump_frames_left = jl

    # Apply scaling to all frames if CHARACTER_SCALE != 1.0. Use smoothscale
    # for better visual quality when enlarging sprites.
    scale = CHARACTER_SCALE
    if scale != 1.0:
        def _scale_surface(surf):
            w, h = surf.get_size()
            return pygame.transform.smoothscale(surf, (max(1, int(w * scale)), max(1, int(h * scale))))

        standing_right = _scale_surface(standing_right)
        standing_left = _scale_surface(standing_left)

        walking_frames_right = [_scale_surface(f) for f in walking_frames_right]
        walking_frames_left = [_scale_surface(f) for f in walking_frames_left]
        down_frames_right = [_scale_surface(f) for f in down_frames_right]
        down_frames_left = [_scale_surface(f) for f in down_frames_left]
        jump_frames_right = [_scale_surface(f) for f in jump_frames_right]
        jump_frames_left = [_scale_surface(f) for f in jump_frames_left]

    # expose to module globals
    globals().update({
        'walking_frames_right': walking_frames_right,
        'walking_frames_left': walking_frames_left,
        'standing_right': standing_right,
        'standing_left': standing_left,
        'down_frames_right': down_frames_right,
        'down_frames_left': down_frames_left,
        'jump_frames_right': jump_frames_right,
        'jump_frames_left': jump_frames_left,
    })
    _assets_loaded = True

# --- Player Class ---
class Player(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        # Frames will be populated by load_assets(); reference module globals
        self.walkingRightFrames = walking_frames_right
        self.walkingLeftFrames = walking_frames_left
        self.downRightFrames = down_frames_right
        self.downLeftFrames = down_frames_left
        self.jumpRightFrames = jump_frames_right
        self.jumpLeftFrames = jump_frames_left
        self.standingRight = standing_right
        self.standingLeft = standing_left
        # Use provided pos as midbottom; also record ground Y for landing checks
        self.image = self.standingRight if self.standingRight is not None else pygame.Surface((32, 64))
        self.rect = self.image.get_rect(midbottom=pos)
        self.facing_right = True
        self.frame_index = 0
        self.onGround = True
        self.velocityY = 0
        self.direction = 0
        # ground Y position (midbottom y) used instead of module HEIGHT
        self.ground_y = pos[1]

    def update(self, walk_progress=None, screen_width=None):
        """Update player. If walk_progress is provided (0..1) the player will be positioned
        for an entrance animation and its walking animation will be advanced.
        Otherwise regular input-driven movement is used.
        """
        keys = pygame.key.get_pressed()

        # If we're being driven by a walk-in progress, position and animate accordingly
        if walk_progress is not None:
            # Position midbottom according to progress and add bounce
            sw = screen_width if screen_width is not None else 1000
            new_x = -50 + (sw // 2 + 50) * walk_progress
            bounce = math.sin(walk_progress * math.pi) * 5
            self.rect.midbottom = (int(new_x), int(self.ground_y + bounce))
            # Advance walk animation frames
            if self.walkingRightFrames:
                self.frame_index = (self.frame_index + 0.2) % len(self.walkingRightFrames)
                if self.facing_right:
                    self.image = self.walkingRightFrames[int(self.frame_index)]
                else:
                    self.image = self.walkingLeftFrames[int(self.frame_index)]
            return
        self.direction = 0

    # Movement
        if not hasattr(self, 'down'):
            self.down = "free"
            self.frame_index = 0

        if keys[pygame.K_s]:
            if self.down in ["free"]:
                self.down = "going_down"
                self.frame_index = 0
        elif self.down in ["holding", "going_down"]:
                self.down = "going_up"
        else:
            self.down = "free"

        move = self.down == "free"

        if move:
            if keys[pygame.K_a]:
                self.rect.x -= 5
                self.direction = -1
                self.facing_right = False
            if keys[pygame.K_d]:
                self.rect.x += 5
                self.direction = 1
                self.facing_right = True

            if keys[pygame.K_w] and self.onGround:
                self.velocityY = -20
                self.onGround = False

        self.velocityY += 1
        self.rect.y += self.velocityY

        if self.rect.bottom >= self.ground_y:
            self.rect.bottom = self.ground_y
            self.velocityY = 0
            self.onGround = True

        # Animation
        if not self.onGround and self.down == "free":
            if self.velocityY > -15:
                self.frame_index = 1
            else:
                self.frame_index = 0
            if self.facing_right:
                if self.jumpRightFrames:
                    self.image = self.jumpRightFrames[int(self.frame_index)]
            else:
                if self.jumpLeftFrames:
                    self.image = self.jumpLeftFrames[int(self.frame_index)]

        elif self.direction != 0 and self.down == "free":
            if self.walkingRightFrames:
                self.frame_index = (self.frame_index + 0.2) % len(self.walkingRightFrames)
                if self.facing_right:
                    self.image = self.walkingRightFrames[int(self.frame_index)]
                else:
                    self.image = self.walkingLeftFrames[int(self.frame_index)]
        elif self.down == "going_down":
            self.frame_index += 0.3
            if self.frame_index >= 2:
                self.frame_index = 2
                self.down = "holding"
            if self.facing_right and self.downRightFrames:
                self.image = self.downRightFrames[int(self.frame_index)]
            elif self.downLeftFrames:
                self.image = self.downLeftFrames[int(self.frame_index)]

        elif self.down == "holding":
            if self.facing_right and self.downRightFrames:
                self.image = self.downRightFrames[2]
            elif self.downLeftFrames:
                self.image = self.downLeftFrames[2]

        elif self.down == "going_up":
            if self.downRightFrames:
                self.frame_index = (self.frame_index - 0.2) % len(self.downRightFrames)
                if self.frame_index <= 0:
                    self.frame_index = 0
                    self.down = "free"

            if self.facing_right:
                if self.downRightFrames:
                    self.image = self.downRightFrames[int(self.frame_index)]
            else:
                if self.downLeftFrames:
                    self.image = self.downLeftFrames[int(self.frame_index)]

        else:
            if self.facing_right and self.standingRight:
                self.image = self.standingRight
            elif self.standingLeft:
                self.image = self.standingLeft



if __name__ == '__main__':
    # Demo runner: only runs when charactermove.py is executed directly
    pygame.init()
    WIDTH, HEIGHT = 1000, 700
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Character Movement Demo")
    background_color = (135, 206, 250)  # light blue background

    # Ensure assets are loaded
    load_assets()

    clock = pygame.time.Clock()
    player = Player(pos=(WIDTH // 2, HEIGHT - 100))
    all_sprites = pygame.sprite.Group(player)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Update
        all_sprites.update()

        # Draw
        screen.fill(background_color)
        all_sprites.draw(screen)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

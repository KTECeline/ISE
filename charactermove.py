import pygame
import sys

pygame.init()

# --- Setup ---
WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Character Movement Demo")

# --- Load assets ---
background_color = (135, 206, 250)  # light blue background

# Load sprite sheets
standing_image = pygame.image.load("ISE\character\chaStanding.png").convert_alpha()
walking_sheet = pygame.image.load("ISE\character\chaWalk.png").convert_alpha()
down_sheet = pygame.image.load("ISE\character\chadown.png").convert_alpha()
jump_sheet = pygame.image.load("ISE\character\chajump.png").convert_alpha()

# --- Extract frames ---
num_walking_frames = 7

num_down_frames = 3
num_jump_frames = 3

def extract_frames(sheet, row, numFrames):
    width = sheet.get_width() // numFrames
    height = sheet.get_height()
    frames = []
    for i in range(numFrames):
        frame = sheet.subsurface(pygame.Rect(i * width, 0, width, height))
        frames.append(frame)
    return frames


walking_frames_right = extract_frames(walking_sheet, 0, num_walking_frames)
# Create flipped versions for left movement
walking_frames_left = [pygame.transform.flip(frame, True, False) for frame in walking_frames_right]

# Standing frames
standing_right = standing_image
standing_left = pygame.transform.flip(standing_image, True, False)

# Down frames
down_frames_right = extract_frames(down_sheet, 0, num_down_frames)
down_frames_left = [pygame.transform.flip(frame, True, False) for frame in down_frames_right]

#jump frames
jump_frames_right = extract_frames(jump_sheet, 0, num_jump_frames)
jump_frames_left = [pygame.transform.flip(frame, True, False) for frame in jump_frames_right]

# --- Player Class ---
class Player(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.walkingRightFrames = walking_frames_right
        self.walkingLeftFrames = walking_frames_left
        self.downRightFrames = down_frames_right
        self.downLeftFrames = down_frames_left
        self.jumpRightFrames = jump_frames_right
        self.jumpLeftFrames = jump_frames_left
        self.standingRight = standing_right
        self.standingLeft = standing_left
        self.image = self.standingRight
        self.rect = self.image.get_rect(midbottom=pos)
        self.facing_right = True
        self.frame_index = 0
        self.onGround = True
        self.velocityY = 0
        self.direction = 0


    def update(self):
        keys = pygame.key.get_pressed()
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

        if self.rect.bottom >= HEIGHT - 100:
            self.rect.bottom = HEIGHT - 100
            self.velocityY = 0
            self.onGround = True

        # Animation
        if not self.onGround and self.down == "free":
            if self.velocityY > -15:
                self.frame_index = 1
            else:
                self.frame_index = 0
            if self.facing_right:
                self.image = self.jumpRightFrames[int(self.frame_index)]
            else:
                self.image = self.jumpLeftFrames[int(self.frame_index)]
            
            pygame.display.flip()
            pygame.time.Clock().tick(60)

        elif self.direction != 0 and self.down == "free":
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
            frame = int(self.frame_index)
            if self.facing_right:
                self.image = self.downRightFrames[int(self.frame_index)]
            else:
                self.image = self.downLeftFrames[int(self.frame_index)]

        elif self.down == "holding":
            self.image = self.downRightFrames[2] if self.facing_right else self.downLeftFrames[2]

        elif self.down == "going_up":
            self.frame_index = (self.frame_index - 0.2) % len(self.downRightFrames)
            if self.frame_index <= 0:
                self.frame_index = 0
                self.down = "free"

            if self.facing_right:
                self.image = self.downRightFrames[int(self.frame_index)]
            else:
                self.image = self.downLeftFrames[int(self.frame_index)]
        
        else:
            self.image = self.standingRight if self.facing_right else self.standingLeft



# --- Main Loop ---
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

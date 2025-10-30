import pygame
import sys
import json
import random
import math  # For sin easing
from PIL import Image, ImageFilter  # pip install pillow

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
FADE_FRAMES = 30
WALK_DURATION = 180  # Frames (~3 sec)

# Init
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Sporeball Gauntlet - Marketplace Walk-In")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 24)
big_font = pygame.font.Font(None, 36)

# Helpers
def load_inventory():
    try:
        with open('inventory.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_inventory(inv):
    with open('inventory.json', 'w') as f:
        json.dump(inv, f)

# Particle class (for trails/ambient)
class Particle(pygame.sprite.Sprite):
    def __init__(self, x, y, vel, color=(100, 255, 200)):
        super().__init__()
        self.image = pygame.Surface((3, 3))
        self.image.fill(color + (128,))
        self.rect = self.image.get_rect(center=(x, y))
        self.vel = vel
        self.lifetime = 60

    def update(self):
        self.rect.x += self.vel.x
        self.rect.y += self.vel.y
        self.vel.y += 0.05
        self.lifetime -= 1
        self.image.set_alpha(int(128 * (self.lifetime / 60)))
        if self.lifetime <= 0 or self.rect.y > SCREEN_HEIGHT:
            self.kill()

# PlayerWalker (no arg in update for group compat, but we won't add to group)
class PlayerWalker(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        try:
            sheet = pygame.image.load('assets/images/player_walk.png').convert_alpha()  # 128x128 sheet, 4x32px frames
            self.frames = [sheet.subsurface((i*32, 0, 32, 128)) for i in range(4)]
            self.current_frame = 0
        except FileNotFoundError:
            self.frames = [pygame.Surface((32, 64))] * 4
            self.frames[0].fill((150, 100, 50))  # Brown mushroom fallback
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=(-50, SCREEN_HEIGHT - 100))
        self.walk_timer = 0

    def update(self, walk_progress=None):
        if walk_progress is not None:
            # Only use progress if provided (explicit call)
            self.rect.x = -50 + (SCREEN_WIDTH // 2 + 50) * walk_progress
            # Sin easing for bouncy walk
            bounce = math.sin(walk_progress * math.pi) * 5
            self.rect.y = (SCREEN_HEIGHT - 100) + bounce
        # Animate always
        self.walk_timer += 1
        if self.walk_timer % 10 == 0:
            self.current_frame = (self.current_frame + 1) % 4
            self.image = self.frames[self.current_frame]

# Marketplace
class Marketplace:
    def __init__(self, spore_points=300):
        self.points = spore_points
        self.inventory = load_inventory()
        self.state = 'walking_in'
        self.walk_progress = 0
        self.fade_alpha = 0
        self.fade_dir = 0
        self.particles = pygame.sprite.Group()
        self.hovered_item = None
        self.selected_item = None
        self.preview_timer = 0
        
        # BGs (handle 1024x1024)
        try:
            orig_market = pygame.image.load('assets/textures/map/marketplace_bg.png').convert()
            self.market_bg = pygame.transform.smoothscale(orig_market, (SCREEN_WIDTH, SCREEN_HEIGHT))
            orig_store = pygame.image.load('assets/textures/map/store_bg.png').convert()
            self.store_bg = pygame.transform.smoothscale(orig_store, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except FileNotFoundError:
            self.market_bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            self.market_bg.fill((50, 30, 20))
            self.store_bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            self.store_bg.fill((30, 50, 20))
        
        # Power-ups
        self.items = {
            'elastic_ball': {'cost': 100, 'desc': 'Bouncier sporeball!', 'effect': 'particles', 'tooltip': 'Higher bounces in Gauntlet!'},
            'blur_dash': {'cost': 150, 'desc': 'Speed blur reveal!', 'effect': 'blurring', 'tooltip': 'Uncover hidden spores on dash.'},
            'mycelium_smoker': {'cost': 120, 'desc': 'Smoke-obscuring pits!', 'effect': 'smoke', 'tooltip': 'Slow down defenders with haze.'},
            'glow_aura': {'cost': 80, 'desc': 'Pulsing light aura!', 'effect': 'gradient', 'tooltip': 'Light up dark paths.'},
            'venom_trail': {'cost': 200, 'desc': 'Slippery kick trails!', 'effect': 'texture', 'tooltip': 'Make hazards slip away.'}
        }
        
        # UI
        self.enter_button = pygame.Rect(300, 400, 200, 50)
        self.buy_button = pygame.Rect(600, 500, 100, 40)
        self.start_button = pygame.Rect(300, 500, 200, 50)
        self.preview_surf = pygame.Surface((200, 150))
        self.item_rects = {}
        self.player = PlayerWalker()  # Not added to particles!
        self.setup_item_rects()
        
        # Initial ambient
        for _ in range(15):
            self.particles.add(Particle(random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), pygame.Vector2(0, 0)))

    def setup_item_rects(self):
        y_offset = 100
        for i, item_key in enumerate(self.items):
            x = (i % 3) * 250 + 50
            y = (i // 3) * 150 + y_offset
            self.item_rects[item_key] = pygame.Rect(x, y, 200, 120)

    def handle_events(self, event):
        if event.type == pygame.MOUSEMOTION and self.state == 'store':
            self.hovered_item = None
            for item_key, rect in self.item_rects.items():
                if rect.collidepoint(event.pos) and item_key not in self.inventory:
                    self.hovered_item = item_key
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            if self.state == 'entry':
                if self.enter_button.collidepoint(mouse_pos):
                    self.transition('store')
            elif self.state == 'store':
                for item_key, rect in self.item_rects.items():
                    if rect.collidepoint(mouse_pos) and item_key not in self.inventory:
                        self.selected_item = item_key
                        self.transition('preview')
                        self.preview_timer = 60
                        return
                if self.start_button.collidepoint(mouse_pos):
                    save_inventory(self.inventory)
                    print("Starting Level 2 with power-ups:", self.inventory)
                    return 'level2'
            elif self.state == 'preview':
                if self.buy_button.collidepoint(mouse_pos):
                    item = self.items[self.selected_item]
                    if self.points >= item['cost']:
                        self.points -= item['cost']
                        self.inventory[self.selected_item] = True
                        save_inventory(self.inventory)
                        self.transition('store')
                        print(f"Equipped {self.selected_item}! Points: {self.points}")

    def transition(self, new_state):
        self.state = new_state
        self.fade_dir = 1  # Fade in
        self.fade_alpha = 0

    def update(self):
        # Walk-in
        if self.state == 'walking_in':
            self.walk_progress += 1 / WALK_DURATION
            if self.walk_progress >= 1:
                self.walk_progress = 1
                # Arrival event: Bloom glow + transition
                for _ in range(5):
                    self.particles.add(Particle(self.player.rect.centerx, self.player.rect.y, pygame.Vector2(0, -1), (255, 255, 0)))
                self.transition('entry')
            # Update player explicitly (no group arg issue)
            self.player.update(self.walk_progress)
            # Footstep trails
            if int(self.walk_progress * WALK_DURATION) % 20 == 0:
                self.particles.add(Particle(self.player.rect.centerx, self.player.rect.bottom, pygame.Vector2(0, 2), (150, 100, 50)))
        
        # Ambient
        if random.randint(1, 100) == 1 and self.state != 'preview':
            self.particles.add(Particle(random.randint(0, SCREEN_WIDTH), 0, pygame.Vector2(random.uniform(-0.5, 0.5), random.uniform(0.5, 1))))
        self.particles.update()
        
        # Fade
        if self.fade_dir != 0:
            self.fade_alpha += self.fade_dir * (255 / FADE_FRAMES)
            if self.fade_dir == 1 and self.fade_alpha >= 255:
                self.fade_alpha = 0
                self.fade_dir = 0
        
        # Preview
        if self.state == 'preview' and self.preview_timer > 0:
            self.preview_timer -= 1
            if self.preview_timer % 5 == 0 and self.items[self.selected_item]['effect'] == 'particles':
                for _ in range(3):
                    vel = pygame.Vector2(random.uniform(-2, 2), random.uniform(-3, 0))
                    self.particles.add(Particle(400, 275, vel))  # Preview offset
            if self.preview_timer == 0:
                self.transition('store')

    def draw(self, screen):
        # BG
        bg = self.market_bg if self.state in ['walking_in', 'entry', 'preview'] else self.store_bg
        screen.blit(bg, (0, 0))
        
        # Player during walk
        if self.state == 'walking_in':
            screen.blit(self.player.image, self.player.rect)
        
        # Particles
        self.particles.draw(screen)
        
        # Fade
        if self.fade_alpha > 0:
            fade_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            fade_surf.fill((0, 0, 0))
            fade_surf.set_alpha(self.fade_alpha)
            screen.blit(fade_surf, (0, 0))
            if self.fade_alpha < 255:
                self.draw_content(screen)
            return
        
        self.draw_content(screen)

    def draw_content(self, screen):
        if self.state == 'walking_in':
            title = big_font.render("Entering Fungal Bazaar...", True, (200, 255, 200))
            screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 100))
        elif self.state == 'entry':
            points_text = big_font.render(f"Spore Points: {self.points}", True, (255, 255, 0))
            screen.blit(points_text, (50, 50))
            pygame.draw.rect(screen, (0, 255, 0), self.enter_button)
            screen.blit(font.render("Enter Spore Shop", True, (0, 0, 0)), (310, 410))
        elif self.state == 'store':
            points_text = font.render(f"Spore Points: {self.points}", True, (255, 255, 0))
            screen.blit(points_text, (50, 50))
            for item_key, data in self.items.items():
                rect = self.item_rects[item_key]
                scale_factor = 1.1 if item_key == self.hovered_item else 1.0
                if scale_factor > 1:
                    glow_surf = pygame.Surface((int(rect.width * 1.2), int(rect.height * 1.2)))
                    glow_surf.fill((0, 255, 100, 100))
                    glow_rect = glow_surf.get_rect(center=rect.center)
                    screen.blit(glow_surf, glow_rect)
                card_surf = pygame.Surface((int(rect.width * scale_factor), int(rect.height * scale_factor)))
                card_surf.fill((50, 50, 50))
                scaled_rect = card_surf.get_rect(center=rect.center)
                screen.blit(card_surf, scaled_rect)
                pygame.draw.rect(screen, (100, 100, 100), rect, 2)
                pygame.draw.circle(screen, (0, 255, 0), rect.center, 20)
                desc_text = font.render(data['desc'], True, (255, 255, 255))
                screen.blit(desc_text, (rect.x, rect.y + 30))
                cost_text = font.render(f"{data['cost']} pts", True, (0, 255, 0) if self.points >= data['cost'] else (255, 0, 0))
                screen.blit(cost_text, (rect.x, rect.y + 50))
                if item_key in self.inventory:
                    owned_text = font.render("[EQUIPPED]", True, (0, 255, 0))
                    screen.blit(owned_text, (rect.x, rect.y + 70))
            pygame.draw.rect(screen, (0, 255, 0), self.start_button)
            screen.blit(font.render("Start Gauntlet", True, (0, 0, 0)), (320, 510))
            if self.hovered_item:
                tooltip = self.items[self.hovered_item]['tooltip']
                tt_surf = pygame.Surface((200, 30))
                tt_surf.fill((0, 0, 0, 200))
                tt_text = font.render(tooltip, True, (255, 255, 255))
                tt_surf.blit(tt_text, (5, 5))
                tt_rect = tt_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
                screen.blit(tt_surf, tt_rect)
        elif self.state == 'preview':
            # Redraw store basics
            points_text = font.render(f"Spore Points: {self.points}", True, (255, 255, 0))
            screen.blit(points_text, (50, 50))
            pygame.draw.rect(screen, (0, 255, 0), self.start_button)
            screen.blit(font.render("Start Gauntlet", True, (0, 0, 0)), (320, 510))
            # Selected item highlight
            if self.selected_item:
                sel_rect = self.item_rects[self.selected_item]
                pygame.draw.rect(screen, (150, 150, 150), sel_rect, 2)
                item = self.items[self.selected_item]
                screen.blit(font.render(f"{item['desc']} - Preview", True, (255, 255, 255)), (sel_rect.x, sel_rect.y))
            # Preview window
            pygame.draw.rect(screen, (0, 0, 0), (300, 200, 200, 150), 2)
            self.preview_surf.fill((50, 20, 10))
            if self.selected_item:
                self.render_preview(self.items[self.selected_item]['effect'])
            screen.blit(self.preview_surf, (300, 200))
            pygame.draw.rect(screen, (0, 255, 0), self.buy_button)
            screen.blit(font.render("Buy", True, (0, 0, 0)), (610, 510))

    def render_preview(self, effect_type):
        if effect_type == 'particles':
            pygame.draw.rect(self.preview_surf, (100, 50, 20), (50, 120, 100, 20))  # Bumper
            pygame.draw.circle(self.preview_surf, (255, 255, 0), (100, 100), 10)  # Ball
        elif effect_type == 'blurring':
            temp_surf = pygame.Surface((50, 50))
            temp_surf.fill((255, 0, 0))
            pil_img = Image.frombytes('RGB', temp_surf.get_size(), pygame.image.tostring(temp_surf, 'RGB'))
            blurred = pil_img.filter(ImageFilter.GaussianBlur(2))
            blurred_surf = pygame.image.fromstring(blurred.tobytes(), blurred.size, 'RGB')
            self.preview_surf.blit(blurred_surf, (75, 50))
            pygame.draw.circle(self.preview_surf, (0, 0, 255), (100, 75), 5)
        elif effect_type == 'smoke':
            for i in range(5):
                alpha_surf = pygame.Surface((20, 10), pygame.SRCALPHA)
                alpha_surf.fill((100, 100, 100, 50))
                self.preview_surf.blit(alpha_surf, (80 + i*5, 100 - i*10))
        elif effect_type == 'gradient':
            for r in range(0, 360, 30):
                color = (random.randint(0, 255), random.randint(100, 255), random.randint(0, 100))
                pygame.draw.circle(self.preview_surf, color, (100, 75), r//30 + 5, 2)
        elif effect_type == 'texture':
            trail_surf = pygame.Surface((100, 5))
            trail_surf.fill((0, 255, 0))
            self.preview_surf.blit(trail_surf, (50, 100))

# Main
def main():
    marketplace = Marketplace()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            next_state = marketplace.handle_events(event)
            if next_state == 'level2':
                running = False
        marketplace.update()
        screen.fill((0, 0, 0))
        marketplace.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
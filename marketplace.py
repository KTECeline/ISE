import pygame
import sys
import json
import random
import math  # For sin easing
from PIL import Image, ImageFilter  # pip install pillow
from charactermove import load_assets, Player

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
        
        # Power-ups (use images from assets/characters)
        self.items = {
            'velocity_vial': {
                'cost': 120,
                'name': 'Velocity Vial',
                'desc': 'Speed boost for fast flings.',
                'effect': 'particles',
                'tooltip': 'Speed boost for fling-heavy play.',
                'img': 'speed1.png'
            },
            'golden_gleam': {
                'cost': 150,
                'name': 'Golden Gleam',
                'desc': 'Double score.',
                'effect': 'blurring',
                'tooltip': 'Double score on combo strikes.',
                'img': 'gold1.png'
            },
            'cluster_cap': {
                'cost': 130,
                'name': 'Cluster Cap',
                'desc': 'Spawns nearby goals.',
                'effect': 'smoke',
                'tooltip': 'Spawns nearby friendly goals on use.',
                'img': 'magnet1.png'
            },
            'aura_alembic': {
                'cost': 140,
                'name': 'Aura Alembic',
                'desc': 'Auto-hit goals on touch.',
                'effect': 'gradient',
                'tooltip': 'Auto-hit goals on touch for a short time.',
                'img': 'circle1.png'
            },
        }
        
        # UI
        self.enter_button = pygame.Rect(300, 400, 200, 50)
        self.buy_button = pygame.Rect(600, 500, 100, 40)
        self.start_button = pygame.Rect(300, 500, 200, 50)
        self.preview_surf = pygame.Surface((200, 150))
        self.item_rects = {}
        # Ensure character assets are loaded (requires a video mode)
        try:
            load_assets()
        except Exception:
            # If asset loading fails, player will still be created with placeholders
            pass
        # Instantiate the character (midbottom pos). Not added to particles.
        self.player = Player(pos=(-50, SCREEN_HEIGHT - 100))
        self.setup_item_rects()
        # Load item images (after rects are known so we can size them)
        self.item_images = {}
        self.load_item_images()
        
        # Initial ambient
        for _ in range(15):
            self.particles.add(Particle(random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), pygame.Vector2(0, 0)))

    def setup_item_rects(self):
        # Improved layout with better spacing and organization
        item_w, item_h = 180, 140  # Slightly smaller for better fit
        y_offset = 120  # More space at top
        
        keys = list(self.items.keys())
        count = len(keys)
        
        # Always use 2 columns for better visual organization
        cols = 2
        rows = (count + 1) // 2  # Round up for odd numbers
        
        h_spacing = 40
        v_spacing = 30
        total_w = cols * item_w + (cols - 1) * h_spacing
        start_x = (SCREEN_WIDTH - total_w) // 2
        
        for idx, item_key in enumerate(keys):
            col = idx % cols
            row = idx // cols
            x = start_x + col * (item_w + h_spacing)
            y = y_offset + row * (item_h + v_spacing)
            self.item_rects[item_key] = pygame.Rect(x, y, item_w, item_h)

    def load_item_images(self):
        """Load and scale item images from assets/characters based on the item rect sizes."""
        for key, info in self.items.items():
            img_name = info.get('img')
            if not img_name:
                continue
            img_path = f"assets/characters/{img_name}"
            try:
                surf = pygame.image.load(img_path).convert_alpha()
                # Scale to fit nicely within the card
                rect = self.item_rects.get(key)
                if rect:
                    max_w = int(rect.width * 0.7)  # Slightly larger for better visibility
                    max_h = int(rect.height * 0.5)
                    w, h = surf.get_size()
                    # compute scale factor that fits within max_w x max_h
                    scale = min(max_w / w, max_h / h)
                    scale = min(scale, 1.0)  # Avoid upscaling
                    new_w = max(1, int(w * scale))
                    new_h = max(1, int(h * scale))
                    if (new_w, new_h) != (w, h):
                        surf = pygame.transform.smoothscale(surf, (new_w, new_h))
                self.item_images[key] = surf
            except Exception:
                # Fallback: colored surface with the item name
                fallback = pygame.Surface((100, 60), pygame.SRCALPHA)
                fallback.fill((120, 120, 120, 180))
                self.item_images[key] = fallback

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
                        self.state = 'store'  # Go back to store without transition
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
            # Update player using its update(walk_progress, screen_width) API so it animates
            try:
                self.player.update(self.walk_progress, SCREEN_WIDTH)
            except Exception:
                # Fallback: position manually if update fails
                new_x = -50 + (SCREEN_WIDTH // 2 + 50) * self.walk_progress
                bounce = math.sin(self.walk_progress * math.pi) * 5
                self.player.rect.midbottom = (int(new_x), SCREEN_HEIGHT - 100 + int(bounce))
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
        
        # Preview timer
        if self.state == 'preview' and self.preview_timer > 0:
            self.preview_timer -= 1
            if self.preview_timer % 5 == 0 and self.items[self.selected_item]['effect'] == 'particles':
                for _ in range(3):
                    vel = pygame.Vector2(random.uniform(-2, 2), random.uniform(-3, 0))
                    self.particles.add(Particle(400, 275, vel))  # Preview offset
            if self.preview_timer == 0:
                self.state = 'store'  # Simply go back to store

    def draw(self, screen):
        # Use marketplace background for all states except store
        if self.state == 'store':
            bg = self.store_bg
        else:
            bg = self.market_bg
            
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
            
            # Draw items in a clean, organized layout
            for item_key, data in self.items.items():
                rect = self.item_rects[item_key]
                
                # Draw card background
                card_color = (80, 60, 40)  # Nice earthy tone for mushrooms
                if item_key == self.hovered_item:
                    card_color = (100, 80, 60)  # Lighter when hovered
                
                pygame.draw.rect(screen, card_color, rect)
                pygame.draw.rect(screen, (120, 100, 80), rect, 2)  # Border
                
                # Draw item image centered at top of card
                img = self.item_images.get(item_key)
                if img:
                    img_rect = img.get_rect(center=(rect.centerx, rect.y + 40))
                    screen.blit(img, img_rect)
                
                # Item name
                name_text = font.render(data.get('name', item_key), True, (255, 215, 0))
                name_rect = name_text.get_rect(center=(rect.centerx, rect.y + 75))
                screen.blit(name_text, name_rect)
                
                # Description
                desc_text = font.render(data['desc'], True, (255, 255, 255))
                desc_rect = desc_text.get_rect(center=(rect.centerx, rect.y + 95))
                screen.blit(desc_text, desc_rect)
                
                # Cost
                cost_color = (0, 255, 0) if self.points >= data['cost'] else (255, 0, 0)
                cost_text = font.render(f"{data['cost']} pts", True, cost_color)
                cost_rect = cost_text.get_rect(center=(rect.centerx, rect.y + 115))
                screen.blit(cost_text, cost_rect)
                
                # Owned indicator
                if item_key in self.inventory:
                    owned_text = font.render("EQUIPPED", True, (0, 255, 0))
                    owned_rect = owned_text.get_rect(center=(rect.centerx, rect.y + 20))
                    screen.blit(owned_text, owned_rect)
            
            # Start button
            pygame.draw.rect(screen, (0, 200, 0), self.start_button)
            screen.blit(font.render("Start Gauntlet", True, (0, 0, 0)), (320, 510))
            
            # Tooltip
            if self.hovered_item:
                tooltip = self.items[self.hovered_item]['tooltip']
                tt_surf = pygame.Surface((300, 40))
                tt_surf.fill((0, 0, 0, 200))
                tt_text = font.render(tooltip, True, (255, 255, 255))
                tt_rect = tt_text.get_rect(center=(tt_surf.get_width()//2, tt_surf.get_height()//2))
                tt_surf.blit(tt_text, tt_rect)
                screen.blit(tt_surf, (SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT - 50))
                
        elif self.state == 'preview':
            # Keep the marketplace background for preview
            points_text = font.render(f"Spore Points: {self.points}", True, (255, 255, 0))
            screen.blit(points_text, (50, 50))
            
            # Semi-transparent overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))
            screen.blit(overlay, (0, 0))
            
            # Preview window
            preview_rect = pygame.Rect(200, 150, 400, 300)
            pygame.draw.rect(screen, (60, 40, 20), preview_rect)
            pygame.draw.rect(screen, (120, 100, 80), preview_rect, 3)
            
            if self.selected_item:
                item = self.items[self.selected_item]
                
                # Item name
                name_text = big_font.render(item['name'], True, (255, 215, 0))
                screen.blit(name_text, (preview_rect.centerx - name_text.get_width()//2, preview_rect.y + 20))
                
                # Item image
                img = self.item_images.get(self.selected_item)
                if img:
                    img_rect = img.get_rect(center=(preview_rect.centerx, preview_rect.y + 100))
                    screen.blit(img, img_rect)
                
                # Description
                desc_text = font.render(item['desc'], True, (255, 255, 255))
                screen.blit(desc_text, (preview_rect.centerx - desc_text.get_width()//2, preview_rect.y + 150))
                
                # Tooltip
                tooltip_text = font.render(item['tooltip'], True, (200, 200, 200))
                screen.blit(tooltip_text, (preview_rect.centerx - tooltip_text.get_width()//2, preview_rect.y + 180))
                
                # Cost
                cost_text = font.render(f"Cost: {item['cost']} points", True, (255, 255, 0))
                screen.blit(cost_text, (preview_rect.centerx - cost_text.get_width()//2, preview_rect.y + 210))
                
                # Buy button (only show if not owned and can afford)
                if self.selected_item not in self.inventory:
                    buy_color = (0, 200, 0) if self.points >= item['cost'] else (100, 100, 100)
                    pygame.draw.rect(screen, buy_color, self.buy_button)
                    screen.blit(font.render("Buy", True, (0, 0, 0)), (610, 510))
                
                # Effect preview in a small area
                effect_rect = pygame.Rect(preview_rect.centerx - 50, preview_rect.y + 240, 100, 40)
                pygame.draw.rect(screen, (40, 30, 20), effect_rect)
                effect_text = font.render("Effect Preview", True, (200, 200, 200))
                screen.blit(effect_text, (effect_rect.centerx - effect_text.get_width()//2, effect_rect.centery - effect_text.get_height()//2))
                
                # Show the actual effect
                self.render_preview(item['effect'], preview_rect.centerx, preview_rect.y + 260)
            
            # Close preview hint
            hint_text = font.render("Click anywhere to close", True, (200, 200, 200))
            screen.blit(hint_text, (SCREEN_WIDTH//2 - hint_text.get_width()//2, preview_rect.bottom + 20))

    def render_preview(self, effect_type, x, y):
        # Draw effect preview at specified position
        if effect_type == 'particles':
            pygame.draw.circle(screen, (255, 255, 0), (x, y), 8)
            for i in range(3):
                offset = (self.preview_timer // 5 + i * 3) % 10
                pygame.draw.circle(screen, (255, 200, 0), (x + offset, y - offset), 4)
        elif effect_type == 'blurring':
            pygame.draw.circle(screen, (255, 215, 0), (x, y), 10)
            for r in range(12, 20, 2):
                alpha = 100 - (r - 12) * 10
                temp_surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                pygame.draw.circle(temp_surf, (255, 215, 0, alpha), (r, r), r)
                screen.blit(temp_surf, (x - r, y - r))
        elif effect_type == 'smoke':
            for i in range(3):
                size = 5 + i * 2
                alpha = 150 - i * 50
                offset = math.sin(self.preview_timer / 10 + i) * 5
                temp_surf = pygame.Surface((size*2, size), pygame.SRCALPHA)
                pygame.draw.ellipse(temp_surf, (200, 200, 200, alpha), (0, 0, size*2, size))
                screen.blit(temp_surf, (x - size + offset, y - size//2))
        elif effect_type == 'gradient':
            for i in range(5):
                radius = 5 + i * 3
                color = (100 + i * 30, 150 + i * 20, 200)
                pygame.draw.circle(screen, color, (x, y), radius, 1)

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
            # Allow clicking anywhere to close preview
            if event.type == pygame.MOUSEBUTTONDOWN and marketplace.state == 'preview':
                marketplace.state = 'store'
                
        marketplace.update()
        screen.fill((0, 0, 0))
        marketplace.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
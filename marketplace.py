import pygame
import sys
import json
import random
import math
from PIL import Image, ImageFilter  # pip install pillow
from charactermove import load_assets, Player

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
FADE_FRAMES = 30
WALK_DURATION = 180  # Frames (~3 sec)

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Sporeball Gauntlet - Marketplace Walk-In")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 24)
big_font = pygame.font.Font(None, 36)

# Sound setup (optional)
hover_sfx = None
click_sfx = None
try:
    try:
        pygame.mixer.init()
    except Exception:
        pass
    if pygame.mixer.get_init():
        if __import__('os').path.exists('assets/sounds/Hover.mp3'):
            try:
                hover_sfx = pygame.mixer.Sound('assets/sounds/Hover.mp3')
            except Exception:
                hover_sfx = None
        if __import__('os').path.exists('assets/sounds/Click.mp3'):
            try:
                click_sfx = pygame.mixer.Sound('assets/sounds/Click.mp3')
            except Exception:
                click_sfx = None
except Exception:
    hover_sfx = click_sfx = None

# ---------- Helpers ----------
def load_inventory():
    try:
        with open('inventory.json', 'r') as f:
            data = json.load(f)
            # Normalize old boolean-style inventory to counts
            if isinstance(data, dict):
                norm = {}
                for k, v in data.items():
                    if isinstance(v, bool):
                        norm[k] = 1 if v else 0
                    elif isinstance(v, int):
                        norm[k] = v
                    else:
                        try:
                            norm[k] = int(v)
                        except Exception:
                            norm[k] = 0
                return norm
            return {}
    except FileNotFoundError:
        return {}

def save_inventory(inv):
    with open('inventory.json', 'w') as f:
        json.dump(inv, f)

# ---------- Particle ----------
class Particle(pygame.sprite.Sprite):
    def __init__(self, x, y, vel, color=(100, 255, 200)):
        super().__init__()
        self.image = pygame.Surface((3, 3), pygame.SRCALPHA)
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

# ---------- Marketplace ----------
class Marketplace:
    def __init__(self, spore_points=350):
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
        # Confirmation popup state (text, frames remaining)
        self.confirmation_text = ""
        self.confirmation_timer = 0

        # Backgrounds
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

        # Items
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
                'tooltip': 'Spawns nearby friendly goals.',
                'img': 'magnet1.png'
            },
            'aura_alembic': {
                'cost': 140,
                'name': 'Aura Alembic',
                'desc': 'Auto-hit goals on touch.',
                'effect': 'gradient',
                'tooltip': 'Auto-hit goals for a short time.',
                'img': 'circle1.png'
            },
        }

        # UI
        self.enter_button = pygame.Rect(300, 400, 200, 50)
        self.start_button = pygame.Rect(300, 500, 200, 50)
        self.item_rects = {}
        self.setup_item_rects()

        try:
            load_assets()
        except Exception:
            pass

        self.player = Player(pos=(-50, SCREEN_HEIGHT - 100))
        self.item_images = {}
        self.load_item_images()

        # Ambient particles
        for _ in range(15):
            self.particles.add(Particle(random.randint(0, SCREEN_WIDTH),
                                        random.randint(0, SCREEN_HEIGHT),
                                        pygame.Vector2(0, 0)))

    def setup_item_rects(self):
        item_w, item_h = 180, 140
        y_offset = 120
        keys = list(self.items.keys())
        cols = 2
        h_spacing, v_spacing = 40, 30
        total_w = cols * item_w + (cols - 1) * h_spacing
        start_x = (SCREEN_WIDTH - total_w) // 2
        for idx, key in enumerate(keys):
            col = idx % cols
            row = idx // cols
            x = start_x + col * (item_w + h_spacing)
            y = y_offset + row * (item_h + v_spacing)
            self.item_rects[key] = pygame.Rect(x, y, item_w, item_h)

    def load_item_images(self):
        for key, info in self.items.items():
            img_name = info.get('img')
            if not img_name:
                continue
            img_path = f"assets/characters/{img_name}"
            try:
                surf = pygame.image.load(img_path).convert_alpha()
                rect = self.item_rects.get(key)
                if rect:
                    max_w = int(rect.width * 0.7)
                    max_h = int(rect.height * 0.5)
                    w, h = surf.get_size()
                    scale = min(max_w / w, max_h / h, 1.0)
                    new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
                    surf = pygame.transform.smoothscale(surf, new_size)
                self.item_images[key] = surf
            except Exception:
                fallback = pygame.Surface((100, 60), pygame.SRCALPHA)
                fallback.fill((120, 120, 120, 180))
                self.item_images[key] = fallback

    def handle_events(self, event):
        if event.type == pygame.MOUSEMOTION and self.state == 'store':
            prev = self.hovered_item
            self.hovered_item = None
            for item_key, rect in self.item_rects.items():
                if rect.collidepoint(event.pos):
                    self.hovered_item = item_key
                    break
            # play hover sfx when newly hovered
            if self.hovered_item and self.hovered_item != prev and hover_sfx:
                try:
                    hover_sfx.play()
                except Exception:
                    pass
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            if self.state == 'entry' and self.enter_button.collidepoint(mouse_pos):
                self.transition('store')

            elif self.state == 'store':
                for item_key, rect in self.item_rects.items():
                    if rect.collidepoint(mouse_pos):
                        item = self.items[item_key]
                        # Allow multiple purchases: inventory stores counts
                        if self.points >= item['cost']:
                            self.points -= item['cost']
                            self.inventory[item_key] = self.inventory.get(item_key, 0) + 1
                            save_inventory(self.inventory)
                            # Show short confirmation popup
                            self.confirmation_text = f"Bought {item['name']}! Owned: {self.inventory[item_key]}"
                            self.confirmation_timer = 90  # frames (~1.5s at 60fps)
                            try:
                                if click_sfx:
                                    click_sfx.play()
                            except Exception:
                                pass
                            print(f"Bought {item['name']}! Remaining Points: {self.points} (Owned: {self.inventory[item_key]})")
                        else:
                            print("Not enough points!")
                if self.start_button.collidepoint(mouse_pos):
                    save_inventory(self.inventory)
                    try:
                        if click_sfx:
                            click_sfx.play()
                    except Exception:
                        pass
                    print("Starting Level 2 with:", self.inventory)
                    return ('level2', self.inventory)

    def transition(self, new_state):
        self.state = new_state
        self.fade_dir = 1
        self.fade_alpha = 0

    def update(self):
        # Walking in
        if self.state == 'walking_in':
            self.walk_progress += 1 / WALK_DURATION
            if self.walk_progress >= 1:
                self.walk_progress = 1
                for _ in range(5):
                    self.particles.add(Particle(self.player.rect.centerx, self.player.rect.y,
                                                pygame.Vector2(0, -1), (255, 255, 0)))
                self.transition('entry')
            try:
                self.player.update(self.walk_progress, SCREEN_WIDTH)
            except Exception:
                new_x = -50 + (SCREEN_WIDTH // 2 + 50) * self.walk_progress
                bounce = math.sin(self.walk_progress * math.pi) * 5
                self.player.rect.midbottom = (int(new_x), SCREEN_HEIGHT - 100 + int(bounce))
            if int(self.walk_progress * WALK_DURATION) % 20 == 0:
                self.particles.add(Particle(self.player.rect.centerx,
                                            self.player.rect.bottom,
                                            pygame.Vector2(0, 2), (150, 100, 50)))

        if random.randint(1, 100) == 1:
            self.particles.add(Particle(random.randint(0, SCREEN_WIDTH), 0,
                                        pygame.Vector2(random.uniform(-0.5, 0.5),
                                                       random.uniform(0.5, 1))))
        self.particles.update()

        if self.fade_dir != 0:
            self.fade_alpha += self.fade_dir * (255 / FADE_FRAMES)
            if self.fade_dir == 1 and self.fade_alpha >= 255:
                self.fade_alpha = 0
                self.fade_dir = 0
        # Confirmation popup countdown
        if getattr(self, 'confirmation_timer', 0) > 0:
            self.confirmation_timer -= 1

    def draw(self, screen):
        bg = self.store_bg if self.state == 'store' else self.market_bg
        screen.blit(bg, (0, 0))
        if self.state == 'walking_in':
            screen.blit(self.player.image, self.player.rect)
        self.particles.draw(screen)
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
            screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))

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
                card_color = (80, 60, 40)
                if item_key == self.hovered_item:
                    card_color = (100, 80, 60)
                pygame.draw.rect(screen, card_color, rect)
                pygame.draw.rect(screen, (120, 100, 80), rect, 2)

                img = self.item_images.get(item_key)
                if img:
                    img_rect = img.get_rect(center=(rect.centerx, rect.y + 40))
                    screen.blit(img, img_rect)

                name_text = font.render(data['name'], True, (255, 215, 0))
                name_rect = name_text.get_rect(center=(rect.centerx, rect.y + 75))
                screen.blit(name_text, name_rect)

                desc_text = font.render(data['desc'], True, (255, 255, 255))
                desc_rect = desc_text.get_rect(center=(rect.centerx, rect.y + 95))
                screen.blit(desc_text, desc_rect)

                cost_color = (0, 255, 0) if self.points >= data['cost'] else (255, 0, 0)
                cost_text = font.render(f"{data['cost']} pts", True, cost_color)
                cost_rect = cost_text.get_rect(center=(rect.centerx, rect.y + 115))
                screen.blit(cost_text, cost_rect)

                # Show owned count badge when user has one or more copies
                owned_count = self.inventory.get(item_key, 0)
                if owned_count > 0:
                    # small green badge top-right of card
                    badge_x = rect.right - 18
                    badge_y = rect.y + 14
                    pygame.draw.circle(screen, (0, 200, 0), (badge_x, badge_y), 12)
                    cnt_text = font.render(str(owned_count), True, (0, 0, 0))
                    cnt_rect = cnt_text.get_rect(center=(badge_x, badge_y))
                    screen.blit(cnt_text, cnt_rect)

            pygame.draw.rect(screen, (0, 200, 0), self.start_button)
            screen.blit(font.render("Start Level 2~", True, (0, 0, 0)), (320, 510))

            if self.hovered_item:
                tooltip = self.items[self.hovered_item]['tooltip']
                tt_surf = pygame.Surface((300, 40))
                tt_surf.fill((0, 0, 0))
                tt_text = font.render(tooltip, True, (255, 255, 255))
                tt_rect = tt_text.get_rect(center=(150, 20))
                tt_surf.blit(tt_text, tt_rect)
                screen.blit(tt_surf, (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT - 50))

            # Draw confirmation popup if any (center-bottom)
            if getattr(self, 'confirmation_timer', 0) > 0 and getattr(self, 'confirmation_text', ""):
                box_w = 520
                box_h = 40
                box_x = SCREEN_WIDTH // 2 - box_w // 2
                box_y = SCREEN_HEIGHT - 100
                popup_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
                popup_surf.fill((10, 10, 10, 200))
                txt = font.render(self.confirmation_text, True, (255, 255, 255))
                txt_rect = txt.get_rect(center=(box_w // 2, box_h // 2))
                popup_surf.blit(txt, txt_rect)
                screen.blit(popup_surf, (box_x, box_y))

# ---------- Main ----------
def main():
    marketplace = Marketplace()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            result = marketplace.handle_events(event)
            if isinstance(result, tuple) and result[0] == 'level2':
                selected_powerups = result[1]
                print("Carry these into Level 2:", selected_powerups)
                # Save inventory and exit this process with a special return code
                # so the caller (main menu) can decide to launch Level 2.
                save_inventory(selected_powerups)
                try:
                    pygame.quit()
                except Exception:
                    pass
                # Exit with code 2 to indicate "start level2"
                sys.exit(2)

        marketplace.update()
        screen.fill((0, 0, 0))
        marketplace.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()

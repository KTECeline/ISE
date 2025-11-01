import pygame
import random
import math

# Firework colors used by the firework particle effect
FIREWORK_COLORS = [(255, 40, 40), (255, 80, 60), (200, 30, 30), (255, 100, 80)]

class SporeParticle(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((4, 4), pygame.SRCALPHA)
        # bright lime-like particle
        self.image.fill((0, 255, 100))
        self.rect = self.image.get_rect(center=(x, y))
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(3, 6)
        self.vel = [math.cos(angle) * speed, math.sin(angle) * speed]
        self.lifetime = 30

    def update(self):
        self.rect.x += self.vel[0]
        self.rect.y += self.vel[1]
        self.vel[1] += 0.2  # Gravity
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()


class FireworkParticle(pygame.sprite.Sprite):
    """A bright firework-style spark that fades out."""
    def __init__(self, x, y, color=None):
        super().__init__()
        self.radius = random.randint(3, 6)
        self.color = color if color is not None else random.choice(FIREWORK_COLORS)
        size = max(8, self.radius * 3)
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        # draw a filled circle plus a faint outer ring for glow
        pygame.draw.circle(self.image, self.color + (255,), (size//2, size//2), self.radius)
        try:
            glow_color = (self.color[0], self.color[1], self.color[2], 80)
            pygame.draw.circle(self.image, glow_color, (size//2, size//2), int(self.radius * 1.8))
        except Exception:
            pass
        self.orig_image = self.image.copy()
        self.rect = self.image.get_rect(center=(int(x), int(y)))
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(3.0, 9.0)
        self.vel = [math.cos(angle) * speed, math.sin(angle) * speed]
        self.lifetime = random.randint(45, 90)
        self.age = 0

    def update(self):
        self.age += 1
        self.rect.x += self.vel[0]
        self.rect.y += self.vel[1]
        self.vel[1] += 0.08
        if self.age >= self.lifetime:
            self.kill()
            return
        alpha = int(255 * (1.0 - (self.age / self.lifetime)))
        if alpha < 0:
            alpha = 0
        self.image = self.orig_image.copy()
        try:
            self.image.set_alpha(alpha)
        except Exception:
            pass

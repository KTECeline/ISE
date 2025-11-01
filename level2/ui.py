import pygame
import math

class ScorePopup:
    def __init__(self, x, y, points, lifetime=60):
        self.x = x
        self.y = y
        self.points = points
        self.lifetime = lifetime
        self.start_y = y

    def update(self):
        self.y -= 1
        self.lifetime -= 1
        return self.lifetime > 0

    # Draw now takes a font parameter to avoid depending on module globals
    def draw(self, screen, cam_x, cam_y, font):
        if self.lifetime <= 0:
            return
        screen_x = int(self.x - cam_x)
        screen_y = int(self.y - cam_y)
        alpha = int(255 * (self.lifetime / float(max(1, self.start_y if isinstance(self.start_y, int) else 60))))
        try:
            text = font.render(f"+{self.points}", True, (255, 255, 0))
            text.set_alpha(alpha)
            screen.blit(text, (screen_x - 10, screen_y))
        except Exception:
            pass


def draw_minimap(screen, player_pos, map_image, mushroom_ball, cam_x, cam_y,
                 world_width, world_height, minimap_size, minimap_zoom, goals=None):
    """Draw a small minimap in the top-right showing a cropped region centered on the player.
    The function is parameterized so it does not rely on module globals.
    """
    MINIMAP_SIZE = minimap_size
    MINIMAP_ZOOM = minimap_zoom
    minimap = pygame.Surface(MINIMAP_SIZE)

    zoom = max(1.0, MINIMAP_ZOOM)
    crop_w = max(1, int(world_width / zoom))
    crop_h = max(1, int(world_height / zoom))
    center_x = int(player_pos[0])
    center_y = int(player_pos[1])
    crop_x = max(0, min(center_x - crop_w // 2, world_width - crop_w))
    crop_y = max(0, min(center_y - crop_h // 2, world_height - crop_h))
    crop_rect = pygame.Rect(crop_x, crop_y, crop_w, crop_h)
    try:
        cropped = map_image.subsurface(crop_rect).copy()
    except Exception:
        cropped = map_image.copy()
    scaled_map = pygame.transform.scale(cropped, MINIMAP_SIZE)
    minimap.blit(scaled_map, (0, 0))

    pygame.draw.rect(minimap, (255, 255, 255), (0, 0, MINIMAP_SIZE[0], MINIMAP_SIZE[1]), 1)

    scale_x = MINIMAP_SIZE[0] / crop_w
    scale_y = MINIMAP_SIZE[1] / crop_h
    player_map_x = int((player_pos[0] - crop_x) * scale_x)
    player_map_y = int((player_pos[1] - crop_y) * scale_y)
    pygame.draw.circle(minimap, (0, 0, 255), (player_map_x, player_map_y), 3)

    # Goals list passed in explicitly (safer than relying on global state)
    if goals:
        for goal in goals:
            try:
                goal_map_x = int((goal[0] - crop_x) * scale_x)
                goal_map_y = int((goal[1] - crop_y) * scale_y)
                pygame.draw.circle(minimap, (0, 255, 0), (goal_map_x, goal_map_y), 3)
            except Exception:
                pass

    if getattr(mushroom_ball, 'active', False):
        ball_map_x = int((mushroom_ball.pos[0] - crop_x) * scale_x)
        ball_map_y = int((mushroom_ball.pos[1] - crop_y) * scale_y)
        pygame.draw.circle(minimap, (255, 255, 0), (ball_map_x, ball_map_y), 2)

    cam_map_x = int((cam_x - crop_x) * scale_x)
    cam_map_y = int((cam_y - crop_y) * scale_y)
    cam_map_w = int(pygame.display.get_surface().get_width() * scale_x)
    cam_map_h = int(pygame.display.get_surface().get_height() * scale_y)
    pygame.draw.rect(minimap, (255, 255, 255), (cam_map_x, cam_map_y, cam_map_w, cam_map_h), 1)

    screen.blit(minimap, (pygame.display.get_surface().get_width() - MINIMAP_SIZE[0] - 10, 10))

    label_font = pygame.font.SysFont(None, 18)
    label = label_font.render("Minimap: Blue=You, Green=Goals, Yellow=Ball", True, (255, 255, 255))
    screen.blit(label, (pygame.display.get_surface().get_width() - MINIMAP_SIZE[0] - 10, 10 + MINIMAP_SIZE[1] + 5))

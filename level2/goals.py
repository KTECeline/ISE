import pygame
import random
import math
from level2.goal import walking_frames_right, hit_frames_right

# Module-level storage for goals and sprites
goals = []  # list of [x,y]
goal_sprites = pygame.sprite.Group()
goal_sprite_map = {}  # (x,y) -> GoalSprite

# Defaults that can be overridden by caller via generate_goals args
HIT_DISPLAY_FRAMES = 120
SPRITE_SCALE = 1.8


class GoalSprite(pygame.sprite.Sprite):
    def __init__(self, world_x, world_y, index=0, sprite_scale=SPRITE_SCALE, hit_display_frames=HIT_DISPLAY_FRAMES):
        super().__init__()
        self.world_x = int(world_x)
        self.world_y = int(world_y)
        self.index = index
        self.sprite_scale = sprite_scale
        self.hit_display_frames = hit_display_frames

        # Prepare scaled frames
        self.walkingFrames = []
        self.hitFrames = []
        try:
            for f in walking_frames_right:
                nw = max(1, int(f.get_width() * self.sprite_scale))
                nh = max(1, int(f.get_height() * self.sprite_scale))
                self.walkingFrames.append(pygame.transform.smoothscale(f, (nw, nh)))
            for f in hit_frames_right:
                nw = max(1, int(f.get_width() * self.sprite_scale))
                nh = max(1, int(f.get_height() * self.sprite_scale))
                self.hitFrames.append(pygame.transform.smoothscale(f, (nw, nh)))
        except Exception:
            # Fallback to empty lists (caller will handle drawing)
            self.walkingFrames = []
            self.hitFrames = []

        self.frame_index = 0.0
        self.hit = False
        self.remove_timer = None

        if self.walkingFrames:
            self.image = self.walkingFrames[0]
        else:
            # fallback surface
            s = max(8, int(30 * self.sprite_scale))
            surf = pygame.Surface((s, s), pygame.SRCALPHA)
            pygame.draw.circle(surf, (0, 255, 0), (s//2, s//2), s//2)
            self.image = surf
        self.rect = self.image.get_rect()

        # Precompute glow image
        try:
            img_w, img_h = self.image.get_size()
            glow_w = int(max(img_w, img_h) * 1.6)
            glow_h = int(max(img_w, img_h) * 1.6)
            glow_surf = pygame.Surface((glow_w, glow_h), pygame.SRCALPHA)
            center = (glow_w // 2, glow_h // 2)
            max_radius = int(min(glow_w, glow_h) // 2)
            steps = 6
            base_color = (255, 255, 255)
            for i in range(steps, 0, -1):
                frac = i / float(steps)
                radius = int(max_radius * frac)
                alpha = int(80 * (frac ** 1.2))
                color = (base_color[0], base_color[1], base_color[2], alpha)
                pygame.draw.circle(glow_surf, color, center, radius)
            self.glow_image = glow_surf
        except Exception:
            self.glow_image = None

    def step(self):
        if not self.hit:
            if self.walkingFrames:
                self.frame_index = (self.frame_index + 0.2) % len(self.walkingFrames)
                self.image = self.walkingFrames[int(self.frame_index)]
        else:
            if self.hitFrames:
                self.frame_index = (self.frame_index + 0.2) % len(self.hitFrames)
                self.image = self.hitFrames[int(self.frame_index)]
            if self.remove_timer is not None:
                self.remove_timer -= 1
                if self.remove_timer <= 0:
                    try:
                        self.kill()
                    except Exception:
                        pass

    def sync_to_camera(self, cam_x, cam_y):
        screen_x = int(self.world_x - cam_x)
        screen_y = int(self.world_y - cam_y)
        self.rect = self.image.get_rect(midbottom=(screen_x, screen_y))

    def mark_hit(self):
        self.hit = True
        self.remove_timer = self.hit_display_frames


def generate_goals(world_width, world_height, forbidden_y_max, num_goals, check_collision_fn,
                   goal_radius=30, sprite_scale=SPRITE_SCALE):
    """Populate module-level goals, goal_sprites, and goal_sprite_map.

    Parameters:
    - world_width, world_height: map size
    - forbidden_y_max: minimum y for goals (goals y > forbidden_y_max)
    - num_goals: target number of goals
    - check_collision_fn: callable(x,y,r) -> bool to test valid placement
    - goal_radius: radius to avoid collisions
    - sprite_scale: scale for sprite visuals
    """
    global goals, goal_sprites, goal_sprite_map
    # Mutate the existing collections in-place instead of rebinding names.
    # This preserves references held by other modules that imported these
    # objects (e.g., `from level2.goals import goals`).
    goals.clear()
    goal_sprites.empty()
    goal_sprite_map.clear()
    attempts = 0
    min_y = forbidden_y_max + 1
    index = 0
    while len(goals) < num_goals and attempts < 500:
        goal_x = random.randint(100, world_width - 100)
        goal_y = random.randint(min_y, world_height - 100)
        if not check_collision_fn(goal_x, goal_y, goal_radius):
            goals.append([goal_x, goal_y])
            gs = GoalSprite(goal_x, goal_y, index=index, sprite_scale=sprite_scale)
            goal_sprites.add(gs)
            goal_sprite_map[(int(goal_x), int(goal_y))] = gs
            index += 1
        attempts += 1
    return goals


def pop_goals_hit_by_point(point, point_radius, goal_radius, aura_extra=0):
    """Remove goals hit by a point (e.g., ball) and return list of removed coords.

    - point: (x,y)
    - point_radius: radius of the hitter (ball radius)
    - goal_radius: radius of goals (for collision test)
    - aura_extra: additional padding to goal radius (for aura-powered hits)
    """
    global goals, goal_sprite_map
    removed = []
    for i in range(len(goals)-1, -1, -1):
        gx, gy = goals[i][0], goals[i][1]
        dx = point[0] - gx
        dy = point[1] - gy
        dist = math.hypot(dx, dy)
        effective_goal_radius = goal_radius + aura_extra
        if dist < effective_goal_radius + point_radius:
            removed.append((gx, gy))
            del goals[i]
            gs = goal_sprite_map.pop((int(gx), int(gy)), None)
            if gs:
                try:
                    gs.mark_hit()
                except Exception:
                    pass
    return removed


def pop_goals_in_radius(center, aura_radius, goal_radius):
    """Remove goals within `aura_radius` of `center` and return list of removed coords."""
    global goals, goal_sprite_map
    removed = []
    for i in range(len(goals)-1, -1, -1):
        gx, gy = goals[i][0], goals[i][1]
        dx = center[0] - gx
        dy = center[1] - gy
        dist = math.hypot(dx, dy)
        if dist < aura_radius:
            removed.append((gx, gy))
            del goals[i]
            gs = goal_sprite_map.pop((int(gx), int(gy)), None)
            if gs:
                try:
                    gs.mark_hit()
                except Exception:
                    pass
    return removed

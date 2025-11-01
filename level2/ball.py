import pygame
import math
import random

class MushroomBall:
    """MushroomBall moved to its own module.

    This class is intentionally parameterized to avoid circular imports with the
    main level module. Pass in frames and small callables for runtime state.
    """
    def __init__(
        self,
        initial_pos,
        radius=15,
        frames=None,
        get_shoot_speed_multiplier=lambda: 1.0,
        check_collision_fn=lambda x,y,r: False,
        BALL_SPEED=10,
        BALL_FRICTION=0.98,
        MUSHROOM_ANIM_SCALE=2.0,
        ROLL_VELOCITY_THRESHOLD=1.2,
        ROLL_FRAME_SPEED=0.5,
        SQUISH_DURATION=10,
        BALL_TRAIL_MAX=12,
        BALL_TRAIL_ALPHA=160,
        WORLD_WIDTH=2000,
        WORLD_HEIGHT=2000,
    ):
        self.pos = list(initial_pos)
        self.vel = [0.0, 0.0]
        self.radius = radius
        self.active = False
        self.stopped = True
        self.hit_this_shot = False

        # Provided resources / helpers
        self.frames = list(frames) if frames else []
        self.get_shoot_speed_multiplier = get_shoot_speed_multiplier
        self.check_collision_fn = check_collision_fn

        # animation / physics constants
        self.BALL_SPEED = BALL_SPEED
        self.BALL_FRICTION = BALL_FRICTION
        self.MUSHROOM_ANIM_SCALE = MUSHROOM_ANIM_SCALE
        self.ROLL_VELOCITY_THRESHOLD = ROLL_VELOCITY_THRESHOLD
        self.ROLL_FRAME_SPEED = ROLL_FRAME_SPEED
        self.SQUISH_DURATION = SQUISH_DURATION
        self.BALL_TRAIL_MAX = BALL_TRAIL_MAX
        self.BALL_TRAIL_ALPHA = BALL_TRAIL_ALPHA
        self.WORLD_WIDTH = WORLD_WIDTH
        self.WORLD_HEIGHT = WORLD_HEIGHT

        # rolling / squish state
        self.frame_index = 0.0
        self.roll_frames = self.frames if self.frames else []
        self.squish_frames = []
        self.squish_timer = 0
        self.squish_phase = 0

        if self.frames:
            try:
                base = self.frames[0]
                bw, bh = base.get_size()
                key_scales = [(0.9, 1.1), (1.0, 1.0), (1.2, 0.8), (1.0, 1.0)]
                for sx, sy in key_scales:
                    nw = max(1, int(bw * sx))
                    nh = max(1, int(bh * sy))
                    try:
                        kf = pygame.transform.smoothscale(base, (nw, nh))
                    except Exception:
                        kf = base.copy()
                    self.squish_frames.append(kf)
            except Exception:
                self.squish_frames = []

        self.trail = []  # list of (surface, (world_x, world_y))

    def shoot(self, start_pos, target_pos):
        dx = target_pos[0] - start_pos[0]
        dy = target_pos[1] - start_pos[1]
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            sp = self.BALL_SPEED * (self.get_shoot_speed_multiplier() if self.get_shoot_speed_multiplier else 1.0)
            self.vel = [ (dx / dist) * sp, (dy / dist) * sp ]
        self.pos = list(start_pos)
        self.active = True
        self.stopped = False
        self.hit_this_shot = False

    def update(self):
        if not self.active:
            return
        self.pos[0] += self.vel[0]
        self.pos[1] += self.vel[1]
        # friction
        self.vel[0] *= self.BALL_FRICTION
        self.vel[1] *= self.BALL_FRICTION
        if abs(self.vel[0]) < 0.1:
            self.vel[0] = 0
        if abs(self.vel[1]) < 0.1:
            self.vel[1] = 0
        if self.vel[0] == 0 and self.vel[1] == 0:
            self.stopped = True

        # bounds
        self.pos[0] = max(self.radius, min(self.pos[0], self.WORLD_WIDTH - self.radius))
        self.pos[1] = max(self.radius, min(self.pos[1], self.WORLD_HEIGHT - self.radius))

        # collision check
        try:
            if self.check_collision_fn(self.pos[0], self.pos[1], self.radius):
                self.vel[0] *= -0.7
                self.vel[1] *= -0.7
                self.pos[0] += self.vel[0] * 2
                self.pos[1] += self.vel[1] * 2
                if self.squish_frames:
                    self.squish_timer = self.SQUISH_DURATION
                    if abs(self.vel[1]) > abs(self.vel[0]):
                        self.squish_phase = 0
                    else:
                        self.squish_phase = 2
        except Exception:
            pass

    def draw(self, screen, cam_x, cam_y):
        if not self.active:
            return
        screen_x = int(self.pos[0] - cam_x)
        screen_y = int(self.pos[1] - cam_y)
        frame_s = None
        try:
            if self.frames:
                speed = math.hypot(self.vel[0], self.vel[1])
                if self.squish_timer > 0 and self.squish_frames:
                    t = (self.SQUISH_DURATION - self.squish_timer) / float(max(1, self.SQUISH_DURATION))
                    idx = int(t * len(self.squish_frames))
                    idx = min(idx, len(self.squish_frames) - 1)
                    frame = self.squish_frames[(self.squish_phase + idx) % len(self.squish_frames)]
                    self.squish_timer -= 1
                    base_size = int(self.radius * 2)
                    fw = max(1, int(base_size * self.MUSHROOM_ANIM_SCALE))
                    fh = max(1, int(base_size * self.MUSHROOM_ANIM_SCALE))
                    frame_s = pygame.transform.smoothscale(frame, (fw, fh))
                elif speed > self.ROLL_VELOCITY_THRESHOLD and self.roll_frames:
                    self.frame_index = (self.frame_index + self.ROLL_FRAME_SPEED * (speed / 5.0)) % len(self.roll_frames)
                    frame = self.roll_frames[int(self.frame_index)]
                    angle = -math.degrees(math.atan2(self.vel[1], self.vel[0])) if speed > 0 else 0
                    base_size = int(self.radius * 2)
                    fw = max(1, int(base_size * self.MUSHROOM_ANIM_SCALE))
                    fh = max(1, int(base_size * self.MUSHROOM_ANIM_SCALE))
                    frame_s = pygame.transform.smoothscale(frame, (fw, fh))
                    try:
                        frame_s = pygame.transform.rotate(frame_s, angle)
                    except Exception:
                        pass
                else:
                    self.frame_index = (self.frame_index + 0.2) % len(self.frames)
                    frame = self.frames[int(self.frame_index)]
                    base_size = int(self.radius * 2)
                    fw = max(1, int(base_size * self.MUSHROOM_ANIM_SCALE))
                    fh = max(1, int(base_size * self.MUSHROOM_ANIM_SCALE))
                    frame_s = pygame.transform.smoothscale(frame, (fw, fh))
        except Exception:
            frame_s = None

        if frame_s is None:
            surf = pygame.Surface((self.radius * 2 + 6, self.radius * 2 + 6), pygame.SRCALPHA)
            pygame.draw.circle(surf, (139, 69, 19), (surf.get_width()//2, surf.get_height()//2 - 2), self.radius)
            pygame.draw.rect(surf, (255, 255, 255), (surf.get_width()//2 - 5, surf.get_height()//2, 10, 10))
            for i in range(3):
                ox = surf.get_width()//2 + (i-1) * 6
                oy = surf.get_height()//2 + 2
                pygame.draw.circle(surf, (0, 255, 0), (ox + random.randint(-2,2), oy + random.randint(-2,2)), 2)
            frame_s = surf

        # draw trail
        if self.trail:
            n = len(self.trail)
            for idx, (tsurf, (wx, wy)) in enumerate(self.trail):
                try:
                    alpha = int(self.BALL_TRAIL_ALPHA * ((idx + 1) / float(n)))
                    draw_surf = tsurf.copy()
                    draw_surf.set_alpha(alpha)
                    screen_x_t = int(wx - cam_x)
                    screen_y_t = int(wy - cam_y)
                    rect = draw_surf.get_rect(center=(screen_x_t, screen_y_t))
                    screen.blit(draw_surf, rect)
                except Exception:
                    pass

        rect = frame_s.get_rect(center=(screen_x, screen_y))
        screen.blit(frame_s, rect)

        try:
            snap = frame_s.copy()
            self.trail.append((snap, (self.pos[0], self.pos[1])))
            if len(self.trail) > self.BALL_TRAIL_MAX:
                del self.trail[0]
        except Exception:
            pass

    def reset(self, player_pos):
        self.pos = list(player_pos)
        self.vel = [0.0, 0.0]
        self.active = False
        self.stopped = True
        self.hit_this_shot = False

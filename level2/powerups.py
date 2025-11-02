import pygame
import random
import json
import math
from .goals import generate_goals
from .particles import SporeParticle

# Powerup configuration
POWERUP_INFO = {
    'velocity_vial': {'img': 'speed1.png', 'name': 'Velocity Vial'},
    'golden_gleam': {'img': 'gold1.png', 'name': 'Golden Gleam'},
    'cluster_cap': {'img': 'magnet1.png', 'name': 'Cluster Cap'},
    'aura_alembic': {'img': 'circle1.png', 'name': 'Aura Alembic'},
}

def load_inventory():
    try:
        with open('inventory.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_inventory(inv):
    try:
        with open('inventory.json', 'w') as f:
            json.dump(inv, f)
    except Exception:
        pass

def load_powerup_images():
    """Load and scale powerup icons."""
    powerup_images = {}
    for key, info in POWERUP_INFO.items():
        path = f"assets/characters/{info['img']}"
        try:
            surf = pygame.image.load(path).convert_alpha()
            surf = pygame.transform.smoothscale(surf, (48, 48))
        except Exception:
            surf = pygame.Surface((48, 48), pygame.SRCALPHA)
            surf.fill((100, 100, 100, 200))
        powerup_images[key] = surf
    return powerup_images

def activate_powerup(key, inventory, powerup_timers, POWERUP_DURATION_FRAMES, POWERUP_DURATIONS,
                    temp_goal_timers, goals, goal_sprites, goal_sprite_map, 
                    mushroom_ball, player_pos, check_collision_fn, 
                    GOAL_RADIUS, WORLD_WIDTH, WORLD_HEIGHT, FORBIDDEN_Y_MAX, particles):
    """Activate a powerup and apply its immediate effects."""
    if inventory.get(key, 0) <= 0 or powerup_timers.get(key, 0) > 0:
        return False
    
    # Consume one from inventory
    inventory[key] = inventory.get(key, 0) - 1
    save_inventory(inventory)
    
    # Activate effect using per-powerup override if present
    powerup_timers[key] = POWERUP_DURATIONS.get(key, POWERUP_DURATION_FRAMES)
    
    # Apply immediate behaviors if needed
    if key == 'cluster_cap':
        _activate_cluster_cap(powerup_timers, temp_goal_timers, goals, goal_sprites, goal_sprite_map,
                             mushroom_ball, player_pos, check_collision_fn, GOAL_RADIUS,
                             WORLD_WIDTH, WORLD_HEIGHT, FORBIDDEN_Y_MAX, particles, 
                             POWERUP_DURATION_FRAMES)
    
    print(f"Used {key}; remaining: {inventory.get(key,0)}")
    return True

def _activate_cluster_cap(powerup_timers, temp_goal_timers, goals, goal_sprites, goal_sprite_map,
                         mushroom_ball, player_pos, check_collision_fn, GOAL_RADIUS,
                         WORLD_WIDTH, WORLD_HEIGHT, FORBIDDEN_Y_MAX, particles, duration):
    """Spawn temporary goals for cluster cap powerup."""
    spawned = 0
    # Choose center: prefer ball if active, otherwise player
    if mushroom_ball and getattr(mushroom_ball, 'pos', None) and mushroom_ball.active:
        center_x, center_y = int(mushroom_ball.pos[0]), int(mushroom_ball.pos[1])
    else:
        center_x, center_y = int(player_pos[0]), int(player_pos[1])
    
    # Try to place exactly 3 goals
    for goal_i in range(3):
        placed = False
        for _try in range(12):
            gx = center_x + random.randint(-100, 100)
            gy = center_y + random.randint(-100, 100)
            gx = max(GOAL_RADIUS, min(WORLD_WIDTH - GOAL_RADIUS, gx))
            gy = max(GOAL_RADIUS, min(WORLD_HEIGHT - GOAL_RADIUS, gy))
            
            if gy > FORBIDDEN_Y_MAX and not check_collision_fn(gx, gy, GOAL_RADIUS):
                goals.append([gx, gy])
                from .goals import GoalSprite
                gs = GoalSprite(gx, gy, index=len(goals))
                goal_sprites.add(gs)
                goal_sprite_map[(int(gx), int(gy))] = gs
                temp_goal_timers[(int(gx), int(gy))] = duration
                
                # Spawn particles so player notices
                for _p in range(10):
                    particles.add(SporeParticle(gx, gy))
                spawned += 1
                placed = True
                break
    
    # Activate full-screen overlay
    globals()['cluster_overlay_timer'] = duration
    
    if spawned == 0:
        print("Cluster cap used but no safe spawn locations found near", center_x, center_y)
    else:
        print(f"Cluster cap spawned {spawned} temporary goals near ({center_x},{center_y})")

def update_powerup_timers(powerup_timers, temp_goal_timers, goals, goal_sprite_map, goal_sprites):
    """Update powerup timers and remove expired temporary goals."""
    # Decrement powerup timers
    for k in list(powerup_timers.keys()):
        if powerup_timers[k] > 0:
            powerup_timers[k] -= 1
    
    # Decrement temporary goal timers and remove expired ones
    for key in list(temp_goal_timers.keys()):
        temp_goal_timers[key] -= 1
        if temp_goal_timers[key] <= 0:
            gx, gy = key
            # Remove matching goal from goals list
            goals[:] = [g for g in goals if not (int(g[0]) == gx and int(g[1]) == gy)]
            gs = goal_sprite_map.pop((gx, gy), None)
            if gs:
                try:
                    gs.kill()
                except Exception:
                    pass
            del temp_goal_timers[key]

def get_powerup_effects(powerup_timers, POWERUP_DURATIONS, POWERUP_DURATION_FRAMES):
    """Get current powerup effects (speed multipliers, etc.)."""
    player_speed_multiplier = 1.0
    shoot_speed_multiplier = 1.0
    
    if powerup_timers.get('velocity_vial', 0) > 0:
        player_speed_multiplier = 2.5
        shoot_speed_multiplier = 1.6
    
    return player_speed_multiplier, shoot_speed_multiplier

def draw_powerup_ui(screen, powerup_slots, powerup_images, powerup_timers, font, FPS):
    """Draw powerup UI at bottom-left."""
    for slot in powerup_slots:
        r = slot['rect']
        # Background card
        pygame.draw.rect(screen, (40, 40, 40), r)
        pygame.draw.rect(screen, (120, 120, 120), r, 2)
        
        # Icon
        key = slot['key']
        img = powerup_images.get(key)
        if img:
            img_r = img.get_rect(center=(r.x + 28, r.y + 28))
            screen.blit(img, img_r)
        
        # Count badge
        cnt = slot['count']
        badge_pos = (r.right - 10, r.y + 10)
        pygame.draw.circle(screen, (0, 200, 0), badge_pos, 10)
        ct = font.render(str(cnt), True, (0, 0, 0))
        ct_r = ct.get_rect(center=badge_pos)
        screen.blit(ct, ct_r)
        
        # Active timer indicator
        t = powerup_timers.get(key, 0)
        if t > 0:
            secs = int(math.ceil(t / float(FPS)))
            sec_text = font.render(f"{secs}s", True, (255, 255, 0))
            st_r = sec_text.get_rect(center=(r.centerx, r.y - 10))
            screen.blit(sec_text, st_r)
import pygame
import random

def update_camera(player_pos, mushroom_ball, cam_x, cam_y, SCREEN_WIDTH, SCREEN_HEIGHT, 
                 WORLD_WIDTH, WORLD_HEIGHT, screen_shake_timer, SCREEN_SHAKE_FRAMES):
    """Update camera to center on player, but lerp toward ball if active."""
    cam_target_x, cam_target_y = cam_x, cam_y
    
    # Target: Midpoint between player and ball if active
    if mushroom_ball and getattr(mushroom_ball, 'active', False):
        mid_x = (player_pos[0] + mushroom_ball.pos[0]) / 2
        mid_y = (player_pos[1] + mushroom_ball.pos[1]) / 2
        cam_target_x = mid_x - SCREEN_WIDTH // 2
        cam_target_y = mid_y - SCREEN_HEIGHT // 2
    else:
        cam_target_x = player_pos[0] - SCREEN_WIDTH // 2
        cam_target_y = player_pos[1] - SCREEN_HEIGHT // 2
    
    # Lerp camera (smooth follow)
    lerp_speed = 0.1
    cam_x += (cam_target_x - cam_x) * lerp_speed
    cam_y += (cam_target_y - cam_y) * lerp_speed
    
    # Clamp camera so edges don't show outside world
    cam_x = max(0, min(cam_x, WORLD_WIDTH - SCREEN_WIDTH))
    cam_y = max(0, min(cam_y, WORLD_HEIGHT - SCREEN_HEIGHT))
    
    # Apply screen shake if active
    if screen_shake_timer and screen_shake_timer > 0:
        frac = screen_shake_timer / float(max(1, SCREEN_SHAKE_FRAMES))
        shake_amount = 6 * frac
        sx = random.uniform(-shake_amount, shake_amount)
        sy = random.uniform(-shake_amount, shake_amount)
        cam_x += sx
        cam_y += sy
        screen_shake_timer -= 1
    
    return cam_x, cam_y, screen_shake_timer

def ease_in_out_cubic(t: float) -> float:
    """Smooth cubic ease-in/out. t in [0,1]."""
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - pow(-2 * t + 2, 3) / 2
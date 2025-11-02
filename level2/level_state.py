import pygame

def reset_level(player_max_health, WORLD_WIDTH, WORLD_HEIGHT, FORBIDDEN_Y_MAX, 
               NUM_GOALS, check_collision, GOAL_RADIUS, generate_goals):
    """Reset the level to initial state."""
    from . import goals, goal_sprites, goal_sprite_map
    from .powerups import powerup_timers, temp_goal_timers
    
    # Basic state
    player_pos = [730.0, 8230.0]
    player_health = player_max_health
    score = 0
    streak = 0
    
    # Clear effects
    particles = pygame.sprite.Group()
    enemy_projectiles = pygame.sprite.Group()
    popups = []
    
    # Reset powerups
    for k in powerup_timers.keys():
        powerup_timers[k] = 0
    temp_goal_timers.clear()
    cluster_overlay_timer = 0
    
    # Clear and re-generate goals
    goals[:] = []
    for gs in list(goal_sprites):
        try:
            gs.kill()
        except Exception:
            pass
    goal_sprites.empty()
    goal_sprite_map.clear()
    
    generate_goals(WORLD_WIDTH, WORLD_HEIGHT, FORBIDDEN_Y_MAX, NUM_GOALS, 
                  check_collision, goal_radius=GOAL_RADIUS, sprite_scale=1.8)
    
    # Reset ball
    mushroom_ball.reset(player_pos)
    mushroom_ball.active = False
    mushroom_ball.stopped = True
    mushroom_ball.return_timer = 0
    mushroom_ball.hit_this_shot = False
    
    # Reset flow flags
    level_cleared = False
    transporting = False
    post_transport = False
    player_locked = False
    chest_opened = False
    prev_chest_opened = False
    level_failed = False
    level_failed_start = 0
    
    # Reset runtime multipliers
    player_speed_multiplier = 1.0
    shoot_speed_multiplier = 1.0
    
    return {
        'player_pos': player_pos,
        'player_health': player_health,
        'score': score,
        'streak': streak,
        'particles': particles,
        'enemy_projectiles': enemy_projectiles,
        'popups': popups,
        'level_cleared': level_cleared,
        'transporting': transporting,
        'post_transport': post_transport,
        'player_locked': player_locked,
        'chest_opened': chest_opened,
        'prev_chest_opened': prev_chest_opened,
        'level_failed': level_failed,
        'level_failed_start': level_failed_start,
        'player_speed_multiplier': player_speed_multiplier,
        'shoot_speed_multiplier': shoot_speed_multiplier,
        'cluster_overlay_timer': cluster_overlay_timer
    }

def handle_transport_sequence(level_cleared, level_cleared_start, transporting, 
                            post_transport, player_locked, player_pos, 
                            TRANSPORT_START_POS, TRANSPORT_END_POS, 
                            TRANSPORT_DURATION_MS, tunnel_sound, tunnel_is_music):
    """Handle the level completion transport sequence."""
    from .camera import ease_in_out_cubic
    
    if level_cleared and (not transporting) and (not post_transport):
        now = pygame.time.get_ticks()
        if now - level_cleared_start >= 1500:  # LEVEL_CLEARED_DISPLAY_MS
            player_pos[0] = TRANSPORT_START_POS[0]
            player_pos[1] = TRANSPORT_START_POS[1]
            transporting = True
            transport_start_ticks = pygame.time.get_ticks()
            player_locked = True
            
            # Play tunnel sound
            try:
                if tunnel_sound:
                    if tunnel_is_music:
                        # tunnel_sound may be a filepath (string) or already-loaded music.
                        # Attempt to (re)load if a path was passed, then play on loop.
                        try:
                            if isinstance(tunnel_sound, str):
                                pygame.mixer.music.load(tunnel_sound)
                        except Exception:
                            pass
                        try:
                            pygame.mixer.music.set_volume(0.8)
                        except Exception:
                            pass
                        try:
                            pygame.mixer.music.play(-1)
                        except Exception:
                            pass
                    else:
                        # For Sound objects, set a sensible volume and loop.
                        try:
                            tunnel_sound.set_volume(0.8)
                        except Exception:
                            pass
                        try:
                            tunnel_sound.play(-1)
                        except Exception:
                            pass
            except Exception:
                pass
            return True, transport_start_ticks
    
    return False, 0

def update_transport(transporting, transport_start_ticks, player_pos, 
                    TRANSPORT_START_POS, TRANSPORT_END_POS, TRANSPORT_DURATION_MS,
                    tunnel_sound, tunnel_is_music):
    """Update transport animation."""
    from .camera import ease_in_out_cubic
    
    if not transporting:
        return False, False, False  # transporting, post_transport, player_locked
    
    now = pygame.time.get_ticks()
    elapsed = now - transport_start_ticks
    t_raw = min(1.0, elapsed / float(TRANSPORT_DURATION_MS))
    t = ease_in_out_cubic(t_raw)
    
    # Lock X to transport start X and ease Y from start -> end
    player_pos[0] = TRANSPORT_START_POS[0]
    player_pos[1] = TRANSPORT_START_POS[1] + (TRANSPORT_END_POS[1] - TRANSPORT_START_POS[1]) * t
    
    # Once transport finishes
    if t_raw >= 1.0:
        transporting = False
        post_transport = True
        player_locked = False
        
        # Stop tunnel sound
        try:
            if tunnel_sound:
                if tunnel_is_music:
                    try:
                        pygame.mixer.music.fadeout(400)
                    except Exception:
                        try:
                            pygame.mixer.music.stop()
                        except Exception:
                            pass
                else:
                    try:
                        tunnel_sound.fadeout(400)
                    except Exception:
                        try:
                            tunnel_sound.stop()
                        except Exception:
                            pass
        except Exception:
            pass
        
        return False, True, False
    
    return True, False, True
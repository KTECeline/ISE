from ursina import *

app = Ursina()

player = SpriteSheetAnimation(
    'character/chamove', 
    tileset_size=(7,9),
    fps=10,
    animations={
        'walkright': ((0,7), (5,7)),
        'walkleft': ((0,8), (5,8)),
        'idle': ((0,6), (0,6)),
        'idleLeft': ((1,6), (1,6)),
        'jumpright' : ((2,6), (2,6)),
        'jumpleft' : ((3,6), (3,6)),
        'downright' : ((2,4), (2,4)),
        'downleft' : ((3,4), (3,4)),
        'dashright' : ((0,3), (6,3)),
        'dashleft' : ((0, 2), (6, 2)),
        'jumpdownRight' : ((0, 1), (3, 1)),
        'jumpdownLeft' : ((0,9), (3,9))
    },
    position=(0,0),
    scale=1.5
)

player.origin = (0,0)
speed = 3
gravity = 0.7
jump_speed = 25
velocity_y = 0
on_ground = True
current_animation = 'idle'
facePosition = 'right'

# --- jump cooldown ---
can_jump = True
jump_cooldown = 0.6
jump_timer = 0

# --- dash variables ---
is_dashing = False
dash_speed = 12
dash_duration = 0.25
dash_timer = 0
dash_cooldown = 1.0
can_dash = True
dash_cooldown_timer = 0


def update():
    global current_animation, velocity_y, on_ground, facePosition
    global can_jump, jump_timer, is_dashing, dash_timer, can_dash, dash_cooldown_timer

    moving = False
    squating = False

    # --- update jump cooldown ---
    if not can_jump:
        jump_timer += time.dt
        if jump_timer >= jump_cooldown:
            can_jump = True
            jump_timer = 0

    # --- update dash cooldown ---
    if not can_dash:
        dash_cooldown_timer += time.dt
        if dash_cooldown_timer >= dash_cooldown:
            can_dash = True
            dash_cooldown_timer = 0

    # --- DASH movement ---
    if is_dashing:
        dash_timer += time.dt
        if facePosition == 'right':
            player.x += dash_speed * time.dt
        else:
            player.x -= dash_speed * time.dt
        if dash_timer >= dash_duration:
            is_dashing = False
            dash_timer = 0
            if on_ground:
                if facePosition == 'right':
                    player.play_animation('idle')
                    current_animation = 'idle'
                else:
                    player.play_animation('idleLeft')
                    current_animation = 'idleLeft'

    # --- Normal movement (only if not dashing) ---
    if not is_dashing:
        if held_keys['d'] and not held_keys['s']:
            player.x += time.dt * speed
            if current_animation != 'walkright' and current_animation != 'jumpright':
                if on_ground:
                    player.play_animation('walkright')
                    current_animation = 'walkright'
                    facePosition = 'right'
            moving = True

        elif held_keys['a'] and not held_keys['s']:
            player.x -= time.dt * speed
            if current_animation != 'walkleft' and current_animation != 'jumpleft':
                if on_ground:
                    player.play_animation('walkleft')
                    current_animation = 'walkleft'
                    facePosition = 'left'
            moving = True

        # --- Jump ---
        if held_keys['space'] and on_ground and can_jump:
            can_jump = False
            velocity_y = jump_speed
            on_ground = False
            if facePosition == 'right':
                player.play_animation('jumpright')
                current_animation = 'jumpright'
            else:
                player.play_animation('jumpleft')
                current_animation = 'jumpleft'
            moving = True

        # --- added jumpdown feature ---
        if held_keys['s'] and not on_ground and velocity_y > -5:
            # faster fall when pressing S in air
            velocity_y = -20  # strong downward speed
            if facePosition == 'right':
                player.play_animation('jumpdownRight')
                current_animation = 'jumpdownRight'
            else:
                player.play_animation('jumpdownLeft')
                current_animation = 'jumpdownLeft'

        # --- Dash key pressed ---
        if held_keys['shift'] and not is_dashing and can_dash:
            is_dashing = True
            can_dash = False
            dash_timer = 0
            if facePosition == 'right':
                player.play_animation('dashright')
                current_animation = 'dashright'
            else:
                player.play_animation('dashleft')
                current_animation = 'dashleft'

        if held_keys['s'] and on_ground and not is_dashing:
            if facePosition == 'right':
                player.play_animation('downright')
                current_animation = 'downright'
            else:
                player.play_animation('downleft')
                current_animation = 'downleft'
            moving = True
            squating = True

    if on_ground and not current_animation.startswith('walk') and not current_animation.startswith('down') and not current_animation.startswith('dash'):
        if facePosition == 'right':
            player.play_animation('idle')
            current_animation = 'idle'
        else:
            player.play_animation('idleLeft')
            current_animation = 'idleLeft'

    # --- Apply gravity ---
    if not on_ground:
        velocity_y -= gravity
        player.y += velocity_y * time.dt
        if player.y <= 0:
            player.y = 0
            velocity_y = 0
            on_ground = True

    # --- Idle ---
    if on_ground and not moving and not is_dashing and current_animation != 'idle':
        if facePosition == 'right':
            player.play_animation('idle')
            current_animation = 'idle'
        else:
            player.play_animation('idleLeft')
            current_animation = 'idleLeft'


app.run()

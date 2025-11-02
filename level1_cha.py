from ursina import *
import numpy as np
from PIL import Image
import time

app = Ursina()
# Remove the internal exit button
window.exit_button.enabled = False

# Load and process mushroom coins with different colors
mushroom_sheet = Image.open('assets/images/mushroom_coins.png')
sheet_width, sheet_height = mushroom_sheet.size

# Create color variations
color_filters = {
    'original': (1, 1, 1),  # No tint
    'red': (1, 0.2, 0.2),   # Red tint
    'green': (0.2, 1, 0.2), # Green tint
    'blue': (0.2, 0.2, 1)   # Blue tint
}

# Store the textures with different colors
mushroom_textures = {}
for color_name, color_filter in color_filters.items():
    # Apply color filter to the image
    colored_image = mushroom_sheet.copy()
    # Convert to RGBA if not already
    if colored_image.mode != 'RGBA':
        colored_image = colored_image.convert('RGBA')
    
    # Apply color tint
    data = np.array(colored_image)
    data[..., 0] = data[..., 0] * color_filter[0]  # Red channel
    data[..., 1] = data[..., 1] * color_filter[1]  # Green channel
    data[..., 2] = data[..., 2] * color_filter[2]  # Blue channel
    
    # Convert back to Image and create texture
    colored_image = Image.fromarray(data)
    mushroom_textures[color_name] = Texture(colored_image)

# Create a visual ground plane with the main image
ground = Entity(
    model='plane',
    texture='assets/textures/map/Level_1_The_Fungal_Ascent.png',
    scale=(81, 1, 75),
    position=(0, 0, 0)
)

# Create a collision layer using the collision map
collision_ground = Entity(
    model='plane',
    texture=load_texture('assets/textures/map/Level_1_The_Fungal_Ascent_Collision.png'),
    scale=(81, 1, 75),
    position=(0, 0, 0),
    visible=False  # Hide the collision map
)

# --- Collision System ---
collision_map = Image.open('assets/textures/map/Level_1_The_Fungal_Ascent_Collision.png')
tex_w, tex_h = collision_map.width, collision_map.height

# Define the specific red color for collision (#F02327)
RED_COLLISION = (240, 35, 39)  # #F02327 in RGB
TOLERANCE = 20  # Color matching tolerance

def world_to_texture_coords(x, z):
    """Convert world X,Z to texture pixel coordinates."""
    u = int((x / ground.scale_x + 0.5) * tex_w)
    v = int((z / ground.scale_z + 0.5) * tex_h)
    return u, tex_h - v - 1  # flip vertically

def is_solid(x, z):
    """Return True if world position hits a #F02327 red pixel."""
    try:
        u, v = world_to_texture_coords(x, z)
        # Clamp coordinates to valid range
        u = max(0, min(tex_w - 1, u))
        v = max(0, min(tex_h - 1, v))
        
        r, g, b, *a = collision_map.getpixel((u, v))
        # Check for #F02327 red color with tolerance
        if (abs(r - RED_COLLISION[0]) < TOLERANCE and 
            abs(g - RED_COLLISION[1]) < TOLERANCE and 
            abs(b - RED_COLLISION[2]) < TOLERANCE):
            return True
    except:
        pass
    return False


def check_collision_at_position(x, z, radius=0.3):
    """Check multiple points around the character to prevent sticking."""
    points = [
        (x, z),  # center
        (x - radius, z),  # left
        (x + radius, z),  # right
        (x, z - radius),  # bottom
        (x, z + radius),  # top
        (x - radius * 0.7, z - radius * 0.7),  # bottom-left
        (x + radius * 0.7, z - radius * 0.7),  # bottom-right
        (x - radius * 0.7, z + radius * 0.7),  # top-left
        (x + radius * 0.7, z + radius * 0.7),  # top-right
    ]
    
    for px, pz in points:
        if is_solid(px, pz):
            return True
    return False
# --- End Collision System ---

# Variables to track diagnostic mode
diagnostic_mode = False
prev_t_state = False

# Debug text for collision checking
collision_debug = Text(
    text='No collision data',
    position=(-0.5, 0.4),
    scale=1.2,
    origin=(0, 0),
    background=True,
    enabled=False  # Hidden by default
)

# Character
player = SpriteSheetAnimation(
    'character/chamove', 
    tileset_size=(7,11),
    fps=10,
    animations={
        'walkright': ((0,9), (5,9)),
        'walkleft': ((0,10), (5,10)),
        'idle': ((0,8), (0,8)),
        'idleLeft': ((1,8), (1,8)),
        'jumpright' : ((2,8), (2,8)),
        'jumpleft' : ((3,8), (3,8)),
        'downright' : ((2,6), (2,6)),
        'downleft' : ((3,6), (3,6)),
        'dashright' : ((3,5), (3,5)),
        'dashleft' : ((3, 4), (3, 4)),
        'jumpdownRight' : ((0, 3), (3, 3)),
        'jumpdownLeft' : ((0,2), (3,2)),
        'throwRight' : ((0,11), (2,11)),
        'throwLeft' : ((3,11), (5,11)),
        'climbRight': ((0,1), (0,1)),
        'climbLeft' : ((1,1),(1,1))
    },
    position=(-30, 0.25, -30),
    scale=3
)

# Position adjustment values
x_offset = 27  # Decrease to move right, increase to move left
z_offset = 9.8    # Decrease to move up, increase to move down

# Create an animated red mushroom coin
red_coin = Entity(
    model='quad',
    texture=mushroom_textures['red'],
    texture_scale=(1/5, 1),
    texture_offset=(0, 0),
    scale=(1, 1),
    position=(592/81 - x_offset, 1, 1568/75 - z_offset),
    rotation_x=90
)

# Create an animated green mushroom coin
green_coin = Entity(
    model='quad',
    texture=mushroom_textures['green'],
    texture_scale=(1/5, 1),
    texture_offset=(0, 0),
    scale=(1, 1),
    position=(1175/81 - x_offset, 1, -760/75 - z_offset),
    rotation_x=90
)

# Create an animated blue mushroom coin
blue_coin = Entity(
    model='quad',
    texture=mushroom_textures['blue'],
    texture_scale=(1/5, 1),
    texture_offset=(0, 0),
    scale=(1, 1),
    position=(4745/81 - x_offset, 1, 1740/75 - z_offset),
    rotation_x=90
)

# Animation variables for the coins
for coin in [red_coin, green_coin, blue_coin]:
    coin.frame = 0
    coin.animation_time = 0
    coin.frame_duration = 0.2

def update_coin_animation():
    for coin in [red_coin, green_coin, blue_coin]:
        coin.animation_time += time.dt
        if coin.animation_time >= coin.frame_duration:
            coin.frame = (coin.frame + 1) % 5
            coin.texture_offset = (coin.frame/5, 0)
            coin.animation_time = 0

# Camera positioned above the player
camera.position = (player.x, 50, player.z)
camera.rotation_x = 90

# Movement settings
move_speed = 5

# Zoom settings
min_height = 5
max_height = 100
zoom_speed = 2

# Diagnostic view settings
diagnostic_base_height = 5
diagnostic_min_zoom = 3
diagnostic_max_zoom = 40
diagnostic_zoom = 25

# Score display
score = 0
score_text = Text(
    text='Mushroom Coins collected: 0',
    position=(-0.5, 0.45),
    scale=1.2,
    origin=(0, 0),
    background=True
)

zoom_indicator = Text(
    text=f'Height: {int(camera.y)}',
    position=(0.7, 0.45),
    scale=1.2,
    origin=(0, 0),
    background=True,
    enabled=False
)

def check_coin_collection(coin, player):
    distance = (coin.position - player.position).length()
    return distance < 1

# Player physics
player.rotation_x = 90 
player.origin = (0,0)
speed = 10
gravity = 50
jump_speed = 25
velocity_z = 0

on_ground = False  # Start in air to force falling
current_animation = 'idle'
facePosition = 'right'

# Jump and dash settings
can_jump = True
double_jump = False
jump_cooldown = 2
jump_timer = 0
is_dashing = False
dash_speed = 23
dash_duration = 0.25
dash_timer = 0
dash_cooldown = 1.0
can_dash = True
dash_cooldown_timer = 0

on_wall = False
wall_jump_cooldown = 0.2
wall_jump_timer = 0

# Collision resolution settings
collision_push_distance = 0.05
max_push_attempts = 5

def resolve_collision(x, z, original_x, original_z):
    """Try to push the character out of collision in the best direction."""
    # Try different push directions
    directions = [
        (original_x - x, original_z - z),  # Opposite of movement
        (0, collision_push_distance),      # Up
        (0, -collision_push_distance),     # Down
        (collision_push_distance, 0),      # Right
        (-collision_push_distance, 0),     # Left
        (collision_push_distance, collision_push_distance),   # Up-Right
        (-collision_push_distance, collision_push_distance),  # Up-Left
        (collision_push_distance, -collision_push_distance),  # Down-Right
        (-collision_push_distance, -collision_push_distance), # Down-Left
    ]
    
    for dx, dz in directions:
        new_x = x + dx
        new_z = z + dz
        if not check_collision_at_position(new_x, new_z):
            return new_x, new_z
    
    # If all else fails, return to original position
    return original_x, original_z

def update():
    global current_animation, velocity_z, on_ground, facePosition
    global can_jump, jump_timer, is_dashing, dash_timer, can_dash, dash_cooldown_timer, on_wall, wall_jump_timer, wall_jump_cooldown

    moving = False
    squating = False
    global score, diagnostic_mode, prev_t_state

    update_coin_animation()

    # Toggle diagnostic mode
    if held_keys['t'] and not prev_t_state:
        diagnostic_mode = not diagnostic_mode
    prev_t_state = held_keys['t']

    collision_debug.enabled = diagnostic_mode
    zoom_indicator.enabled = diagnostic_mode
    if diagnostic_mode:
        camera.rotation_x = lerp(camera.rotation_x, 45, time.dt * 5)
    else:
        camera.rotation_x = lerp(camera.rotation_x, 90, time.dt * 5)

    # Coin collection
    for coin in [red_coin, green_coin, blue_coin]:
        if coin.enabled and check_coin_collection(coin, player):
            coin.enabled = False
            score += 1
            score_text.text = f'Mushroom Coins collected: {score}'

    # Jump and dash cooldown timers
    if not can_jump:
        jump_timer += time.dt
        if jump_timer >= jump_cooldown:
            can_jump = True
            jump_timer = 0
            

    if not can_dash:
        dash_cooldown_timer += time.dt
        if dash_cooldown_timer >= dash_cooldown:
            can_dash = True
            dash_cooldown_timer = 0

    # Store original position for collision resolution
    original_x, original_z = player.x, player.z

    # --- DASH movement ---
    if is_dashing:
        dash_timer += time.dt
        if facePosition == 'right':
            next_x = player.x + dash_speed * time.dt
            if not check_collision_at_position(next_x, player.z):
                player.x = next_x
            else:
                # Resolve collision during dash
                player.x, player.z = resolve_collision(player.x, player.z, original_x, original_z)
        else:
            next_x = player.x - dash_speed * time.dt
            if not check_collision_at_position(next_x, player.z):
                player.x = next_x
            else:
                player.x, player.z = resolve_collision(player.x, player.z, original_x, original_z)
        if dash_timer >= dash_duration:
            is_dashing = False
            dash_timer = 0
 
            if facePosition == 'right':
                player.play_animation('idle')
                current_animation = 'idle'
            else:
                player.play_animation('idleLeft')
                current_animation = 'idleLeft'

    # --- Normal movement ---
    if not is_dashing:
        wall_left = check_collision_at_position(player.x - 0.3, player.z)
        wall_right = check_collision_at_position(player.x + 0.3, player.z)
        touching_wall = wall_left or wall_right

        # Update wall status
        if touching_wall and not on_ground:
            on_wall = True
            # Maintain climbing pose while on wall
            if wall_left:
                facePosition = 'left'
            elif wall_right:
                facePosition = 'right'
            if current_animation not in ['climbRight', 'climbLeft']:
                anim = 'climbRight' if facePosition == 'right' else 'climbLeft'
                player.play_animation(anim)
                current_animation = anim
        else:
            on_wall = False

        # Only allow horizontal movement if not on wall
        if not on_wall:
            if held_keys['d'] and not held_keys['s']:
                next_x = player.x + time.dt * speed
                if not check_collision_at_position(next_x, player.z):
                    player.x = next_x
                else:
                    # Try to resolve collision
                    player.x, player.z = resolve_collision(player.x, player.z, original_x, original_z)
                if current_animation != 'walkright' and on_ground:
                    player.play_animation('walkright')
                    current_animation = 'walkright'
                    facePosition = 'right'
                moving = True

            elif held_keys['a'] and not held_keys['s']:
                next_x = player.x - time.dt * speed
                if not check_collision_at_position(next_x, player.z):
                    player.x = next_x
                else:
                    player.x, player.z = resolve_collision(player.x, player.z, original_x, original_z)
                if current_animation != 'walkleft' and on_ground:
                    player.play_animation('walkleft')
                    current_animation = 'walkleft'
                    facePosition = 'left'
                moving = True

        if not hasattr(player, 'jump_count'):
            player.jump_count = 0
        if not hasattr(player, 'space_held'):
            player.space_held = False

        # Regular jump
        if held_keys['space']:
            if not player.space_held:
                player.space_held = True

                if on_ground:
                    # Normal jump
                    velocity_z = jump_speed
                    on_ground = False
                    if velocity_z >= 0:
                        if held_keys['a']:
                            facePosition = 'left'
                        elif held_keys['d']:
                            facePosition = 'right'
                    anim = 'jumpright' if facePosition == 'right' else 'jumpleft'
                    player.play_animation(anim)
                    current_animation = anim

                elif on_wall and wall_jump_timer <= 0:
                    # Wall jump
                    velocity_z = jump_speed + 5  # slightly less vertical
                    # Push away from wall
                    if wall_left:
                        player.x += 0.3
                        facePosition = 'left'
                    elif wall_right:
                        player.x -= 0.3
                        facePosition = 'right'

                    on_wall = False
                    wall_jump_timer = wall_jump_cooldown

                    anim = 'jumpright' if facePosition == 'right' else 'jumpleft'
                    player.play_animation(anim)
                    current_animation = anim
        else:
            player.space_held = False

        # wall jump cooldown timer
        if wall_jump_timer > 0:
            wall_jump_timer -= time.dt

        # Slow fall when on wall
        if on_wall and velocity_z < 0:
            velocity_z = -5

        # Fall faster (only when not on wall)
        if held_keys['s'] and not on_ground and not on_wall:
            velocity_z = -45
            anim = 'jumpdownRight' if facePosition == 'right' else 'jumpdownLeft'
            player.play_animation(anim)
            current_animation = anim

        # Dash
        if held_keys['shift'] and not is_dashing and can_dash and not on_wall:
            is_dashing = True
            can_dash = False
            dash_timer = 0
            anim = 'dashright' if facePosition == 'right' else 'dashleft'
            player.play_animation(anim)
            current_animation = anim

        # Squat (only when on ground)
        if held_keys['s'] and on_ground and not is_dashing:
            anim = 'downright' if facePosition == 'right' else 'downleft'
            player.play_animation(anim)
            current_animation = anim
            moving = True
            squating = True


    # --- ALWAYS APPLY GRAVITY until collision is reached ---
    if not on_ground:
        velocity_z -= gravity * time.dt
        next_z = player.z + velocity_z * time.dt

        
        if not check_collision_at_position(player.x, next_z):
            player.z = next_z
            # Continue falling - update animation to falling state
            if velocity_z < 0 and not is_dashing and not current_animation in ['jumpdownRight', 'jumpdownLeft'] and not on_wall:
                if held_keys['a']:
                    facePosition = 'left'
                elif held_keys['d']:
                    facePosition = 'right'
                anim = 'jumpright' if facePosition == 'right' else 'jumpleft'
                player.play_animation(anim)
                current_animation = anim
                
                if current_animation != anim:
                    player.play_animation(anim)
                    current_animation = anim
            elif velocity_z < 0 and current_animation in ['dashright', 'dashleft']:
                anim = 'dashright' if facePosition == 'right' else 'dashleft'
                player.play_animation(anim)
                current_animation = anim
        else:
            # Landed - resolve vertical collision
            if velocity_z < 0:  # Falling down
                on_ground = True
                player.jump_count = 0
                velocity_z = 0
                # Push up until not colliding
                for i in range(max_push_attempts):
                    if not check_collision_at_position(player.x, player.z):
                        break
                    player.z += collision_push_distance
                # Set idle animation after landing
                anim = 'idle' if facePosition == 'right' else 'idleLeft'
                player.play_animation(anim)
                current_animation = anim
            else:  # Hitting ceiling
                velocity_z = min(velocity_z, 0)  # Stop upward movement
                # Push down a bit
                player.z -= collision_push_distance

    # Force falling if not on ground and no vertical movement
    if on_ground and not check_collision_at_position(player.x, player.z - 0.1):
        on_ground = False
        velocity_z = -1  # Start falling slowly

    # --- Idle ---
    if on_ground and not moving and not is_dashing and not squating and not on_wall:
        if current_animation not in ['idle', 'idleLeft']:
            anim = 'idle' if facePosition == 'right' else 'idleLeft'
            player.play_animation(anim)
            current_animation = anim

    # --- Camera follow ---
    if diagnostic_mode:
        global diagnostic_zoom
        if held_keys['q']:
            diagnostic_zoom -= zoom_speed * time.dt * 40
            diagnostic_zoom = clamp(diagnostic_zoom, diagnostic_min_zoom, diagnostic_max_zoom)
        if held_keys['e']:
            diagnostic_zoom += zoom_speed * time.dt * 40
            diagnostic_zoom = clamp(diagnostic_zoom, diagnostic_min_zoom, diagnostic_max_zoom)
        camera_offset = -(diagnostic_zoom * 0.25)
        camera.position = (player.x, player.y + (diagnostic_zoom * 0.3), player.z + camera_offset)
    else:
        if held_keys['q']:
            camera.y += zoom_speed * time.dt * 10
            camera.y = clamp(camera.y, min_height, max_height)
        if held_keys['e']:
            camera.y -= zoom_speed * time.dt * 10
            camera.y = clamp(camera.y, min_height, max_height)
        camera.position = (player.x, camera.y, player.z)

    zoom_indicator.text = f'Height: {int(camera.y)}'

def input(key):
    global diagnostic_zoom
    if key == 'escape':
        application.quit()
    if diagnostic_mode:
        if key == 'scroll up':
            diagnostic_zoom -= zoom_speed * 4
            diagnostic_zoom = clamp(diagnostic_zoom, diagnostic_min_zoom, diagnostic_max_zoom)
        if key == 'scroll down':
            diagnostic_zoom += zoom_speed * 4
            diagnostic_zoom = clamp(diagnostic_zoom, diagnostic_min_zoom, diagnostic_max_zoom)
    else:
        if key == 'scroll up':
            camera.y -= zoom_speed
            camera.y = clamp(camera.y, min_height, max_height)
        if key == 'scroll down':
            camera.y += zoom_speed
            camera.y = clamp(camera.y, min_height, max_height)

AmbientLight(color=color.rgba(255, 255, 255, 0.5))
app.run()
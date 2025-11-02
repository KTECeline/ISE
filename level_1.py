from ursina import *
import numpy as np
from PIL import Image
import random
import math

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

# Create an upper layer with the inverted map for 3D effect
upper_layer = Entity(
    model='plane',
    texture=load_texture('assets/textures/map/Level_1_The_Fungal_Ascent_Layering_Inverted.png'),
    scale=(81, 1, 75),
    position=(0, 0.5, 0),  # Slightly above the ground
    alpha=1,  # Full opacity for black parts
    collider=None  # Disable collision for the upper layer
)

# Custom shader to only show black parts
upper_layer.shader = Shader(
    vertex='''
    #version 430
    uniform mat4 p3d_ModelViewProjectionMatrix;
    in vec4 p3d_Vertex;
    in vec2 p3d_MultiTexCoord0;
    out vec2 uv;
    void main() {
        gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
        uv = p3d_MultiTexCoord0;
    }
    ''',
    
    fragment='''
    #version 430
    uniform sampler2D p3d_Texture0;
    in vec2 uv;
    out vec4 fragColor;
    void main() {
        vec4 color = texture(p3d_Texture0, uv);
        // Only show pixels that are black (RGB = 0,0,0)
        if (color.r == 0.0 && color.g == 0.0 && color.b == 0.0) {
            fragColor = vec4(0.0, 0.0, 0.0, 1.0);
        } else {
            fragColor = vec4(0.0, 0.0, 0.0, 0.0);  // Transparent for non-black pixels
        }
    }
    '''
)

# Particle system for atmospheric spores
class Particle(Entity):
    def __init__(self, **kwargs):
        # Randomize particle properties
        base_scale = random.uniform(0.1, 0.25)  # Varied sizes
        glow_strength = random.uniform(0.8, 1.2)  # Variable glow intensity
        
        # Create the main particle
        super().__init__(
            model='sphere',
            scale=base_scale,
            color=color.rgba(200, 255, 180, 180),
            **kwargs
        )
        
        # Add glow effect as a child entity
        self.glow = Entity(
            parent=self,
            model='sphere',
            scale=1.5,  # Slightly larger than parent
            color=color.rgba(200, 255, 180, 100),
            alpha=0.3 * glow_strength
        )
        
        # Random movement parameters
        self.velocity = Vec3(
            random.uniform(-0.5, 0.5),
            random.uniform(0.2, 0.8),
            random.uniform(-0.5, 0.5)
        )
        self.lifetime = random.uniform(5, 10)
        self.age = 0
        self.float_speed = random.uniform(0.3, 0.8)  # More varied float speeds
        self.drift_offset = random.uniform(0, 6.28)
        
        # Pulse effect parameters
        self.pulse_speed = random.uniform(1, 3)
        self.pulse_magnitude = random.uniform(0.1, 0.3)
        self.base_scale = base_scale
        
    def update(self):
        # Floating movement with sine wave drift
        self.age += time.dt
        drift = math.sin(self.age * self.float_speed + self.drift_offset) * 0.5
        
        self.x += (self.velocity.x + drift * 0.1) * time.dt
        self.y += self.velocity.y * time.dt * 0.5
        self.z += (self.velocity.z + drift * 0.1) * time.dt
        
        # Pulsing size effect
        pulse = math.sin(self.age * self.pulse_speed) * self.pulse_magnitude + 1
        self.scale = self.base_scale * pulse
        self.glow.scale = 1.5 + pulse * 0.2  # Glow follows the pulse
        
        # Fade out near end of lifetime
        fade_start = 0.7  # Start fading at 70% of lifetime
        if self.age / self.lifetime > fade_start:
            fade_progress = (self.age / self.lifetime - fade_start) / (1 - fade_start)
            alpha = 1 - fade_progress
            self.color = color.rgba(200, 255, 180, int(alpha * 180))
            self.glow.color = color.rgba(200, 255, 180, int(alpha * 100))
        
        # Add slight rotation for more dynamic appearance
        self.rotation_y += time.dt * random.uniform(-20, 20)
        
        # Reset particle when lifetime expires
        if self.age >= self.lifetime:
            self.respawn()
    
    def respawn(self):
        # Respawn around the player position
        angle = random.uniform(0, 6.28)
        radius = random.uniform(5, 15)
        self.position = (
            player.x + math.cos(angle) * radius,
            random.uniform(0.5, 3),
            player.z + math.sin(angle) * radius
        )
        self.age = 0
        self.velocity = Vec3(
            random.uniform(-0.5, 0.5),
            random.uniform(0.2, 0.8),
            random.uniform(-0.5, 0.5)
        )
        self.lifetime = random.uniform(5, 10)
        # Reset color and alpha
        self.color = color.rgba(200, 255, 180, 180)
        self.glow.color = color.rgba(200, 255, 180, 100)

# Create particle pool and list to store them
particles = []
particle_count = 50  # Number of particles in the scene

# Variables to track diagnostic mode
diagnostic_mode = False
prev_t_state = False

# Ground state debounce variables
ground_check_timer = 0
ground_check_delay = 0.1  # Time in seconds to wait before allowing state change
last_ground_state = True

# Debug text for collision checking
collision_debug = Text(
    text='No collision data',
    position=(-0.85, -0.35),
    scale=1.2,
    origin=(0, 0),
    background=True,
    enabled=False  # Hidden by default
)

# Collision type indicator
collision_type_text = Text(
    text='Collision: None',
    position=(-0.85, -0.40),
    scale=1.2,
    origin=(0, 0),
    background=True,
    enabled=False  # Hidden by default
)

# Animation state indicator
animation_debug_text = Text(
    text='Animation: idle',
    position=(-0.85, -0.45),
    scale=1.2,
    origin=(0, 0),
    background=True,
    enabled=False  # Hidden by default
)

# Create player with sprite sheet animation
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
    position=(12, 0.25, -32) ,
    scale=1.5,
    rotation_x=90  # Rotate to face down for top-down view
)

player.origin = (0, -0.15)

# Initialize particle system
for i in range(particle_count):
    # Spawn particles around the starting area
    angle = random.uniform(0, 6.28)
    radius = random.uniform(2, 12)
    particle = Particle(
        position=(
            player.x + math.cos(angle) * radius,
            random.uniform(0.5, 3),
            player.z + math.sin(angle) * radius
        )
    )
    particles.append(particle)

# Character movement variables
speed = 5
gravity = 0.7
jump_speed = 25
velocity_y = 0
on_ground = True
current_animation = 'idle'
facePosition = 'right'

# Jump cooldown
can_jump = True
jump_cooldown = 0.6
jump_timer = 0

# Dash variables
is_dashing = False
dash_speed = 12
dash_duration = 0.25
dash_timer = 0
dash_cooldown = 1.0
can_dash = True
dash_cooldown_timer = 0

# Position adjustment values
x_offset = 27  # Decrease to move right, increase to move left
z_offset = 9.8    # Decrease to move up, increase to move down

# Create an animated red mushroom coin
red_coin = Entity(
    model='quad',
    texture=mushroom_textures['red'],
    texture_scale=(1/5, 1),      # Show 1/5th of the texture
    texture_offset=(0, 0),       # Start with first frame
    scale=(1, 1),
    position=(592/81 - x_offset, 1, 1568/75 - z_offset),
    rotation_x=90                # Face down for top view
)

# Create an animated green mushroom coin
green_coin = Entity(
    model='quad',
    texture=mushroom_textures['green'],
    texture_scale=(1/5, 1),      # Show 1/5th of the texture
    texture_offset=(0, 0),       # Start with first frame
    scale=(1, 1),
    position=(1175/81 - x_offset, 1, -760/75 - z_offset),
    rotation_x=90                # Face down for top view
)

# Create an animated blue mushroom coin
blue_coin = Entity(
    model='quad',
    texture=mushroom_textures['blue'],
    texture_scale=(1/5, 1),      # Show 1/5th of the texture
    texture_offset=(0, 0),       # Start with first frame
    scale=(1, 1),
    position=(4745/81 - x_offset, 1, 1740/75 - z_offset),
    rotation_x=90                # Face down for top view
)

# Animation variables for the coins
red_coin.frame = 0
red_coin.animation_time = 0
green_coin.frame = 0
green_coin.animation_time = 0
blue_coin.frame = 0
blue_coin.animation_time = 0
red_coin.frame_duration = 0.2    # Time per frame in seconds
green_coin.frame_duration = 0.2  # Time per frame in seconds
blue_coin.frame_duration = 0.2   # Time per frame in seconds

def update_coin_animation():
    # Update red coin
    red_coin.animation_time += time.dt
    if red_coin.animation_time >= red_coin.frame_duration:
        # Move to next frame
        red_coin.frame = (red_coin.frame + 1) % 5
        red_coin.texture_offset = (red_coin.frame/5, 0)
        red_coin.animation_time = 0
    
    # Update green coin
    green_coin.animation_time += time.dt
    if green_coin.animation_time >= green_coin.frame_duration:
        # Move to next frame
        green_coin.frame = (green_coin.frame + 1) % 5
        green_coin.texture_offset = (green_coin.frame/5, 0)
        green_coin.animation_time = 0
    
    # Update blue coin
    blue_coin.animation_time += time.dt
    if blue_coin.animation_time >= blue_coin.frame_duration:
        # Move to next frame
        blue_coin.frame = (blue_coin.frame + 1) % 5
        blue_coin.texture_offset = (blue_coin.frame/5, 0)
        blue_coin.animation_time = 0

# Create camera positioned above the player for top-down view
camera.position = (0, 21, 0)  # Set default height to 21
camera.rotation_x = 90

# Zoom settings (only used in diagnostic mode)
min_height = 5
max_height = 100
zoom_speed = 2

# Diagnostic view settings
diagnostic_base_height = 5  # Lower default diagnostic view height
diagnostic_min_zoom = 3
diagnostic_max_zoom = 40  # Increased max zoom for more zoomed out view
diagnostic_zoom = 25  # Starting with a more zoomed out view

    # Score, lives and game state
score = 0
lives = 3
is_game_over = False
score_text = Text(
    text='Mushroom Coins collected: 0',
    position=(-0.5, 0.45),
    scale=1.2,
    origin=(0, 0),
    background=True
)

lives_text = Text(
    text='Lives: 3',
    position=(-0.5, 0.40),
    scale=1.2,
    origin=(0, 0),
    background=True
)

# Game Over screen elements
game_over_panel = Entity(
    model='quad',
    color=color.black66,
    scale=(2, 1),
    position=(0, 0),
    parent=camera.ui,
    enabled=False
)

game_over_text = Text(
    text='GAME OVER',
    scale=4,
    origin=(0, 0),
    position=(0, 0.1),
    color=color.red,
    parent=camera.ui,
    enabled=False
)

retry_button = Button(
    text='Retry',
    color=color.red,
    scale=(0.2, 0.1),
    position=(0, -0.1),
    parent=camera.ui,
    enabled=False
)# Store initial player position for respawn
initial_player_position = Vec3(12, 0.25, -32)

# Zoom level indicator
zoom_indicator = Text(
    text=f'Height: {int(camera.y)}',
    position=(-0.85, -0.45),
    scale=2,
    color=color.white,
    origin=(0, 0),
    background=True,
    enabled=False  # Hidden
)

def check_coin_collection(coin, player):
    # Calculate distance between player and coin
    distance = (coin.position - player.position).length()
    # If player is close enough to coin (within 1 unit)
    return distance < 1

def check_collision(new_position):
    """Check if new position would collide with a wall or trap"""
    global lives
    # Convert world position to UV coordinates
    scale_x, _, scale_z = collision_ground.scale
    tex_x = int((new_position.x / scale_x + 0.5) * collision_ground.texture.width)
    tex_z = int((new_position.z / scale_z + 0.5) * collision_ground.texture.height)
    
    try:
        # Get color at position from collision map
        color = collision_ground.texture.get_pixel(tex_x, tex_z)
        
        # Debug color information
        collision_debug.text = f'Pos: ({tex_x}, {tex_z}) Color: R:{int(color[0]*255)} G:{int(color[1]*255)} B:{int(color[2]*255)}'
        
        # Check if it's near the wall color (ED1C24 - red) with some tolerance
        is_wall = (abs(color[0] - 237/255) < 0.1 and 
                  abs(color[1] - 28/255) < 0.1 and 
                  abs(color[2] - 36/255) < 0.1)
        
        # Check if it's near the trap color (22C722 - green) with some tolerance
        is_trap = (abs(color[0] - 34/255) < 0.1 and 
                  abs(color[1] - 199/255) < 0.1 and 
                  abs(color[2] - 34/255) < 0.1)
        
        # Update collision type indicator
        if is_wall:
            collision_type_text.text = 'Collision: WALL (Red)'
        elif is_trap:
            collision_type_text.text = 'Collision: TRAP (Green)'
        else:
            collision_type_text.text = 'Collision: None (Safe)'
        
        return is_wall
    except Exception as e:
        collision_debug.text = f'Error: {str(e)}'
        collision_type_text.text = 'Collision: ERROR'
        return True  # Assume collision on error
    except Exception as e:
        collision_debug.text = f'Error: {str(e)}'
        collision_type_text.text = 'Collision: ERROR'
        return True  # Assume collision on error

def check_ground(position):
    """Check if there's solid ground (only red walls or green traps)"""
    # Convert world position to UV coordinates
    scale_x, _, scale_z = collision_ground.scale
    tex_x = int((position.x / scale_x + 0.5) * collision_ground.texture.width)
    tex_z = int((position.z / scale_z + 0.5) * collision_ground.texture.height)
    
    try:
        # Get color at position
        color = collision_ground.texture.get_pixel(tex_x, tex_z)
        
        # Check specifically for red walls (ED1C24) with some tolerance
        is_red_wall = (abs(color[0] - 237/255) < 0.1 and 
                      abs(color[1] - 28/255) < 0.1 and 
                      abs(color[2] - 36/255) < 0.1)
        
        # Check specifically for green traps (22C722) with some tolerance
        is_green_trap = (abs(color[0] - 34/255) < 0.1 and 
                        abs(color[1] - 199/255) < 0.1 and 
                        abs(color[2] - 34/255) < 0.1)
        
        # Return True ONLY if we hit either red wall or green trap
        return is_red_wall or is_green_trap
        
    except Exception as e:
        print(f"Ground check error: {e}")
        return False  # If there's an error, assume no ground

def check_trap_collision():
    """Check if player is on a trap"""
    global lives, is_game_over
    # Don't check for traps if game is already over
    if is_game_over:
        return False

    # Convert player position to UV coordinates
    scale_x, _, scale_z = collision_ground.scale
    tex_x = int((player.x / scale_x + 0.5) * collision_ground.texture.width)
    tex_z = int((player.z / scale_z + 0.5) * collision_ground.texture.height)
    
    try:
        # Get color at current position from collision map
        color = collision_ground.texture.get_pixel(tex_x, tex_z)
        
        # Convert color values to 0-255 range for easier comparison
        r = int(color[0] * 255)
        g = int(color[1] * 255)
        b = int(color[2] * 255)
        
        # Check if it's near the trap color (181, 230, 29) with some tolerance
        is_trap = (abs(r - 181) < 20 and 
                  abs(g - 230) < 20 and 
                  abs(b - 29) < 20)
        
        if is_trap:
            # Lose a life and respawn
            lives -= 1
            lives_text.text = f'Lives: {lives}'
            
            # Check if game over
            if lives <= 0:
                is_game_over = True
                show_game_over()
                return True
                
            # Reset position to initial spawn point
            player.position = initial_player_position
            # Reset velocity and animation state
            return True
        
        # Debug output
        if diagnostic_mode:
            print(f"Current color: R:{r} G:{g} B:{b}")
            
        return False
    except Exception as e:
        print(f"Trap check error: {e}")
        return False

def update():
    global score, diagnostic_mode, prev_t_state
    global current_animation, velocity_y, on_ground, facePosition
    global can_jump, jump_timer, is_dashing, dash_timer, can_dash, dash_cooldown_timer
    
    # Update coin animation
    update_coin_animation()
    
    # Check if player is on a trap
    if check_trap_collision():
        velocity_y = 0
        on_ground = True
        is_dashing = False
    
    # Toggle diagnostic mode when T is pressed (not held)
    if held_keys['t'] and not prev_t_state:
        diagnostic_mode = not diagnostic_mode
    prev_t_state = held_keys['t']
    
    # Update UI elements based on diagnostic mode
    collision_debug.enabled = diagnostic_mode
    collision_type_text.enabled = diagnostic_mode
    animation_debug_text.enabled = diagnostic_mode
    
    # Always update collision info at current position for diagnostic display
    if diagnostic_mode:
        check_collision(player.position)
    
    # Update camera rotation in diagnostic mode
    if diagnostic_mode:
        camera.rotation_x = lerp(camera.rotation_x, 45, time.dt * 5)
    else:
        camera.rotation_x = lerp(camera.rotation_x, 90, time.dt * 5)
    
    # Check coin collection
    if red_coin.enabled and check_coin_collection(red_coin, player):
        red_coin.enabled = False
        score += 1
        score_text.text = f'Mushroom Coins collected: {score}'
        
    if green_coin.enabled and check_coin_collection(green_coin, player):
        green_coin.enabled = False
        score += 1
        score_text.text = f'Mushroom Coins collected: {score}'
        
    if blue_coin.enabled and check_coin_collection(blue_coin, player):
        blue_coin.enabled = False
        score += 1
        score_text.text = f'Mushroom Coins collected: {score}'
    
    moving = False
    squating = False
    
    # Update animation debug BEFORE any animation changes
    if diagnostic_mode:
        animation_debug_text.text = f'Animation: {current_animation} | Moving: {moving} | OnGround: {on_ground} | Dashing: {is_dashing}'

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
        move_amount = dash_speed * time.dt
        
        if facePosition == 'right':
            new_pos = Vec3(player.x + move_amount, player.y, player.z)
        else:
            new_pos = Vec3(player.x - move_amount, player.y, player.z)
        
        # Check collision before moving
        if not check_collision(new_pos):
            player.position = new_pos
            
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
        # Right movement (D key)
        if held_keys['d'] and not held_keys['s']:
            new_pos = Vec3(player.x + time.dt * speed, player.y, player.z)
            if not check_collision(new_pos):
                player.x = new_pos.x
                if current_animation != 'walkright' and current_animation != 'jumpright':
                    if on_ground:
                        player.play_animation('walkright')
                        current_animation = 'walkright'
                        facePosition = 'right'
            moving = True

        # Left movement (A key)
        elif held_keys['a'] and not held_keys['s']:
            new_pos = Vec3(player.x - time.dt * speed, player.y, player.z)
            if not check_collision(new_pos):
                player.x = new_pos.x
                if current_animation != 'walkleft' and current_animation != 'jumpleft':
                    if on_ground:
                        player.play_animation('walkleft')
                        current_animation = 'walkleft'
                        facePosition = 'left'
            moving = True

        # Forward movement (W key)
        if held_keys['w'] and not held_keys['s']:
            new_pos = Vec3(player.x, player.y, player.z + time.dt * speed)
            if not check_collision(new_pos):
                player.z = new_pos.z
            moving = True

        # Backward movement (S key) - only when on ground
        if held_keys['s'] and on_ground:
            new_pos = Vec3(player.x, player.y, player.z - time.dt * speed)
            if not check_collision(new_pos):
                player.z = new_pos.z
            if facePosition == 'right':
                player.play_animation('downright')
                current_animation = 'downright'
            else:
                player.play_animation('downleft')
                current_animation = 'downleft'
            moving = True
            squating = True

        # --- jumpdown feature ---
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
        
        # Check if player has landed on ground
        if check_ground(player.position):
            player.y = 0.25
            velocity_y = 0
            on_ground = True
            # Reset to idle animation when landing
            if facePosition == 'right':
                player.play_animation('idle')
                current_animation = 'idle'
            else:
                player.play_animation('idleLeft')
                current_animation = 'idleLeft'
        elif player.y <= 0.25:
            # Fallback if player goes too low
            player.y = 0.25
            velocity_y = 0
            on_ground = True
    else:
        # Ground state check with debounce
        global ground_check_timer, last_ground_state
        ground_check_timer += time.dt
        
        # Only check ground state after delay
        if ground_check_timer >= ground_check_delay:
            check_pos = player.position
            current_ground_check = check_ground(check_pos)
            
            # Only update state if it's been stable
            if current_ground_check != last_ground_state:
                ground_check_timer = 0  # Reset timer
                last_ground_state = current_ground_check
                
                if not current_ground_check:
                    on_ground = False
                    if facePosition == 'right':
                        player.play_animation('jumpright')
                        current_animation = 'jumpright'
                    else:
                        player.play_animation('jumpleft')
                        current_animation = 'jumpleft'
                else:
                    on_ground = True

    # --- Idle ---
    if on_ground and not moving and not is_dashing and current_animation != 'idle':
        if facePosition == 'right':
            player.play_animation('idle')
            current_animation = 'idle'
        else:
            player.play_animation('idleLeft')
            current_animation = 'idleLeft'
    
    # Camera follows player with offset in diagnostic mode
    if diagnostic_mode:
        global diagnostic_zoom
        # Handle zoom in diagnostic mode
        if held_keys['q']:
            diagnostic_zoom -= zoom_speed * time.dt * 40
            diagnostic_zoom = clamp(diagnostic_zoom, diagnostic_min_zoom, diagnostic_max_zoom)
        if held_keys['e']:
            diagnostic_zoom += zoom_speed * time.dt * 40
            diagnostic_zoom = clamp(diagnostic_zoom, diagnostic_min_zoom, diagnostic_max_zoom)
            
        # Calculate camera position with dynamic offset based on zoom
        camera_offset = -(diagnostic_zoom * 0.25)
        
        camera.position = (
            player.x, 
            player.y + (diagnostic_zoom * 0.3),
            player.z + camera_offset
        )
    else:
        # Normal mode - fixed camera height at 21
        camera.position = (player.x, 21, player.z + 2)  # Added offset to z to see more of the terrain ahead
    
    # Update zoom indicator
    zoom_indicator.text = f'Height: {int(camera.y)}'

def input(key):
    global diagnostic_zoom
    if key == 'escape':
        application.quit()
    
    # Zoom with scroll wheel
    if diagnostic_mode:
        if key == 'scroll up':
            diagnostic_zoom -= zoom_speed * 4
            diagnostic_zoom = clamp(diagnostic_zoom, diagnostic_min_zoom, diagnostic_max_zoom)
        if key == 'scroll down':
            diagnostic_zoom += zoom_speed * 4
            diagnostic_zoom = clamp(diagnostic_zoom, diagnostic_min_zoom, diagnostic_max_zoom)
    else:
        # No zoom controls in normal mode
        pass

# Function to show game over screen
def show_game_over():
    game_over_panel.enabled = True
    game_over_text.enabled = True
    retry_button.enabled = True
    # Disable player movement
    player.enabled = False

def reset_game():
    global lives, score, is_game_over
    # Reset game state
    lives = 3
    score = 0
    is_game_over = False
    lives_text.text = f'Lives: {lives}'
    score_text.text = f'Mushroom Coins collected: {score}'
    
    # Reset player
    player.enabled = True
    player.position = initial_player_position
    
    # Reset coins if they were collected
    red_coin.enabled = True
    green_coin.enabled = True
    blue_coin.enabled = True
    
    # Hide game over screen
    game_over_panel.enabled = False
    game_over_text.enabled = False
    retry_button.enabled = False

# Set up retry button click handler
retry_button.on_click = reset_game

# Add ambient light for better visibility
AmbientLight(color=color.rgba(255, 255, 255, 0.5))

app.run()
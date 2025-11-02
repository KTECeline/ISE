from ursina import *
import numpy as np
from PIL import Image
import random
import math
import os
import json
import pygame

# Initialize pygame mixer for background music
pygame.mixer.init()

# Game data file
GAME_DATA_FILE = "game_data.json"

def load_game_data():
    if os.path.exists(GAME_DATA_FILE):
        try:
            with open(GAME_DATA_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print("[WARN] Could not read game_data.json:", e)
    return {
        "player_name": "",
        "score": 0,
        "lives": 3,
        "mushrooms": 0,
        "current_level": 1,
        "inventory": {},
        "unlocked_levels": [1]
    }

def save_game_data(data):
    try:
        with open(GAME_DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print("[WARN] Could not save game_data.json:", e)

def calculate_score(mushrooms, lives):
    return int((350 / 3) * mushrooms)

# Define sound effects
mushroom_coin_sound = Audio('assets/sounds/level_1_mushroom-coin-poof.mp3', autoplay=False, loop=False)
damage_sound = Audio('assets/sounds/level_1_damaged.mp3', autoplay=False, loop=False)
gameover_sound = Audio('assets/sounds/level_1_gameover.wav', autoplay=False, loop=False)
success_sound = Audio('assets/sounds/level_1_mushroom-coin-poof.mp3', autoplay=False, loop=False)  # Reusing coin sound for success

app = Ursina()
# Remove the internal exit button
window.exit_button.enabled = False

# Set background to black for out-of-bounds area
window.color = color.black

# Load and play background music
bgm_path = os.path.join('assets', 'music', 'Level_1_bgm_In_Gloomy_Meditation.mp3')
pygame.mixer.music.load(bgm_path)
pygame.mixer.music.play(-1)  # -1 means loop indefinitely
pygame.mixer.music.set_volume(0.5)  # Set volume to 50%

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
        
        # Store base colors for consistent recreation
        self.base_color = color.rgba(200, 255, 180, 180)
        self.glow_color = color.rgba(200, 255, 180, 100)
        
        # Create the main particle
        super().__init__(
            model='sphere',
            scale=base_scale,
            color=self.base_color,
            **kwargs
        )
        
        # Add glow effect as a child entity
        self.glow = Entity(
            parent=self,
            model='sphere',
            scale=1.5,  # Slightly larger than parent
            color=self.glow_color,
            alpha=0.3 * glow_strength,
            double_sided=True  # Ensures glow is visible from all angles
        )
        
        # Store initial properties
        self.glow_strength = glow_strength
        self.base_alpha = 180
        self.glow_base_alpha = 100
        
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
        # Calculate distance to player
        dist_to_player = (Vec3(self.x, self.y, self.z) - Vec3(player.x, player.y, player.z)).length()
        
        # Dynamic update rate based on distance
        update_scale = min(1.0, 5.0 / (dist_to_player + 1))  # Closer = more frequent updates
        
        # Floating movement with sine wave drift, scaled by distance
        self.age += time.dt * update_scale
        drift = math.sin(self.age * self.float_speed + self.drift_offset) * 0.5
        
        # Movement scaled by distance
        movement_scale = max(0.2, min(1.0, 3.0 / dist_to_player))  # Smoother movement when closer
        self.x += (self.velocity.x + drift * 0.1) * time.dt * movement_scale
        self.y += self.velocity.y * time.dt * 0.5 * movement_scale
        self.z += (self.velocity.z + drift * 0.1) * time.dt * movement_scale
        
        # Pulsing size effect with distance-based intensity
        pulse_intensity = max(0.3, min(1.0, 2.0 / dist_to_player))
        pulse = math.sin(self.age * self.pulse_speed) * (self.pulse_magnitude * pulse_intensity) + 1
        self.scale = self.base_scale * pulse
        self.glow.scale = 1.5 + pulse * 0.2 * pulse_intensity  # Glow follows the pulse
        
        # Check distance from player
        dist_to_player = (Vec3(self.x, self.y, self.z) - Vec3(player.x, player.y, player.z)).length()
        max_distance = 20  # Maximum distance from player before forcing respawn
        
        # Force respawn if too far from player
        if dist_to_player > max_distance:
            self.respawn()
            return
            
        # Fade out near end of lifetime
        fade_start = 0.7  # Start fading at 70% of lifetime
        if self.age / self.lifetime > fade_start:
            fade_progress = (self.age / self.lifetime - fade_start) / (1 - fade_start)
            alpha = 1 - fade_progress
            # Update main particle color
            self.color = color.rgba(200, 255, 180, int(alpha * self.base_alpha))
            # Update glow effect
            self.glow.alpha = 0.3 * self.glow_strength * alpha
        else:
            # Maintain normal appearance when not fading
            self.color = self.base_color
            self.glow.color = self.glow_color
            self.glow.alpha = 0.3 * self.glow_strength
        
        # Ensure glow effect maintains proper scale relative to particle
        self.glow.scale = Vec3(1.5, 1.5, 1.5)
        
        # Add slight rotation for more dynamic appearance
        self.rotation_y += time.dt * random.uniform(-20, 20)
        
        # Reset particle when lifetime expires
        if self.age >= self.lifetime:
            self.respawn()
    
    def respawn(self):
        # Calculate spawn position relative to current player position
        angle = random.uniform(0, 6.28)
        radius = random.uniform(5, 15)
        
        # Get player's current position for respawn
        current_player_pos = Vec3(player.position)
        
        # Set new position around current player location
        self.position = Vec3(
            current_player_pos.x + math.cos(angle) * radius,
            random.uniform(0.5, 3),
            current_player_pos.z + math.sin(angle) * radius
        )
        
        # Reset particle properties
        self.age = 0
        self.velocity = Vec3(
            random.uniform(-0.5, 0.5),
            random.uniform(0.2, 0.8),
            random.uniform(-0.5, 0.5)
        )
        self.lifetime = random.uniform(5, 10)
        
        # Reset particle appearance
        self.color = self.base_color
        self.glow.color = self.glow_color
        self.glow.alpha = 0.3 * self.glow_strength
        
        # Ensure glow effect is properly scaled and visible
        self.glow.scale = Vec3(1.5, 1.5, 1.5)
        self.glow.enabled = True
        self.glow.visible = True
        
        # Add slight attraction towards player
        direction_to_player = (current_player_pos - self.position).normalized()
        self.velocity += direction_to_player * 0.2  # Slight bias towards player

# Create particle pool and list to store them
particles = []
particle_count = 50  # Number of particles in the scene

# Variables to track diagnostic mode
diagnostic_mode = False
prev_t_state = False

# Create player with sprite sheet animation
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
    position=(12, 0.25, -32) ,
    scale=1.5,
    rotation_x=90  # Rotate to face down for top-down view
)

player.origin = (0, -0.15)

# Create player glow/aura effect (circular)
player_glow = Entity(
    parent=player,
    model='circle',  # Changed to circle for round glow
    scale=2.2,  # Slightly larger than player
    position=(0, -0.05, 0),  # Slightly below player on Y axis to appear behind
    rotation_x=0,  # Match player's rotation
    color=color.rgba(150, 200, 255, 40),  # Soft blue glow - more transparent
    alpha=0.15,  # More transparent
    double_sided=True
)

# Glow animation properties
player_glow.pulse_time = 0
player_glow.base_scale = 2.2
player_glow.base_alpha = 0.15  # More transparent base alpha

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
speed = 10
gravity = 50
jump_speed = 25
velocity_z = 0  # Changed from velocity_y to velocity_z for Z-axis movement
on_ground = False  # Start in air to force falling
current_animation = 'idle'
facePosition = 'right'

# Jump cooldown
can_jump = True
double_jump = False
jump_cooldown = 2
jump_timer = 0

# Dash variables
is_dashing = False
dash_speed = 23
dash_duration = 0.25
dash_timer = 0
dash_cooldown = 1.0
can_dash = True
dash_cooldown_timer = 0

# Wall jump variables
on_wall = False
wall_jump_cooldown = 0.2
wall_jump_timer = 0

# Collision resolution settings
collision_push_distance = 0.05
max_push_attempts = 5

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

# Idle pulsing animation variables
red_coin.pulse_time = 0
green_coin.pulse_time = 0
blue_coin.pulse_time = 0
red_coin.base_scale = 1
green_coin.base_scale = 1
blue_coin.base_scale = 1

# Collection animation variables
red_coin.is_collecting = False
green_coin.is_collecting = False
blue_coin.is_collecting = False
red_coin.collect_time = 0
green_coin.collect_time = 0
blue_coin.collect_time = 0
red_coin.collect_duration = 0.5  # Duration of expand animation before disappearing
green_coin.collect_duration = 0.5
blue_coin.collect_duration = 0.5

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
    
    # Idle pulsing animation for red coin
    if red_coin.enabled and not red_coin.is_collecting:
        red_coin.pulse_time += time.dt * 3  # Speed of pulsing
        pulse_scale = red_coin.base_scale + math.sin(red_coin.pulse_time) * 0.15  # Pulse between 0.85 and 1.15
        red_coin.scale = (pulse_scale, pulse_scale)
    
    # Idle pulsing animation for green coin
    if green_coin.enabled and not green_coin.is_collecting:
        green_coin.pulse_time += time.dt * 3
        pulse_scale = green_coin.base_scale + math.sin(green_coin.pulse_time) * 0.15
        green_coin.scale = (pulse_scale, pulse_scale)
    
    # Idle pulsing animation for blue coin
    if blue_coin.enabled and not blue_coin.is_collecting:
        blue_coin.pulse_time += time.dt * 3
        pulse_scale = blue_coin.base_scale + math.sin(blue_coin.pulse_time) * 0.15
        blue_coin.scale = (pulse_scale, pulse_scale)
    
    # Collection animation for red coin
    if red_coin.is_collecting:
        red_coin.collect_time += time.dt
        # Expand animation (scale from 1 to 2.5)
        expand_progress = red_coin.collect_time / red_coin.collect_duration
        expand_scale = 1 + (expand_progress * 1.5)  # Grows from 1 to 2.5
        red_coin.scale = (expand_scale, expand_scale)
        
        # Disable after animation completes
        if red_coin.collect_time >= red_coin.collect_duration:
            red_coin.enabled = False
            red_coin.is_collecting = False
    
    # Collection animation for green coin
    if green_coin.is_collecting:
        green_coin.collect_time += time.dt
        expand_progress = green_coin.collect_time / green_coin.collect_duration
        expand_scale = 1 + (expand_progress * 1.5)
        green_coin.scale = (expand_scale, expand_scale)
        
        if green_coin.collect_time >= green_coin.collect_duration:
            green_coin.enabled = False
            green_coin.is_collecting = False
    
    # Collection animation for blue coin
    if blue_coin.is_collecting:
        blue_coin.collect_time += time.dt
        expand_progress = blue_coin.collect_time / blue_coin.collect_duration
        expand_scale = 1 + (expand_progress * 1.5)
        blue_coin.scale = (expand_scale, expand_scale)
        
        if blue_coin.collect_time >= blue_coin.collect_duration:
            blue_coin.enabled = False
            blue_coin.is_collecting = False

# Create camera positioned above the player for top-down view
camera.position = (0, 21, 0)  # Set default height to 21
camera.rotation_x = 90

# Zoom settings (only used in diagnostic mode)
min_height = 5
max_height = 1000
zoom_speed = 2

# Diagnostic view settings
diagnostic_base_height = 5  # Lower default diagnostic view height
diagnostic_min_zoom = 3
diagnostic_max_zoom = 1000  # Increased max zoom for more zoomed out view
diagnostic_zoom = 25  # Starting with a more zoomed out view

    # Score, lives and game state
game_data = load_game_data()
score = 0  # Mushroom coins collected in this level
lives = game_data["lives"]
is_game_over = False
is_game_completed = False
score_text = Text(
    text=f'Mushroom Coins collected: {score}',
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

guide_hint_text = Text(
    text='Hold "Y" for Guide',
    position=(0.35, 0.45),
    scale=1.2,
    origin=(0, 0),
    background=True,
    color=color.yellow
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
)

# Functions to handle navigation
def go_to_marketplace():
    import subprocess, sys, os
    venv_python = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                              'venv', 'Scripts', 'python.exe')
    if not os.path.exists(venv_python):
        venv_python = sys.executable
    
    subprocess.Popen([venv_python, 'marketplace.py'], 
                    cwd=os.path.dirname(os.path.abspath(__file__)))
    application.quit()
    sys.exit()

def go_to_main_menu():
    import subprocess, sys, os
    venv_python = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                              'venv', 'Scripts', 'python.exe')
    if not os.path.exists(venv_python):
        venv_python = sys.executable
    
    subprocess.Popen([venv_python, 'main_menu.py'],
                    cwd=os.path.dirname(os.path.abspath(__file__)))
    application.quit()
    sys.exit()

# Success screen elements
success_panel = Entity(
    model='quad',
    color=color.black66,
    scale=(2, 1),
    position=(0, 0),
    parent=camera.ui,
    enabled=False
)

success_text = Text(
    text='SUCCESS!',
    scale=4,
    origin=(0, 0),
    position=(0, 0.2),
    color=color.green,
    parent=camera.ui,
    enabled=False
)

time_text = Text(
    text='Time: 0:00',
    scale=2,
    origin=(0, 0),
    position=(0, 0),
    color=color.white,
    parent=camera.ui,
    enabled=False
)

marketplace_button = Button(
    text='Go to Marketplace',
    color=color.azure,
    scale=(0.3, 0.1),
    position=(-0.2, -0.2),
    parent=camera.ui,
    enabled=False
)

menu_button = Button(
    text='Main Menu',
    color=color.orange,
    scale=(0.3, 0.1),
    position=(0.2, -0.2),
    parent=camera.ui,
    enabled=False)# Store initial player position for respawn
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

# Info/Guide Panel (shown when Y is held)
info_panel = Entity(
    model='quad',
    color=color.black66,
    scale=(2, 1),
    position=(0, 0),
    parent=camera.ui,
    enabled=False
)

info_title = Text(
    text='GAME GUIDE',
    scale=3,
    origin=(0, 0),
    position=(0, 0.4),
    color=color.yellow,
    parent=camera.ui,
    enabled=False
)

info_text = Text(
    text='''
1) Collect 3 Mushroom Coins to pass
   They're located throughout the map

2) Be careful! Take damage from spikes
   three times and it's game over!

3) Control movements:
   - A/D: Move left/right
   - Space: Jump
   - Shift: Dash
   - S: Duck (on ground) / Fast fall (in air)

4) Q/E or mouse scroll to zoom in and out

5) Press "T" to toggle diagnostic view
   and see what happens!
''',
    scale=1.5,
    origin=(0, 0),
    position=(0, -0.05),
    color=color.white,
    parent=camera.ui,
    enabled=False,
    line_height=1.2
)

# Track Y key state for info display
show_info = False
prev_y_state = False

def check_coin_collection(coin, player):
    # Calculate distance between player and coin
    distance = (coin.position - player.position).length()
    # If player is close enough to coin (within 1 unit)
    return distance < 1

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
        if not check_collision(Vec3(new_x, player.y, new_z)):
            return new_x, new_z
    
    # If all else fails, return to original position
    return original_x, original_z

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
        if check_collision(Vec3(px, player.y, pz)):
            return True
    return False

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
        
        # Check if it's near the wall color (ED1C24 - red) with some tolerance
        is_wall = (abs(color[0] - 237/255) < 0.1 and 
                  abs(color[1] - 28/255) < 0.1 and 
                  abs(color[2] - 36/255) < 0.1)
        
        # Check if it's near the trap color (22C722 - green) with some tolerance
        is_trap = (abs(color[0] - 34/255) < 0.1 and 
                  abs(color[1] - 199/255) < 0.1 and 
                  abs(color[2] - 34/255) < 0.1)
        
        return is_wall
    except Exception as e:
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
            
            # Play damage sound
            damage_sound.play()
            
            # Save game data with updated lives
            game_data["lives"] = lives
            game_data["score"] = calculate_score(game_data["mushrooms"], lives)
            save_game_data(game_data)
            
            # Check if game over
            if lives <= 0:
                is_game_over = True
                show_game_over()
                return True
                
            # Reset position to initial spawn point
            player.position = initial_player_position
            # Reset velocity and animation state
            return True
            
        return False
    except Exception as e:
        print(f"Trap check error: {e}")
        return False

def update():
    global current_animation, velocity_z, on_ground, facePosition
    global can_jump, jump_timer, is_dashing, dash_timer, can_dash, dash_cooldown_timer
    global on_wall, wall_jump_timer

    moving = False
    squating = False
    #character value
    global score, diagnostic_mode, prev_t_state, show_info, prev_y_state
    
    # Skip all updates if game is completed (except for animations)
    if is_game_completed:
        return
        
    # Update coin animation
    update_coin_animation()
    
    # Update player glow animation (pulsing effect)
    player_glow.pulse_time += time.dt * 2  # Pulse speed
    pulse = math.sin(player_glow.pulse_time) * 0.15  # Pulse range
    player_glow.scale = player_glow.base_scale + pulse
    
    # Adjust glow intensity based on player state
    if is_dashing:
        # Brighter and more intense during dash
        player_glow.color = color.rgba(180, 220, 255, 60)
        player_glow.alpha = 0.25
    elif not on_ground:
        # Slightly brighter when jumping/in air
        player_glow.color = color.rgba(160, 210, 255, 50)
        player_glow.alpha = 0.2
    else:
        # Normal subtle glow
        player_glow.color = color.rgba(150, 200, 255, 40)
        player_glow.alpha = 0.15
    
    # Check if player is on a trap
    if check_trap_collision():
        velocity_z = 0
        on_ground = True
        is_dashing = False
    
    # Toggle diagnostic mode when T is pressed (not held)
    if held_keys['t'] and not prev_t_state:
        diagnostic_mode = not diagnostic_mode
    prev_t_state = held_keys['t']
    
    # Show info panel when Y is held
    if held_keys['y']:
        if not show_info:
            show_info = True
            info_panel.enabled = True
            info_title.enabled = True
            info_text.enabled = True
    else:
        if show_info:
            show_info = False
            info_panel.enabled = False
            info_title.enabled = False
            info_text.enabled = False
    
    # Always update collision info at current position for diagnostic display
    if diagnostic_mode:
        check_collision(player.position)
    
    # Update camera rotation in diagnostic mode
    if diagnostic_mode:
        camera.rotation_x = lerp(camera.rotation_x, 45, time.dt * 5)
    else:
        camera.rotation_x = lerp(camera.rotation_x, 90, time.dt * 5)
    
    # Check coin collection
    if red_coin.enabled and not red_coin.is_collecting and check_coin_collection(red_coin, player):
        red_coin.is_collecting = True
        red_coin.collect_time = 0
        score += 1
        score_text.text = f'Mushroom Coins collected: {score}'
        mushroom_coin_sound.play()
        
    if green_coin.enabled and not green_coin.is_collecting and check_coin_collection(green_coin, player):
        green_coin.is_collecting = True
        green_coin.collect_time = 0
        score += 1
        score_text.text = f'Mushroom Coins collected: {score}'
        mushroom_coin_sound.play()
        
    if blue_coin.enabled and not blue_coin.is_collecting and check_coin_collection(blue_coin, player):
        blue_coin.is_collecting = True
        blue_coin.collect_time = 0
        score += 1
        score_text.text = f'Mushroom Coins collected: {score}'
        mushroom_coin_sound.play()
    
    # Check for game success (all 3 mushrooms collected)
    if score == 3:
        show_success()
    
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
        # Normal mode - follow player with Q/E zoom controls
        if held_keys['q']:
            camera.y += zoom_speed * time.dt * 10
            camera.y = clamp(camera.y, min_height, max_height)
        if held_keys['e']:
            camera.y -= zoom_speed * time.dt * 10
            camera.y = clamp(camera.y, min_height, max_height)
        camera.position = (player.x, camera.y, player.z)
    
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
        if key == 'scroll up':
            camera.y -= zoom_speed
            camera.y = clamp(camera.y, min_height, max_height)
        if key == 'scroll down':
            camera.y += zoom_speed
            camera.y = clamp(camera.y, min_height, max_height)

# Function to show success screen
def show_success():
    global total_time, is_game_completed, game_data
    if not is_game_completed:  # Only calculate time and show screen if not already completed
        is_game_completed = True
        total_time = int(time.time() - start_time)
        minutes = total_time // 60
        seconds = total_time % 60
        
        # Update game data
        game_data["mushrooms"] += score  # Add collected mushrooms
        game_data["mushrooms"] = min(game_data["mushrooms"], 3)  # Cap at 3 mushrooms
        game_data["lives"] = lives  # Update remaining lives
        game_data["score"] = calculate_score(game_data["mushrooms"], lives)  # Update total score
        if 2 not in game_data["unlocked_levels"]:
            game_data["unlocked_levels"].append(2)  # Unlock level 2
        save_game_data(game_data)
        
        success_panel.enabled = True
        success_text.enabled = True
        time_text.enabled = True
        marketplace_button.enabled = True
        menu_button.enabled = True
        time_text.text = f'Time: {minutes}:{seconds:02d}'
        # Disable player movement
        player.enabled = False
        # Play success sound
        success_sound.play()

# Function to show game over screen
def show_game_over():
    global game_data
    game_over_panel.enabled = True
    # Update and save game data
    game_data["lives"] = lives
    game_data["score"] = calculate_score(game_data["mushrooms"], lives)
    save_game_data(game_data)
    game_over_text.enabled = True
    retry_button.enabled = True
    # Disable player movement
    player.enabled = False
    # Play game over sound
    gameover_sound.play()

def reset_game():
    global lives, score, is_game_over, is_game_completed, start_time, game_data
    global velocity_z, on_ground, current_animation, facePosition
    # Reload game data
    game_data = load_game_data()
    # Reset lives to 3 when restarting after game over
    lives = 3
    game_data["lives"] = 3
    save_game_data(game_data)
    # Reset game state
    score = 0  # Reset mushrooms collected in this level
    is_game_over = False
    is_game_completed = False
    start_time = time.time()
    lives_text.text = f'Lives: {lives}'
    score_text.text = f'Mushroom Coins collected: {score}'
    
    # Reset player physics
    velocity_z = 0
    on_ground = False
    current_animation = 'idle'
    facePosition = 'right'
    
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
    
    # Hide success screen
    success_panel.enabled = False
    success_text.enabled = False
    time_text.enabled = False
    marketplace_button.enabled = False
    menu_button.enabled = False

# Set up button click handlers
retry_button.on_click = reset_game
marketplace_button.on_click = go_to_marketplace
menu_button.on_click = go_to_main_menu

# Initialize start time for the game timer
start_time = time.time()

# Add ambient light for better visibility
AmbientLight(color=color.rgba(255, 255, 255, 0.5))

app.run()
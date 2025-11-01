from ursina import *
import numpy as np
from PIL import Image

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
    alpha=1  # Full opacity for black parts
)

# Set shader for the upper layer to only show black parts
from ursina.shaders import lit_with_shadows_shader
upper_layer.shader = lit_with_shadows_shader
upper_layer.set_shader_input('texture_scale', Vec2(1,1))
upper_layer.set_shader_input('alpha_texture', upper_layer.texture)
upper_layer.texture_scale = (1,1)

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

# Create player (yellow circle blob)
player = Entity(
    model='sphere',
    color=color.yellow,
    scale=(0.5, 0.5, 0.5),
    position=(0, 0.25, 0),
    collider='sphere'
)

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
camera.position = (0, 50, 0)
camera.rotation_x = 90

# Movement settings
move_speed = 5

# Zoom settings
min_height = 5
max_height = 100
zoom_speed = 2

# Diagnostic view settings
diagnostic_base_height = 5  # Lower default diagnostic view height
diagnostic_min_zoom = 3
diagnostic_max_zoom = 40  # Increased max zoom for more zoomed out view
diagnostic_zoom = 25  # Starting with a more zoomed out view

# Score display
score = 0
score_text = Text(
    text='Mushroom Coins collected: 0',
    position=(-0.5, 0.45),
    scale=1.2,
    origin=(0, 0),
    background=True
)

# Zoom level indicator
zoom_indicator = Text(
    text=f'Height: {int(camera.y)}',
    position=(0.7, 0.45),
    scale=1.2,
    origin=(0, 0),
    background=True,
    enabled=False  # Hidden by default
)

def check_coin_collection(coin, player):
    # Calculate distance between player and coin
    distance = (coin.position - player.position).length()
    # If player is close enough to coin (within 1 unit)
    return distance < 1

def update():
    global score, diagnostic_mode, prev_t_state
    # Update coin animation
    update_coin_animation()
    
    # Toggle diagnostic mode when T is pressed (not held)
    if held_keys['t'] and not prev_t_state:
        diagnostic_mode = not diagnostic_mode
    prev_t_state = held_keys['t']
    
    # Update UI elements based on diagnostic mode
    collision_debug.enabled = diagnostic_mode
    zoom_indicator.enabled = diagnostic_mode
    
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
    
    # WASD movement for player
    move_direction = Vec3(0, 0, 0)
    
    if held_keys['w']:
        move_direction.z += 1
    if held_keys['s']:
        move_direction.z -= 1
    if held_keys['a']:
        move_direction.x -= 1
    if held_keys['d']:
        move_direction.x += 1
    
    # Normalize and calculate new position
    if move_direction.length() > 0:
        move_direction = move_direction.normalized()
        new_position = player.position + move_direction * move_speed * time.dt
        
        # Convert world position to UV coordinates
        scale_x, _, scale_z = collision_ground.scale
        # Adjust the conversion to match texture coordinates
        tex_x = int((new_position.x / scale_x + 0.5) * collision_ground.texture.width)
        tex_z = int((new_position.z / scale_z + 0.5) * collision_ground.texture.height)
        
        # Check if the new position would hit a wall (red color: #ED1C24)
        try:
            # Get color at position
            color = collision_ground.texture.get_pixel(tex_x, tex_z)
            
            # Debug color information
            collision_debug.text = f'Pos: ({tex_x}, {tex_z}) Color: R:{int(color[0]*255)} G:{int(color[1]*255)} B:{int(color[2]*255)}'
            
            # Check if it's near the wall color (ED1C24) with some tolerance
            is_wall = (abs(color[0] - 237/255) < 0.1 and 
                      abs(color[1] - 28/255) < 0.1 and 
                      abs(color[2] - 36/255) < 0.1)
            
            if not is_wall:
                player.position = new_position
        except Exception as e:
            collision_debug.text = f'Error: {str(e)}'
            # If we can't get the pixel color (out of bounds), don't move
            pass
    
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
        camera_offset = -(diagnostic_zoom * 0.25)  # Further reduced offset scale
        
        camera.position = (
            player.x, 
            player.y + (diagnostic_zoom * 0.3),  # Further reduced height multiplier
            player.z + camera_offset
        )
    else:
        # Normal mode camera and zoom
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
            diagnostic_zoom -= zoom_speed * 4  # Increased scroll sensitivity
            diagnostic_zoom = clamp(diagnostic_zoom, diagnostic_min_zoom, diagnostic_max_zoom)
        if key == 'scroll down':
            diagnostic_zoom += zoom_speed * 4  # Increased scroll sensitivity
            diagnostic_zoom = clamp(diagnostic_zoom, diagnostic_min_zoom, diagnostic_max_zoom)
    else:
        if key == 'scroll up':
            camera.y -= zoom_speed
            camera.y = clamp(camera.y, min_height, max_height)
        if key == 'scroll down':
            camera.y += zoom_speed
            camera.y = clamp(camera.y, min_height, max_height)

# Add ambient light for better visibility
AmbientLight(color=color.rgba(255, 255, 255, 0.5))

app.run()
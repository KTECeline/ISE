from ursina import *

app = Ursina()
# Remove the internal exit button
window.exit_button.enabled = False

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

# Debug text for collision checking
collision_debug = Text(
    text='No collision data',
    position=(-0.5, 0.4),
    scale=1.2,
    origin=(0, 0),
    background=True
)

# Create player (yellow circle blob)
player = Entity(
    model='sphere',
    color=color.yellow,
    scale=(0.5, 0.5, 0.5),
    position=(-20, 0.25, 0),
    collider='sphere'
)

# Create camera positioned above the player for top-down view
camera.position = (0, 50, 0)
camera.rotation_x = 90

# Movement settings
move_speed = 5

# Zoom settings
min_height = 5
max_height = 100
zoom_speed = 2

# Camera controls info
info_text = Text(
    text='Top-down view | WASD to move | Q/E or scroll to zoom',
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
    background=True
)

def update():
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
    
    # Camera follows player
    camera.position = (player.x, camera.y, player.z)
    
    # Zoom with Q and E keys
    if held_keys['q']:
        camera.y += zoom_speed * time.dt * 10
        camera.y = clamp(camera.y, min_height, max_height)
    
    if held_keys['e']:
        camera.y -= zoom_speed * time.dt * 10
        camera.y = clamp(camera.y, min_height, max_height)
    
    # Update zoom indicator
    zoom_indicator.text = f'Height: {int(camera.y)}'

def input(key):
    if key == 'escape':
        application.quit()
    
    # Zoom with scroll wheel
    if key == 'scroll up':
        camera.y -= zoom_speed
        camera.y = clamp(camera.y, min_height, max_height)
    
    if key == 'scroll down':
        camera.y += zoom_speed
        camera.y = clamp(camera.y, min_height, max_height)

# Add ambient light for better visibility
AmbientLight(color=color.rgba(255, 255, 255, 0.5))

app.run()
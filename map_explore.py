from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

app = Ursina()

# Create a ground plane with your large image (8100 x 7500)
# The image will be scaled proportionally
ground = Entity(
    model='plane',
    # texture='assets/textures/map/Fungal_Wastes_50.png',  # Your PNG image here
    texture='assets/textures/map/Fungal_Wastes_100.png',  # Your PNG image here
    scale=(81, 1, 75),  # Proportional to image dimensions (8100:7500)
    collider='box',
    position=(0, 0, 0)
)

# Create a player controller - starting high up for zoomed out view
player = FirstPersonController(
    position=(0, 50, 0),  # Start zoomed out (high up)
    speed=5,
    mouse_sensitivity=Vec2(40, 40),
    gravity=0  # Disable gravity for smooth zoom
)

# Lock camera directly above (top-down view, no rotation)
player.camera_pivot.rotation_x = 90  # Directly above
player.camera_pivot.rotation_y = 0
player.camera_pivot.rotation_z = 0

# Disable mouse camera rotation
player.mouse_sensitivity = Vec2(0, 0)

# Zoom settings
min_height = 0.5  # Closest zoom (much closer now)
max_height = 100  # Farthest zoom (highest height)
zoom_speed = 2

# Camera controls info
info_text = Text(
    text='3D-down view | Press T to toggle back',
    position=(-0.5, 0.45),
    scale=1.2,
    origin=(0, 0),
    background=True
)

# Zoom level indicator
zoom_indicator = Text(
    text=f'Height: {int(player.y)}',
    position=(0.7, 0.45),
    scale=1.2,
    origin=(0, 0),
    background=True
)

def update():
    # Alternative zoom with Q and E keys
    if held_keys['q']:
        player.y += zoom_speed * time.dt * 10
        player.y = clamp(player.y, min_height, max_height)
    
    if held_keys['e']:
        player.y -= zoom_speed * time.dt * 10
        player.y = clamp(player.y, min_height, max_height)
    
    # Update zoom indicator
    zoom_indicator.text = f'Height: {int(player.y)}'
    
    # Adjust movement speed based on zoom level (faster when zoomed out)
    player.speed = 5 + (player.y / 10)

def input(key):
    if key == 'escape':
        application.quit()
    
    # Zoom with scroll wheel
    if key == 'scroll up':
        player.y -= zoom_speed
        player.y = clamp(player.y, min_height, max_height)
    
    if key == 'scroll down':
        player.y += zoom_speed
        player.y = clamp(player.y, min_height, max_height)
    
    # Toggle between angled 2.5D and top-down view
    if key == 't':
        if player.camera_pivot.rotation_x == 60:
            player.camera_pivot.rotation_x = 90  # Pure top-down
            info_text.text = 'Top-down view | Press T to toggle back'
        else:
            player.camera_pivot.rotation_x = 60  # 2.5D angled view
            info_text.text = '3D-down view | Press T to toggle back'

# Optional: Add ambient light for better visibility
AmbientLight(color=color.rgba(255, 255, 255, 0.5))

app.run()
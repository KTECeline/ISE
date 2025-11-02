import pygame

def build_collision_grid(collision_surface, WORLD_WIDTH, WORLD_HEIGHT, COLLISION_COLOR, TOLERANCE):
    """Build a coarse collision grid for performance optimization."""
    _COLLISION_CELL = 8
    _collision_grid_w = (WORLD_WIDTH + _COLLISION_CELL - 1) // _COLLISION_CELL
    _collision_grid_h = (WORLD_HEIGHT + _COLLISION_CELL - 1) // _COLLISION_CELL
    
    collision_grid = bytearray(_collision_grid_w * _collision_grid_h)
    _sample_step = 2
    
    for cy in range(_collision_grid_h):
        y0 = cy * _COLLISION_CELL
        y1 = min(WORLD_HEIGHT, y0 + _COLLISION_CELL)
        for cx in range(_collision_grid_w):
            x0 = cx * _COLLISION_CELL
            x1 = min(WORLD_WIDTH, x0 + _COLLISION_CELL)
            marked = 0
            for yy in range(y0, y1, _sample_step):
                found = False
                for xx in range(x0, x1, _sample_step):
                    pixel = collision_surface.get_at((xx, yy))
                    if (abs(pixel[0] - COLLISION_COLOR[0]) < TOLERANCE and
                        abs(pixel[1] - COLLISION_COLOR[1]) < TOLERANCE and
                        abs(pixel[2] - COLLISION_COLOR[2]) < TOLERANCE and
                        pixel[3] > 0):
                        marked = 1
                        found = True
                        break
                if found:
                    break
            collision_grid[cy * _collision_grid_w + cx] = marked
    
    return collision_grid, _COLLISION_CELL, _collision_grid_w, _collision_grid_h

def check_collision(world_x, world_y, radius, collision_surface, collision_grid, 
                   _COLLISION_CELL, _collision_grid_w, _collision_grid_h, 
                   WORLD_WIDTH, WORLD_HEIGHT, COLLISION_COLOR, TOLERANCE):
    """Check if position overlaps red pixels in collision map."""
    min_cx = max(0, int((world_x - radius) // _COLLISION_CELL))
    max_cx = min(_collision_grid_w - 1, int((world_x + radius) // _COLLISION_CELL))
    min_cy = max(0, int((world_y - radius) // _COLLISION_CELL))
    max_cy = min(_collision_grid_h - 1, int((world_y + radius) // _COLLISION_CELL))
    
    step = 2
    for cy in range(min_cy, max_cy + 1):
        base_row = cy * _collision_grid_w
        for cx in range(min_cx, max_cx + 1):
            if collision_grid[base_row + cx] == 0:
                continue
                
            cell_x0 = cx * _COLLISION_CELL
            cell_y0 = cy * _COLLISION_CELL
            x0 = max(int(world_x - radius), cell_x0)
            x1 = min(int(world_x + radius), min(cell_x0 + _COLLISION_CELL - 1, WORLD_WIDTH - 1))
            y0 = max(int(world_y - radius), cell_y0)
            y1 = min(int(world_y + radius), min(cell_y0 + _COLLISION_CELL - 1, WORLD_HEIGHT - 1))
            
            for px in range(x0, x1 + 1, step):
                for py in range(y0, y1 + 1, step):
                    if (px - world_x) ** 2 + (py - world_y) ** 2 > radius * radius:
                        continue
                    pixel = collision_surface.get_at((px, py))
                    if (abs(pixel[0] - COLLISION_COLOR[0]) < TOLERANCE and
                        abs(pixel[1] - COLLISION_COLOR[1]) < TOLERANCE and
                        abs(pixel[2] - COLLISION_COLOR[2]) < TOLERANCE and
                        pixel[3] > 0):
                        return True
    return False
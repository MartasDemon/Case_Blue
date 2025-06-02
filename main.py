import pygame
import math
import random
import os
from game_objects import InfantryUnit, Tile, TERRAIN_TYPES, TERRAIN_COLORS

# === CONFIGURATION ===
IMAGE_PATHS = {
    "ger_infantry": "images/ger_infantry1.jpg"
}

# === HEX UTILS ===
def hex_to_pixel(q, r, size):
    # Pointy topped hex coordinates
    x = size * math.sqrt(3) * (q + r / 2)
    y = size * 3/2 * r
    return x, y

def pixel_to_hex(x, y, size):
    q = (x * math.sqrt(3)/3 - y / 3) / size
    r = y * 2/3 / size
    return hex_round(q, r)

def hex_round(q, r):
    x = q
    z = r
    y = -x - z
    rx, ry, rz = round(x), round(y), round(z)
    x_diff, y_diff, z_diff = abs(rx - x), abs(ry - y), abs(rz - z)
    if x_diff > y_diff and x_diff > z_diff:
        rx = -ry - rz
    elif y_diff > z_diff:
        ry = -rx - rz
    else:
        rz = -rx - ry
    return int(rx), int(rz)

def get_neighbors(q, r):
    directions = [(+1, 0), (+1, -1), (0, -1), (-1, 0), (-1, +1), (0, +1)]
    return [(q + dq, r + dr) for dq, dr in directions]

# === INIT PYGAME ===
pygame.init()
screen_width, screen_height = 1280, 720
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Hex Strategy Game")
font = pygame.font.SysFont(None, 24)
clock = pygame.time.Clock()

# === LOAD IMAGES ===
images = {}
for key, path in IMAGE_PATHS.items():
    if os.path.exists(path):
        img = pygame.image.load(path)
        img = pygame.transform.scale(img, (200, 150))
        images[key] = img
    else:
        print(f"Missing image: {path}")

# === MAP GENERATION ===
MAP_RADIUS = 6
base_hex_size = 40
hex_size = base_hex_size
tile_map = {}
for q in range(-MAP_RADIUS, MAP_RADIUS + 1):
    for r in range(-MAP_RADIUS, MAP_RADIUS + 1):
        if -q - r >= -MAP_RADIUS and -q - r <= MAP_RADIUS:
            terrain = random.choice(TERRAIN_TYPES)
            tile_map[(q, r)] = Tile(q, r, terrain)

# === PLAYER UNIT ===
units = []
player_unit = InfantryUnit("German Infantry", 100, 20, 70, 5, 10, "ger_infantry", range_=1, is_enemy=False)
player_unit.q, player_unit.r = 0, 0
spawn_tile = tile_map[(0, 0)]
spawn_tile.unit = player_unit
units.append(player_unit)

# === ENEMY UNIT ===
enemy_units = []
enemy_unit = InfantryUnit("Russian Infantry", 100, 20, 60, 4, 10, "ger_infantry", range_=1, is_enemy=True)
enemy_unit.q, enemy_unit.r = None, None
for (q, r), tile in tile_map.items():
    if tile.unit is None and abs(q) + abs(r) > 8:
        tile.unit = enemy_unit
        enemy_unit.q, enemy_unit.r = q, r
        enemy_units.append(enemy_unit)
        break

selected_unit = None

# === CAMERA & ZOOM ===
camera_offset_x, camera_offset_y = screen_width // 2, screen_height // 2 - 100
dragging = False
drag_start_pos = (0, 0)
camera_start_offset = (camera_offset_x, camera_offset_y)

min_hex_size, max_hex_size = 20, 80

# === DRAW FUNCTIONS ===
def draw_hex(q, r, color, size, surface, border_color=(0, 0, 0)):
    # Pointy topped hex points
    cx, cy = hex_to_pixel(q, r, size)
    cx += camera_offset_x
    cy += camera_offset_y
    points = [(cx + size * math.cos(math.radians(60 * i - 30)),
               cy + size * math.sin(math.radians(60 * i - 30))) for i in range(6)]
    pygame.draw.polygon(surface, color, points)
    pygame.draw.polygon(surface, border_color, points, 2)
    return pygame.Rect(min(p[0] for p in points), min(p[1] for p in points), size * 2, size * 2)

def draw_map():
    tile_rects = {}
    for (q, r), tile in tile_map.items():
        color = TERRAIN_COLORS[tile.terrain_type]
        rect = draw_hex(q, r, color, hex_size, screen)
        tile_rects[(q, r)] = rect
        if tile.unit:
            cx, cy = hex_to_pixel(q, r, hex_size)
            cx += camera_offset_x
            cy += camera_offset_y
            color = (255, 255, 0) if not tile.unit.is_enemy else (255, 0, 0)
            pygame.draw.circle(screen, color, (int(cx), int(cy)), max(8, int(hex_size / 4)), 3)
    return tile_rects

def draw_unit_info(unit):
    panel_height = 150
    pygame.draw.rect(screen, (30, 30, 30), (0, screen_height - panel_height, screen_width, panel_height))
    if unit.image_key in images:
        screen.blit(images[unit.image_key], (20, screen_height - panel_height + 10))
    stats = [
        f"Name: {unit.name}",
        f"Health: {unit.health}/{unit.base_health}",
        f"Soldiers: {unit.base_soldiers}",
        f"Damage: {unit.base_damage}",
        f"Morale: {unit.base_morale}",
        f"Agility: {unit.agility_points}/{unit.base_agility}"
    ]
    for i, line in enumerate(stats):
        text = font.render(line, True, (255, 255, 255))
        screen.blit(text, (240, screen_height - panel_height + 10 + i * 25))

def draw_end_turn_button():
    btn_rect = pygame.Rect(screen_width - 150, screen_height - 50, 130, 40)
    pygame.draw.rect(screen, (100, 100, 255), btn_rect)
    pygame.draw.rect(screen, (255, 255, 255), btn_rect, 2)
    text = font.render("End Turn", True, (255, 255, 255))
    screen.blit(text, (btn_rect.x + 20, btn_rect.y + 10))
    return btn_rect

# === LOGIC ===
def handle_tile_click(pos, tile_rects):
    global selected_unit
    for (q, r), rect in tile_rects.items():
        if rect.collidepoint(pos):
            tile = tile_map[(q, r)]

            if selected_unit:
                dist = max(abs(q - selected_unit.q), abs(r - selected_unit.r), abs((-selected_unit.q - selected_unit.r) - (-q - r)))
                if tile.unit is None and dist <= selected_unit.range and selected_unit.agility_points >= 1:
                    # Move unit
                    tile_map[(selected_unit.q, selected_unit.r)].unit = None
                    selected_unit.q, selected_unit.r = q, r
                    selected_unit.agility_points -= 1
                    tile.unit = selected_unit
                    return
                elif tile.unit and tile.unit != selected_unit and tile.unit.is_enemy != selected_unit.is_enemy:
                    # Attack
                    if dist <= selected_unit.range and selected_unit.agility_points >= 2:
                        damage = selected_unit.base_damage
                        tile.unit.health -= damage
                        print(f"{selected_unit.name} attacks {tile.unit.name} for {damage} damage.")
                        if tile.unit.health <= 0:
                            print(f"{tile.unit.name} has been defeated!")
                            tile.unit = None
                        selected_unit.agility_points -= 2
                        return

            if tile.unit and not tile.unit.is_enemy:
                selected_unit = tile.unit
                return

def ai_turn():
    for enemy in enemy_units:
        if enemy.health <= 0:
            continue
        enemy.agility_points = enemy.base_agility
        while enemy.agility_points >= 2:
            # Attack player units in range
            attacked = False
            for (q, r), tile in tile_map.items():
                if tile.unit and not tile.unit.is_enemy:
                    dist = max(abs(q - enemy.q), abs(r - enemy.r), abs((-enemy.q - enemy.r) - (-q - r)))
                    if dist <= enemy.range:
                        damage = enemy.base_damage
                        tile.unit.health -= damage
                        print(f"{enemy.name} attacks {tile.unit.name} for {damage} damage.")
                        print("we are under fire")
                        if tile.unit.health <= 0:
                            print(f"{tile.unit.name} has been defeated!")
                            tile.unit = None
                        enemy.agility_points -= 2
                        attacked = True
                        break
            if attacked:
                continue

            # Move closer to player units
            moved = False
            for nq, nr in get_neighbors(enemy.q, enemy.r):
                if (nq, nr) in tile_map and tile_map[(nq, nr)].unit is None:
                    tile_map[(enemy.q, enemy.r)].unit = None
                    enemy.q, enemy.r = nq, nr
                    tile_map[(nq, nr)].unit = enemy
                    enemy.agility_points -= 1
                    moved = True
                    break
            if not moved:
                break

# === MAIN LOOP ===
running = True
turn_player = True

while running:
    screen.fill((10, 10, 20))
    tile_rects = draw_map()

    if selected_unit:
        draw_unit_info(selected_unit)

    end_turn_btn = draw_end_turn_button()
    pygame.display.flip()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                if end_turn_btn.collidepoint(event.pos):
                    turn_player = not turn_player
                    if turn_player:
                        for unit in units:
                            unit.agility_points = unit.base_agility
                    else:
                        ai_turn()
                elif turn_player:
                    handle_tile_click(event.pos, tile_rects)
                # Start dragging for map
                dragging = True
                drag_start_pos = event.pos
                camera_start_offset = (camera_offset_x, camera_offset_y)

            elif event.button == 4:  # Mouse wheel up - zoom in
                hex_size = min(max_hex_size, hex_size + 2)
            elif event.button == 5:  # Mouse wheel down - zoom out
                hex_size = max(min_hex_size, hex_size - 2)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                dragging = False

        elif event.type == pygame.MOUSEMOTION and dragging:
            mx, my = event.pos
            dx = mx - drag_start_pos[0]
            dy = my - drag_start_pos[1]
            camera_offset_x = camera_start_offset[0] + dx
            camera_offset_y = camera_start_offset[1] + dy

    clock.tick(60)

pygame.quit()

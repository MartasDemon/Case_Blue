import pygame
import math
import random
import os
from game_objects import InfantryUnit, TankUnit, Tile, TERRAIN_TYPES, TERRAIN_COLORS
from pygame import mixer

# === CONFIGURATION ===
IMAGE_PATHS = {
    "ger_infantry": "images/geônk1.jpg"
}

# === UI CONSTANTS ===
BUTTON_HEIGHT = 30
BUTTON_WIDTH = 150
MENU_PADDING = 5
MENU_BACKGROUND = (40, 40, 40)
MENU_HOVER = (60, 60, 60)
MENU_TEXT = (255, 255, 255)
MENU_BORDER = (200, 200, 200)

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
mixer.init()
screen_width, screen_height = 1280, 720
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Hex Strategy Game")
font = pygame.font.SysFont(None, 24)
clock = pygame.time.Clock()

# Create a simple gradient background
def create_gradient_background():
    background = pygame.Surface((screen_width, screen_height))
    for y in range(screen_height):
        # Create a dark blue to black gradient
        color = (0, 0, int(50 * (1 - y/screen_height)))
        pygame.draw.line(background, color, (0, y), (screen_width, y))
    return background

# Create the background
background = create_gradient_background()

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

# Add a tank unit
tank_unit = TankUnit("German Tank", 200, 40, 80, 3, 5, "ger_tank", range_=2, armor=50, armor_penetration=30, is_enemy=False)
tank_unit.q, tank_unit.r = 1, 0
tile_map[(1, 0)].unit = tank_unit
units.append(tank_unit)

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
action_menu_active = False
action_menu_pos = None
waiting_for_target = False
current_action = None

# === CAMERA & ZOOM ===
camera_offset_x, camera_offset_y = screen_width // 2, screen_height // 2 - 100
dragging = False
drag_start_pos = (0, 0)
camera_start_offset = (camera_offset_x, camera_offset_y)

min_hex_size, max_hex_size = 20, 80

# === MENU & MISSION SYSTEM ===
MENU_STATE_MAIN = 0
MENU_STATE_MISSION_SELECT = 1
MENU_STATE_SETTINGS = 2
MENU_STATE_GAME = 3
menu_state = MENU_STATE_MAIN
selected_mission = 0

# Menu button positions
menu_buttons = [
    ("Select Mission", (screen_width//2-100, screen_height//2-60, 200, 50)),
    ("Settings", (screen_width//2-100, screen_height//2, 200, 50)),
    ("Quit", (screen_width//2-100, screen_height//2+60, 200, 50)),
]
mission_buttons = [
    ("Mission 1", (screen_width//2-100, screen_height//2-40, 200, 50)),
    ("Mission 2", (screen_width//2-100, screen_height//2+20, 200, 50)),
    ("Back", (screen_width//2-100, screen_height//2+80, 200, 40)),
]
settings_buttons = [
    ("Back", (screen_width//2-100, screen_height//2+80, 200, 40)),
]

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
        if tile.smoke:
            color = (255, 255, 255)  # White color for smoke
        rect = draw_hex(q, r, color, hex_size, screen)
        tile_rects[(q, r)] = rect
        if tile.unit:
            cx, cy = hex_to_pixel(q, r, hex_size)
            cx += camera_offset_x
            cy += camera_offset_y
            color = (255, 255, 0) if not tile.unit.is_enemy else (255, 0, 0)
            pygame.draw.circle(screen, color, (int(cx), int(cy)), max(8, int(hex_size / 4)), 3)
            
            # Draw action indicator if unit is selected and waiting for target
            if tile.unit == selected_unit and waiting_for_target:
                pygame.draw.circle(screen, (0, 255, 0), (int(cx), int(cy)), max(12, int(hex_size / 3)), 2)
    return tile_rects

def draw_action_menu():
    if not action_menu_active or not action_menu_pos:
        return

    menu_items = []
    if selected_unit:
        if selected_unit.agility_points >= 2:
            if isinstance(selected_unit, TankUnit):
                if selected_unit.he_rounds > 0:
                    menu_items.append("Fire HE Round")
                if selected_unit.aphe_rounds > 0:
                    menu_items.append("Fire APHE Round")
            else:
                menu_items.append("Attack")
        if selected_unit.grenades > 0 and selected_unit.agility_points >= 2:
            menu_items.append("Throw Grenade")
        if selected_unit.smoke_grenades > 0 and selected_unit.agility_points >= 2:
            menu_items.append("Throw Smoke")
        menu_items.append("Status Report")

    if not menu_items:
        return

    menu_height = len(menu_items) * (BUTTON_HEIGHT + MENU_PADDING) + MENU_PADDING
    menu_width = BUTTON_WIDTH + MENU_PADDING * 2

    # Ensure menu stays within screen bounds
    x = min(action_menu_pos[0], screen_width - menu_width)
    y = min(action_menu_pos[1], screen_height - menu_height)

    # Draw menu background
    menu_rect = pygame.Rect(x, y, menu_width, menu_height)
    pygame.draw.rect(screen, MENU_BACKGROUND, menu_rect)
    pygame.draw.rect(screen, MENU_BORDER, menu_rect, 2)

    # Draw menu items
    mouse_pos = pygame.mouse.get_pos()
    for i, item in enumerate(menu_items):
        button_rect = pygame.Rect(
            x + MENU_PADDING,
            y + MENU_PADDING + i * (BUTTON_HEIGHT + MENU_PADDING),
            BUTTON_WIDTH,
            BUTTON_HEIGHT
        )

        # Check if mouse is hovering over this button
        is_hovered = button_rect.collidepoint(mouse_pos)
        button_color = MENU_HOVER if is_hovered else MENU_BACKGROUND

        # Draw button
        pygame.draw.rect(screen, button_color, button_rect)
        pygame.draw.rect(screen, MENU_BORDER, button_rect, 1)

        # Draw text
        text = font.render(item, True, MENU_TEXT)
        text_rect = text.get_rect(center=button_rect.center)
        screen.blit(text, text_rect)

        # Store button rect for click detection
        if not hasattr(draw_action_menu, 'buttons'):
            draw_action_menu.buttons = []
        if i < len(draw_action_menu.buttons):
            draw_action_menu.buttons[i] = (button_rect, item)
        else:
            draw_action_menu.buttons.append((button_rect, item))

def handle_menu_click(pos):
    global action_menu_active, waiting_for_target, current_action

    if not hasattr(draw_action_menu, 'buttons'):
        return

    for button_rect, action in draw_action_menu.buttons:
        if button_rect.collidepoint(pos):
            if action == "Attack":
                print(f"{selected_unit.name} is ready to attack!")
                action_menu_active = False
            elif action == "Fire HE Round":
                print(f"{selected_unit.name} is ready to fire HE round!")
                waiting_for_target = True
                current_action = "he_round"
                action_menu_active = False
            elif action == "Fire APHE Round":
                print(f"{selected_unit.name} is ready to fire APHE round!")
                waiting_for_target = True
                current_action = "aphe_round"
                action_menu_active = False
            elif action == "Throw Grenade":
                print(f"{selected_unit.name} is ready to throw a grenade!")
                waiting_for_target = True
                current_action = "grenade"
                action_menu_active = False
            elif action == "Throw Smoke":
                print(f"{selected_unit.name} is ready to throw a smoke grenade!")
                waiting_for_target = True
                current_action = "smoke"
                action_menu_active = False
            elif action == "Status Report":
                print(f"Status Report for {selected_unit.name}:")
                for line in selected_unit.get_status_report():
                    print(line)
                action_menu_active = False
            return True
    return False

def draw_unit_info(unit):
    panel_height = 150
    pygame.draw.rect(screen, (30, 30, 30), (0, screen_height - panel_height, screen_width, panel_height))
    if unit.image_key in images:
        screen.blit(images[unit.image_key], (20, screen_height - panel_height + 10))
    
    status_messages = unit.get_status_report()
    for i, line in enumerate(status_messages):
        text = font.render(line, True, (255, 255, 255))
        screen.blit(text, (240, screen_height - panel_height + 10 + i * 25))

def draw_end_turn_button():
    btn_rect = pygame.Rect(screen_width - 150, screen_height - 50, 130, 40)
    pygame.draw.rect(screen, (100, 100, 255), btn_rect)
    pygame.draw.rect(screen, (255, 255, 255), btn_rect, 2)
    text = font.render("End Turn", True, (255, 255, 255))
    screen.blit(text, (btn_rect.x + 20, btn_rect.y + 10))
    return btn_rect

# === COMBAT FUNCTIONS ===
def calculate_damage(attacker, defender, tile, ammo_type=None, distance=1):
    # Base damage calculation
    damage = attacker.base_damage
    
    # Apply accuracy check with range penalties
    if isinstance(attacker, InfantryUnit):
        accuracy = attacker.get_accuracy_at_range(distance)
    else:
        accuracy = attacker.accuracy
    
    accuracy_roll = random.randint(1, 100)
    if accuracy_roll > accuracy:
        return 0  # Miss
    
    # Apply terrain effects
    if tile.terrain_type == "House":
        damage *= 0.7
    elif tile.terrain_type == "Hill":
        damage *= 0.9
    
    # Apply smoke effects
    if defender.smoke_affected:
        damage *= 0.5
    
    # Apply ammunition type effects
    if isinstance(attacker, TankUnit):
        if ammo_type == "HE":
            # HE rounds are better against infantry
            if isinstance(defender, InfantryUnit):
                damage *= 1.5
            else:
                damage *= 0.8
        elif ammo_type == "APHE":
            # APHE rounds are better against tanks
            if isinstance(defender, TankUnit):
                damage *= 1.3
                armor_reduction = max(0, defender.armor - attacker.armor_penetration * 1.5)
            else:
                damage *= 0.7
                armor_reduction = 0
        else:
            armor_reduction = max(0, defender.armor - attacker.armor_penetration)
    else:
        armor_reduction = max(0, defender.armor - attacker.armor_penetration)
    
    # Apply armor reduction
    damage *= (1 - (armor_reduction / 100))
    
    # Apply range damage reduction for infantry
    if isinstance(attacker, InfantryUnit):
        if distance == 2:
            damage *= 0.8  # 20% damage reduction at medium range
        elif distance == 3:
            damage *= 0.6  # 40% damage reduction at long range
    
    return int(damage)

def throw_grenade(unit, target_tile):
    if unit.grenades <= 0 or unit.agility_points < 2:
        return False
    
    # Check if target is within range
    dist = max(abs(target_tile.q - unit.q), abs(target_tile.r - unit.r), 
              abs((-unit.q - unit.r) - (-target_tile.q - target_tile.r)))
    if dist > 1:
        return False
    
    # Deal damage to all units in adjacent tiles
    for nq, nr in get_neighbors(target_tile.q, target_tile.r):
        if (nq, nr) in tile_map:
            adjacent_tile = tile_map[(nq, nr)]
            if adjacent_tile.unit:
                damage = unit.base_damage * 1.5  # Grenades deal 50% more damage
                adjacent_tile.unit.health -= int(damage)
                if adjacent_tile.unit.health <= 0:
                    adjacent_tile.unit = None
    
    unit.grenades -= 1
    unit.agility_points -= 2
    return True

def throw_smoke(unit, target_tile):
    if unit.smoke_grenades <= 0 or unit.agility_points < 2:
        return False
    
    # Check if target is within range
    dist = max(abs(target_tile.q - unit.q), abs(target_tile.r - unit.r), 
              abs((-unit.q - unit.r) - (-target_tile.q - target_tile.r)))
    if dist > 1:
        return False
    
    # Apply smoke effect to target tile only
    target_tile.smoke = True
    target_tile.smoke_turns = 2  # Smoke lasts for 2 turns
    if target_tile.unit:
        target_tile.unit.smoke_affected = True
    
    unit.smoke_grenades -= 1
    unit.agility_points -= 2
    return True

# === LOGIC ===
def handle_tile_click(pos, tile_rects):
    global selected_unit, action_menu_active, waiting_for_target, current_action
    
    if waiting_for_target:
        for (q, r), rect in tile_rects.items():
            if rect.collidepoint(pos):
                target_tile = tile_map[(q, r)]
                if current_action == "grenade":
                    if throw_grenade(selected_unit, target_tile):
                        print(f"{selected_unit.name} throws a grenade!")
                        waiting_for_target = False
                        current_action = None
                elif current_action == "smoke":
                    if throw_smoke(selected_unit, target_tile):
                        print(f"{selected_unit.name} throws a smoke grenade!")
                        waiting_for_target = False
                        current_action = None
                elif current_action in ["he_round", "aphe_round"] and target_tile.unit:
                    if isinstance(selected_unit, TankUnit):
                        ammo_type = "HE" if current_action == "he_round" else "APHE"
                        if (current_action == "he_round" and selected_unit.he_rounds > 0) or \
                           (current_action == "aphe_round" and selected_unit.aphe_rounds > 0):
                            damage = calculate_damage(selected_unit, target_tile.unit, target_tile, ammo_type)
                            if damage > 0:
                                target_tile.unit.health -= damage
                                print(f"{selected_unit.name} fires {ammo_type} round at {target_tile.unit.name} for {damage} damage!")
                                if target_tile.unit.health <= 0:
                                    print(f"{target_tile.unit.name} has been destroyed!")
                                    target_tile.unit = None
                                if current_action == "he_round":
                                    selected_unit.he_rounds -= 1
                                else:
                                    selected_unit.aphe_rounds -= 1
                                selected_unit.agility_points -= 2
                            else:
                                print(f"{selected_unit.name} missed!")
                            waiting_for_target = False
                            current_action = None
                return
    
    if action_menu_active:
        if handle_menu_click(pos):
            return
    
    for (q, r), rect in tile_rects.items():
        if rect.collidepoint(pos):
            tile = tile_map[(q, r)]
            
            if selected_unit:
                dist = max(abs(q - selected_unit.q), abs(r - selected_unit.r), 
                          abs((-selected_unit.q - selected_unit.r) - (-q - r)))
                
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
                        damage = calculate_damage(selected_unit, tile.unit, tile, distance=dist)
                        if damage > 0:
                            tile.unit.health -= damage
                            range_text = "at point blank" if dist == 1 else f"at {dist} hexes range"
                            print(f"{selected_unit.name} attacks {tile.unit.name} {range_text} for {damage} damage.")
                            if tile.unit.health <= 0:
                                print(f"{tile.unit.name} has been defeated!")
                                tile.unit = None
                            selected_unit.agility_points -= 2
                        else:
                            print(f"{selected_unit.name} missed!")
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
                    dist = max(abs(q - enemy.q), abs(r - enemy.r), 
                             abs((-enemy.q - enemy.r) - (-q - r)))
                    if dist <= enemy.range:
                        damage = calculate_damage(enemy, tile.unit, tile)
                        if damage > 0:
                            tile.unit.health -= damage
                            print(f"{enemy.name} attacks {tile.unit.name} for {damage} damage.")
                            if tile.unit.health <= 0:
                                print(f"{tile.unit.name} has been defeated!")
                                tile.unit = None
                            enemy.agility_points -= 2
                            attacked = True
                            break
                        else:
                            print(f"{enemy.name} missed!")
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

# === MENU FUNCTIONS ===
def draw_menu():
    # Draw gradient background
    screen.blit(background, (0, 0))
    
    # Draw menu overlay
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0,0,0,120))
    screen.blit(overlay, (0,0))
    
    # Draw title
    title = font.render("Hex Strategy Game", True, (255,255,255))
    screen.blit(title, (screen_width//2-title.get_width()//2, 100))
    
    # Draw buttons
    for text, rect in menu_buttons:
        pygame.draw.rect(screen, (60,60,80), rect)
        pygame.draw.rect(screen, (255,255,255), rect, 2)
        btn_text = font.render(text, True, (255,255,255))
        screen.blit(btn_text, (rect[0]+rect[2]//2-btn_text.get_width()//2, rect[1]+rect[3]//2-btn_text.get_height()//2))

def draw_mission_select():
    # Draw gradient background
    screen.blit(background, (0, 0))
    
    # Draw menu overlay
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0,0,0,120))
    screen.blit(overlay, (0,0))
    
    title = font.render("Select Mission", True, (255,255,255))
    screen.blit(title, (screen_width//2-title.get_width()//2, 100))
    
    for text, rect in mission_buttons:
        pygame.draw.rect(screen, (60,60,80), rect)
        pygame.draw.rect(screen, (255,255,255), rect, 2)
        btn_text = font.render(text, True, (255,255,255))
        screen.blit(btn_text, (rect[0]+rect[2]//2-btn_text.get_width()//2, rect[1]+rect[3]//2-btn_text.get_height()//2))

def draw_settings():
    # Draw gradient background
    screen.blit(background, (0, 0))
    
    # Draw menu overlay
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0,0,0,120))
    screen.blit(overlay, (0,0))
    
    title = font.render("Settings (placeholder)", True, (255,255,255))
    screen.blit(title, (screen_width//2-title.get_width()//2, 100))
    
    for text, rect in settings_buttons:
        pygame.draw.rect(screen, (60,60,80), rect)
        pygame.draw.rect(screen, (255,255,255), rect, 2)
        btn_text = font.render(text, True, (255,255,255))
        screen.blit(btn_text, (rect[0]+rect[2]//2-btn_text.get_width()//2, rect[1]+rect[3]//2-btn_text.get_height()//2))

# --- Mission setup logic ---
def setup_mission(mission_id):
    global tile_map, units, enemy_units, player_unit, tank_unit, selected_unit, action_menu_active, action_menu_pos, waiting_for_target, current_action, camera_offset_x, camera_offset_y, hex_size
    # Reset all state
    hex_size = base_hex_size
    tile_map = {}
    units = []
    enemy_units = []
    # Mission 1: default spawn
    if mission_id == 0:
        for q in range(-MAP_RADIUS, MAP_RADIUS + 1):
            for r in range(-MAP_RADIUS, MAP_RADIUS + 1):
                if -q - r >= -MAP_RADIUS and -q - r <= MAP_RADIUS:
                    terrain = random.choice(TERRAIN_TYPES)
                    tile_map[(q, r)] = Tile(q, r, terrain)
        player_unit = InfantryUnit("German Infantry", 100, 20, 70, 5, 10, "ger_infantry", range_=1, is_enemy=False)
        player_unit.q, player_unit.r = 0, 0
        tile_map[(0, 0)].unit = player_unit
        units.append(player_unit)
        tank_unit = TankUnit("German Tank", 200, 40, 80, 3, 5, "ger_tank", range_=2, armor=50, armor_penetration=30, is_enemy=False)
        tank_unit.q, tank_unit.r = 1, 0
        tile_map[(1, 0)].unit = tank_unit
        units.append(tank_unit)
        enemy_unit = InfantryUnit("Russian Infantry", 100, 20, 60, 4, 10, "ger_infantry", range_=1, is_enemy=True)
        for (q, r), tile in tile_map.items():
            if tile.unit is None and abs(q) + abs(r) > 8:
                tile.unit = enemy_unit
                enemy_unit.q, enemy_unit.r = q, r
                enemy_units.append(enemy_unit)
                break
    # Mission 2: different spawn
    elif mission_id == 1:
        for q in range(-MAP_RADIUS, MAP_RADIUS + 1):
            for r in range(-MAP_RADIUS, MAP_RADIUS + 1):
                if -q - r >= -MAP_RADIUS and -q - r <= MAP_RADIUS:
                    terrain = random.choice(TERRAIN_TYPES)
                    tile_map[(q, r)] = Tile(q, r, terrain)
        player_unit = InfantryUnit("German Infantry", 100, 20, 70, 5, 10, "ger_infantry", range_=1, is_enemy=False)
        player_unit.q, player_unit.r = -2, 2
        tile_map[(-2, 2)].unit = player_unit
        units.append(player_unit)
        tank_unit = TankUnit("German Tank", 200, 40, 80, 3, 5, "ger_tank", range_=2, armor=50, armor_penetration=30, is_enemy=False)
        tank_unit.q, tank_unit.r = -1, 2
        tile_map[(-1, 2)].unit = tank_unit
        units.append(tank_unit)
        enemy_unit = InfantryUnit("Russian Infantry", 100, 20, 60, 4, 10, "ger_infantry", range_=1, is_enemy=True)
        for (q, r), tile in tile_map.items():
            if tile.unit is None and abs(q) + abs(r) > 8:
                tile.unit = enemy_unit
                enemy_unit.q, enemy_unit.r = q, r
                enemy_units.append(enemy_unit)
                break
    selected_unit = None
    action_menu_active = False
    action_menu_pos = None
    waiting_for_target = False
    current_action = None
    camera_offset_x, camera_offset_y = screen_width // 2, screen_height // 2 - 100

# === MAIN LOOP ===
running = True
turn_player = True
menu_state = MENU_STATE_MAIN
selected_mission = 0

while running:
    if menu_state == MENU_STATE_MAIN:
        draw_menu()
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                for i, (text, rect) in enumerate(menu_buttons):
                    r = pygame.Rect(rect)
                    if r.collidepoint(mx, my):
                        if text == "Select Mission":
                            menu_state = MENU_STATE_MISSION_SELECT
                        elif text == "Settings":
                            menu_state = MENU_STATE_SETTINGS
                        elif text == "Quit":
                            running = False
    elif menu_state == MENU_STATE_MISSION_SELECT:
        draw_mission_select()
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                for i, (text, rect) in enumerate(mission_buttons):
                    r = pygame.Rect(rect)
                    if r.collidepoint(mx, my):
                        if text == "Mission 1":
                            selected_mission = 0
                            setup_mission(0)
                            menu_state = MENU_STATE_GAME
                        elif text == "Mission 2":
                            selected_mission = 1
                            setup_mission(1)
                            menu_state = MENU_STATE_GAME
                        elif text == "Back":
                            menu_state = MENU_STATE_MAIN
    elif menu_state == MENU_STATE_SETTINGS:
        draw_settings()
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                for i, (text, rect) in enumerate(settings_buttons):
                    r = pygame.Rect(rect)
                    if r.collidepoint(mx, my):
                        if text == "Back":
                            menu_state = MENU_STATE_MAIN
    elif menu_state == MENU_STATE_GAME:
        screen.fill((10, 10, 20))
        tile_rects = draw_map()
        if selected_unit:
            draw_unit_info(selected_unit)
        draw_action_menu()
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
                                unit.accuracy = unit.base_accuracy
                                unit.smoke_affected = False
                            # Update smoke duration
                            for tile in tile_map.values():
                                if tile.smoke:
                                    tile.smoke_turns -= 1
                                    if tile.smoke_turns <= 0:
                                        tile.smoke = False
                        else:
                            ai_turn()
                    elif turn_player:
                        if action_menu_active:
                            if handle_menu_click(event.pos):
                                continue
                            action_menu_active = False
                        handle_tile_click(event.pos, tile_rects)
                    # Start dragging for map
                    dragging = True
                    drag_start_pos = event.pos
                    camera_start_offset = (camera_offset_x, camera_offset_y)
                elif event.button == 3:  # Right click
                    if turn_player:
                        for (q, r), rect in tile_rects.items():
                            if rect.collidepoint(event.pos):
                                tile = tile_map[(q, r)]
                                if tile.unit and not tile.unit.is_enemy:
                                    selected_unit = tile.unit
                                    action_menu_active = True
                                    action_menu_pos = event.pos
                                    break
                        else:
                            # If clicked outside a unit, close the menu
                            action_menu_active = False
                            action_menu_pos = None
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

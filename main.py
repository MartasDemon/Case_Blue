import pygame
import math
import random
import os
import cv2
import numpy as np
from game_objects import InfantryUnit, TankUnit, Tile, TERRAIN_TYPES, TERRAIN_COLORS
from pygame import mixer

# === CONFIGURATION ===
# Add River and Bridge to terrain types
TERRAIN_TYPES.extend(["River", "Bridge"])
TERRAIN_COLORS.update({
    "River": (0, 0, 255),  # Blue for river
    "Bridge": (139, 69, 19)  # Brown for bridge
})

IMAGE_PATHS = {
    "ger_infantry": ["images/ger_infantry1.jpg", "images/ger_infantry2.jpg"],
    "ger_tank": "images/ger_stug1.jpg"
}

# === UI CONSTANTS ===
BUTTON_HEIGHT = 30
BUTTON_WIDTH = 150
MENU_PADDING = 5
MENU_BACKGROUND = (40, 40, 40)
MENU_HOVER = (60, 60, 60)
MENU_TEXT = (255, 255, 255)
MENU_BORDER = (200, 200, 200)
MESSAGE_LOG_HEIGHT = 200
MESSAGE_LOG_WIDTH = 500
MESSAGE_LOG_PADDING = 10
MESSAGE_LOG_MAX_LINES = 15
MESSAGE_LOG_LINE_HEIGHT = 25
MESSAGE_LOG_BULLET = "- "
BOTTOM_PANEL_HEIGHT = 200
SCROLL_STEP = 30  # How many pixels to scroll per wheel step

# === DISPLAY SETTINGS ===
is_fullscreen = False
screen_width, screen_height = 1600, 900

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
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Hex Strategy Game")
font = pygame.font.SysFont(None, 24)
clock = pygame.time.Clock()

# === LOAD IMAGES ===
images = {}
for key, paths in IMAGE_PATHS.items():
    if isinstance(paths, list):
        # For infantry, randomly choose one of the two images
        path = random.choice(paths)
    else:
        path = paths
        
    if os.path.exists(path):
        img = pygame.image.load(path)
        img = pygame.transform.scale(img, (200, 150))
        images[key] = img
    else:
        print(f"Missing image: {path}")

# Create a simple gradient background
def create_gradient_background():
    background = pygame.Surface((screen_width, screen_height))
    for y in range(screen_height):
        color = (0, 0, int(50 * (1 - y/screen_height)))
        pygame.draw.line(background, color, (0, y), (screen_width, y))
    return background

# Create the background
background = create_gradient_background()

# Video background setup
class VideoBackground:
    def __init__(self, video_path):
        try:
            self.cap = cv2.VideoCapture(video_path)
            if not self.cap.isOpened():
                print(f"Error: Could not open video file {video_path}")
                self.cap = None
                return

            # Get video properties
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.frame_delay = 1000 / self.fps  # Delay in milliseconds
            self.last_frame_time = pygame.time.get_ticks()
            
            # Get video dimensions
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Create a surface for the video frame
            self.frame_surface = pygame.Surface((screen_width, screen_height))
            
            # Try multiple audio file formats
            audio_formats = ['.wav', '.mp3', '.ogg']
            audio_loaded = False
            
            for audio_format in audio_formats:
                audio_path = video_path.replace('.mp4', audio_format)
                if os.path.exists(audio_path):
                    try:
                        pygame.mixer.music.load(audio_path)
                        pygame.mixer.music.set_volume(0.7)  # Set volume to 70%
                        pygame.mixer.music.play(-1)  # -1 means loop indefinitely
                        audio_loaded = True
                        print(f"Successfully loaded audio from {audio_path}")
                        break
                    except Exception as e:
                        print(f"Warning: Could not load audio file {audio_path}: {e}")
            
            if not audio_loaded:
                print("Warning: No audio file found or could not be loaded")
                
        except Exception as e:
            print(f"Error initializing video background: {e}")
            self.cap = None
    
    def get_frame(self):
        if self.cap is None:
            return background
            
        try:
            # Check if it's time for the next frame
            current_time = pygame.time.get_ticks()
            if current_time - self.last_frame_time < self.frame_delay:
                return self.frame_surface  # Return the last frame if not enough time has passed
            
            self.last_frame_time = current_time
            
            ret, frame = self.cap.read()
            if not ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if not ret:
                    return background
            
            # Convert frame to RGB (OpenCV uses BGR)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize frame to screen dimensions while maintaining aspect ratio
            h, w = frame.shape[:2]
            aspect = w / h
            if aspect > screen_width / screen_height:
                new_w = screen_width
                new_h = int(new_w / aspect)
            else:
                new_h = screen_height
                new_w = int(new_h * aspect)
            
            frame = cv2.resize(frame, (new_w, new_h))
            
            # Create a black background
            self.frame_surface.fill((0, 0, 0))
            
            # Calculate position to center the frame
            x = (screen_width - new_w) // 2
            y = (screen_height - new_h) // 2
            
            # Convert to pygame surface and blit centered
            frame_surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
            self.frame_surface.blit(frame_surface, (x, y))
            
            return self.frame_surface
        except Exception as e:
            print(f"Error getting video frame: {e}")
            return background

# Initialize video background
video_path = os.path.join('video', 'intro.mp4')
if os.path.exists(video_path):
    video_bg = VideoBackground(video_path)
else:
    print(f"Warning: Video file not found at {video_path}")
    video_bg = None

# === MAP GENERATION ===
MAP_RADIUS = 8
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
    ("Toggle Fullscreen", (screen_width//2-100, screen_height//2-40, 200, 50)),
    ("Back", (screen_width//2-100, screen_height//2+80, 200, 40)),
]

# === MISSION DATA ===
MISSIONS = {
    0: {
        "name": "Operation Case Blue - Mission 1",
        "date": "June 28, 1942",
        "description": "Initial assault on the Soviet positions. Secure the forward positions and establish a foothold.",
        "player_pos": (0, 0),
        "tank_pos": (1, 0)
    },
    1: {
        "name": "Operation Case Blue - Mission 2",
        "date": "July 1, 1942",
        "description": "Advance through enemy territory. Capture key strategic positions and eliminate enemy resistance.",
        "player_pos": (-2, 2),
        "tank_pos": (-1, 2)
    }
}

# === MESSAGE LOG ===
class MessageLog:
    def __init__(self):
        self.messages = []
        self.max_lines = MESSAGE_LOG_MAX_LINES
        self.scroll_offset = 0
        self.max_scroll = 0
        self.content_height = 0
        self.was_at_bottom = True  # Track if we were at the bottom before adding a message
    
    def add_message(self, message):
        # Check if we were at the bottom before adding the message
        self.was_at_bottom = (self.scroll_offset >= self.max_scroll - 1)
        
        self.messages.append(message)
        if len(self.messages) > self.max_lines:
            self.messages.pop(0)
        
        # Only reset scroll if we were at the bottom
        if self.was_at_bottom:
            self.scroll_offset = self.max_scroll
        # Otherwise, keep the current scroll position
    
    def wrap_text(self, text, max_width):
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            # Test if adding the word would exceed the width
            test_line = ' '.join(current_line + [word])
            if font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def calculate_content_height(self, available_width):
        total_height = 0
        for message in self.messages:
            wrapped_lines = self.wrap_text(message, available_width)
            total_height += len(wrapped_lines) * MESSAGE_LOG_LINE_HEIGHT
        return total_height
    
    def handle_scroll(self, amount):
        # Calculate new scroll offset
        new_offset = self.scroll_offset + amount
        
        # Ensure scroll offset stays within bounds
        self.scroll_offset = max(0, min(self.max_scroll, new_offset))
        
        # Update was_at_bottom flag
        self.was_at_bottom = (self.scroll_offset >= self.max_scroll - 1)
    
    def draw(self, surface, x, y, width, height):
        # Draw background
        pygame.draw.rect(surface, (30, 30, 30), (x, y, width, height))
        pygame.draw.rect(surface, MENU_BORDER, (x, y, width, height), 2)
        
        # Calculate available width for content
        content_width = width - (2 * MESSAGE_LOG_PADDING)
        
        # Calculate total content height
        self.content_height = self.calculate_content_height(content_width)
        
        # Calculate visible height
        visible_height = height - (2 * MESSAGE_LOG_PADDING)
        
        # Update max scroll
        self.max_scroll = max(0, self.content_height - visible_height)
        
        # If we were at the bottom and new content was added, update scroll offset
        if self.was_at_bottom:
            self.scroll_offset = self.max_scroll
        
        # Create a clipping rectangle for the message area
        clip_rect = pygame.Rect(x + MESSAGE_LOG_PADDING, y + MESSAGE_LOG_PADDING,
                              content_width,
                              visible_height)
        old_clip = surface.get_clip()
        surface.set_clip(clip_rect)
        
        # Draw messages
        y_offset = y + MESSAGE_LOG_PADDING - self.scroll_offset
        
        for message in self.messages:
            # Wrap the message text
            wrapped_lines = self.wrap_text(message, content_width - font.size(MESSAGE_LOG_BULLET)[0])
            
            # Draw each line of the wrapped message
            for i, line in enumerate(wrapped_lines):
                # Add bullet point to first line of each message
                if i == 0:
                    line = MESSAGE_LOG_BULLET + line
                
                text = font.render(line, True, MENU_TEXT)
                surface.blit(text, (x + MESSAGE_LOG_PADDING, y_offset))
                y_offset += MESSAGE_LOG_LINE_HEIGHT
        
        # Restore original clipping rectangle
        surface.set_clip(old_clip)
        
        # Draw scroll indicator if there's more content than can be displayed
        if self.content_height > visible_height:
            # Calculate scroll indicator position
            indicator_height = visible_height * (visible_height / self.content_height)
            indicator_pos = (self.scroll_offset / self.max_scroll) * (visible_height - indicator_height)
            
            # Draw scroll indicator
            indicator_rect = pygame.Rect(x + width - 5, y + MESSAGE_LOG_PADDING + indicator_pos,
                                       5, indicator_height)
            pygame.draw.rect(surface, (100, 100, 100), indicator_rect)

# Create message log instance
message_log = MessageLog()

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
                if selected_unit.grenades > 0:
                    menu_items.append("Throw Grenade")
                if selected_unit.smoke_grenades > 0:
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
                message_log.add_message(f"{selected_unit.name} is ready to attack!")
                action_menu_active = False
            elif action == "Fire HE Round":
                message_log.add_message(f"{selected_unit.name} is ready to fire HE round!")
                waiting_for_target = True
                current_action = "he_round"
                action_menu_active = False
            elif action == "Fire APHE Round":
                message_log.add_message(f"{selected_unit.name} is ready to fire APHE round!")
                waiting_for_target = True
                current_action = "aphe_round"
                action_menu_active = False
            elif action == "Throw Grenade":
                message_log.add_message(f"{selected_unit.name} is ready to throw a grenade!")
                waiting_for_target = True
                current_action = "grenade"
                action_menu_active = False
            elif action == "Throw Smoke":
                message_log.add_message(f"{selected_unit.name} is ready to throw a smoke grenade!")
                waiting_for_target = True
                current_action = "smoke"
                action_menu_active = False
            elif action == "Status Report":
                message_log.add_message(f"Status Report for {selected_unit.name}:")
                for line in selected_unit.get_status_report():
                    message_log.add_message(line)
                action_menu_active = False
            return True
    return False

def draw_bottom_panel():
    # Draw the permanent bottom panel
    pygame.draw.rect(screen, (30, 30, 30), (0, screen_height - BOTTOM_PANEL_HEIGHT, screen_width, BOTTOM_PANEL_HEIGHT))
    pygame.draw.rect(screen, MENU_BORDER, (0, screen_height - BOTTOM_PANEL_HEIGHT, screen_width, BOTTOM_PANEL_HEIGHT), 2)
    
    # Draw message log on the right side
    message_log.draw(screen, screen_width - MESSAGE_LOG_WIDTH - 20, 
                    screen_height - BOTTOM_PANEL_HEIGHT + 10,
                    MESSAGE_LOG_WIDTH, BOTTOM_PANEL_HEIGHT - 20)

def draw_unit_info(unit):
    # Draw unit image
    image_key = "ger_infantry" if isinstance(unit, InfantryUnit) else "ger_tank"
    if image_key in images:
        screen.blit(images[image_key], (20, screen_height - BOTTOM_PANEL_HEIGHT + 10))
    
    # Draw unit status
    status_messages = unit.get_status_report()
    for i, line in enumerate(status_messages):
        text = font.render(line, True, (255, 255, 255))
        screen.blit(text, (240, screen_height - BOTTOM_PANEL_HEIGHT + 10 + i * 25))

def draw_end_turn_button():
    # Move button to top-right corner
    btn_rect = pygame.Rect(screen_width - 150, 20, 130, 40)
    pygame.draw.rect(screen, (100, 100, 255), btn_rect)
    pygame.draw.rect(screen, (255, 255, 255), btn_rect, 2)
    text = font.render("End Turn", True, (255, 255, 255))
    screen.blit(text, (btn_rect.x + 20, btn_rect.y + 10))
    return btn_rect

def draw_back_to_menu_button():
    btn_rect = pygame.Rect(20, 20, 130, 40)
    pygame.draw.rect(screen, (100, 100, 255), btn_rect)
    pygame.draw.rect(screen, (255, 255, 255), btn_rect, 2)
    text = font.render("Back to Menu", True, (255, 255, 255))
    screen.blit(text, (btn_rect.x + 10, btn_rect.y + 10))
    return btn_rect

def draw_message_log():
    # Draw message log at the bottom of the screen
    message_log.draw(screen, screen_width - MESSAGE_LOG_WIDTH - 20, screen_height - MESSAGE_LOG_HEIGHT - 20, MESSAGE_LOG_WIDTH, MESSAGE_LOG_HEIGHT)

# === COMBAT FUNCTIONS ===
def calculate_damage(attacker, defender, tile, ammo_type=None, distance=1):
    # Base damage calculation
    damage = attacker.base_damage
    
    # Calculate base hit chance based on unit stats
    base_hit_chance = attacker.accuracy
    
    # Apply terrain modifiers to hit chance
    terrain_modifiers = {
        "House": 0.7,  # Units in houses are harder to hit
        "Hill": 0.8,   # Units on hills are harder to hit
        "Forest": 0.75, # Units in forests are harder to hit
        "Bridge": 1.3,  # Units on bridges are easier to hit
        "Plains": 1.0,  # Normal hit chance on plains
        "Road": 1.0,    # Normal hit chance on roads
        "River": 0.0,   # Can't hit units in river (they can't be there anyway)
    }
    
    # Apply terrain modifier to hit chance
    hit_chance = base_hit_chance * terrain_modifiers.get(tile.terrain_type, 1.0)
    
    # Apply morale modifier to hit chance (higher morale = better accuracy)
    morale_modifier = 0.5 + (attacker.morale / 200)  # 0.5 to 1.5 range
    hit_chance *= morale_modifier
    
    # Apply range penalty
    if distance > 1:
        hit_chance *= (1 - (distance - 1) * 0.2)  # 20% penalty per hex of distance
    
    # Apply smoke effects
    if defender.smoke_affected:
        hit_chance *= 0.5
    
    # Roll for hit
    hit_roll = random.randint(1, 100)
    if hit_roll > hit_chance:
        return 0  # Miss
    
    # If hit, calculate damage
    damage = attacker.base_damage
    
    # Apply terrain effects to damage
    if tile.terrain_type == "House":
        damage *= 0.7
    elif tile.terrain_type == "Hill":
        damage *= 0.9
    
    # Initialize armor reduction
    armor_reduction = 0
    
    # Apply ammunition type effects
    if isinstance(attacker, TankUnit):
        if ammo_type == "HE":
            if isinstance(defender, InfantryUnit):
                damage *= 1.5
            else:
                damage *= 0.8
            armor_reduction = max(0, defender.armor - attacker.armor_penetration)
        elif ammo_type == "APHE":
            if isinstance(defender, TankUnit):
                damage *= 1.3
                armor_reduction = max(0, defender.armor - attacker.armor_penetration * 1.5)
            else:
                damage *= 0.7
                armor_reduction = max(0, defender.armor - attacker.armor_penetration)
        else:
            armor_reduction = max(0, defender.armor - attacker.armor_penetration)
    else:
        armor_reduction = max(0, defender.armor - attacker.armor_penetration)
    
    # Apply armor reduction
    damage *= (1 - (armor_reduction / 100))
    
    # Apply range damage reduction for infantry
    if isinstance(attacker, InfantryUnit):
        if distance == 2:
            damage *= 0.8
        elif distance == 3:
            damage *= 0.6
    
    # Reduce defender's morale based on damage taken
    morale_loss = int(damage / 5)  # 1 morale loss per 5 damage
    defender.morale = max(0, defender.morale - morale_loss)
    
    return int(damage)

def get_combat_message(attacker, defender, damage, distance, ammo_type=None):
    messages = []
    
    # Get terrain type for the defender
    defender_terrain = defender.tile_map[(defender.q, defender.r)].terrain_type
    
    # Create initial attack message with distance and terrain
    distance_text = "point blank" if distance == 1 else f"{distance} hexes away"
    terrain_text = f"on {defender_terrain.lower()}" if defender_terrain != "Plains" else "in the open"
    
    if isinstance(attacker, TankUnit):
        if ammo_type == "HE":
            messages.append(f"{attacker.name} fires a High Explosive round at {defender.name} {distance_text} {terrain_text}!")
        elif ammo_type == "APHE":
            messages.append(f"{attacker.name} fires an Armor Piercing round at {defender.name} {distance_text} {terrain_text}!")
        else:
            messages.append(f"{attacker.name} engages {defender.name} {distance_text} {terrain_text}!")
    else:
        messages.append(f"{attacker.name} opens fire on {defender.name} {distance_text} {terrain_text}!")
    
    # Damage and result messages
    if damage > 0:
        if isinstance(defender, TankUnit):
            soldier_loss = max(1, int(damage / 10))
            if damage > defender.health * 0.5:
                messages.append(f"Critical hit! The round penetrates the armor, causing severe damage! The tank takes {damage} damage!")
            elif damage > defender.health * 0.2:
                messages.append(f"The round strikes the tank, causing moderate damage! The tank takes {damage} damage!")
            else:
                messages.append(f"The round glances off the armor, causing minor damage! The tank takes {damage} damage!")
        else:
            soldier_loss = max(1, int(damage / 10))
            if soldier_loss > defender.soldiers * 0.5:
                messages.append(f"Devastating fire! {soldier_loss} soldiers fall! The unit takes {damage} damage!")
            elif soldier_loss > defender.soldiers * 0.2:
                messages.append(f"Heavy casualties! {soldier_loss} soldiers are hit! The unit takes {damage} damage!")
            else:
                messages.append(f"{soldier_loss} soldiers are wounded! The unit takes {damage} damage!")
        
        # Add morale effect message
        if defender.morale < 30:
            messages.append(f"The unit's morale is critically low at {defender.morale}%!")
        elif defender.morale < 50:
            messages.append(f"The unit's morale is wavering at {defender.morale}%!")
    else:
        if isinstance(attacker, TankUnit):
            messages.append(f"The round misses its target, exploding harmlessly in the distance!")
        else:
            messages.append(f"The shots go wide, failing to find their mark!")
    
    # Add terrain effect message if relevant
    if damage > 0:
        if defender_terrain == "House":
            messages.append("The building provides some cover from the attack!")
        elif defender_terrain == "Hill":
            messages.append("The elevated position helps mitigate the damage!")
        elif defender_terrain == "Bridge":
            messages.append("The exposed position on the bridge makes the unit more vulnerable!")
        elif defender_terrain == "Forest":
            messages.append("The dense forest provides some protection from the attack!")
    
    # Add smoke effect message if applicable
    if defender.smoke_affected:
        messages.append("The smoke screen helps protect the unit from the attack!")
    
    return messages

def throw_grenade(unit, target_tile):
    if unit.grenades <= 0 or unit.agility_points < 2:
        return False
    
    # Check if target is within range
    dist = max(abs(target_tile.q - unit.q), abs(target_tile.r - unit.r), 
              abs((-unit.q - unit.r) - (-target_tile.q - target_tile.r)))
    if dist > 1:
        return False
    
    # Deal damage to all units in adjacent tiles
    units_hit = []
    for nq, nr in get_neighbors(target_tile.q, target_tile.r):
        if (nq, nr) in tile_map:
            adjacent_tile = tile_map[(nq, nr)]
            if adjacent_tile.unit:
                damage = unit.base_damage * 1.5  # Grenades deal 50% more damage
                adjacent_tile.unit.health -= int(damage)
                units_hit.append(adjacent_tile.unit)
                if adjacent_tile.unit.health <= 0:
                    message_log.add_message(f"{unit.name} throws a grenade! The blast eliminates {adjacent_tile.unit.name}!")
                    adjacent_tile.unit = None
                else:
                    # Reduce morale of surviving units
                    morale_loss = random.randint(5, 15)
                    adjacent_tile.unit.morale = max(0, adjacent_tile.unit.morale - morale_loss)
                    message_log.add_message(f"{unit.name} throws a grenade! {adjacent_tile.unit.name} takes {int(damage)} damage and loses {morale_loss} morale!")
    
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
    
    # Apply smoke effect to target tile and adjacent tiles
    affected_tiles = []
    for nq, nr in get_neighbors(target_tile.q, target_tile.r):
        if (nq, nr) in tile_map:
            adjacent_tile = tile_map[(nq, nr)]
            adjacent_tile.smoke = True
            adjacent_tile.smoke_turns = 2  # Smoke lasts for 2 turns
            affected_tiles.append(adjacent_tile)
            if adjacent_tile.unit:
                adjacent_tile.unit.smoke_affected = True
    
    # Also apply to target tile
    target_tile.smoke = True
    target_tile.smoke_turns = 2
    affected_tiles.append(target_tile)
    if target_tile.unit:
        target_tile.unit.smoke_affected = True
    
    # Create message about affected units
    affected_units = [tile.unit.name for tile in affected_tiles if tile.unit]
    if affected_units:
        message_log.add_message(f"{unit.name} throws a smoke grenade! The smoke screen conceals {', '.join(affected_units)}!")
    else:
        message_log.add_message(f"{unit.name} throws a smoke grenade, creating a smoke screen!")
    
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
                    if selected_unit.throw_grenade(target_tile):
                        message_log.add_message(f"{selected_unit.name} throws a grenade at {target_tile.unit.name if target_tile.unit else 'empty space'}!")
                        waiting_for_target = False
                        current_action = None
                    else:
                        message_log.add_message(f"{selected_unit.name} cannot throw a grenade there!")
                elif current_action == "smoke":
                    if throw_smoke(selected_unit, target_tile):
                        message_log.add_message(f"{selected_unit.name} throws a smoke grenade!")
                        waiting_for_target = False
                        current_action = None
                elif current_action in ["he_round", "aphe_round"] and target_tile.unit:
                    if isinstance(selected_unit, TankUnit):
                        ammo_type = "HE" if current_action == "he_round" else "APHE"
                        if (current_action == "he_round" and selected_unit.he_rounds > 0) or \
                           (current_action == "aphe_round" and selected_unit.aphe_rounds > 0):
                            selected_unit.agility_points -= 2
                            if current_action == "he_round":
                                selected_unit.he_rounds -= 1
                            else:
                                selected_unit.aphe_rounds -= 1
                            
                            damage = calculate_damage(selected_unit, target_tile.unit, target_tile, ammo_type)
                            combat_messages = get_combat_message(selected_unit, target_tile.unit, damage, 1, ammo_type)
                            for msg in combat_messages:
                                message_log.add_message(msg)
                            
                            if damage > 0:
                                if target_tile.unit.take_damage(damage):
                                    message_log.add_message(f"{target_tile.unit.name} has been destroyed!")
                                    target_tile.unit = None
                                elif target_tile.unit.surrendered:
                                    message_log.add_message(f"{target_tile.unit.name} surrenders!")
                                    target_tile.unit = None
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
                
                # Check if movement is valid
                can_move = True
                if tile.terrain_type == "River":
                    can_move = False
                    message_log.add_message("Cannot move into river!")
                elif dist > 1:
                    can_move = False
                    message_log.add_message("Cannot move that far!")
                elif selected_unit.agility_points < 1:
                    can_move = False
                    message_log.add_message("Not enough action points!")
                
                if can_move and tile.unit is None and dist <= 1 and selected_unit.agility_points >= 1:
                    # Move unit (1 AP = 1 hex movement)
                    tile_map[(selected_unit.q, selected_unit.r)].unit = None
                    selected_unit.q, selected_unit.r = q, r
                    selected_unit.agility_points -= 1
                    tile.unit = selected_unit
                    return
                elif tile.unit and tile.unit != selected_unit and tile.unit.is_enemy != selected_unit.is_enemy:
                    # Attack (range is for shooting only)
                    if dist <= selected_unit.range and selected_unit.agility_points >= 2:
                        selected_unit.agility_points -= 2
                        
                        damage = calculate_damage(selected_unit, tile.unit, tile, distance=dist)
                        combat_messages = get_combat_message(selected_unit, tile.unit, damage, dist)
                        for msg in combat_messages:
                            message_log.add_message(msg)
                        
                        if damage > 0:
                            if tile.unit.take_damage(damage):
                                message_log.add_message(f"{tile.unit.name} has been destroyed!")
                                tile.unit = None
                            elif tile.unit.surrendered:
                                message_log.add_message(f"{tile.unit.name} surrenders!")
                                tile.unit = None
                        return
            
            if tile.unit and not tile.unit.is_enemy:
                selected_unit = tile.unit
                return

# === MORALE SYSTEM ===
def update_morale(unit, tile_map):
    if unit.health <= 0 or unit.surrendered:
        return
        
    # Check for nearby friendly units
    nearby_friends = 0
    for nq, nr in get_neighbors(unit.q, unit.r):
        if (nq, nr) in tile_map:
            neighbor_unit = tile_map[(nq, nr)].unit
            if neighbor_unit and not neighbor_unit.is_enemy and neighbor_unit != unit:
                nearby_friends += 1
    
    # Morale boost from nearby friends (up to +5 per turn)
    if nearby_friends > 0:
        morale_boost = min(5, nearby_friends)
        unit.morale = min(100, unit.morale + morale_boost)
        if morale_boost > 0:
            message_log.add_message(f"{unit.name} gains {morale_boost} morale from nearby friendly units!")

def ai_turn():
    for enemy in enemy_units:
        if enemy.health <= 0 or enemy.surrendered:
            continue
        enemy.agility_points = enemy.base_agility
        update_morale(enemy, tile_map)  # Update enemy morale
        while enemy.agility_points >= 2:
            # Attack player units in range
            attacked = False
            for (q, r), tile in tile_map.items():
                if tile.unit and not tile.unit.is_enemy:
                    dist = max(abs(q - enemy.q), abs(r - enemy.r), 
                             abs((-enemy.q - enemy.r) - (-q - r)))
                    if dist <= enemy.range:
                        # Deduct AP before calculating damage
                        enemy.agility_points -= 2
                        
                        damage = calculate_damage(enemy, tile.unit, tile)
                        combat_messages = get_combat_message(enemy, tile.unit, damage, dist)
                        for msg in combat_messages:
                            message_log.add_message(msg)
                        
                        if damage > 0:
                            if tile.unit.take_damage(damage):
                                message_log.add_message(f"{tile.unit.name} has been destroyed!")
                                tile.unit = None
                            elif tile.unit.surrendered:
                                message_log.add_message(f"{tile.unit.name} surrenders!")
                                tile.unit = None
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

# === MENU FUNCTIONS ===
def draw_menu():
    # Draw background
    if video_bg and video_bg.cap is not None:
        screen.blit(video_bg.get_frame(), (0, 0))
    else:
        screen.blit(background, (0, 0))
    
    # Draw menu overlay
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0,0,0,120))
    screen.blit(overlay, (0,0))
    
    # Draw title
    title = font.render("Operation Case Blue", True, (255,255,255))
    screen.blit(title, (screen_width//2-title.get_width()//2, 100))
    
    # Draw buttons
    for text, rect in menu_buttons:
        pygame.draw.rect(screen, (60,60,80), rect)
        pygame.draw.rect(screen, (255,255,255), rect, 2)
        btn_text = font.render(text, True, (255,255,255))
        screen.blit(btn_text, (rect[0]+rect[2]//2-btn_text.get_width()//2, rect[1]+rect[3]//2-btn_text.get_height()//2))

def draw_mission_select():
    # Draw background
    if video_bg and video_bg.cap is not None:
        screen.blit(video_bg.get_frame(), (0, 0))
    else:
        screen.blit(background, (0, 0))
    
    # Draw menu overlay
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0,0,0,120))
    screen.blit(overlay, (0,0))
    
    title = font.render("Select Mission", True, (255,255,255))
    screen.blit(title, (screen_width//2-title.get_width()//2, 100))
    
    # Get mouse position for hover detection
    mouse_pos = pygame.mouse.get_pos()
    hovered_mission = None
    
    # Draw mission buttons and check for hover
    for i, (text, rect) in enumerate(mission_buttons):
        if text != "Back":  # Skip the back button
            mission_id = i
            r = pygame.Rect(rect)
            is_hovered = r.collidepoint(mouse_pos)
            
            # Draw button with hover effect
            color = (80, 80, 100) if is_hovered else (60, 60, 80)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (255, 255, 255), rect, 2)
            
            # Draw mission name
            btn_text = font.render(text, True, (255, 255, 255))
            screen.blit(btn_text, (rect[0]+rect[2]//2-btn_text.get_width()//2, rect[1]+rect[3]//2-btn_text.get_height()//2))
            
            if is_hovered:
                hovered_mission = mission_id
        else:
            # Draw back button normally
            pygame.draw.rect(screen, (60, 60, 80), rect)
            pygame.draw.rect(screen, (255, 255, 255), rect, 2)
            btn_text = font.render(text, True, (255, 255, 255))
            screen.blit(btn_text, (rect[0]+rect[2]//2-btn_text.get_width()//2, rect[1]+rect[3]//2-btn_text.get_height()//2))
    
    # Draw mission info window if hovering over a mission
    if hovered_mission is not None:
        mission = MISSIONS[hovered_mission]
        
        # Create info window
        info_width = 400
        info_height = 200
        info_x = screen_width - info_width - 50
        info_y = 150
        
        # Draw window background
        info_surface = pygame.Surface((info_width, info_height), pygame.SRCALPHA)
        info_surface.fill((0, 0, 0, 200))
        pygame.draw.rect(info_surface, (255, 255, 255), (0, 0, info_width, info_height), 2)
        
        # Draw mission info
        title_font = pygame.font.SysFont(None, 32)
        date_font = pygame.font.SysFont(None, 24)
        desc_font = pygame.font.SysFont(None, 20)
        
        # Draw title
        title_text = title_font.render(mission["name"], True, (255, 255, 255))
        info_surface.blit(title_text, (20, 20))
        
        # Draw date
        date_text = date_font.render(mission["date"], True, (200, 200, 200))
        info_surface.blit(date_text, (20, 60))
        
        # Draw description (wrapped text)
        words = mission["description"].split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            text = " ".join(current_line)
            if desc_font.size(text)[0] > info_width - 40:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
        
        for i, line in enumerate(lines):
            desc_text = desc_font.render(line, True, (200, 200, 200))
            info_surface.blit(desc_text, (20, 100 + i * 25))
        
        # Draw the info window
        screen.blit(info_surface, (info_x, info_y))

def draw_settings():
    # Draw background
    if video_bg and video_bg.cap is not None:
        screen.blit(video_bg.get_frame(), (0, 0))
    else:
        screen.blit(background, (0, 0))
    
    # Draw menu overlay
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0,0,0,120))
    screen.blit(overlay, (0,0))
    
    title = font.render("Settings", True, (255,255,255))
    screen.blit(title, (screen_width//2-title.get_width()//2, 100))
    
    # Draw current display mode
    mode_text = "Fullscreen" if is_fullscreen else "Windowed"
    mode_display = font.render(f"Current Mode: {mode_text}", True, (255,255,255))
    screen.blit(mode_display, (screen_width//2-mode_display.get_width()//2, 150))
    
    for text, rect in settings_buttons:
        pygame.draw.rect(screen, (60,60,80), rect)
        pygame.draw.rect(screen, (255,255,255), rect, 2)
        btn_text = font.render(text, True, (255,255,255))
        screen.blit(btn_text, (rect[0]+rect[2]//2-btn_text.get_width()//2, rect[1]+rect[3]//2-btn_text.get_height()//2))

# --- Mission setup logic ---
def setup_mission(mission_id):
    global tile_map, units, enemy_units, player_unit, tank_unit, selected_unit, action_menu_active, action_menu_pos, waiting_for_target, current_action, camera_offset_x, camera_offset_y, hex_size
    
    # Stop the menu music
    pygame.mixer.music.stop()
    
    # Reset all state
    hex_size = base_hex_size
    tile_map = {}
    units = []
    enemy_units = []
    
    # Get mission data
    mission = MISSIONS[mission_id]
    
    # Create map with fixed layouts based on mission
    if mission_id == 0:  # City-based mission with river
        # Create a city layout with a river and bridges
        for q in range(-MAP_RADIUS, MAP_RADIUS + 1):
            for r in range(-MAP_RADIUS, MAP_RADIUS + 1):
                if -q - r >= -MAP_RADIUS and -q - r <= MAP_RADIUS:
                    # Create a river (horizontal line)
                    if r == 0:
                        terrain = "River"
                    # Create bridges across the river
                    elif r == 0 and (q == -2 or q == 2):
                        terrain = "Bridge"
                    # Create a city center
                    elif abs(q) <= 2 and abs(r) <= 2 and r != 0:
                        terrain = "House"
                    # Create some roads
                    elif q == 0 or r == 0 or q == r or q == -r:
                        terrain = "Road"
                    # Rest is plains
                    else:
                        terrain = "Plains"
                    tile_map[(q, r)] = Tile(q, r, terrain)
    
    else:  # Hill-based mission
        # Create a hill-based layout with some plains
        for q in range(-MAP_RADIUS, MAP_RADIUS + 1):
            for r in range(-MAP_RADIUS, MAP_RADIUS + 1):
                if -q - r >= -MAP_RADIUS and -q - r <= MAP_RADIUS:
                    # Create a central hill formation
                    if abs(q) <= 3 and abs(r) <= 3:
                        terrain = "Hill"
                    # Create some forest patches
                    elif (abs(q) == 4 and abs(r) <= 2) or (abs(r) == 4 and abs(q) <= 2):
                        terrain = "Forest"
                    # Rest is plains
                    else:
                        terrain = "Plains"
                    tile_map[(q, r)] = Tile(q, r, terrain)
    
    # Place player units
    player_unit = InfantryUnit("German Infantry", 100, 20, 70, 5, 10, "ger_infantry", range_=1, is_enemy=False)
    player_unit.q, player_unit.r = mission["player_pos"]
    player_unit.set_tile_map(tile_map)
    tile_map[mission["player_pos"]].unit = player_unit
    units.append(player_unit)
    
    tank_unit = TankUnit("German Tank", 200, 40, 80, 3, 5, "ger_tank", range_=2, armor=50, armor_penetration=30, is_enemy=False)
    tank_unit.q, tank_unit.r = mission["tank_pos"]
    tank_unit.set_tile_map(tile_map)
    tile_map[mission["tank_pos"]].unit = tank_unit
    units.append(tank_unit)
    
    # Place enemy unit
    enemy_unit = InfantryUnit("Russian Infantry", 100, 20, 60, 4, 10, "ger_infantry", range_=1, is_enemy=True)
    for (q, r), tile in tile_map.items():
        if tile.unit is None and abs(q) + abs(r) > 8:
            tile.unit = enemy_unit
            enemy_unit.q, enemy_unit.r = q, r
            enemy_unit.set_tile_map(tile_map)
            enemy_units.append(enemy_unit)
            break
    
    # Reset game state
    selected_unit = None
    action_menu_active = False
    action_menu_pos = None
    waiting_for_target = False
    current_action = None
    camera_offset_x, camera_offset_y = screen_width // 2, screen_height // 2 - 100

def toggle_fullscreen():
    global screen, is_fullscreen, screen_width, screen_height
    is_fullscreen = not is_fullscreen
    if is_fullscreen:
        screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((screen_width, screen_height))
    # Recreate background for new screen size
    global background
    background = create_gradient_background()

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
                        if text == "Toggle Fullscreen":
                            toggle_fullscreen()
                        elif text == "Back":
                            menu_state = MENU_STATE_MAIN
    elif menu_state == MENU_STATE_GAME:
        screen.fill((10, 10, 20))
        tile_rects = draw_map()
        draw_bottom_panel()  # Always draw the bottom panel
        if selected_unit:
            draw_unit_info(selected_unit)
        draw_action_menu()
        end_turn_btn = draw_end_turn_button()
        back_btn = draw_back_to_menu_button()
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    if back_btn.collidepoint(event.pos):
                        menu_state = MENU_STATE_MAIN
                        # Reset game state
                        selected_unit = None
                        action_menu_active = False
                        action_menu_pos = None
                        waiting_for_target = False
                        current_action = None
                        continue
                    elif end_turn_btn.collidepoint(event.pos):
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
                elif event.button == 4:  # Mouse wheel up
                    # Check if mouse is over the message log
                    log_rect = pygame.Rect(screen_width - MESSAGE_LOG_WIDTH - 20, 
                                         screen_height - BOTTOM_PANEL_HEIGHT + 10,
                                         MESSAGE_LOG_WIDTH, BOTTOM_PANEL_HEIGHT - 20)
                    if log_rect.collidepoint(event.pos):
                        message_log.handle_scroll(-SCROLL_STEP)  # Scroll up (show newer messages)
                    else:
                        hex_size = min(max_hex_size, hex_size + 2)  # Zoom in
                elif event.button == 5:  # Mouse wheel down
                    # Check if mouse is over the message log
                    log_rect = pygame.Rect(screen_width - MESSAGE_LOG_WIDTH - 20, 
                                         screen_height - BOTTOM_PANEL_HEIGHT + 10,
                                         MESSAGE_LOG_WIDTH, BOTTOM_PANEL_HEIGHT - 20)
                    if log_rect.collidepoint(event.pos):
                        message_log.handle_scroll(SCROLL_STEP)  # Scroll down (show older messages)
                    else:
                        hex_size = max(min_hex_size, hex_size - 2)  # Zoom out
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    dragging = False
            elif event.type == pygame.MOUSEMOTION:
                if dragging:
                    mx, my = event.pos
                    dx = mx - drag_start_pos[0]
                    dy = my - drag_start_pos[1]
                    camera_offset_x = camera_start_offset[0] + dx
                    camera_offset_y = camera_start_offset[1] + dy
        clock.tick(60)

pygame.quit()

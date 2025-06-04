import pygame
import math
import random

TERRAIN_TYPES = ["Plains", "Hill", "Forest", "House", "Road"]
TERRAIN_COLORS = {
    "Plains": (100, 200, 100),  # Light green
    "Hill": (150, 150, 100),    # Brownish
    "Forest": (0, 100, 0),      # Dark green
    "House": (150, 150, 150),   # Gray
    "Road": (200, 200, 150)     # Light brown/beige
}

def get_neighbors(q, r):
    directions = [(+1, 0), (+1, -1), (0, -1), (-1, 0), (-1, +1), (0, +1)]
    return [(q + dq, r + dr) for dq, dr in directions]

class Unit:
    def __init__(self, name, base_health, base_damage, base_morale, base_agility, base_soldiers, image_key, range_, is_enemy=False):
        self.name = name
        self.base_health = base_health
        self.health = base_health
        self.base_damage = base_damage
        self.base_morale = base_morale
        self.morale = base_morale
        self.base_agility = base_agility
        self.agility_points = base_agility
        self.base_soldiers = base_soldiers
        self.soldiers = base_soldiers
        self.image_key = image_key
        self.range = range_  # Range is now only for shooting
        self.selected = False
        self.is_enemy = is_enemy
        self.base_accuracy = 80  # Base accuracy percentage
        self.accuracy = self.base_accuracy
        self.smoke_affected = False
        self.grenades = 2  # Number of grenades available
        self.smoke_grenades = 1  # Number of smoke grenades available
        self.q = None  # Hex coordinates
        self.r = None
        self.surrendered = False
        self.tile_map = None  # Reference to the tile map

    def set_tile_map(self, tile_map):
        self.tile_map = tile_map

    def reset_turn(self):
        self.agility_points = self.base_agility
        self.accuracy = self.base_accuracy
        self.smoke_affected = False
        self.update_morale()

    def update_morale(self):
        if not self.tile_map:
            return False
            
        # Calculate morale based on health percentage and nearby friendly/enemy units
        health_percentage = (self.health / self.base_health) * 100
        
        # Count nearby friendly and enemy units
        nearby_friendly = 0
        nearby_enemy = 0
        for nq, nr in get_neighbors(self.q, self.r):
            if (nq, nr) in self.tile_map:
                unit = self.tile_map[(nq, nr)].unit
                if unit:
                    if unit.is_enemy == self.is_enemy:
                        nearby_friendly += 1
                    else:
                        nearby_enemy += 1
        
        # Calculate morale modifiers
        health_modifier = health_percentage / 100
        outnumbered_modifier = 1.0
        if nearby_enemy > nearby_friendly:
            outnumbered_modifier = 0.8  # 20% morale penalty when outnumbered
        
        # Update morale
        self.morale = int(self.base_morale * health_modifier * outnumbered_modifier)
        
        # Check for surrender
        if self.morale < 20 and not isinstance(self, TankUnit):  # Tanks don't surrender
            self.surrendered = True
            return True
        return False

    def take_damage(self, damage):
        if isinstance(self, InfantryUnit):
            self.soldiers = max(0, self.soldiers - int(damage / 10))
            self.health = self.soldiers * 10
            if self.health <= 0:
                # 50-50 chance of death or surrender
                if random.random() < 0.5:
                    self.surrendered = True
                    return True
                else:
                    return True  # Unit is destroyed
        else:
            self.health = max(0, self.health - damage)
            if self.health <= 0:
                return True
        return False

    def is_adjacent(self, other_tile):
        dq = abs(self.q - other_tile.q)
        dr = abs(self.r - other_tile.r)
        ds = abs(-self.q - self.r + other_tile.q + other_tile.r)
        return max(dq, dr, ds) == 1

    def can_throw_grenade(self, target_tile):
        # Check if unit has grenades and enough AP
        if self.grenades <= 0 or self.agility_points < 2:
            return False
        # Check if target is adjacent
        return self.is_adjacent(target_tile)

    def throw_grenade(self, target_tile):
        if not self.can_throw_grenade(target_tile):
            return False
        
        # Deal damage to target tile's unit
        if target_tile.unit:
            damage = self.base_damage * 1.5  # Grenades deal 50% more damage
            target_tile.unit.health -= int(damage)
            if target_tile.unit.health <= 0:
                target_tile.unit = None
        
        # Use up grenade and AP
        self.grenades -= 1
        self.agility_points -= 2
        return True

    def get_status_report(self):
        morale_status = "High" if self.morale > 70 else "Medium" if self.morale > 40 else "Low"
        health_status = "Good" if self.health > 70 else "Fair" if self.health > 40 else "Critical"
        accuracy_status = "Excellent" if self.accuracy > 80 else "Good" if self.accuracy > 60 else "Poor"
        
        status_messages = [
            f"Unit Status: {self.name}",
            f"Health: {health_status} ({self.health}/{self.base_health})",
            f"Morale: {morale_status} ({self.morale}%)",
            f"Accuracy: {accuracy_status}",
            f"Remaining Actions: {self.agility_points}/{self.base_agility}",
            f"Movement Range: 1 hex per AP",
            f"Combat Range: {self.range} hexes"
        ]
        
        # Add soldier count for infantry
        if not isinstance(self, TankUnit):
            status_messages.insert(2, f"Soldiers: {self.soldiers}/{self.base_soldiers}")
        
        # Only add grenade info for infantry
        if not isinstance(self, TankUnit):
            status_messages.extend([
                f"Grenades: {self.grenades}",
                f"Smoke Grenades: {self.smoke_grenades}"
            ])
            
        return status_messages

class InfantryUnit(Unit):
    def __init__(self, name, base_health, base_damage, base_morale, base_agility, base_soldiers, image_key, range_, is_enemy=False):
        super().__init__(name, base_health, base_damage, base_morale, base_agility, base_soldiers, image_key, range_, is_enemy)
        self.armor = 0  # Infantry has no armor
        self.armor_penetration = 0  # Infantry has no armor penetration
        self.base_accuracy = 80  # Infantry has good accuracy
        self.accuracy = self.base_accuracy
        self.range = 3  # Infantry can engage at up to 3 hexes

    def get_accuracy_at_range(self, distance):
        # Accuracy decreases with range
        if distance == 1:
            return self.accuracy  # Full accuracy at point blank
        elif distance == 2:
            return self.accuracy * 0.8  # 20% penalty at medium range
        else:
            return self.accuracy * 0.6  # 40% penalty at long range

class TankUnit(Unit):
    def __init__(self, name, base_health, base_damage, base_morale, base_agility, base_soldiers, image_key, range_, armor, armor_penetration, is_enemy=False):
        super().__init__(name, base_health, base_damage, base_morale, base_agility, base_soldiers, image_key, range_, is_enemy)
        self.armor = armor
        self.armor_penetration = armor_penetration
        self.base_accuracy = 70  # Tanks have lower base accuracy
        self.accuracy = self.base_accuracy
        self.he_rounds = 5  # High Explosive rounds
        self.aphe_rounds = 5  # Armor Piercing High Explosive rounds
        self.range = 4  # Tanks have longer range
        # Remove grenades and smoke grenades for tanks
        self.grenades = 0
        self.smoke_grenades = 0

    def get_status_report(self):
        base_report = super().get_status_report()
        base_report.extend([
            f"Armor: {self.armor}",
            f"Armor Penetration: {self.armor_penetration}",
            f"HE Rounds: {self.he_rounds}",
            f"APHE Rounds: {self.aphe_rounds}"
        ])
        return base_report

class Tile:
    def __init__(self, q, r, terrain_type):
        self.q = q
        self.r = r
        self.terrain_type = terrain_type
        self.unit = None
        self.smoke = False
        self.smoke_turns = 0  # Track how many turns the smoke will last

        if terrain_type == "Plain":
            self.defense_bonus = 0
            self.accuracy_penalty = 0
        elif terrain_type == "House":
            self.defense_bonus = 0.3
            self.accuracy_penalty = 0
        elif terrain_type == "Hill":
            self.defense_bonus = 0.1
            self.accuracy_penalty = -0.1

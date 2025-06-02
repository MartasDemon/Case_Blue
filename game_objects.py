import pygame
import math
import random

TERRAIN_TYPES = ["Plain", "House", "Hill"]
TERRAIN_COLORS = {
    "Plain": (180, 220, 180),
    "House": (100, 100, 100),
    "Hill": (160, 130, 100)
}

class InfantryUnit:
    def __init__(self, name, base_health, base_damage, base_morale, base_agility, base_soldiers, image_key, range_, is_enemy=False):
        self.name = name
        self.base_health = base_health
        self.health = base_health
        self.base_damage = base_damage
        self.base_morale = base_morale
        self.base_agility = base_agility
        self.agility_points = base_agility
        self.base_soldiers = base_soldiers
        self.image_key = image_key
        self.range = range_
        self.selected = False
        self.is_enemy = is_enemy

    def reset_turn(self):
        self.agility_points = self.base_agility

    def is_adjacent(self, other_tile):
        dq = abs(self.q - other_tile.q)
        dr = abs(self.r - other_tile.r)
        ds = abs(-self.q - self.r + other_tile.q + other_tile.r)
        return max(dq, dr, ds) == 1

class Tile:
    def __init__(self, q, r, terrain_type):
        self.q = q
        self.r = r
        self.terrain_type = terrain_type
        self.unit = None

        if terrain_type == "Plain":
            self.defense_bonus = 0
            self.accuracy_penalty = 0
        elif terrain_type == "House":
            self.defense_bonus = 0.3
            self.accuracy_penalty = 0.1
        elif terrain_type == "Hill":
            self.defense_bonus = 0.1
            self.accuracy_penalty = -0.1

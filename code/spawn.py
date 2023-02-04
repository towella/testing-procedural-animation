import pygame


class Spawn(pygame.sprite.Sprite):
    def __init__(self, x, y, name, player_facing):
        super().__init__()
        self.x = x
        self.y = y
        self.name = name
        self.player_facing = player_facing

    def apply_scroll(self, scroll_value):
        self.x -= int(scroll_value[1])
        self.y -= int(scroll_value[0])

    def update(self, scroll_value):
        self.apply_scroll(scroll_value)
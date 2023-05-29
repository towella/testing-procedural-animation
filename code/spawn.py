import pygame


# in-room spawns are stored as property of SpawnTrigger class for simplicity of access
class Spawn(pygame.sprite.Sprite):
    def __init__(self, x, y, name, parallax, player_facing):
        super().__init__()
        self.original_pos = (x, y)
        self.x = x
        self.y = y
        self.name = name
        self.parallax = parallax
        self.player_facing = player_facing

    def apply_scroll(self, scroll_value, use_parallax):
        if use_parallax:
            self.x -= int(scroll_value[0] * self.parallax[0])
            self.y -= int(scroll_value[1] * self.parallax[1])
        else:
            self.x -= int(scroll_value[0])
            self.y -= int(scroll_value[1])

    def update(self, scroll_value, use_parallax=False):
        self.apply_scroll(scroll_value, use_parallax)
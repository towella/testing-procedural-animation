import pygame


class Trigger(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, name):
        super().__init__()
        self.hitbox = pygame.Rect(x, y, width, height)
        self.name = name

    def apply_scroll(self, scroll_value):
        self.hitbox.x -= int(scroll_value[1])
        self.hitbox.y -= int(scroll_value[0])

    def update(self, scroll_value):
        self.apply_scroll(scroll_value)
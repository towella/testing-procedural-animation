import pygame


class Trigger(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, name, parallax):
        super().__init__()
        self.original_pos = (x, y)
        self.hitbox = pygame.Rect(x, y, width, height)
        self.name = name
        self.parallax = parallax

    def apply_scroll(self, scroll_value, use_parallax):
        if use_parallax:
            self.hitbox.x -= int(scroll_value[0] * self.parallax[0])
            self.hitbox.y -= int(scroll_value[1] * self.parallax[1])
        else:
            self.hitbox.x -= int(scroll_value[0])
            self.hitbox.y -= int(scroll_value[1])

    def update(self, scroll_value, use_parallax=False):
        self.apply_scroll(scroll_value, use_parallax)


# stores correspoding in-room spawn as property
class SpawnTrigger(Trigger):
    def __init__(self, x, y, width, height, name, parallax, trigger_spawn):
        super().__init__(x, y, width, height, name, parallax)
        self.trigger_spawn = trigger_spawn

    def apply_scroll(self, scroll_value, use_parallax=False):
        if use_parallax:
            self.hitbox.x -= int(scroll_value[0] * self.parallax[0])
            self.hitbox.y -= int(scroll_value[1] * self.parallax[1])
        else:
            self.hitbox.x -= int(scroll_value[0])
            self.hitbox.y -= int(scroll_value[1])
        self.trigger_spawn.update(scroll_value)
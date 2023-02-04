import pygame, random
from support import circle_surf


class Particle(pygame.sprite.Sprite):
    def __init__(self, screen, colour, apply_gravity=False):
        super().__init__()
        self.screen = screen

        # gravity
        self.apply_gravity = apply_gravity
        self.gravity_vel = 4

        # position, velocity, direction, timer
        self.x = random.randint(0, screen.get_width())
        self.y = random.randint(0, screen.get_height())
        self.vel = [random.randint(0, 18) / 10 - 1, random.randint(0, 18) / 10 - 1]
        self.direction = pygame.math.Vector2()
        self.timer = random.randint(1, 10)
        self.size = random.randint(1, 3)
        while self.size > self.timer:
            self.timer = random.randint(1, 10)

        # colour
        self.colour = colour

# -- movement methods --

    def gravity(self):
        self.direction.y += self.gravity_vel

    def apply_x(self):
        self.direction.x += self.x

        self.x += self.direction.x

    def apply_y(self):
        self.direction.y += self.y

        if self.apply_gravity:
            self.gravity()

        self.y += self.direction.y

    def update(self):
        self.direction = pygame.math.Vector2()  # reset direction

        # apply movement directions
        self.apply_x()
        self.apply_y()

        if self.y + self.size >= 70:
            self.kill()
        self.timer -= 0.1
        self.size -= 0.1
        if self.size < 1:
            self.size = 1

        if self.timer <= 0:
            self.kill()

    def draw(self):
        surf = circle_surf(int(self.size), self.colour)
        surf_rect = surf.get_rect()
        surf_rect.centerx = int(self.x)
        surf_rect.centery = int(self.y)
        self.screen.blit(surf, surf_rect.topleft, special_flags=pygame.BLEND_RGB_ADD)

import pygame, math
from support import get_distance, get_angle_rad


class Player(pygame.sprite.Sprite):
    def __init__(self, spawn, screen_surface, radius):
        super().__init__()
        self.surface = screen_surface

        self.pos = [spawn.x, spawn.y]
        self.prev_pos = [spawn.x, spawn.y]
        self.radius = radius

        self.rot = 0  # in RAD
        self.speed = 5
        self.direction = [0, 0]

    def get_input(self):
        keys = pygame.key.get_pressed()

        if keys[pygame.K_w]:
            self.direction[1] -= self.speed
        if keys[pygame.K_s]:
            self.direction[1] += self.speed
        if keys[pygame.K_a]:
            self.direction[0] -= self.speed
        if keys[pygame.K_d]:
            self.direction[0] += self.speed
        # implement diagonal speed limitation

    def get_pos(self):
        return self.pos

    def collision(self, tiles):
        for tile in tiles:
            distance = get_distance(self.pos, tile.hitbox.center)
            if distance - (tile.radius + self.radius) < 0:
                angle = get_angle_rad(self.pos, self.prev_pos)  # angle to move back towards where seg came from
                self.pos[0] += math.sin(angle) * (tile.radius + self.radius - distance + 1)
                self.pos[1] += math.cos(angle) * (tile.radius + self.radius - distance + 1)

    def apply_scroll(self, scroll_value):
        self.pos[0] -= int(scroll_value[0])
        self.pos[1] -= int(scroll_value[1])

    def update(self, tiles, rot, dt, scroll_value):
        self.direction = [0, 0]
        self.prev_pos = [self.pos[0], self.pos[1]]
        self.rot += rot

        # -- INPUT --
        self.get_input()

        # -- CHECKS/UPDATE --
        self.pos[0] += self.direction[0]
        self.pos[1] += self.direction[1]
        self.collision(tiles)

        self.apply_scroll(scroll_value)

    def draw(self):
        pygame.draw.circle(self.surface, 'red', self.pos, self.radius, 1)
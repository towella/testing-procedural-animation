import pygame
from math import sin
from random import randint
from support import circle_surf, pos_for_center, get_rect_corners, get_angle, get_distance


class Light:
    def __init__(self, surface, pos, colour, raycasted, max_radius, min_radius=0, glow_speed=0):
        self.surface = surface
        self.pos = pos
        self.raycasted = raycasted
        # amplitude is difference between max and min / 2, (to account for + and -). This creates correct range for sin
        self.amplitude = (max_radius - min_radius)/2
        self.max_radius = max_radius
        self.min_radius = min_radius
        self.radius = max_radius
        self.colour = colour
        self.time = randint(1, 500)
        self.glow_speed = glow_speed
        self.image = circle_surf(self.radius, self.colour)

    # TODO change angles to RADIANS for precsision
    # use mask of tile layer to get verticies more efficiently
    '''def raycasted_light(self, pos, tiles):
        angles = []
        points = []
        polygon_points = {}
        # get surface
        light_surf = pygame.Surface((self.radius*2, self.radius*2))
        light_surf.set_colorkey((0, 0, 0))

        # get tile corner angles from pos for raycasting (sorted by angle ascending in a list)
        for tile in tiles:
            for point in get_rect_corners(tile.hitbox):
                if self.radius - get_distance(self.pos, point) >= 0:
                    points.append(point)

        for point in points:
            angle = get_angle(self.pos, point)

            polygon_points[angle + 1] = raycast(angle + 1, pos, self.radius, tiles)
            polygon_points[angle] = point
            polygon_points[angle - 1] = raycast(angle - 1, pos, self.radius, tiles)

            angles.append(angle)
            angles.append(angle + 1)
            angles.append(angle - 1)
                #point[0] -= pos[0] - self.radius  # makes point relative to the screen origin rather than pos origin
                #point[1] -= pos[1] - self.radius
                #points.append(point)

        for point in points:
            pygame.draw.circle(self.surface, 'red', point, 1)

        angles.sort()
        points = []

        for angle in angles:
            points.append(polygon_points[angle])

        print(points)

        if len(points) > 2:
            pygame.draw.polygon(light_surf, self.colour, points, 0)

        return light_surf'''

    def get_surf(self):
        surf = pygame.Surface((self.radius * 2, self.radius * 2))
        surf.set_colorkey((0, 0, 0))
        surf.blit(self.image, (0, 0))
        return surf

    # masks light circles based on mask image (only light up certain layers of game, which are flattened into masked image)
    def composite_lighting(self, mask_tile):
        surf = self.get_surf()
        light_center = pos_for_center(surf, self.pos)

        surf.blit(mask_tile.image, (-light_center[0] + mask_tile.rect.topleft[0], -light_center[1] + mask_tile.rect.topleft[1]))
        surf.set_colorkey((0, 0, 0))
        return surf

    def update(self, dt, pos, tiles=pygame.sprite.Group()):
        # amplitude * sin(time * speed) + max_radius - amplitude
        # adding difference between max_radius and amplitude brings sin values (based on amplitude)
        # into correct range between max and min.
        self.radius = self.amplitude * sin(self.time * self.glow_speed) + self.max_radius - self.amplitude
        self.pos = pos

        # if not self.raycasted:
        self.image = circle_surf(abs(self.radius), self.colour)
        # else:
            # self.image = self.raycasted_light(pos, tiles)

        self.time += round(1 * dt)

    # mask_tile must be of a tile class with image (surface) and position attributes (e.g. rect, 2-tuple)
    def draw(self, mask_tile=None):
        if mask_tile is None:
            surf = self.image
        else:
            surf = self.composite_lighting(mask_tile)
        self.surface.blit(surf, pos_for_center(self.image, self.pos), special_flags=pygame.BLEND_RGB_ADD)


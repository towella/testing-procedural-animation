import pygame
from random import randint
import math
from support import get_distance, lerp1D, rotate_point_deg

minute = 60 * 60  # 60fps * 60 seconds


class Flock:
    def __init__(self, surface, flock_size, use_predator=False, use_wind=False, parallax=(1, 1)):
        self.surface = surface
        self.parallax = parallax  # modifier to scroll_value provided in update

        self.chunk_size = 80
        # chunks height and width include 2 buffer chunks as a margin beyond screen view
        self.chunks_width = self.surface.get_width() // self.chunk_size + 2  # number of chunks horizontally
        self.chunks_height = self.surface.get_height() // self.chunk_size + 2  # number of chunks vertically
        self.chunks = {}
        # loop from -1 to 1 less than chunk width/height (due to nature of range function)
        for y in range(-1, self.chunks_height):
            for x in range(-1, self.chunks_width):
                self.chunks[(x, y)] = []

        self.boids = [Boid(self.surface) for b in range(flock_size)]

        self.use_predator = use_predator
        if self.use_predator:
            self.predator = BoidPredator(self.surface)
        else:
            self.predator = None

        self.max_wind = 3
        self.min_wind_change = int(minute * 0.1)
        self.max_wind_change = int(minute * 0.2)
        self.wind_transition = 60
        self.wind_change = randint(self.min_wind_change, self.max_wind_change)
        self.use_wind = use_wind
        self.wind = [0, 0]
        self.new_wind = [0.0, 0.0]  # wind for next transition

    def update(self, scroll_value, rot_value, origin=(0, 0)):
        if self.use_wind:
            self.wind_change -= 1
            # lerp wind to new wind if in transitional period
            if -self.wind_transition <= self.wind_change < 0:
                self.wind[0] = lerp1D(self.wind[0], self.new_wind[0], abs(self.wind_change) / self.wind_transition)
                self.wind[1] = lerp1D(self.wind[1], self.new_wind[1], abs(self.wind_change) / self.wind_transition)
            # set new wind for next transition if transition is completed
            elif self.wind_change < -self.wind_transition:
                self.new_wind[0] = randint(-self.max_wind * 100, self.max_wind * 100) / 100
                self.new_wind[1] = randint(-self.max_wind * 100, self.max_wind * 100) / 100
                self.wind_change = randint(self.min_wind_change, self.max_wind_change)

        # update predator then apply camera
        if self.use_predator:
            self.predator.pred_update(self.boids, self.wind)
            self.predator.apply_camera(scroll_value, rot_value, origin, self.parallax)

        # first update chunks (reset so empty)
        for chunk in self.chunks.keys():
            self.chunks[chunk] = []
        # update boids by chunk
        for b in self.boids:
            b.apply_camera(scroll_value, rot_value, origin, self.parallax)  # apply camera so in same state as pred
            pos = b.get_pos()
            # find boid chunk index
            y = int(pos[1] // self.chunk_size)
            x = int(pos[0] // self.chunk_size)
            # if boid is outside of chunk area, move inside chunk area outside of screen view and continue
            # (there is a 1 chunk margin outside of screen view so boids can move in and out of view without
            # obvious collision detection)
            # -2 on chunk height and width account for margin chunks
            # x and y are in domain [0, len]
            # coords are in domain [-chunk, len*chunk]
            # hence discrepencies with - 2 and -1. -2 is for x and y (count from 0), -1 is for pixels (count from -chunk)
            # I am so sorry, this is the only way I could think to make it work
            if y < -1:
                b.set_pos((pos[0], -self.chunk_size))
                y = -1
            elif y > self.chunks_height - 2:
                b.set_pos((pos[0], (self.chunks_height - 1) * self.chunk_size))
                y = self.chunks_height - 2
            if x < -1:
                b.set_pos((-self.chunk_size, pos[1]))
                x = -1
            elif x > self.chunks_width - 2:
                b.set_pos(((self.chunks_width - 1) * self.chunk_size, pos[1]))
                x = self.chunks_width - 2
            self.chunks[(x, y)].append(b)

        # x, y
        neighbour_chunks = [[-1, -1], [0, -1], [1, -1],
                            [-1, 0],  [0, 0],  [1, 0],
                            [-1, 1],  [0, 1],  [1, 1]]
        for c in self.chunks.keys():
            # only do chunk checks for chunks that are not empty
            if len(self.chunks[c]) > 0:
                # collect neighbouring boids for chunk
                neighbours = []
                for n in neighbour_chunks:
                    # ensure chunk is within range
                    if 0 <= c[1] + n[1] < self.chunks_height and 0 <= c[0] + n[0] < self.chunks_width:
                        ny = c[1] + n[1]
                        nx = c[0] + n[0]
                        neighbours += self.chunks[(nx, ny)]
                # update boids in chunk using neighbour list
                for b in self.chunks[c]:
                    b.update(neighbours, self.wind, self.predator)

    def draw(self):
        for b in self.boids:
            b.draw()
        if self.use_predator:
            self.predator.draw()


class Boid:
    def __init__(self, surface):
        self.surface = surface
        self.rot_deg = 0

        self.pos = [randint(0, surface.get_width()), randint(0, surface.get_height())]  # x, y
        self.vel = [0, 0]  # x, y
        self.min_speed = 1
        self.max_speed = 5  # 3 or 5

        self.protected_r = 10  # protected distance to steer away from other boids
        self.visual_r = 80  # 50 distance boid can see other boids  MUST BE LESS THAN CHUNK SIZE

        self.turn_factor = 0.1   # 0.1 or 0.05 amount boid turns (multiplier)
        self.screen_margin = 0  # 200 margin from screen edge before turning

        self.matching_factor = 0.05  # loose 0.02 or 0.05 tight, tend towards average velocity (multiplier)
        self.centering_factor = 0.005  # 0.005 0.001 tend towards center of visual flock (multiplier)
        self.escape_factor = 0.2  # factor boids attempt to escape predator (multiplier)

    def get_pos(self):
        return self.pos

    def get_vel(self):
        return self.vel

    def set_pos(self, pos):
        self.pos[0] = pos[0]
        self.pos[1] = pos[1]

    def set_vel(self, vel):
        self.vel[0] = vel[0]
        self.vel[1] = vel[1]

    def apply_camera(self, scroll_value, rot_value, origin, parallax):
        # apply scroll with parallax
        self.pos[0] -= int(scroll_value[0] * parallax[0])
        self.pos[1] -= int(scroll_value[1] * parallax[1])
        # apply rotation
        if rot_value != 0:
            self.pos = rotate_point_deg(self.pos, origin, rot_value)

    def update(self, boids, wind, predator):
        # steering
        close_dx = 0
        close_dy = 0
        # alignment and cohesion
        avg_x_pos = 0
        avg_y_pos = 0
        avg_x_vel = 0
        avg_y_vel = 0
        neighbours = 0

        # loop through all other boids in flock
        for b in boids:
            bpos = b.get_pos()
            bvel = b.get_vel()
            dist = get_distance(self.pos, bpos)
            # within protected
            if dist <= self.protected_r:
                close_dx += self.pos[0] - bpos[0]
                close_dy += self.pos[1] - bpos[1]
            # outside protected but within visual range
            elif dist <= self.visual_r:
                # accumulate averages and total neighbours
                neighbours += 1
                avg_x_pos += bpos[0]
                avg_y_pos += bpos[1]
                avg_x_vel += bvel[0]
                avg_y_vel += bvel[1]
                # TODO for testing
                # pygame.draw.line(self.surface, "pink", self.pos, bpos, 1)

        # - alignment and cohesion -
        if neighbours > 0:
            # calculate avgs
            avg_x_pos /= neighbours
            avg_y_pos /= neighbours
            avg_x_vel /= neighbours
            avg_y_vel /= neighbours
        # apply avg pos to vel
        self.vel[0] += (avg_x_pos - self.pos[0]) * self.centering_factor
        self.vel[1] += (avg_y_pos - self.pos[1]) * self.centering_factor
        # apply avg vels (difference between vels and multiply by match factor multiplier)
        self.vel[0] += (avg_x_vel - self.vel[0]) * self.matching_factor
        self.vel[1] += (avg_y_vel - self.vel[1]) * self.matching_factor

        # - steering away from other boids -
        self.vel[0] += close_dx * self.turn_factor
        self.vel[1] += close_dy * self.turn_factor

        # - steer away from predator -
        if predator is not None:
            pred_pos = predator.get_pos()
            if get_distance(self.pos, pred_pos) <= self.visual_r:
                self.vel[0] += (self.pos[0] - pred_pos[0]) * self.escape_factor
                self.vel[1] += (self.pos[1] - pred_pos[1]) * self.escape_factor

        # - steer away from screen edges -
        # left margin
        if self.pos[0] < self.screen_margin:
            self.vel[0] += self.turn_factor
        # right margin
        elif self.pos[0] > self.surface.get_width() - self.screen_margin:
            self.vel[0] -= self.turn_factor
        # bottom margin
        if self.pos[1] > self.surface.get_height() - self.screen_margin:
            self.vel[1] -= self.turn_factor
        # top margin
        elif self.pos[1] < self.screen_margin:
            self.vel[1] += self.turn_factor

        # - set speed within bounds -
        speed = math.sqrt(self.vel[0]**2 + self.vel[1]**2)
        # find fraction of speed each vel component makes up then multiply to cap at max or min speed
        if speed > self.max_speed:
            self.vel[0] = (self.vel[0] / speed) * self.max_speed
            self.vel[1] = (self.vel[1] / speed) * self.max_speed
        elif speed < self.min_speed:
            self.vel[0] = (self.vel[0] / speed) * self.min_speed
            self.vel[1] = (self.vel[1] / speed) * self.min_speed

        # - apply velocity and wind -
        # wind is separate force to boid velocity (external force)
        self.pos[0] += self.vel[0] + wind[0]
        self.pos[1] += self.vel[1] + wind[1]

        # - calculate angle (for rendering) -
        self.rot_deg = math.degrees(math.atan2(self.vel[0], self.vel[1]))

    def draw(self):
        point_ahead = 6
        point_sides = 2
        outline = [
            # point ahead
            [self.pos[0] + math.sin(math.radians(self.rot_deg)) * point_ahead,
             self.pos[1] + math.cos(math.radians(self.rot_deg)) * point_ahead],
            # point side1
            [self.pos[0] + math.sin(math.radians(self.rot_deg + 90)) * point_sides,
             self.pos[1] + math.cos(math.radians(self.rot_deg + 90)) * point_sides],
            # point side2
            [self.pos[0] + math.sin(math.radians(self.rot_deg - 90)) * point_sides,
             self.pos[1] + math.cos(math.radians(self.rot_deg - 90)) * point_sides]
        ]
        pygame.draw.polygon(self.surface, (30, 30, 30), outline)


class BoidPredator(Boid):
    def __init__(self, surface):
        super().__init__(surface)
        self.min_speed = 1
        self.max_speed = 7

        self.turn_factor = 0.1  # 0.1 or 0.05 amount boid turns (multiplier)
        self.screen_margin = 400  # 200 margin from screen edge before turning

        self.min_attack_timer = int(minute * 0.1)
        self.max_attack_timer = int(minute * 0.7)
        self.attack_timer = randint(self.min_attack_timer, self.max_attack_timer)
        self.attack_duration = 60 * 5  # 60fps * 5 seconds

        self.centering_factor = 0.01  # how fast moves towards flock center (multiplier)
        self.circling_pos = [randint(0, self.surface.get_width()), randint(0, self.surface.get_height())]
        self.circling_factor = 0.004
        self.circling_max_speed = 4

    # cant be called update as parameters are not the same as parent class update
    def pred_update(self, boids, wind):
        # alignment and cohesion
        avg_x_pos = 0
        avg_y_pos = 0
        neighbours = 0

        self.attack_timer -= 1

        # loop through all other boids in flock
        for b in boids:
            bpos = b.get_pos()
            dist = get_distance(self.pos, bpos)
            # attack if timer is in attack window
            if -self.attack_duration <= self.attack_timer < 0:
                avg_x_pos += bpos[0]
                avg_y_pos += bpos[1]
                neighbours += 1

        # if attack timer is exceeded, reset all
        if self.attack_timer < -self.attack_duration:
            self.attack_timer = randint(self.min_attack_timer, self.max_attack_timer)
            self.circling_pos = [randint(0, self.surface.get_width()), randint(0, self.surface.get_height())]

        # tend towards avg pos of entire flock when attacking (neighbours only incremented when attacking)
        if neighbours > 0:
            avg_x_pos /= neighbours
            avg_y_pos /= neighbours
            self.vel[0] += (avg_x_pos - self.pos[0]) * self.centering_factor
            self.vel[1] += (avg_y_pos - self.pos[1]) * self.centering_factor
        # otherwise circle around point
        elif self.attack_timer >= 0:
            # multiply by random(0.5, 1) to add randomness to circling path
            self.vel[0] += (self.circling_pos[0] - self.pos[0]) * self.circling_factor * randint(5, 10) / 10
            self.vel[1] += (self.circling_pos[1] - self.pos[1]) * self.circling_factor * randint(5, 10) / 10

        # - steer away from screen edges -
        # left margin
        if self.pos[0] < self.screen_margin:
            self.vel[0] += self.turn_factor
        # right margin
        elif self.pos[0] > self.surface.get_width() - self.screen_margin:
            self.vel[0] -= self.turn_factor
        # bottom margin
        if self.pos[1] > self.surface.get_height() - self.screen_margin:
            self.vel[1] -= self.turn_factor
        # top margin
        elif self.pos[1] < self.screen_margin:
            self.vel[1] += self.turn_factor

        # - set speed within bounds -
        speed = math.sqrt(self.vel[0] ** 2 + self.vel[1] ** 2)
        # find fraction of speed each vel component makes up then multiply to cap at max or min speed
        # circling has separate cap to normal movement
        if speed > self.circling_max_speed and self.attack_timer > 0:
            self.vel[0] = (self.vel[0] / speed) * self.circling_max_speed
            self.vel[1] = (self.vel[1] / speed) * self.circling_max_speed
        elif speed > self.max_speed:
            self.vel[0] = (self.vel[0] / speed) * self.max_speed
            self.vel[1] = (self.vel[1] / speed) * self.max_speed
        elif speed < self.min_speed:
            self.vel[0] = (self.vel[0] / speed) * self.min_speed
            self.vel[1] = (self.vel[1] / speed) * self.min_speed

        # - apply velocity and wind -
        # wind is separate force to boid velocity (external force)
        self.pos[0] += self.vel[0] + wind[0]
        self.pos[1] += self.vel[1] + wind[1]

        # - calculate angle (for rendering) -
        self.rot_deg = math.degrees(math.atan2(self.vel[0], self.vel[1]))

    def draw(self):
        point_ahead = 12
        point_sides = 4
        outline = [
            # point ahead
            [self.pos[0] + math.sin(math.radians(self.rot_deg)) * point_ahead,
             self.pos[1] + math.cos(math.radians(self.rot_deg)) * point_ahead],
            # point side1
            [self.pos[0] + math.sin(math.radians(self.rot_deg + 90)) * point_sides,
             self.pos[1] + math.cos(math.radians(self.rot_deg + 90)) * point_sides],
            # point side2
            [self.pos[0] + math.sin(math.radians(self.rot_deg - 90)) * point_sides,
             self.pos[1] + math.cos(math.radians(self.rot_deg - 90)) * point_sides]
        ]
        pygame.draw.polygon(self.surface, "brown", outline)
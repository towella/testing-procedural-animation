import pygame
from game_data import controller_map, tile_size


class Camera():
    def __init__(self, surface, screen_rect, player, abs_boundaries, controllers):
        self.player = player  # the target of the camera
        self.target = [self.player.rect.centerx, self.player.rect.centery]  # target position
        self.scroll_value = [0, 0]  # the scroll, shifts the world to create camera effect
        self.abs_boundaries = abs_boundaries
        self.controllers = controllers
        self.focus_target = False

        #-- zoom --
        self.zoom = 1
        self.zoom_speed = 0.1

        # lerp = linear interpolation. Speed the camera takes to center on the player as it moves, (camera smoothing)
        # -- normal lerp --
        self.norm_lerp = 15  # (15) normal camera interpolation speed
        # -- fall --
        self.fall_lerp_max = 8  # (8) maximum sensitivity the camera can track the player w/ while falling
        self.fall_lerp_increment = 0.5  # used to increment the falling lerp gradually to it's max for smoothness
        self.fall_min_time = 60  # number of frames w/ y vel > 0 before falling logic is applied
        # -- lerp active values --
        self.lerp_x = self.norm_lerp  # controls scroll interpolation amount x (sensitivity of camera to movement of target)
        self.lerp_y = self.norm_lerp  # controls scroll interpolation amount y (sensitivity of camera to movement of target)

        # -- offsets --
        self.facing_offset = 25  # offset from the player on the horizontal when not falling and change facing dir (40)
        self.walking_offset = 35  # offset from the player on the horizontal when walking (not falling and move hori)

        self.fall_offset = 0  # added to when falling, allows gradual movement of target
        self.fall_offset_max = 100  # max offset from player on vertical when falling
        self.fall_offset_increment = 6  # increment target is moved by

        self.look_up_down = 100
        self.look_up_down_timer = 0
        self.look_up_down_max = 15

        # -- screen dimensions and rect --
        self.screen_width = surface.get_width()
        self.screen_height = surface.get_height()
        self.screen_center_x = surface.get_width() // 2
        self.screen_center_y = surface.get_height() // 2
        self.screen_rect = screen_rect

        # -- boundary collision --
        # separate for x and y so that the shorter one doesn't glitch out with too large a tolerance
        # half screen dimension to snap camera to wall as soon as player turns around anywhere on wall side of screen
        self.collision_tolerance_x = self.screen_width // 2
        self.collision_tolerance_y = self.screen_height // 2

# -- input --

    def get_input(self):
        keys = pygame.key.get_pressed()

        # -- camera look up and down--
        if self.player.on_ground:
            if keys[pygame.K_DOWN] or self.get_controller_input('look_down'):
                self.look_up_down_timer += 1
                if self.look_up_down_timer >= self.look_up_down_max:
                    self.target[1] += self.look_up_down
            elif keys[pygame.K_UP] or self.get_controller_input('look_up'):
                self.look_up_down_timer += 1
                if self.look_up_down_timer >= self.look_up_down_max:
                    self.target[1] -= self.look_up_down
            else:
                self.look_up_down_timer = 0

        # TODO testing remove potentially
        if keys[pygame.K_LSHIFT] and keys[pygame.K_c]:
            self.change_zoom(-self.zoom_speed)
        elif keys[pygame.K_c]:
            self.change_zoom(self.zoom_speed)

    def get_controller_input(self, input_check):
        if len(self.controllers) >= 1:
            controller = self.controllers[0]
            if input_check == 'look_down' and 0.8 < controller.get_axis(controller_map['right_analog_y']) <= 1:
                return True
            elif input_check == 'look_up' and -0.8 > controller.get_axis(controller_map['right_analog_y']) >= -1:
                return True
        return False

# -- camera --

    def focus(self, focusing):
        self.focus_target = focusing

    def change_zoom(self, zoom_amount):
        # Sets zoom amount
        self.zoom += zoom_amount
        # caps min zoom (no negative zoom)
        if self.zoom < 1:
            self.zoom = 1

    def update_target(self):
        # target[0] = x, target[1] = y
        self.target = [self.player.rect.centerx, self.player.rect.centery]  # sets target to player pos for modification

        self.get_input()

        # -- player horizontal directional offset --
        '''# walking
        if self.player.direction.x != 0:
            # right
            if self.player.direction.x > 0:
                self.target[0] += self.walking_offset
            # left
            else:
                self.target[0] -= self.walking_offset'''

        # facing (multiply distance by direction)
        self.target[0] += self.facing_offset * self.player.facing_right

        # -- falling vertical offset --
        # if player IS falling have vertical offset
        # TODO change or remove offset if player is on a wall
        if self.player.fall_timer > self.fall_min_time:
            # gradually moves target below player
            self.fall_offset += self.fall_offset_increment
            # caps the fall_offset at the max
            if self.fall_offset > self.fall_offset_max:
                self.fall_offset = self.fall_offset_max
            # applies fall_offset
            self.target[1] += self.fall_offset
        else:
            self.fall_offset = 0

    def camera_boundaries(self):
        # enables scroll camera boundaries
        for tile in self.abs_boundaries['x']:
            # having proxy variables allows modification of value for maths without moving actual tile pos
            tile_right = tile.hitbox.right
            tile_left = tile.hitbox.left
            # if the screen's horizontal is a pixel away or inside of tile within collision tollerance, stop scroll and snap
            # must be moving towards the wall, otherwise cant move away from the wall in the other direction
            # TODO if on the screen
            # TODO respawn
            # TODO general bounds
            if self.collision_tolerance_x > tile_right >= self.screen_rect.left and self.scroll_value[0] < 0:

                # stop scroll
                self.scroll_value[0] = 0
                # while the screen is in the tile, snap the screen to the tile grid.
                # allows pixel perfect boundaries
                while tile_right > self.screen_rect.left:
                    self.scroll_value[0] += 1
                    tile_right -= 1
                break
            # TODO potentially need abs?
            elif (self.screen_rect.right - self.collision_tolerance_x) < tile_left <= self.screen_rect.right and \
                    self.scroll_value[0] > 0:
                self.scroll_value[0] = 0
                while tile_left < self.screen_rect.right:
                    self.scroll_value[0] -= 1
                    tile_left += 1
                break

        for tile in self.abs_boundaries['y']:
            tile_top = tile.hitbox.top
            tile_bottom = tile.hitbox.bottom
            # TODO potentially need abs?
            if (self.screen_rect.bottom - self.collision_tolerance_y) < tile_top <= self.screen_rect.bottom and \
                    self.scroll_value[1] > 0:
                self.scroll_value[1] = 0
                while tile_top < self.screen_rect.bottom:
                    self.scroll_value[1] -= 1
                    tile_top += 1
                break
            elif self.collision_tolerance_y > tile_bottom >= self.screen_rect.top and self.scroll_value[1] < 0:
                self.scroll_value[1] = 0
                while tile_bottom > self.screen_rect.top:
                    self.scroll_value[1] += 1
                    tile_bottom -= 1
                break

# -- Getters and Setters --

    # scrolls the world when the player hits certain points on the screen
    # dynamic camera tut, dafluffypotato:  https://www.youtube.com/watch?v=5q7tmIlXROg
    def get_scroll(self, dt, fps):
        self.update_target()

        # if camera is to follow normally, do normal stuff, otherwise, focus camera directly on target
        if not self.focus_target:

            # -- decreases LERP_y gradually when falling and resets when hit ground --
            if self.player.direction.y > 0 and not self.player.on_ground:
                self.lerp_y -= self.fall_lerp_increment
                if self.lerp_y < self.fall_lerp_max:
                    self.lerp_y = self.fall_lerp_max
            else:
                self.lerp_y = self.norm_lerp

            # scroll value cancels player movement with scrolling everything, including player (centerx - scroll_value)
            # subtracts screen width//2 to place player in the center of the screen rather than left edge

            # sets camera to position of target, but divides value in order to provide interpolation
            # making the camera follow with lag and also settle gently as the  fraction gets smaller the closer the camera
            # is to the player

            self.scroll_value[0] = (self.target[0] - self.screen_center_x) / self.lerp_x  # (self.target[0] - self.scroll_value[1] - self.screen_center_x) / self.lerp_x
            self.scroll_value[1] = (self.target[1] - self.screen_center_y) / self.lerp_y  #(self.target[1] - self.scroll_value[0] - self.screen_center_y) / self.lerp_y

        else:
            # focus camera on target.
            self.scroll_value = [-(self.screen_center_x - self.target[0]),
                                 -(self.screen_center_y - self.target[1])]

        # camera boundaries
        self.camera_boundaries()

        # dt
        self.scroll_value[0] = round(self.scroll_value[0] * dt)
        self.scroll_value[1] = round(self.scroll_value[1] * dt)

        return self.scroll_value

    ''' # enables scroll camera boundaries
        for tile in self.boundaries_x:
            # having proxy variables allows modification of value for maths without moving actual tile pos
            tile_right = tile.hitbox.right
            tile_left = tile.hitbox.left
            # if the screen's horizontal is a pixel away or inside of tile within collision tollerance, stop scroll and snap
            # must be moving towards the wall, otherwise cant move away from the wall in the other direction
            # TODO not pixel perfect yet
            # TODO if on the screen
            if self.collision_tolerance > tile_right + 1 >= self.screen_rect.left and self.scroll_value[1] < 0:
                # stop scroll
                self.scroll_value[1] = 0
                # while the screen is in the tile, snap the screen to the tile grid.
                # allows pixel perfect boundaries
                while tile_right > self.screen_rect.left:
                    self.scroll_value[1] += 1
                    tile_right -= 1
                break

            elif (self.screen_rect.right - self.collision_tolerance) < tile_left - 1 <= self.screen_rect.right and self.scroll_value[1] > 0:
                self.scroll_value[1] = 0
                while tile_left < self.screen_rect.right:
                    self.scroll_value[1] -= 1
                    tile_left += 1
                break

        for tile in self.boundaries_y:
            tile_top = tile.hitbox.top
            tile_bottom = tile.hitbox.bottom
            if (self.screen_rect.bottom - self.collision_tolerance) < tile_top <= self.screen_rect.bottom and self.scroll_value[0] > 0:
                self.scroll_value[0] = 0
                while tile_top < self.screen_rect.bottom:
                    self.scroll_value[0] -= 1
                    tile_top += 1
                break
            elif self.collision_tolerance > tile_bottom >= self.screen_rect.top and self.scroll_value[0] < 0:
                self.scroll_value[0] = 0
                while tile_bottom > self.screen_rect.top:
                    self.scroll_value[0] += 1
                    tile_bottom -= 1
                break'''

    # returns zoom value and offset required to zoom into target point (currently center of screen)
    def get_zoom(self):
        # compensates for zooming to origin by offsetting screen with scroll value
        width = pygame.display.get_surface().get_width()
        height = pygame.display.get_surface().get_height()
        # x = (xz - x)/2
        offset = ((width * self.zoom - width) // 2, (height * self.zoom - height) // 2)
        return self.zoom, offset

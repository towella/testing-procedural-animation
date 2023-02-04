import pygame
from game_data import tile_size, controller_map
from lighting import Light
from support import raycast, pos_for_center


# SET UP FOR PLATFORMER SINCE PLATFORMERS ARE HARDER TO CREATE A PLAYER FOR
class Player(pygame.sprite.Sprite):
    def __init__(self, spawn, surface, controllers):
        super().__init__()
        self.surface = surface
        self.controllers = controllers

        # -- player setup --
        self.image = pygame.Surface((tile_size, tile_size * 1.5))
        self.image.fill((255, 88, 98))
        self.rect = pygame.Rect(spawn.x, spawn.y, self.image.get_width(), self.image.get_height())
        self.light_distance = 40
        self.lights = [Light(self.surface, self.rect.center, (10, 10, 10), False, 40, 30, 0.02),
                       Light(self.surface, self.rect.center, (20, 20, 20), False, 25, 20, 0.02)]
        # - hitboxes -
        self.norm_hitbox = pygame.Rect(self.rect.midbottom[0], self.rect.midbottom[1], tile_size * 0.8, tile_size * 1.4)  # used for collisions
        self.crouch_hitbox = pygame.Rect(self.rect.midbottom[0], self.rect.midbottom[1], tile_size * 0.8, tile_size * 0.8)  # used for crouched collisions
        self.hitbox = self.norm_hitbox  # used for collisiona and can be different to rect and image

        if spawn.player_facing == 'right':
            self.facing_right = 1
        else:
            self.facing_right = -1
        self.respawn = False

        # -- player movement --
        self.direction = pygame.math.Vector2(0, 0)  # allows cleaner movement by storing both x and y direction
        # collisions -- provides a buffer allowing late collision
        self.collision_tolerance = tile_size
        self.corner_correction = 8  # tolerance for correcting player on edges of tiles (essentially rounded corners)
        self.vertical_corner_correction_boost = 4

        # - walk -
        self.speed_x = 2.5
        self.right_pressed = False
        self.left_pressed = False

        # - dash -
        self.dashing = False  # NOT REDUNDANT. IS NECCESSARY. Allows resetting timer while dashing. Also more readable code
        self.dash_speed = 4
        self.dash_pressed = False  # if the dash key is being pressed
        self.dash_max = 12  # max time of dash in frames
        self.dash_timer = self.dash_max  # maxed out to prevent being able to dash on start. Only reset on ground
        self.dash_dir_right = True  # stores the dir for a dash. Prevents changing dir during dash. Only dash cancels
        # - buffer dash -
        self.buffer_dash = False  # is a buffer dash cued up
        self.dashbuff_max = 5  # max time a buffered dash can be cued before it is removed (in frames)
        self.dashbuff_timer = self.dashbuff_max  # times a buffered dash from input (starts on max to prevent jump being cued on start)

        # -- gravity and falling --
        self.on_ground = False
        self.fall_timer = 0  # timer for how long the player has had a positive y vel and not on ground
        # - terminal vel -
        self.norm_terminal_vel = 10 # normal terminal vel
        self.terminal_vel = self.norm_terminal_vel  # maximum fall speed. if higher than self.collision_tolerance, will allow phasing :(
        # - gravity -
        self.gravity = 0.4
        self.fall_gravity = 1

        # -- Jump --
        # HEIGHT OF JUMP THEN MINIMUM JUMP
        self.jumping = False  # true when initial hop has been completed, allowing held jump.false if key up or grounded
        # verifies jump is already in progress (jump_timer is reset every time key down)
        self.jump_speed = 5  #294  # controls initial jump hop and height of hold jump
        self.jump_pressed = False  # if any jump key is pressed
        self.jump_max = 12  # max time a jump can be held
        self.jump_hold_timer = self.jump_max  # amount of time jump has been held. Not related to allowing initial jumps

        # - double jump -
        self.can_double_jump = True
        # - coyote time -
        self.coyote_timer = 0  # times the frames since left the floor
        self.coyote_max = 5  # maximum time for a coyote jump to occur
        # - buffer jump -
        self.jumpbuff_max = 10  # max time a buffered jump can be cued before it is removed (in frames)

        self.jump_timer = self.jumpbuff_max  # Time since last jump input if jump not yet executed. (allows initial jump)
        # Used to time jumps (including buffered jumps and wall jumps) from input
        # if jump timer == 0, means button has just been pressed. Used to ensure button isnt being held
        # if jump timer > 0 and not on_ground, means player is jumping or falling after jump
        # if jump timer == 0 in air, buffer jump has been cued up
        # (starts on max to prevent buffer jump being cued on start)

        # -- Crouch --
        self.crouching = False
        self.crouch_speed = 1  # speed of walk when crouching

# -- checks --

    def get_input(self, dt, tiles):
        self.direction.x = 0
        keys = pygame.key.get_pressed()

        #### horizontal movement ####
        # -- walk --
        # the not self.'side'_pressed prevents holding a direction and hitting the other at the same time to change direction
        if (keys[pygame.K_d] or self.get_controller_input('right')) and not self.left_pressed:
            if not self.crouching:
                self.direction.x = self.speed_x
            else:
                self.direction.x = self.crouch_speed
            self.facing_right = 1
            self.right_pressed = True
        else:
            self.right_pressed = False

        if (keys[pygame.K_a] or self.get_controller_input('left')) and not self.right_pressed:
            if not self.crouching:
                self.direction.x = -self.speed_x
            else:
                self.direction.x = -self.crouch_speed
            self.facing_right = -1
            self.left_pressed = True
        else:
            self.left_pressed = False

        # -- dash --
        # if wanting to dash and not holding the button
        if (keys[pygame.K_PERIOD] or self.get_controller_input('dash')) and not self.dash_pressed:
            # if only just started dashing, dashing is true and dash direction is set. Prevents changing dash dir during dash
            if not self.dashing:
                self.dashing = True
                self.dash_dir_right = self.facing_right
            self.dashbuff_timer = 0  # set to 0 ready for next buffdash
            self.dash_pressed = True
        # neccessary to prevent repeated dashes on button hold
        elif not keys[pygame.K_PERIOD] and not self.get_controller_input('dash'):
            self.dash_pressed = False

        self.dash(dt)

        #### vertical movement ####
        # -- jump --
        # input
        if keys[pygame.K_w] or keys[pygame.K_SPACE] or self.get_controller_input('jump'):
            # if jump wasnt previously pressed, allow jump (also dependent on other variable in function)
            # set jump_pressed to true
            # prevents continuous held jumps
            if not self.jump_pressed:
                self.jump_timer = 0  # set to 0 ready for next buffjump, used to prove not holding button
                self.jump_hold_timer = 0
            self.jump_pressed = True
        # jump keys up
        else:
            self.jumping = False
            self.jump_hold_timer = self.jump_max
            self.jump_pressed = False

        self.jump(dt)

        # -- crouch --
        # if wanting to crouch AND on the ground (so as to avoid glide)
        if (keys[pygame.K_s] or self.get_controller_input('crouch')) and self.on_ground:
            self.crouching = True
        else:
            self.crouching = False

        self.crouch(tiles)

        # TODO testing, remove
        if keys[pygame.K_r] or self.get_controller_input('dev'):
            self.invoke_respawn()

    # checks controller inputs and returns true or false based on passed check
    # pygame controller docs: https://www.pygame.org/docs/ref/joystick.html
    def get_controller_input(self, input_check):
        # self.controller.get_hat(0) returns tuple (x, y) for d-pad where 0, 0 is centered, -1 = left or down, 1 = right or up
        # the 0 refers to the dpad on the controller

        # check if controllers are connected before getting controller input (done every frame preventing error if suddenly disconnected)
        if len(self.controllers) > 0:
            controller = self.controllers[0]
            if input_check == 'jump' and controller.get_button(controller_map['X']):
                return True
            elif input_check == 'right':
                if controller.get_hat(0)[0] == 1 or (0.2 < controller.get_axis(controller_map['left_analog_x']) <= 1):
                    return True
            elif input_check == 'left':
                if controller.get_hat(0)[0] == -1 or (-0.2 > controller.get_axis(controller_map['left_analog_x']) >= -1):
                    return True
                '''elif input_check == 'up':
                    if controller.get_hat(0)[1] == 1 or (-0.2 > controller.get_axis(controller_map['left_analog_y']) >= -1):
                        return True
                elif input_check == 'down':
                    if controller.get_hat(0)[1] == -1 or (0.2 < controller.get_axis(controller_map['left_analog_y']) <= 1):
                        return True'''
            elif input_check == 'dash' and controller.get_button(controller_map['R2']) > 0.8:
                return True
            elif input_check == 'glide' and (controller.get_button(controller_map['L1']) or controller.get_hat(0)[1] == -1):
                return True
            elif input_check == 'crouch' and (controller.get_hat(0)[1] == -1 or 0.2 < controller.get_axis(controller_map['left_analog_y']) <= 1):  # TODO crouch controls
                return True
            # TODO testing, remove
            elif input_check == 'dev' and controller.get_button(controller_map['right_analog_press']):
                return True
        return False

    # - respawn -

    def invoke_respawn(self):
        self.respawn = True

    def get_respawn(self):
        return self.respawn

    def player_respawn(self, spawn):
        self.rect.x, self.rect.y = spawn.x, spawn.y  # set position to respawn point
        self.sync_hitbox()
        if spawn.player_facing == 'right':
            self.facing_right = 1
        else:
            self.facing_right = -1
        self.direction = pygame.math.Vector2(0, 0)  # reset movement
        self.dashing = False  # end any dashes on respawn
        self.dash_timer = self.dash_max  # prevent dash immediately on reset
        self.crouching = False  # end any crouching on respawn
        self.jumping = False  # end any jumps on respawn
        self.respawn = False

# -- movement methods --

    def dash(self, dt):
        # - reset -
        # reset dash, on ground OR if on the wall and dash completed (not dashing) - allows dash to finish before clinging
        # reset despite button pressed or not (not dependant on button, can only dash with button not pressed)
        if self.on_ground or (self.on_wall and not self.dashing):
            self.dash_timer = 0
        # - setup buffer dash - (only when not crouching)
        # self.dashing is set to false when buffdash is cued. Sets to true on ground so that it can start a normal dash,
        # which resets buffer dashing variables ready for next one
        if self.on_ground and self.dashbuff_timer < self.dashbuff_max and not self.crouching:
            self.dashing = True
        # - start normal dash or continue dash - (only when not crouching)
        # (if dashing and dash duration not exceeded OR buffered dash) AND not crouching, allow dash
        if self.dashing and self.dash_timer < self.dash_max and not self.crouching:
            # - norm dash -
            # add velocity based on facing direction determined at start of dash
            # self.dash_dir_right multiplies by 1 or -1 to change direction of dash speed distance
            self.direction.x += self.dash_speed * self.dash_dir_right
            # dash timer increment
            self.dash_timer += round(1 * dt)

            # - buffer -
            # reset buffer jump with no jump cued
            self.buffer_dash = False
            self.dashbuff_timer = self.dashbuff_max
        # - kill -
        # if not dashing or timer exceeded, end dash but don't reset timer (prevents multiple dashes in the air)
        else:
            self.dashing = False

        # -- buffer dash timer --
        # cue up dash if dash button pressed (if dash is already allowed it will be maxed out in the dash code)
        # OR having already cued, continue timing
        if (self.dashbuff_timer == 0) or self.buffer_dash:
            self.dashbuff_timer += round(1 * dt)
            self.buffer_dash = True

    # physics maths from clearcode platformer tut (partly)
    def jump(self, dt):
        # -- coyote time --
        if self.on_ground:
            self.coyote_timer = 0  # resets timer on the ground
        else:
            self.coyote_timer += round(1 * dt)  # increments when not on the ground

        # - reset -
        if self.on_ground:
            self.jumping = False
        if self.on_ground or self.on_wall:
            self.can_double_jump = True

        # - execute initial hop and allow jump extension (norm, buffer and coyote) -
        # if on the ground and want to jump
        # OR on the ground and within buffer jump window,
        # OR within coyote time window and want to jump
        # OR double jump
        elif (self.on_ground and self.jump_timer == 0) or \
                (self.on_ground and self.jump_timer < self.jumpbuff_max) or \
                (self.jump_timer == 0 and self.coyote_timer < self.coyote_max) or \
                (self.jump_timer == 0 and self.can_double_jump):

            # - double jump -
            # if not on the ground and coyote window expired and has been able to jump,
            # must be double jumping, so prevent more double jumps
            if not self.on_ground and self.coyote_timer >= self.coyote_max:
                self.can_double_jump = False
                self.direction.y = 0

            # - coyote -
            self.coyote_timer = self.coyote_max  # prevents another coyote jump in mid air

            # - buffer jump -
            self.jump_hold_timer = 0  # Resets timer so buffjump has same extend window as norm.
            self.jump_timer = self.jumpbuff_max  # prevents repeated unwanted buffer jumps.

            # - norm jump - (start the jump)
            self.on_ground = False  # neccessary to prevent direction being cancelled by gravity on ground code later in loop
            self.direction.y = -self.jump_speed
            self.jumping = True  # verifies that a jump is in progress

        # - extend jump (variable height) -
        # if already jumping (has hopped) and not exceeding max jump and want to jump still
        elif self.jumping and self.jump_hold_timer < self.jump_max and self.jump_pressed:
            self.direction.y = -self.jump_speed

        self.jump_timer += round(1 * dt)  # increments the timer (time since jump input if jump hasnt been executed yet)
        self.jump_hold_timer += round(1 * dt)  # increments timer (time jump has been held for)

    def crouch(self, tiles):
        if self.crouching:
            # change to crouched hitbox and sync to the same pos as previous hitbox (using rect midbottom)
            self.hitbox = self.crouch_hitbox
            self.sync_hitbox()
        # - exception case (if not crouching but should be forced to cause under platform) -
        else:
            # if normal hitbox top collides with a tile, make crouched
            for tile in tiles:
                if tile.hitbox.colliderect(self.norm_hitbox):
                    if abs(tile.hitbox.bottom - self.norm_hitbox.top) < self.collision_tolerance:
                        # change to crouched hitbox and sync to the same pos as previous hitbox (using rect midbottom)
                        self.hitbox = self.crouch_hitbox
                        self.sync_hitbox()
                        self.crouching = True
                        break

# -- update methods --

    # checks collision for a given hitbox against given tiles on the x
    def collision_x(self, hitbox, tiles):
        collision_offset = [0, 0]  # position hitbox is to be corrected to after checks
        self.on_wall = False

        top = False
        top_margin = False
        bottom = False
        bottom_margin = False

        for tile in tiles:
            if tile.hitbox.colliderect(hitbox):
                # - normal collision checks -
                # abs ensures only the desired side registers collision
                # not having collisions dependant on status allows hitboxes to change size
                if abs(tile.hitbox.right - hitbox.left) < self.collision_tolerance:
                    collision_offset[0] = tile.hitbox.right - hitbox.left
                    self.on_wall_right = False  # which side is player clinging?
                elif abs(tile.hitbox.left - hitbox.right) < self.collision_tolerance:
                    collision_offset[0] = tile.hitbox.left - hitbox.right
                    self.on_wall_right = True  # which side is player clinging?

                #- horizontal corner correction - (for both side collisions)

                # checking allowed to corner correct
                # Use a diagram. Please
                # checks if the relevant horizontal raycasts on the player hitbox are within a tile or not
                # this allows determination as to whether on the end of a column of tiles or not

                # top
                if tile.hitbox.top <= hitbox.top <= tile.hitbox.bottom:
                    top = True
                if tile.hitbox.top <= hitbox.top + self.corner_correction <= tile.hitbox.bottom:
                    top_margin = True
                # stores tile for later potential corner correction
                if hitbox.top < tile.hitbox.bottom < hitbox.top + self.corner_correction:
                    collision_offset[1] = tile.hitbox.bottom - hitbox.top

                # bottom
                if tile.hitbox.top <= hitbox.bottom <= tile.hitbox.bottom:
                    bottom = True
                if tile.hitbox.top <= hitbox.bottom - self.corner_correction <= tile.hitbox.bottom:
                    bottom_margin = True
                if hitbox.bottom > tile.hitbox.top > hitbox.bottom - self.corner_correction:
                    collision_offset[1] = -(hitbox.bottom - tile.hitbox.top)

        # -- application of offsets --
        # must occur after checks so that corner correction can check every contacted tile
        # without movement of hitbox half way through checks
        # - collision correction -
        hitbox.x += collision_offset[0]
        # - corner correction -
        # adding velocity requirement prevents correction when just walking towards a wall. Only works at a higher
        # velocity like during a dash or if the player is boosted.
        if ((top and not top_margin) or (bottom and not bottom_margin)) and abs(self.direction.x) >= self.dash_speed:
            hitbox.y += collision_offset[1]

        self.sync_rect()

    # checks collision for a given hitbox against given tiles on the y
    def collision_y(self, hitbox, tiles):
        collision_offset = [0, 0]
        self.on_ground = False

        left = False
        left_margin = False
        right = False
        right_margin = False

        bonk = False

        for tile in tiles:
            if tile.hitbox.colliderect(hitbox):
                # abs ensures only the desired side registers collision
                if abs(tile.hitbox.top - hitbox.bottom) < self.collision_tolerance:
                    self.on_ground = True
                    collision_offset[1] = tile.hitbox.top - hitbox.bottom
                # collision with bottom of tile
                elif abs(tile.hitbox.bottom - hitbox.top) < self.collision_tolerance:
                    collision_offset[1] = tile.hitbox.bottom - hitbox.top

                    # - vertical corner correction - (only for top, not bottom collision)
                    # left
                    if tile.hitbox.left <= hitbox.left <= tile.hitbox.right:
                        left = True
                    if tile.hitbox.left <= hitbox.left + self.corner_correction <= tile.hitbox.right:
                        left_margin = True
                    if hitbox.left < tile.hitbox.right < hitbox.left + self.corner_correction:
                        collision_offset[0] = tile.hitbox.right - hitbox.left

                    # right
                    if tile.hitbox.left <= hitbox.right <= tile.hitbox.right:
                        right = True
                    if tile.hitbox.left <= hitbox.right - self.corner_correction <= tile.hitbox.right:
                        right_margin = True
                    if hitbox.right > tile.hitbox.left > hitbox.right - self.corner_correction:
                        collision_offset[0] = -(hitbox.right - tile.hitbox.left)

                    bonk = True

        # -- application of offsets --
        # - normal collisions -
        hitbox.y += collision_offset[1]
        # - corner correction -
        if (left and not left_margin) or (right and not right_margin):
            hitbox.x += collision_offset[0]
            hitbox.y -= self.vertical_corner_correction_boost
        # drop by zeroing upwards velocity if corner correction isn't necessary and hit bottom of tile
        elif bonk:
            self.direction.y = 0

        # resyncs up rect to the hitbox
        self.sync_rect()

    # contains gravity + it's exceptions(gravity code from clearcode platformer tut), terminal velocity, fall timer
    # and application of y direction
    def apply_y_direction(self, dt):
        # -- gravity --
        # if dashing, set direction.y to 0 to allow float
        if self.dashing:
            self.direction.y = 0
        # when on the ground set direction.y to 1. Prevents gravity accumulation. Allows accurate on_ground detection
        # must be greater than 1 so player falls into below tile's hitbox every frame and is brought back up
        elif self.on_ground:
            self.direction.y = 1
        # if not dashing or on the ground apply gravity normally
        else:
            # if falling, apply more gravity than if moving up
            if self.direction.y > 0:
                self.direction.y += self.fall_gravity
            else:
                self.direction.y += self.gravity

        # -- terminal velocity --
        # TODO needs dt??
        if self.direction.y > self.terminal_vel:
            self.direction.y = self.terminal_vel

        # -- fall timer --
        # if falling in the air, increment timer else its 0
        if self.direction.y > 0 and not self.on_ground:
            self.fall_timer += round(1 * dt)
        else:
            self.fall_timer = 0

        # -- apply y direction and sync --
        self.rect.y += round(self.direction.y * dt)
        self.sync_hitbox()

    # syncs the player's current and stored hitboxes with the player rect for proper collisions. For use after movement of player rect.
    def sync_hitbox(self):
        self.hitbox.midbottom = self.rect.midbottom
        self.norm_hitbox.midbottom = self.rect.midbottom
        self.crouch_hitbox.midbottom = self.rect.midbottom

    # syncs the player's rect with the current hitbox for proper movement. For use after movement of main hitbox
    def sync_rect(self):
        self.rect.midbottom = self.hitbox.midbottom

    def apply_scroll(self, scroll_value):
        self.rect.x -= int(scroll_value[1])
        self.rect.y -= int(scroll_value[0])
        self.sync_hitbox()

    def update(self, dt, tiles, scroll_value, current_spawn):
        self.terminal_vel = self.norm_terminal_vel  # resets terminal vel for next frame. Allows wall cling and glide to
        # reset without interfering with each other.
        self.hitbox = self.norm_hitbox  # same with hitbox as terminal vel
        self.sync_hitbox()  # just in case

        # respawns player if respawn has been evoked
        if self.respawn:
            self.player_respawn(current_spawn)

        # -- INPUT --
        self.get_input(dt, tiles)

        # -- CHECKS/UPDATE --

        # - collision and movement -
        # applies direction to player then resyncs hitbox (included in most movement/collision functions)
        # HITBOX MUST BE SYNCED AFTER EVERY MOVE OF PLAYER RECT
        # x and y collisions are separated to make diagonal collisions easier and simpler to handle
        # x
        self.rect.x += round(self.direction.x * dt)
        self.sync_hitbox()
        self.collision_x(self.hitbox, tiles)

        # y
        # applies direction to player then resyncs hitbox
        self.apply_y_direction(dt)  # gravity
        self.collision_y(self.hitbox, tiles)

        # scroll shouldn't have collision applied, it is separate movement
        self.apply_scroll(scroll_value)

        # light (after movement and scroll so pos is accurate)
        for light in self.lights:
            light.update(dt, self.rect.center, tiles)

# -- visual methods --

    def draw(self):
        for light in self.lights:
            light.draw()

        self.surface.blit(self.image, self.rect)


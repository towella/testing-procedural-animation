import pygame, math
from game_data import tile_size, controller_map
from lighting import Light
from support import get_angle, get_distance, lerp2D


# SET UP FOR PLATFORMER SINCE PLATFORMERS ARE HARDER TO CREATE A PLAYER FOR
class Player(pygame.sprite.Sprite):
    def __init__(self, spawn, surface, segments, segment_spacing, controllers):
        super().__init__()
        self.surface = surface
        self.controllers = controllers

        # -- player setup --
        self.speed = 3
        self.seg_spacing = segment_spacing
        self.max_seg_speed = 5
        self.max_flex = 30
        self.points = self.create_body(spawn, segments, segment_spacing)
        self.head = self.points[0]

        self.light_distance = 40
        self.lights = [Light(self.surface, self.head.pos, (10, 10, 10), False, 40, 30, 0.02),
                       Light(self.surface, self.head.pos, (20, 20, 20), False, 25, 20, 0.02)]

        self.respawn = False

        # -- player movement --
        self.direction = pygame.math.Vector2(0, 0)  # allows cleaner movement by storing both x and y direction
        # collisions -- provides a buffer allowing late collision
        self.collision_tolerance = tile_size
        self.corner_correction = 8  # tolerance for correcting player on edges of tiles (essentially rounded corners)
        self.vertical_corner_correction_boost = 4

# -- initialisation --

    # initialises the body
    def create_body(self, spawn, segments, segment_spacing):
        body_points = []

        body_points.append(Body_Segment(self.surface, spawn, self.seg_spacing, self.max_flex, self.max_seg_speed, True))
        for i in range(segments - 1):
            segment_spacing -= 1  # TODO TEST REMOVE (dynamically change spacing and circle size of segs)
            if segment_spacing < 1:  # TODO TEST REMOVE
                segment_spacing = 1  # TODO TEST REMOVE
            body_points.append(Body_Segment(self.surface, spawn, segment_spacing, self.max_flex, self.max_seg_speed, False, body_points[i]))
            body_points[i].set_child(body_points[i + 1])  # max i is length of points - 1 (head is added before loop)
            # therefore child of last point (i) is i + 1

        return body_points

# -- checks --

    def get_input(self, dt, tiles):
        keys = pygame.key.get_pressed()

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
        self.direction = pygame.math.Vector2(0, 0)  # reset movement
        self.respawn = False

# -- movement methods --

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

    def update(self, tiles, mouse_pos, dt): #, scroll_value, current_spawn):
        # reset without interfering with each other.
        #self.hitbox = self.norm_hitbox  # same with hitbox as terminal vel
        #self.sync_hitbox()  # just in case

        # respawns player if respawn has been evoked
        #if self.respawn:
            #self.player_respawn(current_spawn)

        # -- INPUT --
        #self.get_input(dt, tiles)

        # -- CHECKS/UPDATE --

        # - collision and movement -
        # MOVEMENT
        for i in range(len(self.points)):
            # if not a head don't pass mouse cursor (point is based on parent seg)
            if i > 0:
                self.points[i].update(tiles)
            # if head pass mouse cursor as point to follow
            else:
                self.points[i].update(tiles, mouse_pos)

        # COLLISIONS
        # applies direction to player then resyncs hitbox (included in most movement/collision functions)
        # HITBOX MUST BE SYNCED AFTER EVERY MOVE OF PLAYER RECT
        # x and y collisions are separated to make diagonal collisions easier and simpler to handle
        # x
        '''self.sync_hitbox()
        self.collision_x(self.hitbox, tiles)'''

        # y
        # applies direction to player then resyncs hitbox
        '''self.apply_y_direction(dt)  # gravity
        self.collision_y(self.hitbox, tiles)'''

        # scroll shouldn't have collision applied, it is separate movement
        #self.apply_scroll(scroll_value)

        # light (after movement and scroll so pos is accurate)
        for light in self.lights:
            light.update(dt, self.head.get_pos(), None)

# -- visual methods --

    def draw(self):
        for point in self.points:
            point.draw()
        for light in self.lights:
            light.draw()


class Body_Segment:
    def __init__(self, surface, pos, segment_spacing, max_flex, max_move_speed, legs, parent_body_segment=None):
        self.surface = surface  # segment render surface
        self.pos = [pos[0], pos[1]]  # segment position
        self.prev_pos = self.pos
        self.move_speed = max_move_speed  # for head only
        self.direction = pygame.Vector2(0, 0)  # tracks segment movement
        self.rot = 0  # keeps track of segment rotation

        # parent/child
        self.parent_seg = parent_body_segment
        self.child_seg = None

        # legs
        self.has_legs = legs
        self.legs = [Leg(self.surface, self.pos, 1, True, True),
                     Leg(self.surface, self.pos, 1, False, False)]

        # segment values
        self.seg_spacing = segment_spacing
        self.max_flex = max_flex
        self.radius = self.seg_spacing // 2  # collisions and drawn circle
        if self.parent_seg is None:
            self.head = True
        else:
            self.head = False

        # collision
        self.hitbox = pygame.Rect(self.pos[0], self.pos[1], self.radius, self.radius)
        self.collision_tolerance = tile_size
        self.corner_correction = 3

    # --- MOVEMENT ---

    def adjusted_distance(self, point):
        # work out how far P1 needs to move towards P2 (target) while still being spaced appropriately
        hyp = get_distance(self.pos, point)
        hyp -= self.seg_spacing
        return hyp

    def move(self, point, displacement):
        angle = get_angle(self.pos, point)
        angle += 90  # rotate the entire unit circle so + and - numbers are produced on the desired sides

        # - Limit angle (limit segment joint's flex) -
        # relative_angle = the new angle - the neutral alignment from last frame before changing to face point
        if self.head:
            child_rot = self.child_seg.get_rot()
            relative_angle = angle - child_rot
            # relative angle should always be less than 180
            if relative_angle > 180:
                relative_angle = -(180 - (relative_angle - 180))
            elif relative_angle < -180:
                relative_angle = 180 + (relative_angle + 180)
            # TODO head and other segs are all the same now?? no parents required anymore!
            '''#else:
                #prev_point = self.parent_seg.get_prev_pos()  # get parent position before movement
                #prev_alignment = get_angle(self.pos, prev_point)  # get neutral alignment angle from before parent moved
                #relative_angle = angle - prev_alignment  # 'displacement' angle from neutral. + or - indicates > or < neutral'''
            # limit rotation
            if abs(relative_angle) > self.max_flex:
                if relative_angle > 0:
                    angle = child_rot + self.max_flex
                elif relative_angle < 0:
                    angle = child_rot - self.max_flex

        # - update and adjust angles -
        self.rot = angle  # update segment rotation
        angle = math.radians(angle)  # convert to radians for trig funcs

        # - Move point -
        # get how much the x and y should be changed by (so the total displacement is always constant)
        if self.head and displacement > self.move_speed:  # limit movement displacement towards cursor for head
            displacement = self.move_speed

        # calculate how much the individual x and y coord should be modified for a total displacement in given direction
        self.direction.x += math.sin(angle) * displacement
        self.direction.y += math.cos(angle) * displacement


    # --- COLLISIONS ---

    # checks collision for a given hitbox against given tiles on the x
    def collision_x(self, tiles):
        collision_offset = [0, 0]  # position hitbox is to be corrected to after checks

        top = False
        top_margin = False
        bottom = False
        bottom_margin = False

        for tile in tiles:
            if tile.hitbox.colliderect(self.hitbox):
                # - normal collision checks -
                # abs ensures only the desired side registers collision
                # not having collisions dependant on status allows hitboxes to change size
                if abs(tile.hitbox.right - self.hitbox.left) < self.collision_tolerance:
                    collision_offset[0] = tile.hitbox.right - self.hitbox.left
                elif abs(tile.hitbox.left - self.hitbox.right) < self.collision_tolerance:
                    collision_offset[0] = tile.hitbox.left - self.hitbox.right

                # - horizontal corner correction - (for both side collisions)

                # checking allowed to corner correct
                # Use a diagram. Please
                # checks if the relevant horizontal raycasts on the player hitbox are within a tile or not
                # this allows determination as to whether on the end of a column of tiles or not

                # top
                if tile.hitbox.top <= self.hitbox.top <= tile.hitbox.bottom:
                    top = True
                if tile.hitbox.top <= self.hitbox.top + self.corner_correction <= tile.hitbox.bottom:
                    top_margin = True
                # stores tile for later potential corner correction
                if self.hitbox.top < tile.hitbox.bottom < self.hitbox.top + self.corner_correction:
                    collision_offset[1] = tile.hitbox.bottom - self.hitbox.top

                # bottom
                if tile.hitbox.top <= self.hitbox.bottom <= tile.hitbox.bottom:
                    bottom = True
                if tile.hitbox.top <= self.hitbox.bottom - self.corner_correction <= tile.hitbox.bottom:
                    bottom_margin = True
                if self.hitbox.bottom > tile.hitbox.top > self.hitbox.bottom - self.corner_correction:
                    collision_offset[1] = -(self.hitbox.bottom - tile.hitbox.top)

        # -- application of offsets --
        # must occur after checks so that corner correction can check every contacted tile
        # without movement of hitbox half way through checks

        # - collision correction -
        self.hitbox.x += collision_offset[0]

        # - corner correction -
        # adding velocity requirement prevents correction when just walking towards a wall. Only works at a higher
        # velocity like during a dash or if the player is boosted.
        if (top and not top_margin) or (bottom and not bottom_margin):
            self.hitbox.y += collision_offset[1]

    # checks collision for a given hitbox against given tiles on the y
    def collision_y(self, tiles):
        collision_offset = [0, 0]

        left = False
        left_margin = False
        right = False
        right_margin = False

        for tile in tiles:
            if tile.hitbox.colliderect(self.hitbox):
                # abs ensures only the desired side registers collision
                if abs(tile.hitbox.top - self.hitbox.bottom) < self.collision_tolerance:
                    collision_offset[1] = tile.hitbox.top - self.hitbox.bottom
                # collision with bottom of tile
                elif abs(tile.hitbox.bottom - self.hitbox.top) < self.collision_tolerance:
                    collision_offset[1] = tile.hitbox.bottom - self.hitbox.top

                # - vertical corner correction - (only for top, not bottom collision)
                # left
                if tile.hitbox.left <= self.hitbox.left <= tile.hitbox.right:
                    left = True
                if tile.hitbox.left <= self.hitbox.left + self.corner_correction <= tile.hitbox.right:
                    left_margin = True
                if self.hitbox.left < tile.hitbox.right < self.hitbox.left + self.corner_correction:
                    collision_offset[0] = tile.hitbox.right - self.hitbox.left

                # right
                if tile.hitbox.left <= self.hitbox.right <= tile.hitbox.right:
                    right = True
                if tile.hitbox.left <= self.hitbox.right - self.corner_correction <= tile.hitbox.right:
                    right_margin = True
                if self.hitbox.right > tile.hitbox.left > self.hitbox.right - self.corner_correction:
                    collision_offset[0] = -(self.hitbox.right - tile.hitbox.left)

        # -- application of offsets --
        # - normal collisions -
        self.hitbox.y += collision_offset[1]
        # - corner correction -
        if (left and not left_margin) or (right and not right_margin):
            self.hitbox.x += collision_offset[0]

    # --- GETTERS AND SETTERS ---

    def get_prev_pos(self):
        return self.prev_pos

    def get_pos(self):
        return self.pos

    def get_child(self):
        return self.child_seg

    def get_rot(self):
        return self.rot

    def set_child(self, seg_obj):
        self.child_seg = seg_obj

    # --- UPDATE AND DRAW ---

    def update(self, tiles, point=(0, 0)):
        # reset direction vector
        self.direction.x = 0
        self.direction.y = 0

        if not self.head:
            point = self.parent_seg.get_pos()  # norm pos is required for limiting joint angle
        self.prev_pos = self.pos

        # moves towards point based on spacing
        hyp = self.adjusted_distance(point)
        self.move(point, hyp)

        # update position
        self.pos[0] += self.direction.x
        self.pos[1] += self.direction.y

        # TODO try syncing code first before collisions
        self.hitbox.center = self.pos  # sync hitbox after pos moved
        #self.collision_x(tiles)
        #self.collision_y(tiles)

        # -- update legs --
        distance = math.sqrt(self.direction.x ** 2 + self.direction.y ** 2)
        if self.has_legs:
            for leg in self.legs:
                leg.update(self.pos, self.rot, distance)

    def draw(self):
        # -- feet --
        if self.has_legs:
            for leg in self.legs:
                leg.draw()

        # -- body --
        if self.head:
            pygame.draw.circle(self.surface, 'purple', self.pos, 3)
        else:
            pygame.draw.circle(self.surface, 'green', self.pos, 1)
        pygame.draw.circle(self.surface, 'orange', self.pos, self.radius, 1)

        pygame.draw.rect(self.surface, 'grey', self.hitbox, 1)  # TODO TESTING hitbox

        # TODO TESTING self.rot
        x = math.sin(math.radians(self.rot)) * 12
        y = math.cos(math.radians(self.rot)) * 12
        epos = (self.pos[0] + x, self.pos[1] + y)
        pygame.draw.line(self.surface, 'red', self.pos, epos, 1)


class Leg:
    def __init__(self, surface, anchor, num_elbows, right_foot, up_elbow=True):
        # general
        self.surface = surface
        self.anchor = anchor  # where the leg is joined to the parent object
        self.rot = 0  # keeps track of leg rotation

        # foot
        self.right_foot = right_foot
        self.foot = anchor  # the leg's foot point
        self.foot_target = None  # target the foot moves to
        self.foot_move = False

        # elbows
        self.num_elbows = num_elbows  # number of leg segments (elbows to be found)
        self.up_elbow = up_elbow  # whether the elbows face up or down using inverse kinematics

        # leg
        self.max_leg_distance = 60  # maximum amount of frames legs will stay still when moving TODO make input param
        self.leg_distance = 0

        # lerp
        self.lerp_increment = 0.05  # value added to lerp per frame when required
        self.lerp = 0

    # TODO optimise use of trig
    def update(self, pos, rot, distance):
        self.anchor = pos
        self.rot = rot
        self.leg_distance += distance

        rotation = math.radians(self.rot)
        relative_angle = 50  # TODO make param
        left_angle = math.radians(self.rot + relative_angle)
        right_angle = math.radians(self.rot - relative_angle)

        x_displace = 20  # TODO make param
        y_displace = 40  # TODO make param
        y_displace = (math.sin(rotation) * y_displace, math.cos(rotation) * y_displace)

        # -- Calculate foot target if not moving foot --
        # left foot
        if not self.foot_move and not self.right_foot:
            self.foot_target = [self.anchor[0] + math.sin(left_angle) * x_displace + y_displace[0],
                                self.anchor[1] + math.cos(left_angle) * x_displace + y_displace[1]]
        # right foot
        if not self.foot_move and self.right_foot:
            self.foot_target = [self.anchor[0] + math.sin(right_angle) * x_displace + y_displace[0],
                                self.anchor[1] + math.cos(right_angle) * x_displace + y_displace[1]]

        # -- Move Feet --
        # Lerps feet towards targets (always makes it in time no matter distance because % distance is used)
        if self.leg_distance > self.max_leg_distance:
            self.leg_distance = 0
            self.foot_move = True
        # lerp (end lerp if at 100%)
        if self.foot_move:
            self.foot = lerp2D(self.foot, self.foot_target, self.lerp)
            self.lerp += self.lerp_increment
            # stop and reset lerp if at 100% (foot at target)
            if self.lerp >= 1:
                self.foot_move = False
                self.lerp = 0

        # Lerps feet towards targets (always makes it in time no matter distance because % distance is used)
        # activate lerp
        if self.leg_distance > self.max_leg_distance:
            self.leg_distance = 0
            self.foot_move = True
        # lerp (end lerp if at 100%)
        if self.foot_move:
            self.foot = lerp2D(self.foot, self.foot_target, self.lerp)
            self.lerp += self.lerp_increment
            # stop and reset lerp if at 100% (foot at target)
            if self.lerp >= 1:
                self.foot_move = False
                self.lerp = 0

    # TODO optimise use of trig
    def draw(self):
        # ------------ FOOT BALLS ---------------
        pygame.draw.circle(self.surface, 'blue', self.foot, 4)

        #------------- LEG LINES ----------------
        # TODO name variables better and optimise
        leg_seg_length = self.max_leg_distance // 2

        b = get_distance(self.anchor, self.foot)
        # b can not be 0 (division by 0 error) May start as zero when anchor == foot meaning leg distance = 0
        if b == 0:
            b = 1

        law_cosines = (leg_seg_length ** 2 + b ** 2 - leg_seg_length ** 2) / (2 * leg_seg_length * b)
        # prevent law_cosines from causing error when being passed into cos: [-1, 1]
        if law_cosines > 1:
            law_cosines = 1
        elif law_cosines < -1:
            law_cosines = -1

        # TODO left leg is the problem

        # Find elbows
        if self.up_elbow:
            # --- Up Elbow ---  (right)
            angle = math.acos(law_cosines) + math.radians(get_angle(self.anchor, self.foot))
            # find elbow
            elbow = [self.anchor[0] + math.sin(angle) * leg_seg_length, self.anchor[1] + math.cos(angle) * leg_seg_length]

        else:
            # --- Down Elbow ---  (left)
            angle = math.radians(get_angle(self.anchor, self.foot)) - math.acos(law_cosines)
            # find elbow
            elbow = [self.anchor[0] - math.sin(angle) * leg_seg_length, self.anchor[1] - math.cos(angle) * leg_seg_length]

        # Render
        pygame.draw.line(self.surface, 'black', self.anchor, elbow, 2)
        pygame.draw.line(self.surface, 'black', elbow, self.foot, 2)


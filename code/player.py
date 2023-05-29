import pygame, math
from game_data import tile_size, controller_map
from lighting import Light
from support import get_angle, get_distance, lerp2D


# SET UP FOR PLATFORMER SINCE PLATFORMERS ARE HARDER TO CREATE A PLAYER FOR
class Player(pygame.sprite.Sprite):
    def __init__(self, level, spawn, segments, segment_spacing):
        super().__init__()
        self.level = level
        self.surface = self.level.screen_surface
        self.controllers = self.level.controllers

        # -- player setup --
        self.speed = 3
        self.seg_spacing = segment_spacing
        self.max_seg_speed = 5
        self.max_flex = 30
        self.segments = self.create_body(spawn, segments, segment_spacing)
        self.head = self.segments[0]

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
        body_points = [Body_Segment(self.surface, spawn, self.seg_spacing, self.max_flex, self.max_seg_speed, True)]

        for i in range(segments - 1):
            segment_spacing -= 1  # TODO TEST REMOVE (dynamically change spacing and circle size of segs)
            if segment_spacing < 1:  # TODO TEST REMOVE
                segment_spacing = 1  # TODO TEST REMOVE
            if i == 5 or i == 0:
                body_points.append(Body_Segment(self.surface, spawn, segment_spacing, self.max_flex, self.max_seg_speed, True, body_points[i]))
            else:
                body_points.append(Body_Segment(self.surface, spawn, segment_spacing, self.max_flex, self.max_seg_speed, True, body_points[i]))
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
        for i in range(len(self.segments)):
            # if not a head don't pass mouse cursor (point is based on parent seg)
            if i > 0:
                self.segments[i].update(tiles)
            # if head pass mouse cursor as point to follow
            else:
                self.segments[i].update(tiles, mouse_pos)

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
        for segment in self.segments:
            segment.draw()
        for light in self.lights:
            light.draw()


class Body_Segment:
    def __init__(self, surface, spawn, segment_spacing, max_flex, max_move_speed, legs, parent_body_segment=None):
        self.surface = surface  # segment render surface
        self.pos = [spawn.x, spawn.y]  # segment position
        self.prev_pos = self.pos
        self.move_speed = max_move_speed  # for head only
        self.direction = pygame.Vector2(0, 0)  # tracks segment movement
        self.rot = 0  # keeps track of segment rotation

        # parent/child
        self.parent_seg = parent_body_segment
        self.child_seg = None

        # legs
        self.has_legs = legs
        # TODO define these parameters better (mainly for testing)
        leg_thickness = 3
        max_leg_length = 60
        number_elbows = 1
        target_angle = 40
        target_displacement = 35
        time_offset = 0
        self.legs = [LegPair(self.surface, self.pos, number_elbows, max_leg_length, target_angle, target_displacement,
                             time_offset, leg_thickness)]

        # segment values
        self.seg_spacing = segment_spacing
        self.max_flex = max_flex
        self.radius = self.seg_spacing // 2  # collisions and drawn circle
        if self.parent_seg is None:
            self.head = True
        else:
            self.head = False

        # collision
        self.hitbox = pygame.Rect(self.pos[0], self.pos[1], self.radius*2, self.radius*2)
        self.collision_tolerance = tile_size

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
    def collisions(self, tiles):
        # -- X Collisions --
        collision_offset = 0  # position pos (and therefore hitbox) is to be corrected to after checks
        for tile in tiles:
            if tile.hitbox.colliderect(self.hitbox):
                # - normal collision checks -
                # abs ensures only the desired side registers collision
                if abs(tile.hitbox.right - self.hitbox.left) < self.collision_tolerance:
                    collision_offset = tile.hitbox.right - self.hitbox.left
                elif abs(tile.hitbox.left - self.hitbox.right) < self.collision_tolerance:
                    collision_offset = tile.hitbox.left - self.hitbox.right

        # -- application of offsets --
        # must occur after checks so that corner correction can check every contacted tile
        # without movement of hitbox half way through checks
        # - collision correction -
        self.pos[0] += collision_offset
        self.hitbox.center = self.pos  # sync hitbox after pos moved in collisions

        # -- Y Collisions --
        collision_offset = 0
        for tile in tiles:
            if tile.hitbox.colliderect(self.hitbox):
                # abs ensures only the desired side registers collision
                if abs(tile.hitbox.top - self.hitbox.bottom) < self.collision_tolerance:
                    collision_offset = tile.hitbox.top - self.hitbox.bottom
                elif abs(tile.hitbox.bottom - self.hitbox.top) < self.collision_tolerance:
                    collision_offset = tile.hitbox.bottom - self.hitbox.top

        # -- application of offsets --
        # - normal collisions -
        self.pos[1] += collision_offset
        self.hitbox.center = self.pos  # sync hitbox after pos moved in collisions

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
            point = self.parent_seg.get_prev_pos()
        self.prev_pos = self.pos

        # moves towards point based on spacing
        hyp = self.adjusted_distance(point)
        self.move(point, hyp)

        # update position
        self.pos[0] += self.direction.x
        self.pos[1] += self.direction.y
        self.hitbox.center = self.pos  # sync hitbox after pos has been moved

        # collision detection
        self.collisions(tiles)

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


class LegPair:
    def __init__(self, surface, anchor, num_elbows, max_leg_length, target_angle=50, target_displacement=50, move_time_offset=0, leg_thickness=2):
        # general
        self.surface = surface
        self.anchor = anchor  # where the leg is joined to the parent object
        self.rot = 0  # keeps track of leg rotation

        # elbows
        self.num_elbows = num_elbows  # number of leg segments (elbows to be found)

        # leg
        self.max_leg_length = max_leg_length  # informs length of leg segments
        # tracks distance of body to feet to determine when to move feet [left, right]
        # max_leg_distance // 2 creates offset between the legs
        self.leg_distance = [self.max_leg_length // 2 + move_time_offset, 0 + move_time_offset]  # TODO verify move_time_offset is functional
        self.leg_thickness = leg_thickness

        # foot target
        self.target_angle = target_angle
        self.target_disp = target_displacement  # (x, y), displacement of foot targets for x and y relative to seg rot
        if self.target_disp > self.max_leg_length:
            self.target_disp = self.max_leg_length

        self.foot_targets = [(0, 0), (0, 0)]  # target the foot moves to [left, right]
        self.find_targets()

        # foot
        self.feet = [self.foot_targets[0], self.foot_targets[1]]  # the leg's foot points [left, right]
        self.foot_move = [False, False]  # whether a foot should move or not [left, right]

        # lerp
        self.lerp_increment = 0.05  # value added to lerp per frame when required
        self.lerp = [0, 0]  # tracks lerp value of feet when moving (between 0 and 1, representing a percentage of movement) []left, right]

    def find_targets(self):
        left_angle = math.radians(self.rot + self.target_angle)
        right_angle = math.radians(self.rot - self.target_angle)

        # left foot
        self.foot_targets[0] = (self.anchor[0] + math.sin(left_angle) * self.target_disp,
                                self.anchor[1] + math.cos(left_angle) * self.target_disp)
        # right foot
        self.foot_targets[1] = (self.anchor[0] + math.sin(right_angle) * self.target_disp,
                                self.anchor[1] + math.cos(right_angle) * self.target_disp)

    # TODO optimise use of trig
    def update(self, pos, rot, distance):
        self.anchor = pos
        self.rot = rot
        self.leg_distance[0] += distance
        self.leg_distance[1] += distance

        # -- Calculate foot target if not moving foot --
        self.find_targets()

        # TODO test render for targets
        #pygame.draw.circle(self.surface, 'red', self.foot_targets[0], 5, 1)
        #pygame.draw.circle(self.surface, 'red', self.foot_targets[1], 5, 1)

        # -- Move Feet --
        # Check if foot needs to move. If it does, zero distance for next move and set bool
        if self.leg_distance[0] > self.max_leg_length:
            # TODO if get_distance(self.anchor, self.feet[0]) > self.max_leg_length:
            self.leg_distance[0] = 0
            self.foot_move[0] = True
        if self.leg_distance[1] > self.max_leg_length:
            # TODO if get_distance(self.anchor, self.feet[1]) > self.max_leg_length:
            self.leg_distance[1] = 0
            self.foot_move[1] = True

        # Lerps feet towards targets (always makes it in time no matter distance because % distance is used) (end lerp if at 100%)
        if self.foot_move[0]:
            self.feet[0] = lerp2D(self.feet[0], self.foot_targets[0], self.lerp[0])
            self.lerp[0] += self.lerp_increment
            # stop and reset lerp if at 100% (foot at target)
            if self.lerp[0] >= 1:
                self.foot_move[0] = False
                self.lerp[0] = 0
        if self.foot_move[1]:
            self.feet[1] = lerp2D(self.feet[1], self.foot_targets[1], self.lerp[1])
            self.lerp[1] += self.lerp_increment
            if self.lerp[1] >= 1:
                self.foot_move[1] = False
                self.lerp[1] = 0

    # TODO optimise use of trig
    def draw(self):
        # ------------ FEET BALLS ---------------
        pygame.draw.circle(self.surface, 'blue', self.feet[0], 4)
        pygame.draw.circle(self.surface, 'blue', self.feet[1], 4)

        #------------- LEG LINES ----------------
        # TODO name variables better and optimise
        leg_seg_length = self.max_leg_length // (self.num_elbows + 1)

        b = get_distance(self.anchor, self.feet[0])
        # b can not be 0 (division by 0 error) May start as zero when anchor == foot meaning leg distance = 0
        if b == 0:
            b = 1

        law_cosines = (leg_seg_length ** 2 + b ** 2 - leg_seg_length ** 2) / (2 * leg_seg_length * b)
        # prevent law_cosines from causing error when being passed into cos: [-1, 1]
        if law_cosines > 1:
            law_cosines = 1
        elif law_cosines < -1:
            law_cosines = -1

        # Find elbows
        # --- Down Elbow ---  (left)
        angle_to_foot = math.radians(get_angle(self.anchor, self.feet[0]))
        angle = angle_to_foot - math.acos(law_cosines)
        # find elbow
        elbow = [self.anchor[0] - math.sin(angle) * leg_seg_length, self.anchor[1] - math.cos(angle) * leg_seg_length]
        # Render
        pygame.draw.line(self.surface, 'black', self.anchor, elbow, self.leg_thickness)
        pygame.draw.line(self.surface, 'black', elbow, self.feet[0], self.leg_thickness)

        # --- Up Elbow ---  (right)
        angle_to_foot = math.radians(get_angle(self.anchor, self.feet[1]))
        angle = math.acos(law_cosines) + angle_to_foot
        # find elbow
        elbow = [self.anchor[0] + math.sin(angle) * leg_seg_length, self.anchor[1] + math.cos(angle) * leg_seg_length]
        # Render
        pygame.draw.line(self.surface, 'black', self.anchor, elbow, self.leg_thickness)
        pygame.draw.line(self.surface, 'black', elbow, self.feet[1], self.leg_thickness)

        # TODO testing 0 elbow
        #pygame.draw.line(self.surface, 'black', self.anchor, self.feet[0], self.leg_thickness)
        #pygame.draw.line(self.surface, 'black', self.anchor, self.feet[1], self.leg_thickness)

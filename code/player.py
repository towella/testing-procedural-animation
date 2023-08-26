import pygame, math
from random import randint
from game_data import tile_size, controller_map, screen_width, screen_height
from support import get_angle_rad, get_angle_deg, get_distance, lerp2D


# SET UP FOR PLATFORMER SINCE PLATFORMERS ARE HARDER TO CREATE A PLAYER FOR
class Player(pygame.sprite.Sprite):
    def __init__(self, level, spawn, segments, segment_spacing):
        super().__init__()
        self.level = level
        self.surface = self.level.screen_surface
        self.controllers = self.level.controllers

        # -- player setup --
        # - Body -
        self.seg_spacing = segment_spacing
        self.speed = 3
        self.max_flex = 50
        self.segments = self.create_body(spawn, segments, segment_spacing)
        self.head = self.segments[0]
        self.max_length = 0
        for seg in self.segments:
            self.max_length += seg.radius * 2

        self.respawn = False

        # -- player movement --
        # collisions -- provides a buffer allowing late collision
        self.collision_tolerance = tile_size
        self.corner_correction = 8  # tolerance for correcting player on edges of tiles (essentially rounded corners)

        # - Brain -
        self.brain = Brain(self.head, self.surface)

# -- initialisation --

    # initialises the body
    def create_body(self, spawn, segments, segment_spacing):
        body_points = [BodySegment(self.surface, spawn, segment_spacing, False)]

        for i in range(segments - 1):
            segment_spacing -= 1  # TODO TEST REMOVE (dynamically change spacing and circle size of segs)
            if segment_spacing < 1:  # TODO TEST REMOVE
                segment_spacing = 1  # TODO TEST REMOVE
            if i == 5 or i == 0:
                body_points.append(BodySegment(self.surface, spawn, segment_spacing, True, body_points[i]))
            else:
                body_points.append(BodySegment(self.surface, spawn, segment_spacing, False, body_points[i]))
            body_points[i].set_child(body_points[i + 1])  # max i is length of points - 1 (head is added before loop)
            # therefore child of last point (i) is i + 1

        return body_points

# -- checks --

    # - input -

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

    def player_respawn(self, spawn):
        self.rect.x, self.rect.y = spawn.x, spawn.y  # set position to respawn point
        self.sync_hitbox()
        self.respawn = False

# -- getters and setters --
    def get_respawn(self):
        return self.respawn

    def get_head(self):
        return self.head

# -- update methods --

    # towards anchor
    def fabrik_forwards(self, target):
        # set start elbow to anchor position
        self.segments[0].set_pos([target[0], target[1]])

        # from 1 to n to exclude 0th elbow, since we have already positioned it
        for i in range(1, len(self.segments)):
            # spacing = combined radius of this segment and it's parent
            spacing = self.segments[i].get_radius() + self.segments[i].get_parent().get_radius()

            # update joint
            prev_seg_pos = self.segments[i - 1].get_pos()
            angle = get_angle_rad(prev_seg_pos, self.segments[i].get_pos())

            '''# + 180 to get the angle in the direction of the child rather than parent segment
            if not self.segments[i - 1].head:
                prev_seg_rot = get_angle_deg(self.segments[i - 2].get_pos(), self.segments[i - 1].get_pos())
            else:
                prev_seg_rot = math.degrees(self.segments[i - 1].get_rot()) + 180
            if abs(prev_seg_rot - angle) > self.max_flex:
                if angle > prev_seg_rot:
                    angle = prev_seg_rot + self.max_flex
                elif angle < prev_seg_rot:
                    angle = prev_seg_rot - self.max_flex'''

            self.segments[i].set_pos([prev_seg_pos[0] + math.sin(angle) * spacing,
                                      prev_seg_pos[1] + math.cos(angle) * spacing])

    # FABRIK algorithm (Forwards And Backwards Reaching Inverse Kinematic)
    def solve_body(self, target):
        # anchor is end of tail
        anchor = self.segments[-1].get_pos()
        # head is end effector

        # - if the target is too far away, fully extend appendage -
        if get_distance(anchor, target) >= self.max_length:
            target_angle = get_angle_rad(anchor, target)
            # modifies every elbow in relation to anchor. Repositions towards target
            length = 0
            # skips 0th joint which should be on anchor
            for i in range(1, len(self.segments)):
                length += self.segments[i].radius * 2
                self.segments[i] = [anchor[0] + math.sin(target_angle) * length,
                                    anchor[1] + math.cos(target_angle) * length]

        else:
            self.fabrik_forwards(target)

    def apply_scroll(self, scroll_value):
        self.rect.x -= int(scroll_value[1])
        self.rect.y -= int(scroll_value[0])
        self.sync_hitbox()

    def update(self, tiles, dt, mouse_pos): #, scroll_value, current_spawn):

        # respawns player if respawn has been evoked
        #if self.respawn:
            #self.player_respawn(current_spawn)

        # -- INPUT --
        #self.get_input(dt, tiles)

        # -- CHECKS/UPDATE --
        # - update brain -
        self.brain.update(tiles, mouse_pos)
        target = self.brain.get_target()
        head_pos = self.head.get_pos()
        angle = get_angle_rad(head_pos, target)
        target = [head_pos[0] + math.sin(angle) * self.speed,
                  head_pos[1] + math.cos(angle) * self.speed]

        # - update body -
        self.solve_body(target)
        for i in range(len(self.segments)):
            # if not a head don't pass mouse cursor (point is based on parent seg)
            if i > 0:
                self.segments[i].update(tiles)
            # if head seg, pass angle from head to target before head was moved to target
            else:
                self.segments[i].update(tiles, angle)

        # scroll shouldn't have collision applied, it is separate movement
        #self.apply_scroll(scroll_value)

# -- visual methods --

    def draw(self):
        for segment in self.segments:
            segment.draw()


# --------- BODY ---------

# --- body segments ---

class BodySegment(pygame.sprite.Sprite):
    def __init__(self, surface, spawn, segment_spacing, legs, parent_body_segment=None):
        super().__init__()

        self.surface = surface  # segment render surface
        self.pos = [spawn.x, spawn.y]  # segment position
        self.prev_pos = self.pos
        self.rot = 0  # keeps track of segment rotation in RADIANS for legs
        self.direction = pygame.Vector2()

        # parent/child
        self.parent_seg = parent_body_segment
        self.child_seg = None

        # segment values
        self.radius = segment_spacing // 2  # collisions and drawn circle
        if self.parent_seg is None:
            self.head = True
        else:
            self.head = False

        # collision
        # TODO ensure not inside tile before creating legs
        diameter = self.radius * 2
        self.hitbox = pygame.Rect(self.pos[0], self.pos[1], diameter, diameter)
        self.rect = self.hitbox
        self.collision_tolerance = tile_size

        # legs
        self.has_legs = legs
        if self.has_legs:
            # TODO define these parameters better (mainly for testing)
            max_leg_length = 100
            number_elbows = 3
            target_angle = 30
            step_interval = 150
            leg_thickness = 3
            seg_lengths = []  # [15, 60, 25, 5]
            self.legs = [LegPair(self.surface, self.pos, number_elbows, max_leg_length, target_angle, step_interval,
                                 0, leg_thickness, seg_lengths)]

    # --- COLLISIONS ---

    def collision(self, tiles):
        for tile in tiles:
            distance = get_distance(self.pos, tile.hitbox.center)
            if distance - (tile.radius + self.radius) < 0:
                angle = get_angle_rad(self.pos, self.prev_pos)  # angle to move back towards where seg came from
                self.hitbox.centerx += math.sin(angle) * (tile.radius + self.radius - distance + 1)
                self.hitbox.centery += math.cos(angle) * (tile.radius + self.radius - distance + 1)

                self.pos = [self.hitbox.centerx, self.hitbox.centery]

    # checks collision for a given hitbox against given tiles on the x
    def collision_x(self, tiles):
        # -- X Collisions --
        for tile in tiles:
            if tile.hitbox.colliderect(self.hitbox):
                # - normal collision checks -
                # abs ensures only the desired side registers collision
                if abs(tile.hitbox.right - self.hitbox.left) < self.collision_tolerance:
                    self.hitbox.left = tile.hitbox.right
                elif abs(tile.hitbox.left - self.hitbox.right) < self.collision_tolerance:
                    self.hitbox.right = tile.hitbox.left

                self.pos[0] = self.hitbox.centerx

    def collision_y(self, tiles):
        # -- Y Collisions --
        for tile in tiles:
            if tile.hitbox.colliderect(self.hitbox):
                # abs ensures only the desired side registers collision
                if abs(tile.hitbox.top - self.hitbox.bottom) < self.collision_tolerance:
                    self.hitbox.bottom = tile.hitbox.top
                elif abs(tile.hitbox.bottom - self.hitbox.top) < self.collision_tolerance:
                    self.hitbox.top = tile.hitbox.bottom

                self.pos[1] = self.hitbox.centery

    # --- GETTERS AND SETTERS ---

    def get_prev_pos(self):
        return self.prev_pos

    def get_pos(self):
        return self.pos

    def get_child(self):
        return self.child_seg

    def get_parent(self):
        return self.parent_seg

    def get_rot(self):
        return self.rot

    def get_radius(self):
        return self.radius

    def set_pos(self, pos):
        self.pos = [pos[0], pos[1]]
        self.sync_hitbox()

    def set_child(self, seg_obj):
        self.child_seg = seg_obj

    # --- UPDATE AND DRAW ---

    def sync_hitbox(self):
        self.hitbox.center = self.pos
        self.rect = self.hitbox

    def update(self, tiles, angle=0.0):
        # -- update rotations of segments --
        # non-head seg rot based on parent
        if not self.head:
            self.rot = get_angle_rad(self.pos, self.parent_seg.get_pos())
        # head seg rot based on passed angle
        else:
            self.rot = angle

        # -- update position and collision detection --
        # TODO fix collisions with new follow the leader
        # X
        self.pos[0] += self.direction.x
        self.sync_hitbox()  # sync hitbox after pos has been moved ready for collision detection
        self.collision_x(tiles)  # x collisions after x movement (separate to y movement)
        # Y
        self.pos[1] += self.direction.y
        self.sync_hitbox()  # sync hitbox after pos has been moved ready for collision detection
        self.collision_y(tiles)  # y collisions after y movement (separate to x movement)

        # TODO self.collision(tiles)  <-- radial collisions

        # -- update legs --
        distance = get_distance(self.pos, self.prev_pos)
        if self.has_legs:
            for leg in self.legs:
                leg.update(self.pos, self.rot, distance, tiles)

        self.prev_pos = self.pos  # store current pos in prev_pos ready for next frame

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

        #pygame.draw.rect(self.surface, 'grey', self.hitbox, 1)  # TODO TESTING hitbox

        # TODO TESTING self.rot
        x = math.sin(self.rot) * 12
        y = math.cos(self.rot) * 12
        epos = (self.pos[0] + x, self.pos[1] + y)
        pygame.draw.line(self.surface, 'red', self.pos, epos, 1)


class LegPair:
    def __init__(self, surface, anchor, num_elbows, max_leg_length, target_angle, step_interval, move_offset=0,
                 leg_thickness=3, segment_lengths=[]):
        # TODO merge max_leg_length and segment_lengths into one variable?
        # - general -
        self.surface = surface
        self.anchor = anchor  # where the leg is joined to the parent object
        self.rot = 0  # keeps track of rotation
        self.collision_tolerance = tile_size

        # - leg -
        # define max leg length based on segment lengths or default
        # default
        if len(segment_lengths) == 0:
            self.max_leg_length = max_leg_length  # informs length of leg segments
        # custom
        else:
            self.max_leg_length = 0
            for i in segment_lengths:
                self.max_leg_length += i
        self.step_interval = step_interval
        # tracks movement of body compared to feet to determine when to move feet [left, right]
        # step_interval // 2 creates offset between the legs. Move offset for multiple pairs of legs per body seg
        self.step_timers = [self.step_interval // 2 + move_offset, move_offset]
        self.hip_flex = 80  # range of motion allowed between body segment and leg (annchor to foot)

        # - foot target -
        self.target_angle = target_angle
        # targets points the feet move to [left, right]
        self.targets = [[self.anchor[0], self.anchor[1]],
                        [self.anchor[0], self.anchor[1]]]
        self.find_targets()

        # - foot -
        self.feet = [[self.anchor[0], self.anchor[1]],
                     [self.anchor[0], self.anchor[1]]]  # the leg's foot points [left, right]
        self.foot_move = [False, False]  # whether a foot should move or not [left, right]
        self.lerp_increment = 0.05  # value added to lerp per frame when required
        # tracks lerp value of feet when moving (between 0 and 1, representing a percentage of movement) [left, right]
        self.lerp = [0, 0]

        # - legs -
        self.legs = [Appendage(self.surface, self.anchor, self.max_leg_length, leg_thickness, num_elbows, segment_lengths),
                     Appendage(self.surface, self.anchor, self.max_leg_length, leg_thickness, num_elbows, segment_lengths)]

    # --- COLLISIONS ---

    def collision_x(self, new_pos, prev_pos, tiles):
        # pos == prev pos but with x coordinate changed ready for collision testing
        pos = [new_pos[0], prev_pos[1]]
        # -- X Collisions --
        for tile in tiles:
            if tile.hitbox.collidepoint(pos):
                # if inside tile, return x of prev position (ASSUMES DOESNT START IN TILE)
                return prev_pos[0]
        # if not inside tile, return x of new position
        return new_pos[0]

    def collision_y(self, new_pos, prev_pos, tiles):
        # pos == prev pos but with x coordinate changed ready for collision testing
        pos = [prev_pos[0], new_pos[1]]
        # -- X Collisions --
        for tile in tiles:
            if tile.hitbox.collidepoint(pos):
                # if inside tile, return x of prev position (ASSUMES DOESNT START IN TILE)
                return prev_pos[1]
        # if not inside tile, return x of new position
        return new_pos[1]

    # --- CALCULATE POINTS ---

    def find_targets(self):
        left_angle = self.rot + math.radians(self.target_angle)
        right_angle = self.rot - math.radians(self.target_angle)

        self.targets[0] = [self.anchor[0] + math.sin(left_angle) * self.max_leg_length,
                           self.anchor[1] + math.cos(left_angle) * self.max_leg_length]
        self.targets[1] = [self.anchor[0] + math.sin(right_angle) * self.max_leg_length,
                           self.anchor[1] + math.cos(right_angle) * self.max_leg_length]

    def find_feet(self, distance, tiles):
        # increment timers based on displacement of body seg. Dynamic (based on speed of seg)
        self.step_timers[0] += distance
        self.step_timers[1] += distance

        # -- Move Feet --
        # Check if foot needs to move. If it does, zero timer, sync feet timer offset and set bool
        if self.step_timers[0] > self.step_interval and not self.foot_move[0]:
            self.step_timers = [0, self.step_interval // 2]  # resync legs to stagger and reset moving leg
            self.foot_move[0] = True
        if self.step_timers[1] > self.step_interval and not self.foot_move[1]:
            self.step_timers = [self.step_interval // 2, 0]  # resync legs to stagger and reset moving leg
            self.foot_move[1] = True

        # check if leg is overextending, if so force move foot
        # independent of step timers. Will not mess with offset
        if get_distance(self.anchor, self.feet[0]) > self.max_leg_length:
            self.foot_move[0] = True
        if get_distance(self.anchor, self.feet[1]) > self.max_leg_length:
            self.foot_move[1] = True

        # TODO check if hip is overflexing, if so move force move foot
        '''if abs(get_angle(self.anchor, self.feet[0]) - self.rot) > self.hip_flex:
            self.foot_move[0] = True
        if abs(self.rot - get_angle(self.anchor, self.feet[1])) > self.hip_flex:
            self.foot_move[1] = True'''

        # Lerps feet towards targets (always makes it in time no matter distance because % distance
        # is used) (end lerp if at 100%)
        # - left -
        if self.foot_move[0]:
            # lerp towards target
            posmod = lerp2D(self.feet[0], self.targets[0], self.lerp[0])
            # check feet for collisions
            self.feet[0][0] = self.collision_x(posmod, self.feet[0], tiles)
            self.feet[0][1] = self.collision_y(posmod, self.feet[0], tiles)
            # increases lerp
            self.lerp[0] += self.lerp_increment
            # stop and reset lerp if at 100% (foot at target)
            if self.lerp[0] >= 1:
                self.foot_move[0] = False
                self.lerp[0] = 0
        # - right -
        if self.foot_move[1]:
            # lerp towards target
            posmod = lerp2D(self.feet[1], self.targets[1], self.lerp[1])
            # check feet for collisions
            self.feet[1][0] = self.collision_x(posmod, self.feet[1], tiles)
            self.feet[1][1] = self.collision_y(posmod, self.feet[1], tiles)
            # increase lerp
            self.lerp[1] += self.lerp_increment
            if self.lerp[1] >= 1:
                self.foot_move[1] = False
                self.lerp[1] = 0

    # --- UPDATE AND DRAW ---

    def update(self, pos, rot, distance, tiles):
        self.anchor = pos
        self.rot = rot

        self.find_targets()
        self.find_feet(int(distance), tiles)  # cast distance to int for memory efficiency
        # update legs, passing in feet as targets
        for i in range(len(self.legs)):
            self.legs[i].update(self.anchor, self.feet[i])

    def draw(self):
        # ------------ FEET BALLS ---------------
        pygame.draw.circle(self.surface, 'blue', self.feet[0], 4)
        pygame.draw.circle(self.surface, 'blue', self.feet[1], 4)

        # TODO testing
        #pygame.draw.circle(self.surface, 'red', self.targets[0], 5, 1)
        #pygame.draw.circle(self.surface, 'red', self.targets[1], 5, 1)

        # ----------- LEG SEGMENTS -------------
        for leg in self.legs:
            leg.draw()


class Appendage:
    def __init__(self, surface, anchor, max_length, line_weight=3, num_joints=1, segment_lengths=[]):
        # -- general --
        self.surface = surface
        self.anchor = anchor  # base point appendage is connected to
        self.target = anchor  # point the appendage is aiming to touch

        # -- joints --
        # number of leg segments (joints to be solved for)
        # +1 to account for 0 elbow case (is not a problem because just iterates over anchor 'elbow' as 0th elbow)
        self.num_joints = num_joints + 1
        # num_elbows + 2 allows one 'joint' to be attached to anchor and one be attached to target (see forward() and backward())
        self.joints = [[self.anchor[0], self.anchor[1]] for i in range(num_joints + 2)]

        # -- segments --
        self.seg_lengths = segment_lengths  # custom leg segment lengths

        # if specific lengths are passed in, base max length on their sum as long as len(segment_lengths) + 1 == num_joints
        # A -- o -- o -- o -- E   i.e. 3 joints = 4 lengths
        # default
        if len(segment_lengths) == 0:
            self.custom_lengths = False  # whether segment_lengths has been specified or not
            self.max_length = max_length  # maximum length of appendage

        # error exception
        elif len(segment_lengths) - 1 != num_joints:
            raise Exception("Appendage error: Number of passed segment lengths must be one greater than number of joints.")

        # custom
        else:
            self.custom_lengths = True
            self.max_length = 0
            for length in segment_lengths:
                self.max_length += length
        self.seg_length = self.max_length // self.num_joints  # distance between two joints. Used if segment_lengths is empty

        # -- FABRIK --
        self.tolerance = 1  # maximum pixel distance tolerance between end effector and target
        self.max_iter = 17  # maximum number of iterations before IK terminates (to prevent hang)

        # -- cosmetic --
        self.line_weight = line_weight

    # --- COLLISIONS ---

    def collision_x(self, new_pos, prev_pos, tiles):
        # pos == prev pos but with x coordinate changed ready for collision testing
        pos = [new_pos[0], prev_pos[1]]
        # -- X Collisions --
        for tile in tiles:
            if tile.hitbox.collidepoint(pos):
                # if inside tile, return x of prev position (ASSUMES DOESNT START IN TILE)
                return prev_pos[0]
        # if not inside tile, return x of new position
        return new_pos[0]

    def collision_y(self, new_pos, prev_pos, tiles):
        # pos == prev pos but with x coordinate changed ready for collision testing
        pos = [prev_pos[0], new_pos[1]]
        # -- X Collisions --
        for tile in tiles:
            if tile.hitbox.collidepoint(pos):
                # if inside tile, return x of prev position (ASSUMES DOESNT START IN TILE)
                return prev_pos[1]
        # if not inside tile, return x of new position
        return new_pos[1]

    # -- FABRIK --

    # FABRIK algorithm (Forwards And Backwards Reaching Inverse Kinematic)
    def solve_joints(self):
        # - if the target is too far away, fully extend appendage -
        if get_distance(self.anchor, self.target) >= self.max_length:
            target_angle = get_angle_rad(self.anchor, self.target)
            # modifies every elbow in relation to anchor. Repositions towards target
            length = 0
            # skips 0th joint which should be on anchor
            for i in range(1, len(self.joints)):
                # increment length
                if self.custom_lengths:
                    # cumulatively sum lengths for each joint
                    # joint 1 corresponds to length 0 .: i - 1
                    length += self.seg_lengths[i - 1]
                else:
                    length += self.seg_length

                self.joints[i] = [self.anchor[0] + math.sin(target_angle) * length,
                                  self.anchor[1] + math.cos(target_angle) * length]

        else:
            self.backwards()
            self.forwards()
            # continue to loop until either we have, looped 10 times, or are within the tolerance distance
            loop = 0
            # 0 < loop forces one iteration (so 0th elbow syncs with anchor which may have moved)
            while 0 < loop < self.max_iter and get_distance(self.joints[-1], self.target) > self.tolerance:
                self.backwards()
                self.forwards()
                loop += 1

    def forwards(self):
        # set start elbow to anchor position
        self.joints[0] = [self.anchor[0], self.anchor[1]]

        # from 1 to n to exclude 0th elbow, since we have already positioned it
        for i in range(1, len(self.joints)):
            # get length
            if self.custom_lengths:
                # get corresponding length from custom segment lengths. Joint 1 corresponds to length 0 .: i - 1
                length = self.seg_lengths[i - 1]
            else:
                # otherwise use default length
                length = self.seg_length

            # update joint
            prev_joint = self.joints[i - 1]
            angle = get_angle_rad(prev_joint, self.joints[i])
            self.joints[i] = [prev_joint[0] + math.sin(angle) * length,
                              prev_joint[1] + math.cos(angle) * length]

    def backwards(self):
        # set nth elbow to goal position
        self.joints[-1] = [self.target[0], self.target[1]]
        prev_joint = self.joints[-1]

        # len - 2 to exclude nth elbow, since we have already positioned it
        # loop to -1 since range is noninclusive (want to loop to 0)
        # TBH i don't fully understand how I came up with this. It just works.
        for i in range(len(self.joints) - 2, -1, -1):
            # get length
            if self.custom_lengths:
                # get corresponding length from custom segment lengths. Joint 1 corresponds to length 0 .: i - 1
                length = self.seg_lengths[i - 1]
            else:
                # otherwise use default length
                length = self.seg_length

            # update joint
            angle = get_angle_rad(prev_joint, self.joints[i])
            self.joints[i] = [prev_joint[0] + math.sin(angle) * length,
                              prev_joint[1] + math.cos(angle) * length]
            prev_joint = self.joints[i]

    # -- update and draw --

    def update(self, anchor, target):
        self.anchor = anchor
        self.target = target
        self.solve_joints()

    def draw(self):
        # skip anchor joint
        for i in range(1, len(self.joints)):
            joint = self.joints[i]
            pygame.draw.line(self.surface, 'black', self.joints[i - 1], joint, self.line_weight)
            pygame.draw.circle(self.surface, 'pink', joint, 2)


# --------- BRAIN ---------

class Brain:
    def __init__(self, head_segment, surface):
        self.surface = surface
        self.head = head_segment

        # -- pathfinding --
        self.target = self.head.get_pos()
        self.path = [self.head.get_pos()]  # start path as current position (no target yet defined). Len must be > 0
        self.path_precision = 15  # 15 !!!!! should be less than tile size !!!!!

    # -- calculate propeties --

    def pathfind(self, target, tiles):
        # TODO simplify code
        target_rect = pygame.Rect((target[0] - self.path_precision // 2, target[1] - self.path_precision // 2), (self.path_precision, self.path_precision))
        pygame.draw.rect(self.surface, 'red', target_rect, 1)
        # neighbours includes cardinal and diagonal neighbours
        neighbours = [(self.path_precision, 0),
                      (0, self.path_precision),
                      (-self.path_precision, 0),
                      (0, -self.path_precision),
                      (self.path_precision, self.path_precision),
                      (self.path_precision, -self.path_precision),
                      (-self.path_precision, self.path_precision),
                      (-self.path_precision, -self.path_precision)]
        start = (int(self.head.get_pos()[0]), int(self.head.get_pos()[1]))
        # for open and closed dicts: {(xpos, ypos): nodeInstance}
        open = {start: PathNode(start, 0, start, target)}  # nodes to be evaluated (initally only contains starting node)
        closed = {}  # nodes that have been evalutated

        run = True
        while run:
            # find node with lowest f cost in open
            current_node = open[list(open.keys())[0]]
            for node in open.keys():
                # if node has better f cost than current node or (the f costs are the same but
                # the h cost is better), set to current
                if open[node].get_f() < current_node.get_f() or (open[node].get_f() == current_node.get_f() and open[node].get_h() < current_node.get_h()):
                    current_node = open[node]

            current_pos = current_node.get_pos()
            # update dicts
            closed[current_pos] = current_node  # add node to closed
            del open[current_pos]  # remove node from open

            # if not the target, check through all the neighbouring positions
            for i in neighbours:
                # find adjacent coordinate
                neighbour_pos = (int(current_pos[0] + i[0]), int(current_pos[1] + i[1]))

                # check node is not already in closed before looping over tiles, if it is skip to next neighbour
                if neighbour_pos not in closed.keys():

                    # ends when neighbour is in target hitbox (prevents path overshoot and also prevents hanging bug
                    # where no neighbour can be both in the hitbox and not in a tile).
                    if target_rect.collidepoint(neighbour_pos):
                        run = False

                    # checks if neighbour is traversable or not, if not skip to next neighbour
                    traversable = True
                    for tile in tiles:
                        if tile.hitbox.collidepoint(neighbour_pos):
                            traversable = False
                            break
                    if traversable:

                        neighbour_g = current_node.get_g() + self.path_precision  # increases g one node further along path
                        # if it is either not in open or path to neighbour is shorter (based on g cost), add to open
                        if neighbour_pos not in open.keys() or neighbour_g < open[neighbour_pos].get_g():
                            # set/update node in open
                            open[neighbour_pos] = PathNode(neighbour_pos, neighbour_g, start, target, current_node)

        # -- Return full path --
        node = closed[current_pos]
        path = [target]
        # keep adding parent positions to path until start node is reached. Follow path using parents
        # does not include start node position (already there)
        while node.get_pos() != start:
            path.append(node.get_pos())
            node = node.get_parent()
        # exit loop with the full path (reversed so the start is at the start and the target is at the end)
        path.reverse()

        return path

    def find_target(self, tiles, mouse_pos):
        # TODO testing, if mouse has clicked, change target
        if pygame.mouse.get_pressed(3)[0]:
            in_tile = False
            for tile in tiles:
                if tile.hitbox.collidepoint(mouse_pos):
                    in_tile = True
                    break
            if not in_tile:
                self.target = mouse_pos

        # if target has been collected generate a new one
        if self.head.hitbox.collidepoint(self.target):
            self.target = (randint(0, screen_width), randint(0, screen_height))

            # continue to randomly generate point until point not in a tile
            repeat = True
            while repeat:
                for tile in tiles:
                    if tile.hitbox.collidepoint(self.target):
                        self.target = (randint(0, screen_width), randint(0, screen_height))
                        repeat = True  # point has been re-randomized and needs to be tested again
                        break
                    repeat = False  # point has not yet failed testing

    # -- getters and setters --
    # returns next point in the path to the real final target
    def get_target(self):
        return self.path[0]

    # -- update --
    def update(self, tiles, mouse_pos):
        # find target (if target needs to be found)
        self.find_target(tiles, mouse_pos)

        # create or modify path to target
        if self.head.hitbox.collidepoint(self.path[0]):
            self.path = self.path[1:]
        # if path is empty or the final point (the target) != to the current target, recalculate path
        if len(self.path) == 0 or self.path[-1] != self.target:
            self.path = self.pathfind(self.target, tiles)


class PathNode:
    def __init__(self, pos, g_cost, start, target, parent=None):
        # position
        self.pos = pos

        # points
        self.start = start
        self.target = target

        # parents and children
        self.parent = parent
        self.children = []

        # costs
        # TODO may cause problems if this is incorrect way of calculating them
        self.g = g_cost  # distance from node to start node (not counting this node)
        self.h = int(get_distance(self.pos, target))  # distance from node to target node (not counting this node)
        self.f = self.g + self.h

    # -- getters and setters --

    def get_pos(self):
        return self.pos

    def get_g(self):
        return self.g

    def get_h(self):
        return self.h

    def get_f(self):
        return self.f

    def get_parent(self):
        return self.parent

    def get_children(self):
        return self.children

    def add_child(self, node):
        self.children.append(node)
# - libraries -
import pygame
from pytmx.util_pygame import load_pygame  # allows use of tiled tile map files for pygame use
# - general -
from game_data import tile_size, controller_map, fonts
from support import *
# - tiles -
from tiles import CollideableTile, HazardTile
# - objects -
from player import Player
from trigger import Trigger
from spawn import Spawn
# - systems -
from camera import Camera
from text import Font


class Level:
    def __init__(self, fps, level_data, screen_surface, screen_rect, controllers):
        # TODO testing, remove
        self.dev_debug = False

        # level setup
        self.screen_surface = screen_surface  # main screen surface
        self.screen_rect = screen_rect
        self.screen_width = screen_surface.get_width()
        self.screen_height = screen_surface.get_height()

        self.controllers = controllers

        self.pause = False
        self.pause_pressed = False

        dt = 1  # dt starts as 1 because on the first frame we can assume it is 60fps. dt = 1/60 * 60 = 1

        body_segments = 20
        segment_spacing = 20
        self.player = Player((70, 70), self.screen_surface, body_segments, segment_spacing, self.controllers)

        # TODO testing
        self.tile = pygame.sprite.Group()
        image = pygame.Surface((tile_size, tile_size))
        image.fill("red")
        self.tile.add(CollideableTile((100, 100), (tile_size, tile_size), 0, image))

        # - get level data -
        '''tmx_data = load_pygame(resource_path(level_data))  # tile map file
        self.all_sprites = pygame.sprite.Group()  # contains all sprites for ease of updating/scrolling

        # get objects
        self.transitions = self.create_object_group(tmx_data, 'transitions', 'Trigger')
        self.player_spawns = self.create_object_group(tmx_data, 'spawns', 'Spawn')
        self.spawn_triggers = self.create_object_group(tmx_data, 'spawns', 'Trigger')
        # self.player_spawn_triggers = self.create_object_group(tmx_data, 'spawns', 'Trigger')
        self.player = self.create_object_group(tmx_data, '', 'Player')  # must be completed after player_spawns layer

        # get tiles
        self.collideable = self.create_tile_group(tmx_data, 'collideable', 'CollideableTile')
        self.tiles_in_screen = []
        self.hazards = self.create_tile_group(tmx_data, 'hazards', 'HazardTile')  # TODO hazard, what type?
        self.abs_camera_boundaries = {}
        self.abs_camera_boundaries['x'] = self.create_tile_group(tmx_data, 'abs camera boundaries x', 'CollideableTile')
        self.abs_camera_boundaries['y'] = self.create_tile_group(tmx_data, 'abs camera boundaries y', 'CollideableTile')

        # camera setup
        self.camera = Camera(self.screen_surface, self.screen_rect, self.player.sprite, self.abs_camera_boundaries, controllers)
        self.camera.focus(True)  # focuses camera on target
        scroll_value = self.camera.return_scroll(dt, fps)  # returns scroll, now focused
        self.player.sprite.apply_scroll(scroll_value)  # applies new scroll to player
        self.all_sprites.update(scroll_value)  # applies new scroll to all sprites'''

        # text setup
        self.small_font = Font(fonts['small_font'], 'white')
        self.large_font = Font(fonts['large_font'], 'white')

# -- set up room methods --

    # creates all the neccessary types of tiles seperately and places them in individual layer groups
    def create_tile_group(self, tmx_file, layer, type):
        sprite_group = pygame.sprite.Group()

        if type == 'CollideableTile':
            # gets layer from tmx and creates StaticTile for every tile in the layer, putting them in both SpriteGroups
            for x, y, surface in tmx_file.get_layer_by_name(layer).tiles():
                tile = CollideableTile((x * tile_size, y * tile_size), tile_size, surface)
                sprite_group.add(tile)
                self.all_sprites.add(tile)
        elif type == 'HazardTile':
            for x, y, surface in tmx_file.get_layer_by_name(layer).tiles():
                tile = HazardTile((x * tile_size, y * tile_size), tile_size, surface, self.player.sprite)
                sprite_group.add(tile)
                self.all_sprites.add(tile)
        else:
            raise Exception(f"Invalid create_tile_group type: '{type}' ")

        return sprite_group

    def create_object_group(self, tmx_file, layer, object):
        sprite_group = pygame.sprite.Group()
        if object == 'Trigger':
            for obj in tmx_file.get_layer_by_name(layer):  # can iterate over for objects
                # checks if object is a trigger (multiple objects could be in the layer
                if obj.type == 'trigger':
                    trigger = Trigger(obj.x, obj.y, obj.width, obj.height, obj.name)
                    sprite_group.add(trigger)
                    self.all_sprites.add(trigger)
        elif object == 'Spawn':
            sprite_group = {}
            for obj in tmx_file.get_layer_by_name(layer):
                # multiple types of object could be in layer, so checking it is correct object type (spawn)
                if obj.type == 'spawn':
                    # creates a dictionary containing spawn name: spawn pairs for ease and efficiency of access
                    spawn = Spawn(obj.x, obj.y, obj.name, obj.player_facing)
                    sprite_group[spawn.name] = spawn
                    self.all_sprites.add(spawn)
        elif object == 'Player':
            sprite_group = pygame.sprite.GroupSingle()
            # finds the correct starting position corresponding to the last room/transition
            spawn = (0, 0)
            player = Player(spawn, self.screen_surface, self.controllers)
            sprite_group.add(player)
        else:
            raise Exception(f"Invalid create_object_group type: '{type}' ")

        return sprite_group

# -- check methods --

    def get_input(self):
        keys = pygame.key.get_pressed()

        # pause pressed prevents holding key and rapidly switching between T and F
        if keys[pygame.K_p] or self.get_controller_input('pause'):
            if not self.pause_pressed:
                self.pause = not self.pause
            self.pause_pressed = True
        # if not pressed
        else:
            self.pause_pressed = False


        # TODO testing, remove
        if (keys[pygame.K_z] and keys[pygame.K_LSHIFT]) or self.get_controller_input('dev off'):
            self.dev_debug = False
        elif keys[pygame.K_z] or self.get_controller_input('dev on'):
            self.dev_debug = True

    # checks controller inputs and returns true or false based on passed check
    def get_controller_input(self, input_check):
        # check if controllers are connected before getting controller input (done every frame preventing error if suddenly disconnected)
        if len(self.controllers) > 0:
            controller = self.controllers[0]
            # TODO testing, remove
            if input_check == 'dev on' and controller.get_button(controller_map['share']):
                return True
            elif input_check == 'dev off' and controller.get_button(controller_map['share']) and controller.get_button(controller_map['X']):
                return True

            elif input_check == 'pause' and controller.get_button(controller_map['options']):
                return True
        return False

# -- visual --

    # draw tiles in tile group but only if in camera view (in tile.draw method)
    def draw_tile_group(self, group):
        for tile in group:
            # render tile
            tile.draw(self.screen_surface, self.screen_rect)
            # TODO testing, remove
            if self.dev_debug:
                pygame.draw.rect(self.screen_surface, 'green', tile.hitbox, 1)

# -- menus --

    def pause_menu(self):
        pause_surf = pygame.Surface((self.screen_surface.get_width(), self.screen_surface.get_height()))
        pause_surf.fill((40, 40, 40))
        self.screen_surface.blit(pause_surf, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        width = self.large_font.width('PAUSED')
        self.large_font.render('PAUSED', self.screen_surface, (center_object_x(width, self.screen_surface), 20))

# -------------------------------------------------------------------------------- #

    # updates the level allowing tile scroll and displaying tiles to screen
    # order is equivalent of layers
    def update(self, mouse_pos, dt, fps):
        # #### INPUT > GAME(checks THEN UPDATE) > RENDER ####
        # checks deal with previous frames interactions. Update creates interactions for this frame which is then diplayed

        # -- INPUT --
        self.get_input()

        # -- CHECKS (For the previous frame)  --
        if not self.pause:

            # scroll -- must be first, camera calculates scroll, stores it and returns it for application
            '''scroll_value = self.camera.return_scroll(dt, fps)
            self.camera.focus(False)'''

            # which object should handle collision? https://gamedev.stackexchange.com/questions/127853/how-to-decide-which-gameobject-should-handle-the-collision

            # checks if player has collided with spawn trigger and updates spawn
            '''for trigger in self.spawn_triggers:
                if player.hitbox.colliderect(trigger.hitbox):
                    self.player_spawn = self.player_spawns[trigger.name]
                    break'''

            # checks if the player needs to respawn and therefore needs to focus on the player
            '''if player.get_respawn():
                self.camera.focus(True)'''

            # checks which collideable tiles are in screen view.
            # TODO in function? More tile layers included? Use for tile rendering? IF ADD MORE LAYERS, CHANGE PLAYER TILES COLLISION LAYER
            '''self.tiles_in_screen = []
            for tile in self.collideable:
                if tile.hitbox.colliderect(self.screen_rect):
                    self.tiles_in_screen.append(tile)'''

        # -- UPDATES -- player needs to be before tiles for scroll to function properly
            # TODO IF TILES_IN_SCREEN ATTR IS CHANGED TO INCLUDE MORE LAYERS, CHANGE BACK TO self.collideable HERE!!!!
            self.player.update(self.tile, mouse_pos, dt)  #, self.tiles_in_screen, scroll_value, self.player_spawn)
            #self.all_sprites.update(scroll_value)'''

        # -- RENDER --
        # Draw
        self.player.draw()
        self.draw_tile_group(self.tile)
        '''self.draw_tile_group(self.collideable)
        self.draw_tile_group(self.hazards)'''

        # must be after other renders to ensure menu is drawn last
        if self.pause:
            self.pause_menu()

        # Dev Tools
        if self.dev_debug:
            '''put debug tools here'''
            pygame.draw.line(self.screen_surface, 'red', (0, 0), (15, 15), 1)

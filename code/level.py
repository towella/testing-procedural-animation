# - libraries -
import pygame
from random import randint
from pytmx.util_pygame import load_pygame  # allows use of tiled tile map files for pygame use
# - general -
from game_data import tile_size, controller_map, fonts
from support import *
# - tiles -
from tiles import StaticTile, CollideableTile, HazardTile
# - objects -
from player import Player
from trigger import SpawnTrigger, Trigger
from spawn import Spawn
# - systems -
from camera import Camera
from text import Font


class Level:
    def __init__(self, fps, level_data, screen_surface, screen_rect, controllers, starting_spawn):
        # TODO testing, remove
        self.dev_debug = False

        # level setup
        self.screen_surface = screen_surface  # main screen surface
        self.screen_rect = screen_rect
        self.screen_width = screen_surface.get_width()
        self.screen_height = screen_surface.get_height()

        self.starting_spawn = starting_spawn
        self.player_spawn = None  # will be filled after player is initialised

        self.controllers = controllers

        self.pause = False
        self.pause_pressed = False

        dt = 1  # dt starts as 1 because on the first frame we can assume it is 60fps. dt = 1/60 * 60 = 1

        # - get level data -
        tmx_data = load_pygame(resource_path(level_data))  # tile map file
        self.all_tile_sprites = pygame.sprite.Group()  # contains all tile sprites for ease of updating/scrolling
        self.all_object_sprites = pygame.sprite.Group()

        # get decoration layers
        '''self.background_layers = []  # ordered list of all background layers (in render order)
        self.foreground_layers = []  # ordered list of all foreground layers (in render order)
        for layer in tmx_data.layernames:
            # layer names is in the same order from the editor so background layers will be stored in correct order and
            # rendered in that order. In order for this to work, folder name must not contain 'background' (use bg instead)
            if 'background' in layer:
                self.background_layers.append(self.create_decoration_layer(tmx_data, layer))
            # see commenting for self.background_layers
            elif 'foreground' in layer:
                self.foreground_layers.append(self.create_decoration_layer(tmx_data, layer))'''

        # get objects
        #self.transitions = self.create_object_layer(tmx_data, 'transitions', 'Trigger')
        self.player_spawns = self.create_object_layer(tmx_data, 'spawns', 'Spawn')
        self.spawn_triggers = self.create_object_layer(tmx_data, 'spawns', 'SpawnTrigger')
        # self.player_spawn_triggers = self.create_object_group(tmx_data, 'spawns', 'Trigger')
        self.player = self.create_object_layer(tmx_data, '', 'Player')  # must be completed after player_spawns layer

        # get tiles
        self.collideable = self.create_tile_layer(tmx_data, 'collideable', 'CollideableTile')
        '''self.hazards = self.create_tile_layer(tmx_data, 'hazards',
                                              'HazardTile')  # TODO hazard, what type? (use tiled custom hitboxing feature on hazard tiles)
        self.abs_camera_boundaries = {
            'x': self.create_tile_layer(tmx_data, 'abs camera boundaries x', 'CollideableTile'),
            'y': self.create_tile_layer(tmx_data, 'abs camera boundaries y', 'CollideableTile')}

        # - camera setup -
        self.camera = Camera(self.screen_surface, self.screen_rect, self.player.sprite, self.abs_camera_boundaries,
                             controllers)
        self.camera.focus(True)  # focuses camera on target
        scroll_value = self.camera.get_scroll(dt, fps)  # returns scroll, now focused
        self.player.sprite.apply_scroll(scroll_value)  # applies new scroll to player
        self.all_tile_sprites.update(scroll_value)  # applies new scroll to all tile sprites
        self.all_object_sprites.update(scroll_value)  # applies new scroll to all object sprites'''

        # - text setup -
        self.small_font = Font(resource_path(fonts['small_font']), 'white')
        self.large_font = Font(resource_path(fonts['large_font']), 'white')

# -- set up room methods --

    # creates all the neccessary types of tiles seperately and places them in individual layer groups
    def create_tile_layer(self, tmx_file, layer_name, type):
        sprite_group = pygame.sprite.Group()
        layer = tmx_file.get_layer_by_name(layer_name)
        tiles = layer.tiles()
        parallax = (layer.parallaxx, layer.parallaxy)

        if type == "StaticTile":
            # gets layer from tmx and creates StaticTile for every tile in the layer, putting them in both SpriteGroups
            for x, y, surface in tiles:
                tile = StaticTile((x * tile_size, y * tile_size), (tile_size, tile_size), parallax, surface)
                sprite_group.add(tile)
                self.all_tile_sprites.add(tile)

        elif type == 'CollideableTile':
            for x, y, surface in tiles:
                tile = CollideableTile((x * tile_size, y * tile_size), (tile_size, tile_size), parallax, surface)
                sprite_group.add(tile)
                self.all_tile_sprites.add(tile)

        elif type == 'HazardTile':
            for x, y, surface in tiles:
                tile = HazardTile((x * tile_size, y * tile_size), (tile_size, tile_size), parallax, surface,
                                  self.player.sprite)
                sprite_group.add(tile)
                self.all_tile_sprites.add(tile)

        else:
            raise Exception(f"Invalid create_tile_group type: '{type}' ")

        return sprite_group

    def create_object_layer(self, tmx_file, layer_name, object_class):
        sprite_group = pygame.sprite.Group()
        if layer_name:  # prevents accessing '' layer in case of player
            layer = tmx_file.get_layer_by_name(layer_name)
            parallax = (layer.parallaxx, layer.parallaxy)

        if object_class == 'SpawnTrigger':
            for obj in layer:  # can iterate over for objects
                # checks if object is a trigger (multiple object types/classes could be in the layer)
                if obj.type == object_class:
                    spawn_data = tmx_file.get_object_by_id(obj.trigger_spawn)
                    spawn = Spawn(spawn_data.x, spawn_data.y, spawn_data.name, parallax, spawn_data.player_facing)
                    trigger = SpawnTrigger(obj.x, obj.y, obj.width, obj.height, obj.name, parallax, spawn)
                    sprite_group.add(trigger)
                    self.all_object_sprites.add(trigger)

        elif object_class == "Trigger":
            for obj in layer:
                if obj.type == object_class:
                    trigger = Trigger(obj.x, obj.y, obj.width, obj.height, obj.name, parallax)
                    sprite_group.add(trigger)
                    self.all_object_sprites.add(trigger)

        elif object_class == 'Spawn':
            sprite_group = {}
            for obj in layer:
                # multiple types of object could be in layer, so checking it is correct object type (spawn)
                if obj.type == object_class:
                    # creates a dictionary containing spawn name: spawn pairs for ease and efficiency of access
                    spawn = Spawn(obj.x, obj.y, obj.name, parallax, obj.player_facing)
                    sprite_group[spawn.name] = spawn
                    self.all_object_sprites.add(spawn)

        elif object_class == 'Player':
            sprite_group = pygame.sprite.GroupSingle()
            # finds the correct starting position corresponding to the last room/transition
            # TODO remove need for self.player_spawns
            spawn = self.player_spawns[self.starting_spawn]
            body_segments = 20
            segment_spacing = 20
            player = Player(self, spawn, body_segments, segment_spacing)
            sprite_group.add(player)
            self.player_spawn = spawn  # stores the spawn instance for future respawn

        else:
            raise Exception(f"Invalid create_object_group type: '{type}' ")

        return sprite_group

    def create_image_layer(self, tmx_file, layer_name):
        sprite_group = pygame.sprite.GroupSingle()
        layer = tmx_file.get_layer_by_name(layer_name)
        image = layer.image
        parallax = (layer.parallaxx, layer.parallaxy)

        tile = StaticTile((0, 0), (image.get_width(), image.get_height()), parallax, image)
        sprite_group.add(tile)
        self.all_tile_sprites.add(tile)
        return sprite_group

    # any layer that is purely for visuals, including parallax layers
    def create_decoration_layer(self, tmx_file, layer_name):
        sprite_group = pygame.sprite.GroupSingle()
        layer = tmx_file.get_layer_by_name(layer_name)
        parallax = (layer.parallaxx, layer.parallaxy)

        surf = pygame.Surface((tmx_file.width * tile_size, tmx_file.height * tile_size))
        surf.set_colorkey((0, 0, 0))

        # tile layers
        if layer.type == 'tile decoration':
            for x, y, surface in layer.tiles():
                surf.blit(surface, (x * tile_size, y * tile_size))

        # object layers
        elif layer.type == 'object decoration':  # layer in tmx_file.objectgroups:
            for obj in layer:
                surf.blit(obj.image, (obj.x, obj.y))

        tile = StaticTile((0, 0), (surf.get_width(), surf.get_height()), parallax, surf)
        sprite_group.add(tile)
        self.all_tile_sprites.add(tile)
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

# -- getters and setters --
    def set_pause(self, pause=True):
        self.pause = pause

# -------------------------------------------------------------------------------- #

    # updates the level allowing tile scroll and displaying tiles to screen
    # order is equivalent of layers
    def update(self, mouse_pos, dt):
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
            self.player.update(self.collideable, dt, mouse_pos)  #, self.tiles_in_screen, scroll_value, self.player_spawn)
            #self.all_sprites.update(scroll_value)'''

        # -- RENDER --
        # Draw
        self.player.sprite.draw()
        if not self.dev_debug:
            self.draw_tile_group(self.collideable)
        #self.draw_tile_group(self.hazards)

        # must be after other renders to ensure menu is drawn last
        if self.pause:
            self.pause_menu()

        # Dev Tools
        if self.dev_debug:
            '''put debug tools here'''
            for tile in self.collideable:
                pygame.draw.rect(self.screen_surface, 'green', tile.hitbox, 1)
            # TODO testing
            for point in self.player.sprite.brain.path:
                pygame.draw.circle(self.screen_surface, 'green', point, 2)
            pygame.draw.circle(self.screen_surface, 'pink', self.player.sprite.brain.target, 2)

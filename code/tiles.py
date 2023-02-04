import pygame
from support import import_folder


# base tile class with block fill image and normal surface support (also used for images, i.e, one big tile)
class StaticTile(pygame.sprite.Sprite):
    def __init__(self, pos, size, parallax, surface=None):
        super().__init__()
        self.original_pos = pos
        if surface:
            self.image = surface
        else:
            self.image = pygame.Surface((size[0], size[1]))  # creates tile
            self.image.fill('grey')  # makes tile grey
        self.rect = self.image.get_rect(topleft=pos)  # postions the rect and image
        self.parallax = parallax
        self.screen_width = pygame.display.Info().current_w
        self.screen_height = pygame.display.Info().current_h

    # allows all tiles to scroll at a set speed creating camera illusion
    def apply_scroll(self, scroll_value, use_parallax=False):
        if use_parallax:
            self.rect.x -= int(scroll_value[0] * self.parallax[0])
            self.rect.y -= int(scroll_value[1] * self.parallax[1])
        else:
            self.rect.x -= int(scroll_value[0])
            self.rect.y -= int(scroll_value[1])

    # scroll is separate to update, giving control to children of Tile class to override update
    def update(self, scroll_value, use_parallax=False):
        self.apply_scroll(scroll_value, use_parallax)

    def draw(self, screen, screen_rect):
        # if the tile is within the screen, render tile
        if self.rect.colliderect(screen_rect):
            screen.blit(self.image, self.rect)


# terrain tile type, inherits from main tile and can be assigned an image
class CollideableTile(StaticTile):
    def __init__(self, pos, size, parallax, surface):
        super().__init__(pos, size, parallax)  # passing in variables to parent class
        self.image = surface  # image is passed tile surface
        self.hitbox = self.image.get_rect()

    # allows all tiles to scroll at a set speed creating camera illusion
    def apply_scroll(self, scroll_value, use_parallax=False):
        if use_parallax:
            self.rect.x -= int(scroll_value[0] * self.parallax[0])
            self.rect.y -= int(scroll_value[1] * self.parallax[1])
        else:
            self.rect.x -= int(scroll_value[0])
            self.rect.y -= int(scroll_value[1])
        self.hitbox.midbottom = self.rect.midbottom


class HazardTile(CollideableTile):
    def __init__(self, pos, size, parallax, surface, player):
        super().__init__(pos, size, parallax, surface)
        self.player = player

    def update(self, scroll_value, use_parallax=False):
        if self.hitbox.colliderect(self.player.hitbox):
            self.player.invoke_respawn()
        self.apply_scroll(scroll_value, use_parallax)


# animated tile that can be assigned images from a folder to animate
class AnimatedTile(StaticTile):
    def __init__(self, pos, size, parallax, path):
        super().__init__(pos, size, parallax)
        self.frames = import_folder(path)
        self.frame_index = 0
        self.image = self.frames[self.frame_index]

    def animate(self, dt):
        # change tile image
        self.image = self.frames[self.frame_index]

        # increment index
        self.frame_index += round(1 * dt)
        if self.frame_index >= len(self.frames):
            self.frame_index = 0

    def update(self, dt, scroll_value, use_parallax=False):
        self.animate(dt)
        self.apply_scroll(scroll_value, use_parallax)
import pygame
from support import import_folder, cut_sprite_stack, rotate_point_deg


# base tile class with block fill image and normal surface support (also used for images, i.e, one big tile)
class StaticTile(pygame.sprite.Sprite):
    def __init__(self, pos, size, parallax, image_surface=None):
        super().__init__()
        if image_surface:
            self.images = [image_surface]
        else:
            self.images = [pygame.Surface((size[0], size[1]))]  # creates tile
            self.images[0].fill('grey')  # makes tile grey
        self.rect = self.images[0].get_rect(topleft=pos)  # postions the rect and image
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

    def apply_rotation(self, rot_value, origin):
        self.rect.centerx, self.rect.centery = rotate_point_deg(self.rect.center, origin, rot_value)
        for img in range(len(self.images)):
            self.images[img] = pygame.transform.rotate(self.images[img], rot_value)

    # scroll is separate to update, giving control to children of Tile class to override update
    def update(self, scroll_value, rot_value, origin=(0, 0), use_parallax=False):
        self.apply_scroll(scroll_value, use_parallax)
        if rot_value != 0:
            self.apply_rotation(rot_value, origin)

    def draw(self, screen, screen_rect):
        # if the tile is within the screen, render tile
        if self.rect.colliderect(screen_rect):
            screen.blit(self.images[0], self.rect)


# terrain tile type, inherits from main tile and can be assigned an image
class CollideableTile(StaticTile):
    def __init__(self, pos, size, parallax, surface):
        super().__init__(pos, size, parallax)  # passing in variables to parent class
        self.images = cut_sprite_stack(surface, size)  # image is passed tile surface
        self.hitbox = self.images[0].get_rect()  # TODO fix hitboxing for spritestacked tiles
        self.hitbox.topleft = pos
        self.pos = [pos[0], pos[1]]  # used rather than rect so can use floats for precision
        self.radius = self.hitbox.width // 2  # assumes hitbox is square
        self.rot = 0

    # allows all tiles to scroll at a set speed creating camera illusion
    def apply_scroll(self, scroll_value, use_parallax=False):
        if use_parallax:
            self.pos[0] -= int(scroll_value[0] * self.parallax[0])
            self.pos[1] -= int(scroll_value[1] * self.parallax[1])
        else:
            self.pos[0] -= int(scroll_value[0])
            self.pos[1] -= int(scroll_value[1])
        self.hitbox.center = self.pos

    def apply_rotation(self, rot_value, origin):
        self.pos = rotate_point_deg(self.pos, origin, rot_value)
        self.rot -= rot_value
        self.hitbox.center = self.pos

    # scroll is separate to update, giving control to children of Tile class to override update
    def update(self, scroll_value, rot_value, origin=(0, 0), use_parallax=False):
        self.apply_scroll(scroll_value, use_parallax)
        if rot_value != 0:
            self.apply_rotation(rot_value, origin)

    def draw(self, screen, screen_rect):
        if self.hitbox.colliderect(screen_rect):
            # stack images
            for img in range(len(self.images)):
                surf = pygame.transform.rotate(self.images[img], self.rot)
                screen.blit(surf, (self.pos[0] - surf.get_width()//2, self.pos[1] - surf.get_height()//2 - img))


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
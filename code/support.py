import pygame, os, sys, math
from csv import reader
from game_data import tile_size


# ------------------ IMPORT FUNCTIONS ------------------

# allows paths to be used for both normal running in PyCharm and as an .exe
def resource_path(relative_path):
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
        relative_path = relative_path[3:]  # slices path if using executable to absolute path. Otherwise use relative for PyCharm
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# https://riptutorial.com/pygame/example/23788/transparency    info on alpha values in surfaces (opacity and clear pixels)

# imports all the images in a single folder
# IMAGES MUST BE NAMED NUMERICALLY
def import_folder(path, return_type):
    surface_list = []
    allowed_file_types = ['.png', '.jpg', '.jpeg', '.gif']

    for folder_name, sub_folders, img_files in os.walk(path):
        if '.DS_Store' in img_files:
            img_files.remove('.DS_Store')  # remove before sorting frames into order

        # sorts no matter what the file suffix is, by splitting at the period and only looking at the numeric file name
        img_files.sort(key=lambda x: int(x.split('.')[0]))

        # for every image checks against allowed ftypes and gets image from constructed path.
        for image in img_files:
            for ftype in allowed_file_types:
                if ftype in image.lower():  # prevents invisible non image files causing error while allowing image type to be flexible (e.g. .DS_Store)
                    full_path = path + '/' + image  # accesses image file by creating path name
                    image_surface = pygame.image.load(full_path).convert_alpha()  # creates image surf (convert alpha is best practice)

                    if return_type == 'surface':
                        return image_surface

                    surface_list.append(image_surface)
                    break
        # if return_type == 'list'
        return surface_list


# imports level csvs and returns workable list of lists
def import_csv_layout(path):
    terrain_map = []
    with open(path) as map:
        level = reader(map, delimiter=',')
        for row in level:
            terrain_map.append(list(row))
        return terrain_map


# cuts up tile sheets returning list with provided path and the size each tile is in the image.
# tiles must have no spacing and consistent dimensions
def import_cut_graphics(path, art_tile_size):
    surface = pygame.image.load(path).convert_alpha()
    tile_num_x = int(surface.get_size()[0] / art_tile_size)  # works out how many tiles are on the x and y based on passed value
    tile_num_y = int(surface.get_size()[1] / art_tile_size)
    surface = pygame.transform.scale(surface, (tile_size * tile_num_x, tile_size * tile_num_y)) # expands tileset to game resolution based on dimensions in tiles

    cut_tiles = []
    # keeps track of different segments of tilesheet
    for row in range(tile_num_y):
        for col in range(tile_num_x):
            # x and y refer to x and y tile grid on the imported tileset not the game (top left of tile being sliced)
            x = col * tile_size
            y = row * tile_size
            # makes new surface and places segment of sheet (tile) on new surface
            new_surface = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)  # SRCALPHA allows opacity and invis pixels
            # blit args: thing to be placed, position (the top left corner of the surface), rectangle (mask)
            new_surface.blit(surface, (0, 0), pygame.Rect(x, y, tile_size, tile_size))
            #new_surface.set_alpha(100)  <-- changes alpha value for entire surface
            cut_tiles.append(new_surface)

    return cut_tiles

# ------------------ PROCEDURAL GRAPHICS ------------------


def cut_sprite_stack(surface, dim):
    layer_num = int(surface.get_height() / dim[1])

    cut_layers = []
    # keeps track of different segments of tilesheet
    for layer in range(layer_num):
        # x and y coords on layer img
        x = 0
        y = layer * dim[1]
        # makes new surface and places segment of sheet (tile) on new surface
        new_surf = crop(surface, x, y, dim[0], dim[1])
        cut_layers.append(new_surf)

    cut_layers.reverse()  # layers are in reverse on sprite stack sheet
    return cut_layers


def swap_colour(img, old_c, new_c):
    img.set_colorkey(old_c)
    surf = img.copy()
    surf.fill(new_c)
    surf.blit(img, (0, 0))
    return surf


def outline_image(image, colour='white'):
    # make surf for application
    surf = pygame.Surface((image.get_width() + 2, image.get_height() + 2))
    surf.set_colorkey((0, 0, 0))

    # create mask from image (necessary for white outlines)
    mask = pygame.mask.from_surface(image)
    mask_surf = mask.to_surface()
    mask_surf.set_colorkey((0, 0, 0))

    # create outline area
    surf.blit(mask_surf, (0, 1))
    surf.blit(mask_surf, (1, 0))
    surf.blit(mask_surf, (1, 2))
    surf.blit(mask_surf, (2, 1))

    if colour != 'white' and colour != (255, 255, 255):
        swap_colour(surf, 'white', colour)

    # layer original image over outline
    surf.blit(image, (1, 1))
    return surf


def circle_surf(radius, colour):
    radius = int(radius)
    surf = pygame.Surface((radius*2, radius*2))
    pygame.draw.circle(surf, colour, (radius, radius), radius)
    surf.set_colorkey((0, 0, 0))
    return surf


# ------------------ UTILITIES ------------------

# uses distance between points to lerp based on time between 0 and 1 (acts as % travelled)
# returns updated val1 position
def lerp1D(val1, val2, t):
    return val1 + (val2 - val1) * t


# uses distance between points to lerp based on time between 0 and 1 (acts as % travelled)
# returns updated point1 position
def lerp2D(point1, point2, t):
    return [lerp1D(point1[0], point2[0], t),
            lerp1D(point1[1], point2[1], t)]


def get_rect_corners(rect):
    return [rect.topleft, rect.topright, rect.bottomright, rect.bottomleft]


# returns angle of point from pos in DEGREES
def get_angle_deg(pos, point):
    # negative y values to flip the y axis from cartesian to pygame axis (reversed)
    angle = math.degrees(math.atan2(-point[1] - -pos[1], point[0] - pos[0]))
    # makes the angle produced by tan in any quadrant relative to 0 DEG and positive (0 - 360)
    if angle < 0:
        angle = 360 - abs(angle)
    return angle + 90


def get_angle_rad(pos, point):
    return math.radians(get_angle_deg(pos, point))


def get_distance(pos, point):
    x = point[0] - pos[0]
    y = point[1] - pos[1]
    return math.sqrt(x**2 + y**2)


def rotate_point_deg(point, origin, angle):
    rot = math.radians(angle)
    pos = [point[0] - origin[0], point[1] - origin[1]]  # relative coordinates
    pos = [pos[0] * math.cos(rot) - pos[1] * math.sin(rot),  # rotate
           pos[1] * math.cos(rot) + pos[0] * math.sin(rot)]
    pos = [pos[0] + origin[0], pos[1] + origin[1]]  # cartesian coordinates
    return pos


# crops a surface out of a larger surface (usefull for images)
def crop(surf, x, y, x_size, y_size):
    handle_surf = surf.copy()
    clipR = pygame.Rect(x, y, x_size, y_size)
    handle_surf.set_clip(clipR)
    image = surf.subsurface(handle_surf.get_clip())
    return image.copy()


# centers an object with a given width on the x axis on a given surface
def center_object_x(width_obj, surf):
    x = surf.get_width()//2 - width_obj//2
    return x


# converts a position refering to topleft to be applicable to surface's center
def pos_for_center(surf, pos):
    x = int(surf.get_width() / 2)
    y = int(surf.get_height() / 2)
    return [pos[0] - x, pos[1] - y]


def scale_hitbox(hitbox_image, scaleup):
    hitbox_width = hitbox_image.get_width()
    hitbox_height = hitbox_image.get_height()
    return pygame.transform.scale(hitbox_image, (hitbox_width * scaleup, hitbox_height * scaleup))
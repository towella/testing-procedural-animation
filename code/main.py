# pyinstaller code/main.py code/camera.py code/game_data.py code/player.py code/level.py code/spawn.py code/support.py code/tiles.py code/trigger.py --onefile --noconsole


# screen resizing tut, dafluffypotato: https://www.youtube.com/watch?v=edJZOQwrMKw

import pygame, sys, time
from level import Level
from text import Font
from game_data import *
from support import resource_path

# General setup
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
pygame.mixer.init()
clock = pygame.time.Clock()
#pygame.mouse.set_visible(False)

# window and screen Setup ----- window is real pygame window. screen is surface everything is placed on then resized
# to blit on window. (art pixel == game pixel)
# https://stackoverflow.com/questions/54040397/pygame-rescale-pixel-size

# https://www.pygame.org/docs/ref/display.html#pygame.display.set_mode
# https://www.reddit.com/r/pygame/comments/r943bn/game_stuttering/
# vsync only works with scaled flag. Scaled flag will only work in combination with certain other flags.
# although resizeable flag is present, window can not be resized, only fullscreened with vsync still on
# vsync prevents screen tearing (multiple frames displayed at the same time creating a shuddering wave)
window = pygame.display.set_mode((int(screen_width * scaling_factor), int(screen_height * scaling_factor)), pygame.RESIZABLE | pygame.DOUBLEBUF | pygame.SCALED, vsync=True)

# all pixel values in game logic should be based on the screen! NO .display FUNCTIONS!!
screen = pygame.Surface((screen_width, screen_height))  # the display surface, re-scaled and blit to the window
screen_rect = screen.get_rect()  # used for camera scroll boundaries

# caption and icon
pygame.display.set_caption('Larry the Cosmic Horror')
pygame.display.set_icon(pygame.image.load(resource_path('../assets/icon/app_icon.png')))

# get controller joysticks
pygame.joystick.init()
joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
print(f"joy {len(joysticks)}")
for joystick in joysticks:
    joystick.init()

# font
font = Font(fonts['small_font'], 'white')


def main_menu():
    '''Put main menu code here and call game function(s)'''
    game()


def game():
    click = False

    # delta time
    previous_time = time.time()
    dt = time.time() - previous_time
    previous_time = time.time()
    fps = clock.get_fps()

    starting_spawn = 'initial'
    level = Level(fps, '../rooms/tiled_rooms/room_0.tmx', screen, screen_rect, joysticks, starting_spawn)

    run = True
    while run:
        # delta time  https://www.youtube.com/watch?v=OmkAUzvwsDk
        dt = time.time() - previous_time
        dt *= 60  # keeps units such that movement += 1 * dt means add 1px if at 60fps
        previous_time = time.time()
        fps = clock.get_fps()

        # x and y mouse pos
        mx, my = pygame.mouse.get_pos()
        mouse_pos = (mx // scaling_factor, my // scaling_factor)

        # -- INPUT --
        click = False
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Keyboard events
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_COMMA or event.key == pygame.K_ESCAPE:
                    run = False
                    pygame.quit()
                    sys.exit()
                # TODO Debugging only, remove
                elif event.key == pygame.K_x:
                    global game_speed
                    if game_speed == 60:
                        game_speed = 20
                    else:
                        game_speed = 60
                elif event.key == pygame.K_f:
                    pygame.display.toggle_fullscreen()
                    level.set_pause()

            # Mouse events
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    click = True

            # Controller events
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button == controller_map['left_analog_press']:
                    run = False
                    pygame.quit()
                    sys.exit()

        # -- Update --
        screen.fill((48, 99, 142))  # fill background with colour
        level.update(mouse_pos, dt, fps)  # runs level processes

        font.render(f'FPS: {str(clock.get_fps())}', screen, (0, 0))  # TODO Debugging only, remove

        window.blit(pygame.transform.scale(screen, window.get_rect().size), (0, 0))  # scale screen to window

        # -- Render --
        pygame.display.update()
        clock.tick(game_speed)


main_menu()

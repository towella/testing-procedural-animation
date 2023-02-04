import pygame
from support import import_folder, outline_image
from text import Font


class Button:
    # images must be named 'default', 'hover', 'down' if relevant
    # TODO add sound
    def __init__(self, rect_pos, dimensions, image_offset, images_folder_path, outline_hover=True):
        self.outline_hover = outline_hover  # outline default image on hover

        self.hitbox = pygame.Rect(rect_pos[0], rect_pos[1], dimensions[0], dimensions[1])  # clickable area (also used for positioning)
        self.image_offset = image_offset  # image offset from hitbox top left when rendered
        self.blit_offset = [0, 0]

        self.mouse = pygame.mouse.get_pos()
        self.clicked = pygame.mouse.get_pressed()[0]
        self.activated = False

        # import images from button folder
        self.images = import_folder(images_folder_path)
        self.image = self.images['default']

    def mouse_hover(self):
        if self.hitbox.collidepoint(self.mouse[0], self.mouse[1]):
            if "hover" in self.images:  # checks if functionality wanted by checking if assets are available
                self.image = self.images['hover']
            elif self.outline_hover:
                self.image = outline_image(self.images['default'])
                # offset to account for added outline
                self.blit_offset[0] -= 1
                self.blit_offset[1] -= 1
        else:
            self.image = self.images['default']

    def mouse_click(self):
        just_click = pygame.mouse.get_pressed()[0]  # produces three tuple: (b1, b2, b3). Norm click is b1
        # mouse down changes button image to down image
        # checks if functionality wanted by checking if assets are available
        if self.hitbox.collidepoint(self.mouse[0], self.mouse[1]) and self.clicked and just_click and "down" in self.images:
            self.image = self.images['down']
            self.blit_offset = [0, 0]  # prevents hover offset from being applied
        # mouse up after mouse down over button activates button
        elif self.hitbox.collidepoint(self.mouse[0], self.mouse[1]) and self.clicked and not just_click:
            self.activated = True
        else:
            self.activated = False

    def get_activated(self):
        return self.activated

    def update(self):
        self.blit_offset = [0, 0]
        self.mouse = pygame.mouse.get_pos()
        self.mouse_hover()
        self.mouse_click()
        self.clicked = pygame.mouse.get_pressed()[0]

    def draw(self, surface):
        img_x = self.hitbox.topleft[0] + self.image_offset[0] + self.blit_offset[0]
        img_y = self.hitbox.topleft[1] + self.image_offset[1] + self.blit_offset[1]
        surface.blit(self.image, (img_x, img_y))
        # pygame.draw.rect(surface, 'red', self.hitbox, 1)  #  <-- debug rect


# hover images must be 'hover true' and 'hover false'
class Toggle(Button):
    def __init__(self, active, rect_pos, dimensions, image_offset, images_folder_path, outline_hover=True):
        super().__init__(rect_pos, dimensions, image_offset, images_folder_path, outline_hover)
        self.activated = active

    def mouse_hover(self):
        if self.hitbox.collidepoint(self.mouse[0], self.mouse[1]):
            # checks if functionality wanted by checking if assets are available
            if "hover true" in self.images and "hover false" in self.images:
                if self.activated:
                    self.image = self.images['hover true']
                else:
                    self.image = self.images['hover false']
            elif self.outline_hover:
                # TODO handle offset from border
                if not self.activated:
                    self.image = outline_image(self.images['default'])
                else:
                    self.image = outline_image(self.images['true'])
                # offset to account for added outline
                self.blit_offset[0] -= 1
                self.blit_offset[1] -= 1
        else:
            if self.activated:
                self.image = self.images['true']
            else:
                self.image = self.images['default']

    def mouse_click(self):
        just_click = pygame.mouse.get_pressed()[0]  # produces three tuple: (b1, b2, b3). Norm click is b1
        # mouse down changes button image to down image
        # checks if functionality wanted by checking if assets are available
        if self.hitbox.collidepoint(self.mouse[0], self.mouse[1]) and self.clicked and just_click and "down" in self.images:
            self.image = self.images['down']
            self.blit_offset = [0, 0]  # prevents hover offset from being applied
        if self.hitbox.collidepoint(self.mouse[0], self.mouse[1]) and not self.clicked and just_click:
            self.activated = not self.activated


class Slider:
    # naming images: 'bar', 'default slider', 'hover slider', 'clicked slider'
    def __init__(self, bar_pos, bar_dimensions, slide_increment, slider_value, slider_y, slider_dimensions, bar_img_pos,
                 images_folder_path, slider_img_offset=(0, 0), outline_hover=True):
        # bar length determines range of values on slider (in conjunction with slide_increment)
        self.bar_rect = pygame.Rect(bar_pos[0], bar_pos[1], bar_dimensions[0], bar_dimensions[1])  # bar bounds
        self.slide_increment = slide_increment  # how many pixels per value increase

        x = self.bar_rect.x + self.slide_increment * slider_value
        self.slider_rect = pygame.Rect(x, slider_y, slider_dimensions[0], slider_dimensions[1])  # slider
        self.value = slider_value

        self.bar_pos = bar_img_pos
        self.slider_offset = slider_img_offset
        self.blit_offset = [0, 0]

        self.outline_hover = outline_hover

        self.mouse = pygame.mouse.get_pos()
        self.clicked = pygame.mouse.get_pressed()[0]

        self.images = import_folder(images_folder_path)
        self.image = self.images['default slider']

    def get_value(self):
        return self.value

    def mouse_hover(self):
        if self.slider_rect.collidepoint(self.mouse[0], self.mouse[1]):
            if "hover" in self.images:
                self.image = self.images['hover slider']
            elif self.outline_hover:
                self.image = outline_image(self.images['default slider'])
                # offset to account for added outline
                self.blit_offset[0] -= 1
                self.blit_offset[1] -= 1
        else:
            self.image = self.images['default slider']

    def mouse_click(self):
        just_click = pygame.mouse.get_pressed()[0]  # produces three tuple: (b1, b2, b3). Norm click is b1
        # mouse down changes button image to down image
        if self.bar_rect.collidepoint(self.mouse[0], self.mouse[1]) and self.clicked and "down" in self.images:
            self.image = self.images['down slider']
            # move slider to mouse x if multiple of move increment
            if (self.mouse[0] - self.bar_rect.left) % self.slide_increment == 0:
                self.slider_rect.centerx = self.mouse[0]
            # update value
            self.value = (self.slider_rect.centerx - self.bar_rect.left) // self.slide_increment

            self.blit_offset = [0, 0]  # prevents hover offset from being applied

    def update(self):
        self.blit_offset = [0, 0]
        self.mouse = pygame.mouse.get_pos()
        self.mouse_hover()
        self.mouse_click()
        self.clicked = pygame.mouse.get_pressed()[0]

    def draw(self, surface):
        # bar
        surface.blit(self.images['bar'], self.bar_pos)
        # slider
        surface.blit(self.image, (self.slider_rect.x + self.slider_offset[0] + self.blit_offset[0],
                                  self.slider_rect.y + self.slider_offset[1] + self.blit_offset[1]))

        #pygame.draw.rect(surface, 'red', self.slider_rect, 1)  #< - test
        #pygame.draw.rect(surface, 'red', self.bar_rect, 1)  #<-- test


# source page https://stackoverflow.com/questions/46390231/how-can-i-create-a-text-input-box-with-pygame
class InputBox:
    def __init__(self, x, y, w, h, inactive_colour, active_colour, max_chars, font_path, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.colours = {'inactive': inactive_colour, 'active': active_colour}
        self.colour = inactive_colour
        self.default_text = text
        self.text = text
        # maximum characters allowed for text box
        if max_chars < len(text):
            self.max_chars = len(text)
        else:
            self.max_chars = max_chars
        self.active = False
        self.font = Font(font_path, self.colours['inactive'])

    def handle_event(self, events):
        if pygame.mouse.get_pressed()[0]:
            # If the user clicked on the input_box rect.
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                # Toggle the active variable and clear text if the text is still the default text. Otherwise keep it
                self.active = True
                if self.text == self.default_text:
                    self.text = ''
            else:
                self.active = False

        # TODO fix up events vs key_down
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.active:
                    if event.key == pygame.K_RETURN:
                        self.active = False
                    # LMETA is command button
                    # TODO fix
                    elif event.key == pygame.K_LMETA:
                        self.text = ''
                    elif event.key == pygame.K_BACKSPACE:
                        self.text = self.text[:-1]
                    else:
                        self.text += event.unicode  # adds char string to text
                    # Re-render the text.
        # length cap
        if len(self.text) > self.max_chars:
            self.text = self.text[:self.max_chars]

    def update(self, events):
        self.handle_event(events)
        # Change the current color of the input box.
        self.colour = self.colours['active'] if self.active else self.colours['inactive']
        # Resize the box if the text is too long.
        self.rect.w = max(200, self.font.width(self.text) + 2)

    def draw(self, screen):
        # Blit the text.
        self.font.render(self.text, screen, (self.rect.x+2, self.rect.y+2))
        # Blit the rect.
        pygame.draw.rect(screen, self.colour, self.rect, 1)


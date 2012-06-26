import pygame

from airena.display import BaseDisplay

class PygameDisplay(BaseDisplay):
    def __init__(self, width=640, height=480, 
                 flags=None, 
                 caption="Pygame Display",
                 *args, **kwargs):
        super(PygameDisplay, self).__init__(*args, **kwargs)
        self._flags = flags
        self.caption = caption
        self._initialize_pygame()
        self._initialize_screen()

    def _get_caption(self): 
        return self._caption

    def _set_caption(self, val):
        self._caption = val
        pygame.display.set_caption(self.caption)

    caption = property(_get_caption, _set_caption)

    def _initialize_pygame(self):
        pygame.init()

    def _initialize_screen(self):
        dimensions = (self.width, self.height)
        if self._flags:
            self.screen = pygame.display.set_mode(dimensions, self._flags)
        else:
            self.screen = pygame.display.set_mode(dimensions)

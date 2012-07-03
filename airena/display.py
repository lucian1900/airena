import pygame

class PygameDrawable(pygame.sprite.DirtySprite):
    dirty = 2

class PygameDisplay(object):
    def __init__(self, width=640, height=480, 
                 flags=None, 
                 caption="Pygame Display",
                 framerate=30.0,
                 *args, **kwargs):
        self.width = width
        self.height = height
        self.framerate = float(framerate)
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
        self._time = 0
        self._clock = pygame.time.Clock()

    def _initialize_screen(self):
        dimensions = (self.width, self.height)
        if self._flags:
            self.screen = pygame.display.set_mode(dimensions, self._flags)
        else:
            self.screen = pygame.display.set_mode(dimensions)

    def tick(self):
        dt = self._clock.tick(self.framerate)
        dt = min(100, dt)
        self._time += dt
        return dt, self._time

    def get_events(self):
        return pygame.event.get()

    def flip(self):
        return pygame.display.flip()



    


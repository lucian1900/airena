import pygame

from airena.clocks import BaseClock

class PygameClock(BaseClock):
    def __init__(self, *args, **kwargs):
        super(PygameClock, self).__init__()
        self._clock = pygame.time.Clock()

    def tick(self, framerate):
        return self._clock.tick(framerate)

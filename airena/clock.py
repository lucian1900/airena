from airena.utils import load

class BaseClock(object):
    def __init__(self):
        pass

    def tick(self, framerate):
        pass

def load_clock(class_name):
    return load('airena.clocks', BaseClock, class_name)

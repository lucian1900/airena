
class BaseClock(object):
    def __init__(self):
        pass

    def tick(self, framerate):
        pass

def load_clock(class_name):
    clock_classes = load('airena.clocks', subclasses=BaseClock)

    for cls in clock_classes

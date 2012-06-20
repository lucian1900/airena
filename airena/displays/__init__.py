from airena.utils import load

class BaseDisplay(object):
    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height

def load_display(class_name):
    display_classes = load('airena.displays', subclasses=BaseDisplay)

    for cls in display_classes:
        if class_name == cls.__name__:
            return cls

from airena.utils import ClassManager

class BaseDisplay(object):
    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height

class DisplayManager(ClassManager):
    def __init__(self):
        super(DisplayManager, self).__init__(BaseDisplay, 'airena.plugins')


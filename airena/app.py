
from airena.scene import SceneManager
from airena.displays import load_display

class Application(object):

    def __init__(self):
        self.scene_manager = SceneManager(self)

    def _initialize_display(self, display_name='PygameDisplay'):
        display_class = load_display(display_name)
        self.display = display_class()

    def start(self):
        self._initialize_display()

        sm = self.scene_manager
        current_scene = sm.get_current()
        while current_scene:
            current_scene.update(0, 0)
            current_scene = sm.get_current()

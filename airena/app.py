from airena.utils import load_plugin
from airena.scene import SceneManager, SimulationScene
from airena.display import PygameDisplay
from airena.sim import BaseSimulation

class ApplicationError(Exception): pass

class Application(object):

    def __init__(self, args):
        self.args = args

        self._initialize_sim()

        self.scene_manager = SceneManager()
        
    def _initialize_sim(self):
        if not hasattr(self.args.conf_module, 'SIMULATION'):
            raise ApplicationError("simconf contains no `SIMULATION` settings")

        simconf = getattr(self.args.conf_module, 'SIMULATION')

        search_class = simconf.get('class', None)
        if search_class is None:
            raise ApplicationError("SIMULATION['class'] undefined in simconf")

        search_namespace = simconf.get('namespace', 'airena.plugins')
        simulation_class = load_plugin(BaseSimulation, search_namespace)

        if not simulation_class:
            raise ApplicationError("simulation class `%s` could not be found" % search_class)
        self.sim = simulation_class()

    def _initialize_display(self):
        displayconf = {}
        if hasattr(self.args.simconf, 'DISPLAY'):
            displayconf = getattr(self.args.conf_module, 'DISPLAY')
        self.display = PygameDisplay(**displayconf)

    def start(self):
        self._initialize_display()

        sm = self.scene_manager
        first_scene = SimulationScene(self.sim, sm)
        sm.push_scene(first_scene)

        # named method caches
        clock_tick = self.display.tick
        get_events = self.display.get_events
        flip = self.display.flip

        current_scene = sm.get_current()
        while current_scene:
            # get time delta
            dt, total = clock_tick()
            current_scene.update(dt, total)
            events = get_events()
            current_scene.handle_events(events)
            current_scene = sm.get_current()

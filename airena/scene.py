import pygame

class Scene(object):
    def __init__(self, manager, *args, **kwargs):
        self._manager = manager

    def on_enter(self, old_scene, *args, **kwargs):
        pass

    def on_exit(self, new_scene, *args, **kwargs):
        pass

    def on_pause(self, new_scene, *args, **kwargs):
        pass

    def on_resume(self, old_scene, retval, *args, **kwargs):
        pass

    def update(self, dt, t, *args, **kwargs):
        pass

    def handle_events(self, events, *args, **kwargs):
        for event in events:
            if pygame.KEYDOWN == event.type:
                if pygame.K_ESCAPE == event.key:
                    return self._manager.pop_scene()

class SimulationScene(Scene):
    def __init__(self, sim, manager, *args, **kwargs):
        super(SimulationScene, self).__init__(manager, *args, **kwargs)
        self._sim = sim

    def update(self, dt, t, *args, **kwargs):
        sef._sim.update(dt, t)

    def handle_events(self, events, *args, **kwargs):
        for event in events:
            if pygame.KEYDOWN == event.type:
                if pygame.K_ESCAPE == event.key:
                    return self._manager.pop_scene()
            self._sim.handle_events(events, *args, **kwargs)
                    

class SceneManager(object):
    def __init__(self, first=None):
        self._scenes = []
        if first:
            self.push_scene(first)

    def get_current(self):
        if len(self._scenes):
            return self._scenes[-1]

    def push_scene(self, new_scene):
        old_scene = self.get_current()
        if old_scene:
            old_scene.on_pause(self, new_scene)
        
        new_scene.on_enter(old_scene)
        self._scenes.append(new_scene)

    def pop_scene(self):
        old_scene = self._scenes.pop()
        current_scene = self.get_current()
        old_scene.on_exit(current_scene)

        if current_scene:
            current_scene.on_resume(old_scene)

    def replace_scene(self, new_scene):
        old_scene = self._scenes.pop()
        old_scene.on_exit(new_scene)

        new_scene.on_enter(old_scene)
        self._scenes.append(new_scene)
        

# class AppSceneManager(SceneManager):
#     def __init__(self, app, first=None):
#         self.app = app
#         super(AppSceneManager, self).__init__(first=first)



    
    

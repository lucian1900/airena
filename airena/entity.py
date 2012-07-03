from airena.vec2d import Vec2D

class Entity(object):

    def __init__(self, pos):
        self.pos = Vec2D(*pos)
        self.vel = Vec2D(0, 0)
        self.accel = Vec2D(0, 0)

    def set_vel(self, dx, dy):
        self.vel.x = dx
        self.vel.y = dy

    def set_pos(self, x, y):
        self.pos.x = x
        self.pos.y = y

    def set_accel(self, dx, dy):
        self.accel.x = dx
        self.accel.y = dy

    def update(self, dt, t, *args, **kwargs):
        self.vel += dt * self.accel
        self.pos += dt * self.vel

    def render(self, screen, dt, t, *args, **kwargs):
        pass

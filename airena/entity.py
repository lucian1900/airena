class Grid(object):
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.entities = []

    def check_coord(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def register(self, entity):
        if self.check_coord(entity.x, entity.y):
            self.entities.append(entity)
            entity.grid = self
            return True

        return False


class Entity(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y

class Grid(object):
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.entities = {}

    def check(self, coords):
        x, y = coords

        if not (0 <= x < self.width and 0 <= y < self.height):
            return False

        if (x, y) in self.entities:
            return False

        return True

    def __getitem__(self, key):
        if isinstance(slice, key):
            x1, y1 = slice.start
            x2, y2 = slice.stop

            subgrid = Grid(width=1, height=2)
            return subgrid
        else:
            return self.entities[key]

    def register(self, entity):
        if self.check(entity):
            self.entities[tuple(entity)] = entity
            return True

        return False


class World(object):
    def __init__(self):
        self.grid = Grid(10, 15)

    def tick(self):
        for coords, entity in self.grid.entities.iteritems():
            entity.tick([])


class Entity(object):
    def __init__(self, x, y, brain):
        self.x = x
        self.y = y
        self.brain = brain

    def __iter__(self):
        yield self.x
        yield self.y

    def tick(self, grid):
        self.brain.tick(self, grid)


class Brain(object):
    def tick(self, entity, grid):
        pass

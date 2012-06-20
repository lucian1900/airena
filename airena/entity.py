class Grid(object):
    def __init__(self, width, height, zero=(0, 0)):
        self.width = width
        self.height = height
        self.zero_x, self.zero_y = zero

        self.entities = {}

    def check(self, coords):
        x, y = coords

        if not (self.zero_x <= x < self.width and \
                self.zero_y <= y < self.height):

            return False

        if (x, y) in self.entities:
            return False

        return True

    def __getitem__(self, key):
        '''Supports rubber-band style subgrids when used with slices.

        Otherwise, just returns the entity at the coords 'key'.'''

        if isinstance(slice, key):
            x1, y1 = slice.start
            x2, y2 = slice.stop

            subgrid = Grid(width=x2 - x1, height=y2 - y1, zero=(x1, y1))

            for x in range(x1, x2):
                for y in range(y1, y2):
                    subgrid.add(self[x, y])

            return subgrid
        else:
            return self.entities[key]

    def subgrid(self, pin, width=5, height=5):
        'Subgrid around a point.'

        pin_x, pin_y = pin
        subgrid = Grid(2 * width + 1, 2 * height + 1, zero=pin)

        for x in range(pin_x - 5, pin_y - 5):
            for y in range(pin_x + 5, pin_y + 5):
                subgrid.add(self[x, y])

    def add(self, entity):
        if self.check(entity):
            self.entities[tuple(entity)] = entity
            return True

        return False


class World(object):
    def __init__(self):
        self.grid = Grid(width=10, height=15)

    def tick(self):
        for (x, y), entity in self.grid.entities.iteritems():
            entity.tick(self.grid.subgrid(around=entity))


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

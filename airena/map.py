import pudb

import pygame

from sprite import Sprite

class TilesheetError(Exception): pass

class ManagedQueryList(list):
    def __init__(self, map, items=None):
        super(ManagedQueryList, self).__init__()
        self._map = map

        items = items or list()
        for obj in items:
            self.append(obj)

    def on_add(self, idx, obj):
        print 'adding', obj, 'at', idx

    def on_remove(self, idx, obj):
        print 'removing', obj, 'at', idx

    def __setitem__(self, idx, obj):
        old_obj = None
        if idx >= 0 and idx < len(self):
            old_obj = self[idx]
        super(ManagedQueryList, self).__setitem__(idx, obj)
        self.on_remove(idx, old_obj)
        self.on_add(idx, obj)

    def __delitem__(self, idx):
        item = None
        if idx >= 0 and idx < len(self):
            item = self[idx]
        super(ManagedQueryList, self).__delitem__(idx)
        self.on_remove(idx, item)

    def insert(self, idx, obj):
        length = len(self)
        if idx >= length:
            idx = length
        if idx <= 0:
            idx = 0
        super(ManagedQueryList, self).insert(idx, obj)
        self.on_add(idx, obj)
            
    def append(self, obj):
        length = len(self)
        super(ManagedQueryList, self).append(obj)
        self.on_add(length, obj)

    def obj_by_attr(self, attr, value):
        for item in self:
            try:
                if getattr(item, attr) == value:
                    return item
            except AttributeError:
                pass

    def index_by_attr(self, attr, value):
        for idx, item in enumerate(self):
            try:
                if getattr(item, attr) == value:
                    return idx
            except AttributeError:
                pass

class LayerList(ManagedQueryList):
    def on_add(self, idx, layer):
        print "Added %s layer at %d" % (obj, idx)

    def on_remove(self, idx, layer):
        print "Removed %s layer at %d" % (obj, idx)

class TilesetList(ManagedQueryList):
    def on_add(self, idx, tileset):
        print "Added %s Tileset at %d" % (obj, idx)

    def on_remove(self, idx, tileset):
        print "Removed %s Tileset at %d" % (obj, idx)



class Tilesheet(object):
    """
    An image containing a number of Tile images

    first_gid: int - this Tilesheet's offset for calculating global tile-ids
                     ex. gID = first_gid + idx

    filename : str - the location of the image on disk
    properties : dict - mapping of properties
    image : surface - pygame surface

    tile_width, tile_height : int - dimensions of tiles, in pixels
    width, height : int - dimension of the sheet, in tiles

    get_tile(x, y) : get a subtile from the sheet
    """
    def __init__(self, first_gid, 
                 filename=None, filelike=None, image=None, 
                 transkey=None,tile_width=32, tile_height=32):

        if image:
            # just set preloaded image
            self._image = image
        elif filelike:
            # load image here
            self._image = pygame.image.load(filelike, namehint='png')
        elif filename:
            self._image = pygame.image.load(filename)
            self._filename = filename

        self._first_gid = first_gid
        self._last_gid = first_gid

        self._filename = filename
        self._transkey = transkey

        self._width = 0
        self._height =0

        self._tile_width = tile_width
        self._tile_height = tile_height

        self._spacing = 0
        self._margin = 0

        self.properties = {}
    
        self._tiles = []

        self._calculate_max_column()
        self._calculate_max_row()
        self._process_tiles()

    def _process_tiles(self):
        self._tiles = []
        for x in xrange(self.width):
            for y in xrange(self.height):
                tile = self.cut_by_coord(x, y)
                if tile is None:
                    template = "Tile coordinate %d,%d returned blank cut."
                    message = template % (x, y)
                    raise TilesheetError(message)
                self._tiles.append(tile)
        self._last_gid = self._first_gid + len(self._tiles)
        if self._first_gid:
            self._last_gid -= 1

    @property
    def first_gid(self):
        return self._first_gid

    @property
    def last_gid(self):
        return self._last_gid

    @property
    def filename(self):
        return self._filename

    @property
    def transkey(self):
        return self._transkey

    @property
    def tiles(self):
        return tuple(self._tiles)

    # these calculate dimensions of sheet, in tiles
    def _calculate_max_column(self):
        self._width = (self.image.get_width() - self.margin) / (self._tile_width + self._spacing)

    def _calculate_max_row(self):
        self._height = (self.image.get_height() - self.margin) / (self._tile_height + self._spacing)

    # the pixel width of tiles
    @property
    def tile_width(self):
        return self._tile_width

    @tile_width.setter
    def tile_width(self, val):
        self._tile_width = val
        self._calculate_max_column() # recalculate sheet width

    # the pixel height of tiles
    @property
    def tile_height(self):
        return self._tile_height

    @tile_height.setter
    def tile_height(self, val):
        self._tile_height = val
        self._calculate_max_column() # recalculate sheet height

    # the dimensions of the sheet, in tiles
    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    # the source image of the sheet
    @property
    def image(self):
        return self._image

    @property
    def spacing(self):
        return self._spacing

    @property
    def margin(self):
        return self._margin

    # the transparency color for the sheet
    @property
    def transkey(self):
        return self._transkey

    # return a new subtile from the sheet
    def cut_by_coord(self, x, y):
        part = pygame.Surface((self.tile_width, self.tile_height),
                              self._image.get_flags(),
                              self._image.get_bitsize())
        rect = pygame.Rect(self.margin + (x * (self._tile_width + self.spacing)),
                           self.margin + (y * (self._tile_height + self.spacing)),
                           self.tile_width, self.tile_height)


        if self._transkey:
            part.set_color(self._transkey, pygame.RLEACCEL)
            part.fill(self._transkey)

        part.blit(self._image, (0, 0), rect)

        return part

    def get_coord(self, x, y):
        idx = (y * self.width) + x
        try:
            return self._tiles[idx]
        except IndexError:
            template = "Requested tile %d, %d out of tilesheet range."
            message = template % (x, y)
            raise TilesheetError(message)

    def get_gid(self, gid):
        if gid >= self._first_gid and gid <= self._last_gid:
            idx = gid - self._first_gid
            return self._tiles[idx]

class Tileset(object):
    """
    A tileset holds images used by Tiles

    first_gid : int - first gid of this tileset
    tile_width : int - width of tiles, in pixels
    tile_height : int - height of tiles, in pixels
    spacing : int - distance, in pixels, between tiles
    margin : int - distance, in pixels, around tilesheets
    """
    def __init__(self, first_gid, 
                 tile_width=32, tile_height=32, 
                 spacing=0, margin=0):
        self._first_gid = first_gid
        self._tile_width = tile_width
        self._tile_height = tile_height
        self._spacing = spacing
        self._margin = margin
        self._sheets = []
        self._tiles = []

    @property
    def first_gid(self):
        return self._first_gid

    @property
    def last_gid(self):
        return self._sheets[-1].last_gid

    def _update_sheet_width(self):
        for sheet in self._sheets:
            sheet.tile_width = self.tile_width

    def _update_sheet_height(self):
        for sheet in self._sheets:
            sheet.tile_height = self.tile_height

    @property
    def tile_width(self):
        return self._tile_width

    @tile_width.setter
    def tile_width(self, value):
        self._tile_width = value
        self._update_sheet_width()

    @property
    def tile_height(self):
        return self._tile_height

    @tile_height.setter
    def tile_height(self, value):
        self._tile_height = value
        self._update_sheet_height()

    @property
    def spacing(self):
        return self._spacing

    @property
    def margin(self):
        return self._margin

    def add_tilesheet(self, tilesheet):
        print "adding tilesheet", tilesheet.filename
        tilesheet.tile_width = self.tile_width
        tilesheet.tile_height = self.tile_height
        tilesheet.spacing = self.spacing
        tilesheet.margin = self.margin
        self._sheets.append(tilesheet)

    def get_gid(self, gid):
        first = self._first_gid
        last = self._first_gid
        if gid >= self._first_gid and gid <= self.last_gid:
            for sheet in self._sheets:
                if gid >= sheet.first_gid and gid <= sheet.last_gid:
                    pudb.set_trace()
                    return sheet.get_gid(gid)

class Tile(Sprite):
    """
    A single map tile.

    id : int - id of the tile (gid = firstgid + id)
    properties : dict -  mapping of properties
    """
    def __init__(self, id, *args, **kwargs):
        super(Tile, self).__init__(*args, **kwargs)
        self.id = id

class MapLayer(object):
    """
    A layer of the map.

    name : str - name of this layer

    x : int - horizontal position of the layer, in tiles
    y : int - vertical position of the layer, in tiles

    width : int - width, in tiles
    height : int - height, in tiles

    pixel_width : int - width, in pixels
    pixel_height : int - height, in pixels

    opacity : float - from 0 (transparent) to 1.0 (opaque)
    
    items : list of lists - usage layer.items[x][y]
    """

    def __init__(self, map):
        self._map = map
        self._name = ''

        self._x = 0
        self._y = 0

        self._width = 0
        self._height = 0
        self._pixel_width = 0
        self._pixel_height = 0

        self._visible = True
        self._opacity = 1.0

        self._encoding = None
        self._compression = None

        self._encoded_content = None
        self._decoded_content = []

        self.properties = {}
        self._is_object_group = False

        self._items = None


    @property
    def name(self):
        return self._name

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, val):
        self._x = int(val)

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, val):
        self._y = int(val)

    def _update_pixel_width(self):
        self._pixel_width = self.width * self._map.tile_width

    def _update_pixel_height(self):
        self._pixel_height = self.height * self._map.tile_height

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        self._width = int(value)
        self._update_pixel_width()

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, value):
        self._height = int(value)
        self._update_pixel_height()


    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, val):
        self._visible = bool(val)

    @property
    def opacity(self):
        return self._opacity

    @opacity.setter
    def opacity(self, val):
        self._opacity = float(val)



        

class Map(object):
    """
    The structure that holds all the map data.

    :Ivariables:
        map_file_name : str
            file name of the map
        version : str
            version of the map format
        tilewidth : int
            width of the tiles (for all layers)
        tileheight : int
            height of the tiles (for all layers)
        width : int
            width of the map (number of tiles)
        height : int
            height of the map (number of tiles)
        tile_sets : ManagedQueryList
            managed list of TileSets
        layers : ManagedQueryList
            managed list of TileLayers
        properties : dict
            the propertis set in the editor, name-value pairs, strings
        pixel_width : int
            width of the map in pixels
        pixel_height : int
            height of the map in pixels
    """

    def __init__(self):
        self._map_filename = ''

        self._tile_width = 0
        self._tile_height = 0
        self._width = 0
        self._height = 0

        self.tile_sets = TilesetList(self)
        self.layers = LayerList(self)
        self.properties = {}

        self._pixel_width = 0
        self._pixel_height = 0


    def _update_pixel_width(self):
        self._pixel_width = self.width * self.tile_width

    def _update_pixel_height(self):
        self._pixel_height = self.height * self.tile_height

    @property
    def map_filename(self):
        return self._map_filename

    @property
    def tile_width(self):
        return self._tile_width

    @tile_width.setter
    def tile_width(self, value):
        self._tile_width = int(value)
        self._update_pixel_width()

    @property
    def tile_height(self):
        return self._tile_height

    @tile_height.setter
    def tile_height(self, value):
        self._tile_height = int(value)
        self._update_pixel_height()

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        self._width = int(value)
        self._update_pixel_width()

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, value):
        self._height = int(value)
        self._update_pixel_height()

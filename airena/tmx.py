import sys
from xml.dom import minidom, Node
try:
    # python 2.x
    import StringIO
    from StringIO import StringIO
except:
    # python 3.x
    from io import StringIO
import os.path
import struct
import array

import pygame

from sprite import Sprite
from map import Tilesheet, Tileset, Tile, MapLayer, Map

# -- helpers -- #
def get_nodes(nodes, name):
    for node in nodes:
        if node.nodeType == Node.ELEMENT_NODE and node.nodeName == name:
            yield node
            
def get_abs(base, relative):
    if os.path.isabs(relative):
        return relative
    if os.path.isfile(base):
        base = os.path.dirname(base)
    return os.path.abspath(os.path.join(base, relative))

def get_properties(node):
    props = {}
    for properties_node in get_nodes(node.childNodes, 'properties'):
        for property_node in get_nodes(properties_node.childNodes, 'property'):
            try:
                props[property_node.attributes['name'].nodeValue] = \
                    property_node.attributes['value'].nodeValue
            except KeyError:
                props[property_node.attributes['name'].nodeValue] = \
                                            property_node.lastChild.nodeValue
    return props

def set_properties(node, obj):
    props = get_properties(node)
    obj.properties.update(props)

def get_attributes(node):
    attributes = dict()
    for key, val in node.attributes.items():
        attributes[key] = val
    return attributes

def set_attributes(node, obj):
    for name, node in node.attributes.items():
        setattr(obj, name, node.nodeValue)

def parse_tsx(filename, base_path):
    if not os.path.isabs(filename):
        filename = get_abs(base_path, filename)
    fobj = None
    try:
        fobj = open(filename, 'rb')
        dom = minidom.parseString(fobj.read())
    finally:
        if fobj:
            fobj.close()

    tilesets = []
    for node in get_nodes(dom.childNodes, 'tileset'):
        tilesets.append(build_tileset(node, base_path))
    return tilesets

def build_tilesheet(tilesheet_node, base_path, first_gid):
    attributes = get_attributes(tilesheet_node)
    data = None
    for node in get_nodes(tilesheet_node.childNodes, 'data'):
        data = node.childNodes[0].nodeValue
    if data is not None:
        data = StringIO.StringIO(data)
        data.seek(0)
    source = attributes.get('source')
    transkey = attributes.get('trans')
    return Tilesheet(first_gid, filename=source, filelike=data, transkey=transkey)

def build_tilesets(tileset_node, base_path, first_gid):
    attributes = get_attributes(tileset_node)
    source = attributes.get('source', None)
    if source:
        return parse_tsx(source)
    else:
        firstgid = attributes.get('firstgid')
        tile_width = attributes.get('tilewidth')
        tile_height = attributes.get('tileheight')
        spacing = attributes.get('spacing')
        margin = attributes.get('margin')

        tileset = Tileset(firstgid, tile_width, tile_height,
                          spacing or 0, margin or 0)

        for node in get_nodes(tileset_node.childNodes, 'image'):
            tilesheet = build_tilesheet(node, base_path, first_gid)
            tileset.add_tilesheet(tilesheet)
        return tileset

def build_map(map_node, base_path):
    attributes = get_attributes(map_node)
    if attributes['version'] != '1.0':
        template = 'tmx.parse was designed for version 1.0 maps: found version %s' 
        message = template % map_obj.version
        raise VersionError(message)

    map_obj = Map()

    first_gid = 1
    for node in get_nodes(map_node.childNodes, 'tileset'):
        tileset = build_tilesets(node, base_path, first_gid)
        first_gid = tileset.last_gid + 1

def parse(filename):
    tmxfile = None
    try:
        tmx_file = open(filename, 'rb')
        tmx_data = tmx_file.read()
        dom = minidom.parseString(tmx_data)
    finally:
        if tmx_file:
            tmx_file.close()

    abs_path = os.path.abspath(filename)
    base_path = os.path.dirname(abs_path)
    map_node = list(get_nodes(dom.childNodes, 'map'))[0]
    return build_map(map_node, base_path)


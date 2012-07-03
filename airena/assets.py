import os
from pkg_resources import resource_exists, resource_stream

import pygame

try:
    import tiledtmxloader as tmx
except ImportError:
    import 

def parse_resource_path(path):
    if ':' not in path:
        return 'airena', path
    namespace, path = path.split(':')
    if namespace != 'airena':
        namespace = "airena.plugins.%s" % namespace
    return namespace, path

def check_resource(path):
    return resource_exists(namespace, path)

def get_resource(path):
    namespace, path = parse_resource_path(path)
    if resource_exists(namespace, path):
        return resource_stream(namespace, path)

def get_image(path, convert=True):
    resource = get_resource(path)
    if resource:
        filename = os.path.basename(path)
        img = pygame.image.load(resource)
        if convert:
            img = img.convert()
        if filename.lower().endswith('png'):
            img = img.convert_alpha()
        return img



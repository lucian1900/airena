# -*- coding: utf-8 -*-
"""
This module provides a spritesystem. Its goal was to implement a spritesystem
that has all desired capabilities but it is still easy to use. So far following
features have been implemented::

    - world and screen coordinate system (sprites position is in world coord,
      sprites rect attribute is in screen coord, the rect collision methods can
      cope with the number of rendering sprites, but would be unusable in a large
      world with many more sprites that are rendered) conversion methods can be
      customized in the camera class (default does not use the conversion
      methods, but the default conversions are implemented)

    - easy sprite picking to find out which sprites are in a certain area on
      screen

    - easy way to implement a special render path through a custom 'draw(...)'
      method of the sprite (its not the default because of performance, each
      method call costs)

    - interpolated rendering to be used with a fixed timestep logic, not done by
      default because of performance reasons ( see:
      http://gafferongames.com/game-physics/fix-your-timestep/ )

    - push/pop sprites for scene management or splashscreens without the need to
      save current->clear->add new->clear new->re-add previous sprites

    - simple way to render a hud (heads up display)
        
    - scrolling by a camera system of the known sprites (which sprites are in the
      visible area should be determined by the game logic)

    - camera tracking another sprites

    - multiple cameras for split screen or multi view output of a world
    
    - floating point precision positions

    - visibility flag to make a sprite visible or invisible on screen (invisible
      sprites are removed from the render list, so having many invisible sprites
      should not affect the render performance)

    - anchor system using an offset

    - easy transformations (conbinations alsow allowed):
            - rotation
            - zoom
            - flipping in x and y direction

    - image caching of sprites for performance

    - easy layer implementation, z layer can be changed on the sprites itself

    - parallax scrolling (independent of layer and each axis can be configured
      independently)

    - soure rect support

    - blit flags support

    - own vector implementation

    - easy text sprites

    - easy vector drawing sprites
    
Performance was also a major concern, so the default usage is optimized and
therefore the code might look a bit strange at certain places. For the same
reason the sprite has some attributes that should not be changed directly, only
through a method (properties are slow too).

Things that do not belong into a spritesystem:
    - animation
    - collision detection (except picking because only the renderer actually
      knows where on the screen the sprites are)
    - particle system
    - path following
    - tweening
    - camera visibility determination in the world using a spatial hash,
      quadtree, etc (gos into gamelogic)

NOTES: 

    - Groups: maybe a simply group to apply some function to all of its sprites
      at once (those groups might differ from the renderlist or there might be
      multiple groups with overlapping contents...)

    
The three main classes of the module are:

    - Camera
    - DefaultRenderer
    - Sprite
    
The sprites are added to the renderer and the camera is used to make a part of
the game-world visible on a certain screen area.
"""


import math
from math import sin, cos, atan2, radians, degrees, hypot

import pygame

TYPEPOINT = 1
TYPEVECTOR = 0

# pylint: correct pylint errors:   pylint --rcfile=HG_google_python-pyknic\pyknic\pylint.config -d E0202 symple.py

class Vector(object):
    """
    2D vector class.
    
    w : TYPEPOINT = 1 represents a point
        TYPEVECTOR = 0 represents a vector

    v1, v2 vectors

    operators:
    v1 + v2   addition
    v1 - v2   subtraction
    v1 % v2   elementwise multiplication
    v1 ^ v2   cross product (not implemented)
    v1 | v2   dot product
    ~v1      elementwise invert

    """

    # this will be set after class definition because otherwise
    # there would be a recursive call to this class construction
    position = None

    def __init__(self, x=0.0, y=0.0, w=TYPEVECTOR, position=None):
        """
        x : x component of the vector
        y : y component of the vector
        w[TYPEVECTOR=1] : 1 represents a point
            0 represents a vector

        position[Vector(0,0,w=1)] : a point, where the vector is attached in the
        room (like forces in physics)
        """
        if position is not None:
            assert TYPEPOINT == position.w
            self.position = Vector(position.x, position.y, TYPEPOINT)
        self.x = x
        self.y = y
        self.w = w

    @staticmethod
    def from_points(to_point, from_point):
        """
        Returns the vector between the two given points. The position attribute
        of the resulting vector is set to the position of the from_point. The
        resulting vector will then point to the to_point.
        
        The difference to simply substract the points is the position argument.
        
        """
        assert to_point.w == TYPEPOINT, "to_point isn't a point according to w"
        if from_point:
            assert_msg = "from_point isn't a point according to w"
            assert from_point.w == TYPEPOINT, assert_msg
            return Vector(to_point.x - from_point.x, 
                          to_point.y - from_point.y,
                          w=TYPEVECTOR, position=from_point.copy())
        return Vector(to_point.x, to_point.y)

    @staticmethod
    def from_tuple(tup, w=TYPEVECTOR, position=None):
        """
        Return a Vector instance from a tuple.
        
        :Parameters:
            tup : tuple
                the tuple to use, only the first two values are used.
            w[TYPEVECTOR] : TYPEVECTOR, TYPEPOINT
                optional w argument to define if it is a point or a vector
            position[None] : Vector
                the position of the vector
        """
        return Vector(tup[0], tup[1], w=w, position=position)

    def copy(self):
        """
        Returns a new instance of vector with the same values for all attributes.
        """
        return Vector(self.x, 
                      self.y, 
                      w=self.w, 
                      position=Vector(self.position.x, 
                                      self.position.y, 
                                      self.position.w))

    def round_ip(self, round_func=round, *args):
        """
        Rounds the components of this vector in place using the rounding
        function.
        
        Example::
            
            v = Vector(1.75, 3.33)
            v.round_ip() # v == Vector(2, 3)
            w = Vector(1.75, 3.33)
            w.round(round, 1) # w == Vector(1.8, 3.3)
            x = Vector(1.75, 3.33)
            x.round(int) # x == Vector(1, 3)

        :Parameters:
            round_func[round] : function
                the rounding function to use, defaults to round
            args : args
                the arguments to use for the rounding function.
        """
        self.x = round_func(self.x, *args)
        self.y = round_func(self.y, *args)
        return self

    def round(self, round_func=round, *args):
        """
        Returns a new vector with rounded components using the rounding function.
        
        Example::
            
            v = Vector(1.75, 3.33)
            w = v.round() # w == Vector(2, 3)
            x = v.round(round, 1) # x == Vector(1.8, 3.3)
            y = v.round(int) # y == Vector(1, 3)
        
        :Parameters:
            round_func[round] : function
                the rounding function to use, defaults to round
            args : args
                the arguments to use for the rounding function.
        """
        return Vec(round_func(self.x, *args), 
                   round_func(self.y, *args), 
                   w=self.w, position=self.position.copy())

    def rotate(self, deg):
        """
        Returns a rotated the vector.
        
        :Parameters:
            deg : int
                degrees to rotate, deg > 0 : anti-clockwise rotation
        """
        if deg == 0:
            rotated_x = self.x
            rotated_y = self.y
        elif deg == 90:
            rotated_x = self.y
            rotated_y = -self.x
        elif deg == -90:
            rotated_x = -self.y
            rotated_y = self.x
        elif deg == 180:
            rotated_x = -self.x
            rotated_y = -self.y
        else:
            rad = radians(deg)
            cval = cos(rad)
            sval = sin(rad)
            rotated_x = self.x * cval + self.y * sval
            rotated_y = -self.x * sval + self.y * cval
        return Vector(rotated_x, 
                      rotated_y, 
                      w=self.w, position=self.position.copy())

    def rotate_ip(self, deg):
        """
        Rotates this vector in place.
        
        :Parameters:
            deg : int
                degrees to rotate, deg > 0 : anti-clockwise rotation
        """
        rad = radians(deg)
        rotated_x = self.x * cos(rad) + self.y * sin(rad)
        self.y = -self.x * sin(rad) + self.y * cos(rad)
        self.x = rotated_x
        return self

    @property
    def angle(self):
        """
        Returns the angle between this vector and the x-axis.
        """
        return -degrees(atan2(self.y, self.x))

    @property
    def length(self):
        """
        Returns the length of the vector.
        """
        return hypot(self.x, self.y)

    @length.setter
    def length(self, value):
        """
        Set the length of this vector.
        """
        self.normalize_ip()
        self.x *= value
        self.y *= value

    def normalize(self):
        """
        Returns a normalized (unit length) vector.
        """
        length = self.length
        if length > 0:
            return Vector(self.x / length, 
                          self.y / length, 
                          w=self.w, position=self.position.copy())
        return Vector(w=self.w, position=self.position.copy())

    def normalize_ip(self):
        """
        Does normalize this vector in place.
        """
        length = self.length
        if length > 0:
            self.x /= length
            self.y /= length
        return self

    def __call__(self, round_func=None, *args):
        """
        Returns a tuple with the values of this vector.
        
        Example::
            v = Vector(1.7, 3.3)
            t = v() # t == (1.7, 3.3)
            t = v(int) # t == (1, 3)
            t = v(round) # t == (2, 3)
        
        
        :Parameters:
            round_func[None] : func
                the tuple values can be rounded by the rounding function to use
            args : args
                the arguments for the rounding function
        """
        if round_func:
            return (round_func(self.x, *args), round_func(self.y, *args))
        return (self.x, self.y)

    def __mul__(self, scalar):
        """
        Returns a scaled vector. Only scalar multiplication.
        
        a * v == Vector(a * v.x, a * v.y)
        
        Example:
            a = 2
            v = Vector(1, 3)
            w = a * v  # Vector(2, 6)
            x = v * a  # Vector(2, 6)
        
        """
        return Vector(scalar * self.x, 
                      scalar * self.y, 
                      w=self.w, position=self.position.copy())

    __rmul__ = __mul__

    def __sub__(self, other):
        """
        Vector subtraction.
        
        v - w == Vector(v.x - w.x, v.y - w.y)

        p1 - p2 => v1 -> w = 0
        p1 - v1 => p2 -> w = 1
        v1 - v2 => v3 -> w = 0
        v1 - p1 => error ( w =  -1)
        """
        assert_msg = "trying to substract a point %s from a vector %s "
        assert_msg = assert_msg % (str(other), str(self))
        cond_1 = (self.w - other.w) in [TYPEVECTOR, TYPEPOINT]
        if self.w == TYPEPOINT and other.w == TYPEVECTOR:
            cond_2 = (self.w - other.w) == TYPEPOINT
        else:
            cond_2 = (self.w - other.w) == TYPEVECTOR
        assert cond_1 and cond_2, assert_msg

        return Vector(self.x - other.x, self.y - other.y, w=self.w - other.w)

    def __add__(self, other):
        """
        Vecotr addition.
        
        v + w == Vector(v.x + w.x, v.y + w.y)

        p1 + p2 => error ( w = 2)
        p1 + v1 => p2 -> w = 1
        v1 + v2 => v3 -> w = 0
        v1 + p1 => same as p1 + v1 ( w =  1)

        """
        # assert 1
        cond_1 = (self.w + other.w) in [TYPEVECTOR, TYPEPOINT]
        if self.w == TYPEVECTOR and other.w == TYPEVECTOR:
            cond_2 = (self.w + other.w) == TYPEVECTOR
        else:
            cond_2 = (self.w + other.w) == TYPEPOINT
        assert cond_1 and cond_2, "trying to add two points"
        # assert 2
        assert_msg = "adding two points? %s %s" % (str(self), str(other))
        assert 0 <= self.w + other.w <= 1, assert_msg

        return Vector(self.x + other.x, self.y + other.y, w=self.w + other.w)

    def __mod__(self, other):
        """
        Elementwise multiplication.
        
        v % w == Vector(v.x * w.x, v.y * w.y, v.w * w.w)

        p1 % p2 => error ( w = 1)
        p1 % v1 => p2 -> w = 0
        v1 % v2 => v3 -> w = 0
        v1 % p1 => v2 -> w = 0
        """
        return Vector(self.x * other.x, self.y * other.y, w=self.w)

    def __or__(self, other): # dot
        """
        Vector dot product.
        
        v | w == v.x * w.x + v.y * w.y
        
        """
        assert TYPEVECTOR == self.w and TYPEVECTOR == other.w
        return self.x * other.x + self.y * other.y

    def __invert__(self):
        """
        Elementwise invert.
        
        v = Vector(a, b)
        ~v # Vector( 1.0 / a, 1.0 / b, w)
        """
        assert TYPEVECTOR == self.w
        return Vector(1.0 / self.x, 1.0 / self.y, w=self.w)

    def is_vector(self):
        """
        Returns if it is used as vector.
        """
        return (TYPEVECTOR == self.w)

    def is_point(self):
        """
        Returns if it is used as point.
        """
        return (TYPEPOINT == self.w)

    def __str__(self):
        """
        String representation of the vector.
        """
        # todo: nicer format for vectors
        template = "<{0}[{1}, {2}, w={3}]>"
        return template.format(self.__class__.__name__, self.x, self.y, self.w)

    def __repr__(self):
        """
        Representation of the vector using __repr__ everywhere.
        """
        template = "<{0}[{1}, {2}, w={3}] object at {4}>"
        return template.format(self.__class__.__name__, 
                               repr(self.x), 
                               repr(self.y), 
                               self.w, 
                               hex(id(self)))

Vector.position = Vector(0, 0, w=TYPEVECTOR)
Vector.position.w = TYPEPOINT

Vec = Vector

def Point(x=0.0, y=0.0, position=None):
    """
    Returns a vector instance configured as TYPEPOINT.
    
    :Parameters:
        x[0.0] : 
            x component of vector
        y[0.0] :
            y component of vector
        position[None] : Vector
            the position of the vector
    """
    return Vec(x, y, w=TYPEPOINT, position=position)


class Camera(object):
    """
    The camera class used to determine the visual area in the world and on
    screen.
    """

    use_conversion_methods = False
    padding = 50

    def __init__(self, screen_rect, position=None, padding=None):
        """
        :Parameters:
            
            screen_rect : pygame.Rect
                The screen area in screen coordinates
            position[None] : Vector
                Position in world coordinates
            padding[None] : int
                Padding in world coordinates, it defaults to a 50 wide border 
        """
        # viewport
        self._screen_rect = None
        self.offset = Vec()
        self.rect = screen_rect

        if padding:
            self.padding = padding

        # position
        self._position = Point()
        self.old_position = Point()
        if position:
            assert position.w == TYPEPOINT
            self.position = position
            self.old_position = self.position.copy()

        self.tracker = None

    @property
    def track(self):
        """
        Returns the tracked object in the world. The tracked object
        only needs a position attribute returning a Vector.
        """
        return self.tracker

    @track.setter
    def track(self, obj):
        """
        Set the object of the world to be tracked.
        """
        self.tracker = obj

    def is_tracking(self):
        """
        Returns true if the camera is tracking an object.
        """
        return (self.tracker is not None)

    @property
    def position(self):
        """
        The position of the camera in world coordinates.
        """
        if self.tracker:
            self.old_position = self._position
            self._position = self.tracker.position
        return self._position

    @position.setter
    def position(self, pos):
        """
        Set the position the cam should center on in world coordinates. Resets
        the tracking object to None.s
        """
        self.tracker = None
        self.old_position = self._position
        self._position = pos

    @property
    def rect(self):
        """
        Returns a copy of the screen rect in screen coordinates.
        """
        return pygame.Rect(self._screen_rect)

    @rect.setter
    def rect(self, value):
        """
        Set the screen rect in screen coordinates.
        """
        self._screen_rect = value
        self.offset = Vec(-self._screen_rect.w / 2 - value.left, 
                           -self._screen_rect.h / 2 - value.top)

    @property
    def world_rect(self):
        """
        world_rect in world coordinates. Use attribute 'rect' for a rect in
        screen coordinates.  This is the visible area of the world.
        """
        border = 2 * self.padding
        world_rect = self._screen_rect.inflate(border, border)
        # rect.center = (self._position.x, self._position.y)
        world_rect.center = self._position()
        return world_rect

    def world_to_screen(self, world_pos, parallax_factors=Vec(1.0, 1.0), offset=Vec()):
        """
        Converts world to screen coordinates.
        
        :Parameters:
            world_pos : Vector
                world coordinates to convert
            parallax_factors : Vector
                The parallax factor to use during the conversion
            offset[Vector(0, 0)] : Vector
                offset in screen coordinates, used for the sprite offset
                
        :Returns:
            The screen coordinates as a Vector.
        """
        # todo: interpolation factor here also?
        # return world_pos - self._position % parallax_factors - self.offset - offset
        return Vec(world_pos.x - self._position.x * parallax_factors.x - self.offset.x - offset.x,
                   world_pos.y - self._position.y * parallax_factors.y - self.offset.y - offset.y)

    def screen_to_world(self, screen_pos, parallax_factors=Vec(1.0, 1.0), offset=Vec()):
        """
        Converts a screen coordinate to world coordinate.
        
        :Parameters:
            screen_pos : Vector
                screen coordinates to convert
            parallax_factors : Vector
                The parallax factor to use during the conversion
            offset[Vector(0, 0)] : Vector
                offset in screen coordinates, used for the sprite offset
                
        :Returns:
            The world coordinates as a Vector.
        """
        # return screen_pos  + offset + self.offset + self._position % parallax_factors
        return Vec(screen_pos.x  + offset.x + self.offset.x + self._position.x * parallax_factors.x,
                   screen_pos.y  + offset.y + self.offset.y + self._position.y * parallax_factors.y)

class DefaultRenderer(object):
    """
    The base rendering class. Its only purpose is to hold a list of sprites and
    render them onto the screen. By doing so the sprites rect attribute is
    updated to reflect the screen coordinate.
    
    :note: invisible sprites are not rendered and therefore its rect attribute is
    not updated.
    """

    def __init__(self):
        """
        Constructor.
        """
        self._sprites = []
        self._sprite_stack = []
        self.need_sort = True
        self.draw = self._draw_sort
        
    @property
    def need_sort(self):
        """
        Returns True if re-sorting in the next call to draw.
        """
        return (self.draw == self._draw_sort)
        
    @need_sort.setter
    def need_sort(self, value):
        """
        Set this flag to True to force a re-sort of sprites orders.
        """
        if value:
            self.draw = self._draw_sort

    def add_sprite(self, spr):
        """
        Add a single sprite. Only visible sprites are added (as soon the
        visibility attribute is set on the sprite it will be added too).
        """
        if spr.is_visible and spr not in self._sprites:
            self._sprites.append(spr)
            # todo: if the sprites have the same z_layer then this might cause flimmer
            # self._sprites = list(set(self._sprites)) # filter double sprites
            # self.need_sort = True
            self.draw = self._draw_sort

    def add_sprites(self, new_sprites):
        """
        Add multiple sprites at once. Only the visible sprites are added ( as
        soon the visibility attribute is set on the sprite it will be added too).
        
        :Parameters:
            new_sprites : list, iterator
                any iterable containing sprites
        """
        # todo: performance
        self._sprites.extend([spr for spr in new_sprites if spr.is_visible and spr not in self._sprites])
        # self._sprites = list(set(self._sprites)) # filter double sprites
        # self.need_sort = True
        self.draw = self._draw_sort

    def remove_sprite(self, spr):
        """
        Remove the given sprite. 
        
        :Parameters:
            spr : Sprite
                the sprite to remove
        
        :note: If you set the visible attribute of a sprite to True again, then
        it will be added again.
        
        """
        try:
            self._sprites.remove(spr)
        except ValueError:
            pass

    def clear(self):
        """
        Remove all sprites at once.
        """
        self._sprites = []

    def push_sprites(self, new_sprites):
        """
        Push the current sprites onto the internal stack and add the new sprites.
        """
        self._sprite_stack.append(self._sprites)
        self.clear()
        self.add_sprites(new_sprites)

    def pop_sprites(self):
        """
        Clear the current sprites and pop the internal sprite stack back as
        active sprites.
        
        :Returns:
            the currently active sprites that are removed
        """
        old_sprites = []
        if self._sprite_stack:
            old_sprites = self._sprites
            self._sprites = self._sprite_stack.pop(-1)
        else:
            self.clear()
        return old_sprites

    def get_sprites(self):
        """
        Returns a list with all currently drawn sprites.
        """
        return list(self._sprites)

    # only used for documentation!
    def draw(self, surf, cam, fill_color=None, do_flip=False, interpolation_factor=1.0):
        """
        Draws all currently visible sprites and updates theis rect attribute to
        reflect their screen position.
        
        :Parameters:
            surf : Surface
                the surface to render onto
            cam : Camera
                the camera to use to render (for scrolling and viewport)
            fill_color[None] : tuple
                if set to a rgb tuple then the area given by the cam will be
                filled with it on the given surface
            do_flip[False] : bool
                if set to True, do a display flip at the end of rendering
            interpolation_factor[1.0] : float
                the interpolation factor to use, should be in the range [0, 1.0),
                other values might work too but the result might be unwanted
        
        """
        pass
        
    def _draw_sort(self, surf, cam, fill_color=None, do_flip=False, interpolation_factor=1.0):
        """
        Special, internal method to first sort before drawing the sprites.
        
        For arguments description see draw()
        
        """
        # if self.need_sort:
        self._sprites.sort(key = lambda e: e.internal_z)
        # self.need_sort = False
        self.draw = self._draw
        self._draw(surf, cam, fill_color, do_flip, interpolation_factor)

    def _draw(self, surf, cam, fill_color=None, do_flip=False, interpolation_factor=1.0):
        """
        Draws all currently visible sprites and updates theis rect attribute to
        reflect their screen position.
        
        For arguments description see draw()
        
        """

        surf.set_clip(cam.rect)

        if fill_color is not None:
            surf.fill(fill_color)

        surf_blit = surf.blit

        if cam.use_conversion_methods:
            camera_world_to_screen = cam.world_to_screen
            for spr in self._sprites:
                # if spr.is_visible: # no need for this because self._sprites contains only visible sprites
                if spr.draw_special:
                    spr.rect = spr.draw(surf, cam, interpolation_factor)
                    assert spr.rect is not None
                else:
                    spr.rect.center = camera_world_to_screen(spr.position, spr.parallax_factors, spr.offset)()
                    surf_blit(spr.image, spr.rect, spr.area, spr.surf_flags)
        else:
            camera_offset_x = cam.offset.x
            camera_offset_y = cam.offset.y

            if 1.0 == interpolation_factor:
                camera_position_x = cam.position.x
                camera_position_y = cam.position.y
                for spr in self._sprites:
                    # if spr.is_visible: # no need for this because self._sprites contains only visible sprites
                    if spr.draw_special:
                        spr.rect = spr.draw(surf, cam, interpolation_factor)
                        assert spr.rect is not None
                    else:
                        assert spr.position.w == TYPEPOINT, \
                                "sprite possition should be a point " + str(spr.position)
                        # previousState + interpolation_factor * (currentState - previousState)
                        spr.rect.centerx = spr.position.x - camera_offset_x - \
                                                        camera_position_x * spr.parallax_factors.x - spr.offset.x
                        spr.rect.centery = spr.position.y - camera_offset_y - \
                                                        camera_position_y * spr.parallax_factors.y - spr.offset.y

                        surf_blit(spr.image, spr.rect, spr.area, spr.surf_flags)
            else:
                camera_position_x = cam.old_position.x + interpolation_factor * (cam.position.x - cam.old_position.x)
                camera_position_y = cam.old_position.y + interpolation_factor * (cam.position.y - cam.old_position.y)
                for spr in self._sprites:
                    # if spr.is_visible: # no need for this because self._sprites contains only visible sprites
                    if spr.draw_special:
                        spr.rect = spr.draw(surf, cam, interpolation_factor)
                        assert spr.rect is not None
                    else:
                        assert spr.position.w == TYPEPOINT, \
                                "sprite possition should be a point " + str(spr.position)
                        # previousState + interpolation_factor * (currentState - previousState)
                        spr_pos_x = spr.old_position.x + \
                                        interpolation_factor * (spr.position.x - spr.old_position.x)
                        spr_pos_y = spr.old_position.y + \
                                        interpolation_factor * (spr.position.y - spr.old_position.y)

                        spr.rect.centerx = spr_pos_x - camera_offset_x - \
                                                        camera_position_x * spr.parallax_factors.x - spr.offset.x
                        spr.rect.centery = spr_pos_y - camera_offset_y - \
                                                        camera_position_y * spr.parallax_factors.y - spr.offset.y

                        surf_blit(spr.image, spr.rect, spr.area, spr.surf_flags)

        surf.set_clip(None)
        if do_flip:
            pygame.display.flip()

    # def clean(self, cameras):
        # indices = set()
        # for cam in cameras:
            # indices.update(cam.rect.collidelistall(self._sprites))
        # self._sprites = [self._sprites[idx] for idx in indices]
        # self.need_sort = True

    # def get_off_cameras_sprites(self, cameras):
        # # todo
        # pass

    # todo: how to pick invisible sprites?
    def get_sprites_in_rect(self, screen_rect, do_reverse=True):
        """
        Get the colliding sprites in the given rect in screen coordinates. Using
        the do_reverse argument the sort order of the sprites can be reversed. By
        default the first sprites it the topmost.
        
        :note: only visible sprites are checked (because the rect attribute of
        invisible sprites is not updated
                
        :Parameters:
            screen_rect : Rect
                rect in screen coordinates used to determine colliding sprites
            do_reverse[True] : bool
                if True then the first sprites is the topmost, otherwise its the
                last one.
        """
        indices = screen_rect.collidelistall(self._sprites)
        if do_reverse:
            return [self._sprites[idx] for idx in reversed(indices)]
        else:
            return [self._sprites[idx] for idx in indices]


class HudRenderer(DefaultRenderer):
    """
    This is a simple renderer that does not respect scrolling (the cameras
    position is ignored).
    """

    def __init__(self):
        """
        Constructor.
        """
        DefaultRenderer.__init__(self)
        self.draw = self._draw

    def _draw(self, surf, cam, fill_color=None, do_flip=False, interpolation_factor=1.0):
        """
        See DefaultRenderer.draw() for documentation.
        """
        if self.need_sort:
            self._sprites.sort(key = lambda e: e.internal_z)
            self.need_sort = False

        surf.set_clip(cam.rect)
        if fill_color is not None:
            surf.fill(fill_color)

        surf_blit = surf.blit

        for spr in self._sprites:
            if spr.draw_special:
                spr.rect = spr.draw(surf, cam, interpolation_factor)
                assert spr.rect is not None
            else:
                assert spr.position.w == TYPEPOINT, \
                            "sprite possition should be a point " + str(spr.position)

                spr.rect.centerx = spr.position.x - spr.offset.x
                spr.rect.centery = spr.position.y - spr.offset.y

                surf_blit(spr.image, spr.rect, spr.area, spr.surf_flags)

        surf.set_clip(None)
        if do_flip:
            pygame.display.flip()


class Sprite(object):
    """
    The sprite class. A sprite mainly stores following attributes:
        
        - position in world coordinates
        - image
        - rotation
        - flip (x- and y-axis)
        - zoom
        - rect in screen coordinates (position on screen used in the blit method,
          see note)
        - anchor 
        - (source-) area (for the blit method)
        - surf_flags (for the blit method)
        - parallax_factors
        - visible (see note)
        - renderer (see note about visible, a sprite can only be associated with
          one renderer only)
        - z_layer
        - old_position (for interpolation only, see note)
        
    :note: setting the visible attribute to True will add this sprite to the
    renderer saved in the renderer attribute, setting it to False will remove it
    from the renderer.  :note: the rect attribute will only be updated if the
    sprite is visible.  :note: if using interpolation when rendering then the
    update logic of the game should take care to set the old_position too
    additionally to setting the position
        
    The sprite class uses a image cache to cache images to avoid doing image
    transformations in each frame. This works best if many sprites share the same
    image and a discrete set of angle and scale factors are used. For this
    reasong there is also a rotation precision and zoom precision which
    determines how many digits for a angle will be used. The number of cached
    images is limited (to limit memory usage). When this limit is reached the
    cache is cleared. This limit can be customized.The image cache can also be
    disabled completely.
        
    """
    
    renderer = DefaultRenderer()
    area = None
    surf_flags = 0
    draw_special = False 
    # todo: how to implement alpha transparency?
    # alpha = 255

    # how many digites after point to round angle to, 
    # e.g. 0 means 1 degree precision, 1 means 0.1 degree precision
    rotation_precision = 0
    zoom_precision = 2
    # max number of entries before cache will be cleared
    max_cache_entry_count = 1000
    use_image_cache = False
    image_cache = {}
    
    # following attributes are used internally by the renderer
    # for performance reasons they are public, but they should
    # not be used directly
    internal_z = 0 # internal use only
    is_visible = False # internal use only
    fixed_point = 'center' # same as anchor, internal use only
    parallax_factors = Vec(1.0, 1.0)
    offset = Vec() # internal use only

    rot = 0.0 # internal use only
    flip_x = False # internal use only
    flip_y = False # internal use only
    zoom_factor = 1.0 # internal use only

    def __init__(self, image, position, anchor=None, visible=True, z_layer=None, parallax_factors=None, renderer=None):
        """
        
        :Parameters:
            image : Surface
                the image to use for that sprite, use 'set_image' to change the
                image later and do not set the image attribute directly (its
                because of the transformations like rotation and zoom)
            position : Vector
                the position of the entitiy in world coordinates
            anchor['center'] : rect attribute name or Vector
                anchor point, defaults to 'center' but can be one of following:
                topleft, midtop, topright, midright, bottomright, midbottom,
                bottomleft, midleft, center or a Vector (in sprite coordinates)
                defining the offset from the sprite center
            visible[True] : bool
                if set to True, then the sprite will be added ot its renderer and
                is visible
            z_layer[0] : float or int
                the layer this sprite is in, lower values is 'farther away'
            parallax_factors[Vector(1.0, 1.0)] : Vector
                a vector containin two floats, normally in the range [0.0, 1.0],
                if set to 0.0 then the sprite will not scroll (kinda attacked to
                the camera), this works good for single screen games using one
                camera (for split screen with multiple cameras this wont work
                because each screen should have its own HUD sprites, therefore
                the HUDRenderer should be used)
            renderer[DefaultRenderer] : DefaultRenderer
                the renderer that does draw this sprite to the screen
        
        """
        self.image = image
        self._image = image
        self.rect = pygame.Rect(0, 0, 0, 0)
        if renderer:
            self.renderer = renderer
        if image:
            self.rect = image.get_rect() # screen rect, updated by renderer
        if anchor:
            self.anchor = anchor
        assert position.w == TYPEPOINT, "sprite possition should be a point " + str(position)
        self.position = position
        self.old_position = self.position.copy()
        self.visible = visible
        if z_layer:
            self.z_layer = z_layer
        if parallax_factors:
            self.parallax_factors = parallax_factors

    @property
    def anchor(self):
        """
        Returns the value of the anchor, can be one of: 
            topleft, midtop, topright, midright, bottomright, midbottom,
            bottomleft, midleft, center or a Vector (in sprite coordinates)
            defining the offset from the sprite center
        """
        return self.fixed_point

    @anchor.setter
    def anchor(self, value):
        """
        Set the anchor, can be one of:
            topleft, midtop, topright, midright, bottomright, midbottom,
            bottomleft, midleft, center or a Vector (in sprite coordinates)
            defining the offset from the sprite center
        """
        self.fixed_point = value
        self._update_offset()

    @property
    def rotation(self):
        """
        Returns the rotation angle of the sprite in degrees.
        """
        return self.rot

    @rotation.setter
    def rotation(self, value):
        """
        Set the rotation angle in degrees.

        :note: the angle will be rounded into the range [0, 360)

        :note: the padding area will be filled with black, therefore a colorkey
        for black will be set, so avoid black in the original image!
        """
        if value == self.rot:
            return
        # round to 1 degree precision to get an reasonable amount of cashing values
        self.rot = round(value % 360.0, self.rotation_precision)
        self._update_offset()

    @property
    def flipped_x(self):
        """
        Return if the sprite is flipped in the x-axis.
        """
        return self.flip_x

    @flipped_x.setter
    def flipped_x(self, value):
        """
        If set to True, then it will be flipped along the x-axis.
        """
        if value == self.flip_x:
            return
        self.flip_x = value
        self._update_offset()

    @property
    def flipped_y(self):
        """
        Return if the sprite is flipped in the y-axis.
        """
        return self.flip_y

    @flipped_y.setter
    def flipped_y(self, value):
        """
        If set to True, then it will be flipped along the y-axis.
        """
        if value == self.flip_y:
            return
        self.flip_y = value
        self._update_offset()

    @property
    def zoom(self):
        """
        Returns the current zoom value (scale).
        """
        return self.zoom_factor

    @zoom.setter
    def zoom(self, value):
        """
        Set the zoom value.
        """
        if value == self.zoom_factor:
            return
        self.zoom_factor = round(value, self.zoom_precision)
        self._update_offset()

    @property
    def visible(self):
        """
        Returns if the sprite is visible.
        """
        return self.is_visible

    @visible.setter
    def visible(self, value):
        """
        Set the visibility of the sprite, if set to True it will added to the
        renderer.
        """
        if self.is_visible == value:
            return
        self.is_visible = value
        # todo:there is a problem: if a sprite is set to invisible and the renderer holds the
        # only reference, then the sprite is garbage collected
        if value:
            self.renderer.add_sprite(self)
        else:
            self.renderer.remove_sprite(self)

    @property
    def z_layer(self):
        """
        Returns the z-layer of the sprite.
        """
        return self.internal_z

    @z_layer.setter
    def z_layer(self, value):
        """
        Set the z-layer of the sprite, causes a re-sort in the renderer.
        """
        self.internal_z = value
        self.renderer.need_sort = True

    def set_renderer(self, renderer):
        """
        Exchange the current renderer of this sprite.
        
        :Parameters:
            renderer : DefaultRenderer
                an instance of DefaultRenderer (or inherited)
        """
        vis = self.visible
        if self.visible:
            self.visible = False
        self.renderer = renderer
        if vis:
            self.visible = True
            
    def set_image(self, image):
        """
        Set a different image for this sprite. Use this method to make sure that
        the sprites rect and anchor point are adjusted correctly.
        
        :Parameters:
            image : Surface
                the new image to use.
        """
        self.image = image
        self._image = image
        self.rect = self.image.get_rect(center=self.rect.center)
        self._update_offset()

    def _update_offset(self):
        """
        Update the anchor point (convert to an vector offset and transformt it
        according to the active transformations).
        """

        # todo: is there a better caching strategy???
        key = (self._image, self.rot, self.flip_x, self.flip_y, self.zoom_factor)
        if self.use_image_cache and key in self.image_cache:
            self.image = self.image_cache[key]
        else:
            if self.rot != 0 or self.zoom_factor != 1.0:
                self.image = pygame.transform.rotozoom(self._image, self.rot, self.zoom_factor)
                self.image.set_colorkey((0, 0, 0))
                self.image = pygame.transform.flip(self.image, self.flip_x, self.flip_y)
            else:
                self.image = pygame.transform.flip(self._image, self.flip_x, self.flip_y)
            self.image_cache[key] = self.image
            if len(self.image_cache) > self.max_cache_entry_count:
                self.image_cache.clear()

        self.rect = self.image.get_rect(center=self.rect.center)

        try:
            if self.rect:
                width, hight = self.rect.size
                offx, offy = getattr(pygame.Rect(0, 0, width, hight ), self.fixed_point)
                offx -= width / 2.0
                offy -= hight / 2.0
                self.offset = Vec(offx, offy)
        except TypeError as ex:
            assert isinstance(self.fixed_point, Vector), \
                        "anchor has wrong type, expected <Vector>, not " + str(type(self.fixed_point)) + \
                        " exception: " + str(ex)
            self.offset = self.fixed_point.copy()

        if self.rot != 0.0:
            self.offset.rotate_ip(self.rot)
        if self.flip_x:
            self.offset.x = -self.offset.x
        if self.flip_y:
            self.offset.y = -self.offset.y
        if self.zoom_factor != 1.0:
            self.offset = self.offset * self.zoom_factor

    def draw(self, surf, cam, interpolation_factor=1.0):
        """
        If 'draw_special' is set to True, then this method will be called from
        the renderer. Here special draw code can be implemented. All coordinate
        transformations have to be done here (simplest is to use the
        cam.world_to_screen() method). It should return a rect in screen
        coordinates that will be used for drawing and picking.
        
        :returns: rect in screen coordinates (returns a Rect(0, 0, 0, 0) by default)
        
        :Parameters:
            surf : Surface
                the surface to draw onto
            cam : Camera
                the camera that is used to render, determines the world position
                and the screen area
            interpolation_factor[1.0] : float
                the interpolation factor to use, should be in the range [0, 1.0),
                other values might work too but the result might be unwanted
        """
        return pygame.Rect(0, 0, 0, 0)


class TextSprite(Sprite):
    """
    A sprite for displaying text. It inherits from sprite and the only difference
    is that a string is provided instead of an image.
    """
    
    font = None
    antialias = 10
    color = (255, 255, 255)
    backcolor = None

    def __init__(self, text, position, font=None, antialias=None, color=None, backcolor=None, \
                                        anchor=None, visible=True, z_layer=1000, parallax_factors=None, renderer=None):
        """
        
        :Parameters:
            text : string
                the text to display
            position : Vector
                where it should be, in world coordinates
            font[pygame default font] : pygame.font.Font
                the font to use
            antialias[10] : int
                the antialias factor as for the pygame.font.Font
            color[(255, 255, 255)] : tuple
                the color for the text
            backcolor[None] : tuple
                background color for the text, it will be transparent if None is
                provided
            anchor['center'] : rect attribute name or Vector
                anchor point, defaults to 'center' but can be one of following:
                topleft, midtop, topright, midright, bottomright, midbottom,
                bottomleft, midleft, center or a Vector (in sprite coordinates)
                defining the offset from the sprite center
            visible[True] : bool
                if set to True, then the sprite will be added ot its renderer and
                is visible
            z_layer[1000] : float or int
                the layer this sprite is in, lower values is 'farther away'
            parallax_factors[Vector(1.0, 1.0)] : Vector
                a vector containin two floats, normally in the range [0.0, 1.0],
                if set to 0.0 then the sprite will not scroll (kinda attacked to
                the camera), this works good for single screen games using one
                camera (for split screen with multiple cameras this wont work
                because each screen should have its own HUD sprites, therefore
                the HUDRenderer should be used)
            renderer[DefaultRenderer] : DefaultRenderer
                the renderer that does draw this sprite to the screen
        
        """
        if self.font is None:
            TextSprite.font = pygame.font.Font(None, 20)
        if font is not None:
            self.font = font
        if antialias is not None:
            self.antialias = antialias
        if color is not None:
            self.color = color
        if backcolor is not None:
            self.backcolor = backcolor
        self._text = ""
        self.text = text
        image = self.render()
        Sprite.__init__(self, image, position, anchor=anchor, visible=visible, \
                                               z_layer=z_layer, parallax_factors=parallax_factors, renderer=renderer)

    @property
    def text(self):
        """
        Get the text.
        """
        return self._text

    @text.setter
    def text(self, value, update_offset=False):
        """
        Set the text.
        """
        self._text = value
        self.image = self.render()
        self.rect = self.image.get_rect()
        if update_offset:
            self._update_offset()

    def render(self):
        """
        Renders the text using the attributes saved onto an image and returns it.
        
        :Returns: surface with the rendered text.
        """
        if self.backcolor is None:
            img = self.font.render(self.text, self.antialias, self.color)
        else:
            img = self.font.render(self.text, self.antialias, self.color, self.backcolor)
            
        return img


class VectorSprite(Sprite):
    """
    Draws a vector sprite. The ideas was to visualize a vector. The position
    attribute of the vector will be used as starting point to draw.
    
    This class will use the special_draw ability of the renderer and call its
    draw method.  Therefore it might not be that performant.

    """


    color = (255, 255, 255)

    # @staticmethod
    # def from_vector(v, color=None, visible=True, z_layer=1000, label=None):
        # return VectorSprite(v.x, v.y, v.w, v.position, color, visible, z_layer, label)

    def __init__(self, vec, color=None, visible=True, z_layer=999, label=None, parallax_factors=None):
        """
        :Parameters:
            vec : Vector
                the vector to draw
            color[(255, 255, 255)] : tuple
                the color to draw the vector
            visible[True] : bool
                if this sprite is visible
            z_layer[999] : float
                the layer this vector will be drawn
            label[None] : TextSprite
                the text to draw near the vector, for a vector the label.position
                is relative to the vector.position, if the vector is a point then
                the label.position is relative to the vector
        """
        self.vector = vec
        Sprite.__init__(self, None, self.vector.position, visible=visible, \
                                                    z_layer=z_layer, parallax_factors=parallax_factors)
        if color is not None:
            self.color = color
        self.draw_special = True
        self.label = label
        if label:
            if self.vector.w == TYPEPOINT:
                self.label_offset = self.label.position - self.vector.position
                self.label.position = self.vector + self.label_offset
            else:
                self.label.position = self.vector.position + (self.label.position - Point())

    def draw(self, surf, cam, interpolation_factor=1.0):
        """
        Draws this vector.
        
        :Parameters:
            surf : Surface
                the surface to draw the vector on
            cam : Camera
                the cam to use to draw
            interpolation_factor[1.0] : float
                the interpolation factor to use, should be in the range [0, 1.0),
                other values might work too but the result might be unwanted
        
        """
        if self.vector.w == TYPEVECTOR:
            wpos = cam.world_to_screen(self.vector.position)
            pointlist = []
            pointlist.append(wpos())
            tip = wpos + self.vector
            pointlist.append(tip())
            pointlist.append((wpos + self.vector * 0.75 + self.vector.rotate(90) * 0.125 )())
            pointlist.append((wpos + 0.75 * self.vector - 0.125 * self.vector.rotate(90))())
            pointlist.append(tip())

            self.rect = pygame.draw.aalines(surf, self.color, False, pointlist)
        else:
            vpos = cam.world_to_screen(self.vector)
            # self.rect = pygame.draw.circle(surf, self.color, (int(vpos.x), int(vpos.y)), 2)
            surf.set_at(vpos(int), self.color)
            self.rect = pygame.Rect(vpos(int), (1, 1))
        return self.rect



if __name__ == '__main__':

    import random

    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    SCREENSIZE = (800, 600)

    def random_rgb():
        return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

    def invert_color(col):
        return (255 - col[0], 255 - col[1], 255 - col[2], col[3] if len(col) == 4 else 255)

    def create_arrows_sprites():
        # font = pygame.font.Font(None, 12)
        sprites = [
            VectorSprite(Vec(20, 0), color=(255,0,0,128)),
            # TextSprite("x", Vec(20, 10), font=font, color=(255,0,0,128)),
            VectorSprite(Vec(0, 20), color=(0,255,0,128)),
            # TextSprite("y", Vec(-10, 20), font=font, color=(0,255,0,128)),
            ]
        return sprites

    def create_random_surf(col):
        surf = pygame.Surface((random.randint(5, 100), random.randint(5, 100)))
        surf.fill(col)
        return surf

    class BallEnt(Sprite):

        def __init__(self, pos, velo, image=None):
            self.vel = velo
            # def __init__(self, image, position, anchor=None, visible=True, z_layer=None, parallax_factors=None):
            if image is None:
                col = random.choice(list(pygame.color.THECOLORS.values()))
                Sprite.__init__(self, create_random_surf(col), pos, anchor="center")
            else:
                Sprite.__init__(self, image, pos, anchor="center")
                
        def update(self, dt):
            self.old_position.x = self.position.x
            self.old_position.y = self.position.y
            self.position.x = self.position.x  + self.vel.x * dt
            self.position.y = self.position.y  + self.vel.y * dt

            if self.position.x > SCREENSIZE[0]:
                self.position.x = SCREENSIZE[0]
                self.vel.x = -self.vel.x
            if self.position.x < 0:
                self.position.x = 0
                self.vel.x = -self.vel.x

            if self.position.y > SCREENSIZE[1]:
                self.position.y = SCREENSIZE[1]
                self.vel.y = -self.vel.y
            if self.position.y < 0:
                self.position.y = 0
                self.vel.y = -self.vel.y

    class BallEntExt(BallEnt):
    
        def __init__(self, pos, velo):
            BallEnt.__init__(self, pos, velo)
            self.rotation = random.randint(0, 360)
            self.zoom = random.random() * 2 + 0.1
            self.zoom_change = random.random() * 0.0051
            self.rot_speed = (random.random() * 2 - 1) * 0.05
            
        def update(self, dt):
        
            self.rotation = self.rotation + self.rot_speed * dt
            self.zoom = self.zoom + self.zoom_change * dt
            if self.zoom > 2.0:
                self.zoom_change *= -1
                self.zoom = 2.0
            if self.zoom <= 0:
                self.zoom_change *= -1
                self.zoom = 0.1
        
            BallEnt.update(self, dt)


    def demo_interpolation(screen):
        create_arrows_sprites()

        num = 50
        balls = []
        balls2 = []
        renderer2 = DefaultRenderer()
        for i in range(num):
            pos = Point(random.randint(0, SCREENSIZE[0]), random.randint(0, SCREENSIZE[1]))
            vel = Vector(random.randint(-5, 5), random.randint(-5, 5)) * 0.1
            balls.append(BallEnt(pos, vel))
            ent = BallEnt(pos.copy(), vel.copy())
            ent.set_image(balls[-1]._image.copy())
            ent.set_renderer(renderer2)
            balls2.append(ent)
        for y in range(0, 500, 20):
            for x in range(0, 500, 20):
                # pos = Point(random.randint(0, SCREENSIZE[0]), random.randint(0, SCREENSIZE[1]))
                pos = Point(x, y)
                spr1 = Sprite(create_random_surf(random_rgb()), pos, z_layer=-1)
                spr = Sprite(spr1.image, pos, z_layer=-1)
                spr.set_renderer(renderer2)

        renderer = Sprite.renderer
        hud_renderer = HudRenderer()
        screen_rect = screen.get_rect()
        cx, cy = screen_rect.center

        tspr = TextSprite("use arrow keys to move", Point(cx, SCREENSIZE[1] - 50), color=WHITE, \
                                                z_layer=1000, anchor='center', parallax_factors=Vec(0.0, 0.0))
        tspr.set_renderer(hud_renderer)
        tspr = TextSprite("interpolated", Point(50, SCREENSIZE[1] - 50), color=WHITE, \
                                                z_layer=1000, anchor='midleft', parallax_factors=Vec(0.0, 0.0))
        tspr.set_renderer(hud_renderer)
        tspr = TextSprite("ordinary dt update", Point(SCREENSIZE[0] - 50, SCREENSIZE[1] - 50), color=WHITE, \
                                                z_layer=1000, anchor='midright', parallax_factors=Vec(0.0, 0.0))
        tspr.set_renderer(hud_renderer)

        cam_hud = Camera(pygame.Rect((0, 0), screen_rect.size) , position=Point())
        cam1 = Camera(pygame.Rect((0, 0), screen_rect.midbottom).inflate(-5, -5) , position=Point(cx, cy))
        cam2 = Camera(pygame.Rect(screen_rect.midtop, screen_rect.midbottom).inflate(-5, -5) , position=Point(cx, cy))
        # # # cams = [cam1, cam2]

        running = True
        clock = pygame.time.Clock()
        step_time = 10.0 # 100 fps
        accumulator = 0
        while running:
            dto = clock.tick(20)# * random.random()
            dt = dto
            if dt > 20:
                dt = 20
            
            # interpolated update
            accumulator += dt
            while accumulator >= step_time:
            
                for ball in balls:
                    ball.update(step_time)
                    
                accumulator -= step_time
                
            alpha = accumulator / step_time
            
            # not interpolated updated, just ordinary dt update
            for ball in balls2:
                ball.update(dt)

            # render
            screen.fill((255, 00, 00))
            renderer.draw(screen, cam1, fill_color=BLACK, interpolation_factor=alpha)
            renderer2.draw(screen, cam2, fill_color=BLACK)
            hud_renderer.draw(screen, cam_hud, fill_color=None)
            pygame.display.flip()

            # event handling
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    elif event.key == pygame.K_c:
                        # for cam in cams:
                        cam1.use_conversion_methods = not cam1.use_conversion_methods
                        cam2.use_conversion_methods = not cam2.use_conversion_methods
                        cam_hud.use_conversion_methods = not cam_hud.use_conversion_methods
                        print("cam.use_conversion_methods", cam1.use_conversion_methods)
                    elif event.key == pygame.K_F2:
                        print(clock.get_fps())
                elif event.type == pygame.QUIT:
                    return
            # move cams
            pressed = pygame.key.get_pressed()
            dir = Vec()
            if pressed[pygame.K_RIGHT]:
                dir += Vec(1, 0)
            if pressed[pygame.K_LEFT]:
                dir -= Vec(1, 0)
            if pressed[pygame.K_UP]:
                dir += Vec(0, -1)
            if pressed[pygame.K_DOWN]:
                dir += Vec(0, 1)
            dir.length = 5
            cam1.position += dir
            cam2.position += dir
 

    def demo_viewport(screen):
        create_arrows_sprites()

        num = 200
        for i in range(num):
            col = random.choice(list(pygame.color.THECOLORS.values()))
            surf = create_random_surf(col)
            pos = Point(random.randint(-390, 390), random.randint(-290, 290))
            spr = Sprite(surf, pos, z_layer=100, anchor='center')

        cam = Camera(pygame.Rect(350, 250, 100, 100))
        cam.use_conversion_methods = False
        running = True
        clock = pygame.time.Clock()
        while running:
            clock.tick(50)
            screen.fill(BLACK)
            Sprite.renderer.draw(screen, cam, do_flip=True)
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    elif event.key == pygame.K_c:
                        cam.use_conversion_methods = not cam.use_conversion_methods
                        print("cam.use_conversion_methods", cam.use_conversion_methods)
                    elif event.key == pygame.K_F2:
                        print(clock.get_fps())
                elif event.type == pygame.QUIT:
                    return

            pressed = pygame.key.get_pressed()
            direction = Vec()
            if pressed[pygame.K_RIGHT]:
                direction += Vec(1, 0)
            if pressed[pygame.K_LEFT]:
                direction -= Vec(1, 0)
            if pressed[pygame.K_UP]:
                direction += Vec(0, -1)
            if pressed[pygame.K_DOWN]:
                direction += Vec(0, 1)
            direction.length = 2
            # round is needed because the vieport rect only can handle integer coordinates!!
            # otherwise strange roundin error effects occure
            direction.round_ip(int)
            crect = cam.rect
            cam.position = cam.position + direction
            cam.rect = pygame.Rect((crect.left + direction.x, crect.top + direction.y), crect.size)
    
    def demo_sprite_performance(screen):
        create_arrows_sprites()

        num = 10
        balls = []
        for i in range(num):
            pos = Point(random.randint(0, SCREENSIZE[0]), random.randint(0, SCREENSIZE[1]))
            vel = Vector(random.randint(-5, 5), random.randint(-5, 5)) * 0.05
            balls.append(BallEnt(pos, vel))
        text = TextSprite("fps: ", Point(200, 250), color=(255, 255, 0), \
                                            z_layer=10000, anchor='center', parallax_factors=Vec(0.0, 0.0))

        cam = Camera(screen.get_rect(), position=Point(400, 300))

        running = True
        clock = pygame.time.Clock()
        time = 0
        while running:
            dt = clock.tick(50)
            time += dt
            if time > 1:
                time = 0
                fps = clock.get_fps()
                if fps < 20:
                    x = balls.pop()
                    x.visible = False
                if fps > 21:
                    pos = Point(random.randint(0, SCREENSIZE[0]), random.randint(0, SCREENSIZE[1]))
                    vel = Vector(random.randint(-5, 5), random.randint(-5, 5)) * 0.05
                    ball = BallEnt(pos, vel)
                    balls.append(ball)
                text.text = "fps: " + str(round(clock.get_fps(), 2)) + "    count: " + str(len(balls))
            Sprite.renderer.draw(screen, cam, fill_color=BLACK, do_flip=True)
            
            for ball in balls:
                ball.update(dt)

            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    elif event.key == pygame.K_c:
                        cam.use_conversion_methods = not cam.use_conversion_methods
                        print("cam.use_conversion_methods", cam.use_conversion_methods)
                    elif event.key == pygame.K_F2:
                        print(clock.get_fps())
                elif event.type == pygame.QUIT:
                    return

    
    def demo_transformation_performance(screen):
        create_arrows_sprites()

        num = 10
        balls = []
        for i in range(num):
            pos = Point(random.randint(0, SCREENSIZE[0]), random.randint(0, SCREENSIZE[1]))
            vel = Vector(random.randint(-5, 5), random.randint(-5, 5)) * 0.051
            balls.append(BallEntExt(pos, vel))
        text = TextSprite("fps: ", Point(200, 250), color=(255, 255, 0), \
                                                        z_layer=10000, anchor='center', parallax_factors=Vec(0.0, 0.0))

        cam = Camera(screen.get_rect(), position=Point(400, 300))

        running = True
        clock = pygame.time.Clock()
        time = 0
        while running:
            dt = clock.tick(50)
            time += dt
            if time > 1:
                time = 0
                fps = clock.get_fps()
                if fps < 20:
                    if len(balls) > 1:
                        x = balls.pop()
                        x.visible = False
                if fps > 25:
                    pos = Point(random.randint(0, SCREENSIZE[0]), random.randint(0, SCREENSIZE[1]))
                    vel = Vector(random.randint(-5, 5), random.randint(-5, 5)) * 0.051
                    ball = BallEntExt(pos, vel)
                    ball.z_layer = len(balls) + 1
                    balls.append(ball)
                text.text = "fps: " + str(round(clock.get_fps())) + "    count: " + str(len(balls))
            Sprite.renderer.draw(screen, cam, fill_color=BLACK, do_flip=True)

            for ball in balls:
                ball.update(dt)

            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    elif event.key == pygame.K_c:
                        cam.use_conversion_methods = not cam.use_conversion_methods
                        print("cam.use_conversion_methods", cam.use_conversion_methods)
                    elif event.key == pygame.K_F2:
                        print(clock.get_fps())
                elif event.type == pygame.QUIT:
                    return


    def demo_split_screen(screen):
        create_arrows_sprites()

        num = 20
        balls = []
        for i in range(num):
            pos = Point(random.randint(0, SCREENSIZE[0]), random.randint(0, SCREENSIZE[1]))
            vel = Vector(random.randint(-5, 5), random.randint(-5, 5)) * 0.05
            balls.append(BallEnt(pos, vel))
        for i in range(int(num)):
            pos = Point(random.randint(0, SCREENSIZE[0]), random.randint(0, SCREENSIZE[1]))
            spr = Sprite(create_random_surf(WHITE), pos)

        hud_renderer = HudRenderer()

        tspr = TextSprite("use A,S,W,D to move", Point(200, 50), color=WHITE, \
                                                z_layer=1000, anchor='center', parallax_factors=Vec(0.0, 0.0))
        tspr.set_renderer(hud_renderer)
        tspr = TextSprite("use arrow keys to move", Point(600, 50), color=WHITE, \
                                                z_layer=1000, anchor='center', parallax_factors=Vec(0.0, 0.0))
        tspr.set_renderer(hud_renderer)

        screen_rect = screen.get_rect()
        cam1 = Camera(pygame.Rect((0, 0), screen_rect.midbottom).inflate(-5, -5) , position=Point())
        cam2 = Camera(pygame.Rect(screen_rect.midtop, screen_rect.midbottom).inflate(-5, -5) , position=Point())
        cams = [cam1, cam2]
        renderer = Sprite.renderer

        running = True
        clock = pygame.time.Clock()
        while running:
            dt = clock.tick(50)
            screen.fill((255, 00, 00))
            for cam in cams:
                renderer.draw(screen, cam, fill_color=BLACK, do_flip=False)
                hud_renderer.draw(screen, cam, fill_color=None, do_flip=False)
            pygame.display.flip()

            for ball in balls:
                ball.update(dt)

            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    elif event.key == pygame.K_c:
                        for cam in cams:
                            cam.use_conversion_methods = not cam.use_conversion_methods
                        print("cam.use_conversion_methods", cam.use_conversion_methods)
                    elif event.key == pygame.K_F2:
                        print(clock.get_fps())
                elif event.type == pygame.QUIT:
                    return
                    
            # move the cameras positions
            pressed = pygame.key.get_pressed()
            direction = Vec()
            if pressed[pygame.K_RIGHT]:
                direction += Vec(1, 0)
            if pressed[pygame.K_LEFT]:
                direction -= Vec(1, 0)
            if pressed[pygame.K_UP]:
                direction += Vec(0, -1)
            if pressed[pygame.K_DOWN]:
                direction += Vec(0, 1)
            direction.length = 5
            cam2.position += direction
            
            # move other cam
            direction = Vec()
            if pressed[pygame.K_d]:
                direction += Vec(1, 0)
            if pressed[pygame.K_a]:
                direction -= Vec(1, 0)
            if pressed[pygame.K_w]:
                direction += Vec(0, -1)
            if pressed[pygame.K_s]:
                direction += Vec(0, 1)
            direction.length = 5
            cam1.position += direction


    def demo_cam_tracking(screen):
        create_arrows_sprites()

        num = 20
        balls = []
        for i in range(num):
            pos = Point(random.randint(0, SCREENSIZE[0]), random.randint(0, SCREENSIZE[1]))
            vel = Vector(random.randint(-5, 5), random.randint(-5, 5)) * 0.01
            balls.append(BallEnt(pos, vel))
        col = random_rgb()
        for i in range(int(num)):
            pos = Point(random.randint(0, SCREENSIZE[0]), random.randint(0, SCREENSIZE[1]))
            spr = Sprite(create_random_surf(col), pos)


        TextSprite("use mouse to select a rect to track", Point(0, 0), color=WHITE, \
                                                        z_layer=1000, anchor='center', parallax_factors=Vec(0.0, 0.0))

        cam = Camera(screen.get_rect(), position=Point(400, 300))

        running = True
        clock = pygame.time.Clock()
        while running:
            dt = clock.tick(50)
            Sprite.renderer.draw(screen, cam, fill_color=BLACK, do_flip=True)

            for ball in balls:
                ball.update(dt)

            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    elif event.key == pygame.K_c:
                        cam.use_conversion_methods = not cam.use_conversion_methods
                        print("cam.use_conversion_methods", cam.use_conversion_methods)
                    elif event.key == pygame.K_F2:
                        print(clock.get_fps())
                elif event.type == pygame.QUIT:
                    return
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        selection_rect = pygame.Rect(pygame.mouse.get_pos(), (1, 1))
                        marked = Sprite.renderer.get_sprites_in_rect(selection_rect)
                        if marked:
                            cam.track = marked[0]
                        else:
                            mx, my = event.pos
                            cam.position = cam.screen_to_world(Vec(mx, my))


    def demo_mouse_select(screen):
        create_arrows_sprites()

        num = 200
        balls = []
        for i in range(num):
            pos = Point(random.randint(0, SCREENSIZE[0]), random.randint(0, SCREENSIZE[1]))
            vel = Vector(random.randint(-5, 5), random.randint(-5, 5)) * 0.01
            balls.append(BallEnt(pos, vel))
        TextSprite("use mouse buttons to resize selection rect", Point(50, SCREENSIZE[1] - 50), color=WHITE, \
                                                                                        z_layer=10000, anchor='topleft')

        selection_rect = pygame.Rect(pygame.mouse.get_pos(), (50, 50))
        cam = Camera(screen.get_rect(), position=Point(400, 300))
        running = True
        clock = pygame.time.Clock()
        while running:
            dt = clock.tick(50)
            Sprite.renderer.draw(screen, cam, fill_color=BLACK, do_flip=False)
            marked = Sprite.renderer.get_sprites_in_rect(selection_rect, False)
            for idx, mark in enumerate(marked):
                pygame.draw.rect(screen, (max((idx + 1) * 255/len(marked), 0), 0, 0, 100), mark.rect)
            pygame.draw.rect(screen, (255, 255, 0, 100), selection_rect, 1)
            pygame.display.flip()

            for ball in balls:
                ball.update(dt)

            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    elif event.key == pygame.K_c:
                        cam.use_conversion_methods = not cam.use_conversion_methods
                        print("cam.use_conversion_methods", cam.use_conversion_methods)
                    elif event.key == pygame.K_F2:
                        print(clock.get_fps())
                elif event.type == pygame.QUIT:
                    return
                elif event.type == pygame.MOUSEMOTION:
                    selection_rect.center = pygame.mouse.get_pos()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        selection_rect.inflate_ip(20, 20)
                    else:
                        if selection_rect.size[0] > 20 and selection_rect.size[1] > 20: 
                            selection_rect.inflate_ip(-20, -20)

    class Markable(Sprite):
        marked = False
        color = None
        def on_click(self):
            if self.marked:
                self.marked = False
                self.image.fill(self.color)
            else:
                self.marked = True
                self.color = self.image.get_at((0,0))
                layer = self.z_layer if self.z_layer <= 1.0 else 1
                layer = layer if layer > 0 else 0.1
                self.image.fill((50 + 200 * layer, 50 + 200 * layer, 0))
                        
    def demo_parallax_select(screen):
        create_arrows_sprites()

        num = 200.0
        for i in range(int(num)):
            col = random.choice(list(pygame.color.THECOLORS.values()))
            surf = create_random_surf(col)
            factors = Vec(i/num, i/num)
            z_layer = i/num
            if z_layer < 0.02:
                z_layer = 1000
                factors = Vec(0.0, 0.0)
            pos = Point(random.randint(-390, 390), random.randint(-290, 290))
            spr = Markable(surf, pos, z_layer=z_layer, parallax_factors=factors, anchor='center')

        selection_rect = pygame.Rect(0, 0, 1, 1)
        cam = Camera(screen.get_rect())
        cam.use_conversion_methods = False
        running = True
        clock = pygame.time.Clock()
        while running:
            clock.tick()
            Sprite.renderer.draw(screen, cam, fill_color=BLACK, do_flip=True)
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    elif event.key == pygame.K_c:
                        cam.use_conversion_methods = not cam.use_conversion_methods
                        print("cam.use_conversion_methods", cam.use_conversion_methods)
                    elif event.key == pygame.K_F2:
                        print(clock.get_fps())
                elif event.type == pygame.QUIT:
                    return
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    selection_rect.center = pygame.mouse.get_pos()
                    marked = Sprite.renderer.get_sprites_in_rect(selection_rect)
                    if marked:
                        marked[0].on_click()

            pressed = pygame.key.get_pressed()
            direction = Vec()
            if pressed[pygame.K_RIGHT]:
                direction += Vec(1, 0)
            if pressed[pygame.K_LEFT]:
                direction -= Vec(1, 0)
            if pressed[pygame.K_UP]:
                direction += Vec(0, -1)
            if pressed[pygame.K_DOWN]:
                direction += Vec(0, 1)
            direction.length = 5
            cam.position += direction


    def demo_parallax(screen):
        create_arrows_sprites()

        num = 200.0
        for i in range(int(num)):
            col = random.choice(list(pygame.color.THECOLORS.values()))
            surf = create_random_surf(col)
            factors = Vec(i/num, i/num)
            z_layer = i/num
            if z_layer < 0.02:
                z_layer = 1000
                factors = Vec(0.0, 0.0)
            pos = Point(random.randint(-390, 390), random.randint(-290, 290))
            spr = Sprite(surf, pos, z_layer=z_layer, parallax_factors=factors, anchor='center')
            TextSprite("prallax factors={0} z_layer={1}".format(factors.x, z_layer), pos, color=invert_color(col), \
                                    backcolor=col, z_layer=z_layer+0.00001, parallax_factors=factors, anchor='center')
        spr = Sprite(surf, Point(), z_layer=100, parallax_factors=factors, anchor='center')

        # fixed sprites


        cam = Camera(screen.get_rect())
        cam.use_conversion_methods = False
        running = True
        clock = pygame.time.Clock()
        while running:
            clock.tick()
            Sprite.renderer.draw(screen, cam, fill_color=BLACK, do_flip=True)
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    elif event.key == pygame.K_c:
                        cam.use_conversion_methods = not cam.use_conversion_methods
                        print("cam.use_conversion_methods", cam.use_conversion_methods)
                    elif event.key == pygame.K_F2:
                        print(clock.get_fps())
                elif event.type == pygame.QUIT:
                    return

            pressed = pygame.key.get_pressed()
            direction = Vec()
            if pressed[pygame.K_RIGHT]:
                direction += Vec(1, 0)
            if pressed[pygame.K_LEFT]:
                direction -= Vec(1, 0)
            if pressed[pygame.K_UP]:
                direction += Vec(0, -1)
            if pressed[pygame.K_DOWN]:
                direction += Vec(0, 1)
            if pressed[pygame.K_PAGEUP]:
                spr.parallax_factors += Vec(0.01, 0.01)
                print(spr.parallax_factors, spr.position)
            if pressed[pygame.K_PAGEDOWN]:
                spr.parallax_factors -= Vec(0.01, 0.01)
                print(spr.parallax_factors, spr.position)
            direction.length = 5
            cam.position += direction

    def demo_vectors(screen):
        create_arrows_sprites()

        pos = Point(200, -100)
        for deg in range(0, 360, 30):
            color = pygame.Color(0, 0, 0, 255)
            color.hsva = (deg, 50, 50, 100)
            v = Vec(1.0, 0).rotate(deg)
            v.length = 0.5 * deg
            VectorSprite(v, color=color)

            direction = Vec(100, 0, position=pos.copy()).rotate(deg)
            label = TextSprite(str(round(direction.angle, 3)), Point() + 1.2 * direction, \
                                                    color=invert_color(color), anchor="center")
            VectorSprite(direction, color, label=label)

        for i in range(10):
            col = random.choice(list(pygame.color.THECOLORS.values()))
            label = TextSprite("Point " + str(i), Point(10, 10), color=col, anchor="topleft")
            VectorSprite(Point(random.randint(50, 400), random.randint(50, 300)), color=col, label=label)


        cam = Camera(screen.get_rect())
        cam.use_conversion_methods = False
        running = True
        while running:
            Sprite.renderer.draw(screen, cam, fill_color=BLACK, do_flip=True)
            event = pygame.event.wait()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                elif event.key == pygame.K_c:
                    cam.use_conversion_methods = not cam.use_conversion_methods
                    print("cam.use_conversion_methods", cam.use_conversion_methods)
            elif event.type == pygame.QUIT:
                return

    def demo_transforms(screen):
        create_arrows_sprites()
        # anchors = ["topleft", "bottomleft", "topright", "bottomright",
                    # "midtop", "midleft", "midbottom", "midright",
                    # "center", Vec(15, 5)]
        t = ['flipx', 'flipy', 'rot', 'zoom']
        import itertools
        combinations = []
        for i in range(len(t)+1):
            combinations += [sorted(list(c)) for c in itertools.permutations(t, i)]
        combinations = list(set([tuple(c) for c in combinations]))
        combinations.sort(key=lambda x: len(x))
        
        # for testing a the flip bug
        # combinations = (tuple(), 'flipy', 'flipx', ('flipx', 'flipy'), ('flipy', 'flipx'))
        
        count = math.ceil(math.sqrt(len(combinations)))

        w, h = screen.get_size()
        dx = w / (count + 1)
        dy = h / (count + 1)
        pos = Point(w // 2,  -h // 2)
        img = pygame.Surface((40, 40))
        img.fill((200, 200, 200))
        pygame.draw.rect(img, (255, 255, 0), pygame.Rect(25, 25, 10, 10))
        pygame.draw.circle(img, (50, 200, 50), (30, 10), 5)
        pygame.draw.polygon(img, (255, 255, 255), [(5, 25), (5, 35), (15, 35)])
        pygame.draw.line(img, (255, 0, 0), (20, 20), (35, 20))
        pygame.draw.line(img, (0, 255, 0), (20, 20), (20, 35))

        red = pygame.Surface((2, 2))
        red.fill((255, 255, 255))
        offset = Vec(-15.0, -15.0) # Vec(random.randint(-30, 30), random.randint(-30, 30))
        rnd_rot = 20 #random.randint(0, 360)
        rnd_zoom = random.random() * 0.5 + 0.4
        sprites = []
        rot_sprites = []
        zoom_sprites = []
        for idx, comb in enumerate(combinations):
            if idx % count == 0:
                pos = pos + Vec(-w+dx, dy)
            spr = Sprite(img, pos)
            sprites.append(spr)
            spr.anchor = offset
            if 'flipx' in comb:
                spr.flipped_x = True
            if 'flipy' in comb:
                spr.flipped_y = True
            if 'rot' in comb:
                spr.rotation = rnd_rot
                rot_sprites.append(spr)
            if 'zoom' in comb:
                spr.zoom = rnd_zoom
                zoom_sprites.append(spr)

            Sprite(red, pos, 'center', z_layer=1)
            TextSprite(str(comb), pos + Vec(0, 60 * (1 if (idx % 2 == 0) else 1)), font=pygame.font.Font(None, 15))
            pos = pos + Vec(dx, 0)
        text = TextSprite("offset: "+str(offset)+"    rot: "+str(rnd_rot)+"    zoom: "+str(rnd_zoom), \
                                    Point(-w//2 + 20, -h//2 + 20), font=pygame.font.Font(None, 15), anchor="topleft")
        TextSprite("press 'r' to rotate", Point(w//2 - 130, -h//2 + 20), \
                                                                font=pygame.font.Font(None, 15), anchor="topleft")
        TextSprite("press 's' to zoom", Point(w//2 - 130, -h//2 + 40), \
                                                                font=pygame.font.Font(None, 15), anchor="topleft")
        TextSprite("arrows to move offset", Point(w//2 - 130, -h//2 + 60), \
                                                                font=pygame.font.Font(None, 15), anchor="topleft")
        cam = Camera(screen.get_rect())
        cam.use_conversion_methods = True
        running = True
        while running:
            Sprite.renderer.draw(screen, cam, fill_color=(255, 0, 255), do_flip=True)
            event = pygame.event.wait()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                elif event.key == pygame.K_s:
                    for spr in zoom_sprites:
                        spr.zoom = spr.zoom + 0.05 if spr.zoom < 1.55 else 0.05
                        rnd_zoom = spr.zoom
                    text.text = "offset: "+str(offset)+"    rot: "+str(rnd_rot)+"    zoom: "+str(rnd_zoom)
                elif event.key == pygame.K_r:
                    rnd_rot = random.randint(0, 360)
                    for spr in rot_sprites:
                        # spr.rotation = rnd_rot
                        spr.rotation = spr.rotation + 10
                        rnd_rot = spr.rotation
                    text.text = "offset: "+str(offset)+"    rot: "+str(rnd_rot)+"    zoom: "+str(rnd_zoom)
                elif event.key == pygame.K_LEFT:
                    offset.x -= 1
                    for spr in sprites:
                        spr.anchor = offset
                    text.text = "offset: "+str(offset)+"    rot: "+str(rnd_rot)+"    zoom: "+str(rnd_zoom)
                elif event.key == pygame.K_RIGHT:
                    offset.x += 1
                    for spr in sprites:
                        spr.anchor = offset
                    text.text = "offset: "+str(offset)+"    rot: "+str(rnd_rot)+"    zoom: "+str(rnd_zoom)
                elif event.key == pygame.K_UP:
                    offset.y += 1
                    for spr in sprites:
                        spr.anchor = offset
                    text.text = "offset: "+str(offset)+"    rot: "+str(rnd_rot)+"    zoom: "+str(rnd_zoom)
                elif event.key == pygame.K_DOWN:
                    offset.y -= 1
                    for spr in sprites:
                        spr.anchor = offset
                    text.text = "offset: "+str(offset)+"    rot: "+str(rnd_rot)+"    zoom: "+str(rnd_zoom)
                elif event.key == pygame.K_c:
                    cam.use_conversion_methods = not cam.use_conversion_methods
                    print("cam.use_conversion_methods", cam.use_conversion_methods)
            elif event.type == pygame.QUIT:
                return


    def demo_anchors(screen):
        create_arrows_sprites()
        anchors = ["topleft", "bottomleft", "topright", "bottomright",
                    "midtop", "midleft", "midbottom", "midright",
                    "center", Vec(15, 5)]
        w, h = screen.get_size()
        dx = w / (len(anchors) + 1)
        pos = Point(dx - w // 2, 0)
        img = pygame.Surface((40, 40))
        img.fill((200, 200, 200))
        red = pygame.Surface((2, 2))
        red.fill((255, 0, 0))
        for idx, anch in enumerate(anchors):
            Sprite(img, pos, anch)
            Sprite(red, pos, 'center', z_layer=1)
            TextSprite(str(anch), pos + Vec(0, 60 * (-1 if (idx % 2 == 0) else 1)), font=pygame.font.Font(None, 15))
            pos = pos + Vec(dx, 0)
        cam = Camera(screen.get_rect())
        cam.use_conversion_methods = True
        running = True
        while running:
            Sprite.renderer.draw(screen, cam, fill_color=BLACK, do_flip=True)
            event = pygame.event.wait()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                elif event.key == pygame.K_c:
                    cam.use_conversion_methods = not cam.use_conversion_methods
                    print("cam.use_conversion_methods", cam.use_conversion_methods)
            elif event.type == pygame.QUIT:
                return

    def demo_depth(screen):
        # create_arrows_sprites()
        TextSprite("press space", Point(400, 550), anchor="bottomleft")
        dx = 10
        count = 30
        for i in range(count):
            img = pygame.Surface((30, 30))
            img.fill((random_rgb()))
            pos = Point(dx * i, dx * i)
            spr = Sprite(img, pos, 'topleft', z_layer=(i+1))
            TextSprite(str(spr.z_layer), pos, font=pygame.font.Font(None, 15), \
                                                                            z_layer=spr.z_layer + 0.1, anchor="topleft")
        img = pygame.Surface(screen.get_size())
        img.fill((255, 0, 0))
        img.set_alpha(128)
        sprite = Sprite(img, Point(), anchor="topleft", z_layer=0.5)
        text_sprite = TextSprite("z_layer = " + str(sprite.z_layer), \
                                                Point(20, 550), font=pygame.font.Font(None, 25), anchor="bottomleft")

        cam = Camera(screen.get_rect(), Point(400, 300))
        running = True
        while running:
            Sprite.renderer.draw(screen, cam, fill_color=BLACK, do_flip=True)
            event = pygame.event.wait()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                elif event.key == pygame.K_SPACE:
                    sprite.z_layer = (sprite.z_layer + 1) % (count + 1)
                    text_sprite.text = "z_layer = " + str(sprite.z_layer)
            elif event.type == pygame.QUIT:
                return

    class Item(TextSprite):
        font = None
        fixed_point = "topleft"
        def __init__(self, key, text, action, pos):
            TextSprite.__init__(self, text, pos, anchor="topleft")
            self.key = key
            self.action = action

    def main():
        pygame.init()
        screen = pygame.display.set_mode(SCREENSIZE, pygame.RESIZABLE)
        Item.font = pygame.font.Font(None, 30)
        items = [
                Item(pygame.K_ESCAPE, "esc to exit", None, Point()),
                Item(pygame.K_ESCAPE, "", None, Point()),
                Item(pygame.K_a, "a. anchors", demo_anchors, Point()),
                Item(pygame.K_b, "b. true z-depth", demo_depth, Point()),
                Item(pygame.K_c, "c. vector drawing", demo_vectors, Point()),
                Item(pygame.K_d, "d. pallax scrolling", demo_parallax, Point()),
                Item(pygame.K_e, "e. mouse selection", demo_mouse_select, Point()),
                Item(pygame.K_f, "f. cam tracking", demo_cam_tracking, Point()),
                Item(pygame.K_g, "g. split screen", demo_split_screen, Point()),
                Item(pygame.K_h, "h. transformations", demo_transforms, Point()),
                Item(pygame.K_i, "i. transformations performance", demo_transformation_performance, Point()),
                Item(pygame.K_j, "j. sprite performance", demo_sprite_performance, Point()),
                Item(pygame.K_k, "k. parallax sprite selection", demo_parallax_select, Point()),
                Item(pygame.K_l, "l. viewport", demo_viewport, Point()),
                Item(pygame.K_m, "m. interpolation", demo_interpolation, Point()),
                
                ]
        dh = Point(0, items[0].font.get_linesize())
        for idx, item in enumerate(items):
            item.position = idx * dh

        running = True
        module_name = "symple"
        caption = "demos for " + module_name
        pygame.display.set_caption(caption)
        w, h = screen.get_size()
        cam = Camera(screen.get_rect(), position=Point(0.4 * w, 0.4 * h))
        selected_item = None
        create_arrows_sprites()

        while running:

            Sprite.renderer.draw(screen, cam, fill_color=BLACK, do_flip=True)

            event = pygame.event.wait()

            if event.type == pygame.KEYDOWN:
                for item in items:
                    if event.key == item.key:
                        selected_item = item
            elif event.type == pygame.MOUSEBUTTONUP:
                hit_items = Sprite.renderer.get_sprites_in_rect(pygame.Rect(event.pos, (1, 1)))
                if hit_items:
                    selected_item = hit_items[0]
            elif event.type == pygame.QUIT:
                running = False

            if selected_item:
                if selected_item.action:
                    Sprite.renderer.push_sprites([])
                    pygame.display.set_caption(selected_item.text)
                    selected_item.action(screen)
                    pygame.display.set_caption(caption)
                    Sprite.renderer.pop_sprites()
                    selected_item = None
                else:
                    running = False

    def test_vector_class():
        v = Vec(1, 2)
        w = v * 3
        assert w.x == 3 and w.y == 6
        x = 4 * v
        assert x.x == 4 and x.y == 8

    test_vector_class()

    main()
    import sys
    sys.exit()

    # def test_pos():
        # class A(object):
            # def __init__(self):
                # self.pos = 0
                # self.old_pos = 0
            # def set_pos(self, p):
                # self.old_pos, self.pos = self.pos, p
        # class B(object):
            # def __init__(self):
                # self.pos = 0
                # self.old_pos = 0
            # def set_pos(self, p):
                # self.old_pos = self.pos
                # self.pos = p
        # class C(object):
            # def __init__(self):
                # self.pos = 0
                # self.old_pos = 0
            # @property
            # def position(self):
                # return self.pos
            # @position.setter
            # def position(self, p):
                # self.old_pos = self.pos
                # self.pos = p


        # a = A()
        # b = B()
        # c = C()
        # for i in range(1000000):
            # a.set_pos(i)
            # b.set_pos(i)
            # c.position = i

    import cProfile
    import datetime
    t = datetime.datetime.now()

    profile_name = "symple2.profile" # datetime.strftime("%Y-%m-%d-%H-%M-%S-") + "symple.profile"
    cProfile.run('main()', profile_name)
    # cProfile.run('test_pos()', profile_name)
    import pstats
    p = pstats.Stats(profile_name)
    p.strip_dirs().sort_stats(-1).print_stats()
    p.sort_stats('name')
    p.print_stats()
    p.sort_stats('cumulative').print_stats(20)

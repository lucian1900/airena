#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
TODO: docstring
"""

__version__ = '$Id: geometry.py 197 2009-04-27 22:07:25Z dr0iddr0id $'

import math
from math import hypot
from math import radians
from math import sin
from math import cos
from math import pi

PI_DIV_180 = pi / 180.0

class Vec2D(object):

    __slots__ = tuple('xy')

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def clone(self):
        return self.__class__(self.x, self.y)

    def _set_values(self, other):
        assert isinstance(other,  Vec2D)
        # TODO: should tuples and lists also be allowed?
        self.x = other.x
        self.y = other.y
    values = property(None, _set_values, doc='set only,value assignemt')

    def __repr__(self):
        return "<%s(%f,%f)>" %(self.__class__.__name__, self.x, self.y)

    def __add__(self, other):
        return self.__class__(self.x + other.x, self.y + other.y)

    def __iadd__(self, other):
        self.x += other.x
        self.y += other.y
        return self

    def __sub__(self, other):
        return self.__class__(self.x - other.x, self.y - other.y)

    def __isub__(self, other):
        self.x -= other.x
        self.y -= other.y
        return self

    def __mul__(self, scalar):
        return self.__class__(self.x * scalar,  self.y * scalar)
    __rmul__ = __mul__

    def __imul__(self, scalar):
        self.x *= scalar
        self.y *= scalar
        return self

    def __len__(self):
        return 2

    def __div__(self, scalar):
        return self.__class__(self.x / scalar, self.y / scalar)

    def __idiv__(self, scalar):
        self.x /= scalar
        self.y /= scalar
        return self

    def __neg__(self):
        return self.__class__(-self.x, -self.y)

    def __pos__(self):
        return self.__class__(abs(self.x), abs(self.y))

    def round(self, n_digits=3):
        self.x = round(self.x, n_digits)
        self.y = round(self.y, n_digits)

    def rounded(self, n_digits=3):
        return self.__class__(round(self.x, n_digits), round(self.y, n_digits))

    def _length(self):
        return hypot(self.x, self.y)

    def _lengthSQ(self):
        return self.x * self.x + self.y * self.y

    length = property(_length)
    lengthSQ = property(_lengthSQ)

    def _normalized(self):
        leng = self.length
        return self.__class__(self.x / leng, self.y / leng)
    normalized = property(_normalized)

    def normalize(self):
        leng = self.length
        self.x /= leng
        self.y /= leng

    def _normal_R(self):
        return self.__class__(self.y, -self.x)
    normal_R = property(_normal_R)

    def _normal_L(self):
        return self.__class__(-self.y, self.x)
    normal_L = property(_normal_L)

    def dot(self, other):
        return self.x * other.x + self.y * other.y

    def project_onto(self, other):
        return self.dot(other) / other.lengthSQ * other

    def reflect(self, normal):
        """normal should be normalized unitlength"""
        return self - 2 * self.dot(normal) * normal

    def reflect_tangent(self, tangent):
        """tangent should be normalized, unitlength"""
        return 2 * tangent.dot(self) * tangent - self

    def rotate(self, degrees):
        """+ clockwise, - ccw"""
        rad = degrees * PI_DIV_180
        s = sin(rad)
        c = cos(rad)
        x = self.x
        self.x = c * x + s * self.y
        self.y = -s * x + c * self.y

    def rotated(self, degrees):
        """
        returns rotated vec
        + cw, - ccw
        """
        rad = degrees * PI_DIV_180
        s = sin(rad)
        c = cos(rad)
        return self.__class__(c * self.x + s * self.y, -s * self.x + c * self.y)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.x == other.x and self.y == other.y
        return False

    def __neq__(self, other):
        return not self.__eq__(other)

    def as_tuple(self):
        return self.x, self.y

    def __getitem__(self, key):
        return (self.x, self.y)[key]

    def __iter__(self):
        return iter((self.x, self.y))


def sign(value):
    assert isinstance(value, int) or isinstance(value, float)
    if 0 < value:
        return 1
    elif 0 > value:
        return -1
    else:
        return 0

if __name__ == '__main__':
    
    v = Vec2D(2, 2)
    w = Vec2D(3, 5)
    assert v == Vec2D(2, 2), 'equal failed'
    assert v + w == Vec2D(5, 7), 'add failed'
    assert w - v == Vec2D(1, 3), 'sub failed'
    assert 2 * v == Vec2D(4, 4), 'rmul failed'
    assert v * 3 == Vec2D(6, 6), 'mul failed'
    assert v.dot(w) == 16, 'dot failed'
    z = v.clone()
    z *= 4
    assert z == Vec2D(8, 8) , 'imul failed'
    assert z / 2 == Vec2D(4, 4), 'div failed'
    z /= 2
    assert z == Vec2D(4, 4), 'idiv failed'
    assert Vec2D(3, 4).length == 5, 'length failed'
    assert Vec2D(5, 2).lengthSQ == 29, 'lengsq failed'
    v += w
    assert v == Vec2D(5, 7), 'iadd failed'
    v -= w
    assert v == Vec2D(2, 2), 'isub failed'
    assert v.normal_L == Vec2D(-2, 2), 'normal_L failed'
    assert v.normal_R == Vec2D(2, -2), 'normal_R failed'
    assert v.normalized == v / v.length, 'normalized failed'
    n = v.normalized
    v.normalize()
    assert v == n, 'normalize failed'
    v = Vec2D(1, 0)
    n = Vec2D(1, 1).normalized
    r = v.rotated(-45).normalized
    assert round(r.x, 5) == round(n.x, 5) and r.y == n.y, 'rotated failed'
    r = Vec2D(1, 0)
    r.rotate(-45)
    assert round(r.x, 5) == round(n.x, 5) and round(r.y, 5) == round(n.y, 5), 'rotate failed'
    assert Vec2D(1, 1).project_onto(Vec2D(1, 0)) == Vec2D(1, 0), 'project_onto failed'
    assert Vec2D(-1, 1).project_onto(Vec2D(0, 1)) == Vec2D(0, 1), 'project_onto failed'
    assert Vec2D(1, -1).reflect(Vec2D(0, 1)) == Vec2D(1, 1), 'reflect failed'
    assert Vec2D(1, -1).reflect_tangent(Vec2D(1, 0)) == Vec2D(1, 1), 'reflect_tangent failed'
    v = Vec2D(1, 1)
    w = Vec2D(3, 3)
    v.value = w
    w.x = 100
    w.y = 100
    assert v.x == 3, 'value for x failed'
    assert v.y == 3, 'value for y failed'
    raw_input('press any key to continue...')


import sys
from inspect import getmembers, isclass
import numpy as np

from src.base.errors import WasatchError, UserInputError
import src.fem.element.element as el
from src.fem.shapefunctions import shapefunctions as sf


class Bar2(el.Element, sf["Bar2"]):
    """Linear bar element"""
    name = "Bar2"
    eid = 1
    nnodes = 2
    ncoord = 1
    ndof = 1
    def __init__(self, n, nodes, coords, material, *args, **kwargs):
        super(Bar2, self).__init__(n, nodes, coords, material, *args, **kwargs)

    @classmethod
    def volume(self, coords=None):
        # update the volume
        area = 1.
        length = 1.
        return area * length


class Tri3(el.Element, sf["Tri3"]):
    """Constant strain triangle"""
    name = "Triangle3"
    eid = 4
    nnodes = 3
    ncoord = 2
    ndof = 2
    canreduce = True
    def __init__(self, n, nodes, coords, material, *args, **kwargs):
        super(Tri3, self).__init__(n, nodes, coords, material, *args, **kwargs)

    @classmethod
    def volume(self, coords=None):
        # update the volume
        depth = 1.
        area = 1.
        return area * depth


class Quad4(el.Element, sf["Quad4"]):
    """Bilinear quad element"""
    name = "Quad4"
    eid = 2
    nnodes = 4
    ncoord = 2
    ndof = 2
    canreduce = True
    hasplanestress = True
    def __init__(self, n, nodes, coords, material, *args, **kwargs):
        super(Quad4, self).__init__(n, nodes, coords, material, *args, **kwargs)

    @classmethod
    def volume(self, coords):
        # update the volume
        x, y = coords[:, [0, 1]].T
        depth = 1.
        area = .5 * ((x[0] - x[2]) * (y[1] - y[3]) - (x[1] * x[3]) * (y[0] - y[2]))
        return area * depth


class Hex8(el.Element, sf["Hex8"]):
    """Trilinear hex element"""
    name = "Hex8"
    eid = 3
    nnodes = 8
    ncoord = 3
    ndof = 3
    canreduce = True
    def __init__(self, n, nodes, coords, material, *args, **kwargs):
        super(Hex8, self).__init__(n, nodes, coords, material, *args, **kwargs)

    @classmethod
    def volume(self, coords):
        # update the volume
        volume = 1.
        return volume

# List of installed elements
DEFAULT_ELEMENTS = dict((x[0].upper(), x[1]) for x in
                        getmembers(sys.modules[__name__], isclass)
                        if x[1].__module__ == __name__)

import os
import sys
import imp
import math
import pyclbr
import inspect
import numpy as np

class Namespace:
    def __init__(self, _id, **kwargs):
        self.keys = []
        self._id = _id
        for (k, v) in kwargs.items():
            setattr(self, k, v)
            self.keys.append(k)
    def update(self, kwargs):
        self.__dict__.update(kwargs)
        for k in kwargs:
            if k not in self.keys:
                self.keys.append(k)
    def __getattr__(self, key):
        return self.__dict__[key]
    def __contains__(self, item):
        return item in self.__dict__.keys()
    def __str__(self):
        return "{0}({1})".format(self._id, ", ".join(self.keys))

def whoami():
    """return a function's name

    Returns
    -------
    whoami : str
        The name of the function calling this function

    """
    return inspect.stack()[1][3]


def who_is_calling():
    """return the name of the calling function

    Returns
    -------
    who_is_calling : str
        The name of the function calling a function

    Notes
    -----
    If function A calls function B and function B calls who_is_calling,
    who_is_calling will return 'A'

    """
    stack = inspect.stack()[2]
    return "{0}.{1}".format(
        os.path.splitext(os.path.basename(stack[1]))[0], stack[3])


def shape(l):
    """Determine the shape of a python list l

    Parameters
    ----------
    l : list

    Returns
    -------
    shape : tuple (i, [j])
        number of rows i, and number of columsn j

    """
    length = len(l)
    try:
        return length, len(l[0])
    except TypeError:
        return length,


def isstr(item):
    try:
        item.upper()
        return True
    except AttributeError:
        return False


def eqstr(a, b):
    return a.upper().strip() == b.upper().strip()


def reduce_map(i, j, ncoord, ndof=None):
    """Mapping from higher order tensor space to lower order

    Parameters
    ----------
    ij : tuple
        Indeces in the higher-order tensor space (1, 1)
        ij[0] -> ith index
        ij[1] -> jth index

    Returns
    -------
    I : int
        Index in the lower-order tensor space

    Comments
    --------
    Maps according to:

       2D               3D
    00 -> 0           00 -> 0
    11 -> 1           11 -> 1
                      22 -> 2
    01 -> 2           01 -> 3
                      12 -> 4
                      02 -> 5

    """
    ij = (i, j)
    if ndof is None:
        ndof = ncoord
    if ndof != ncoord:
        raise SystemExit("NDOF must equal NCOORD (for now)")

    # sort the indices
    ij = sorted(ij)

    if ij[0] == ij[1]:
        return ij[0]

    if ncoord == 2:
        if any(i > 1 for i in ij):
            raise SystemExit("Bad index for 2D mapping: {0}".format(repr(ij)))
        return 2

    if ij == [0, 1]:
        return 3
    elif ij == [1, 2]:
        return 4
    elif ij == [0, 2]:
        return 5
    raise SystemExit("Bad index for 3D mapping: {0}".format(repr(ij)))

def find_descendents(directory, parent, skip=[]):
    """Find classes that inherit from parent in directory

    """
    descendents = []
    sys.path.insert(0, directory)
    for f in os.listdir(directory):
        if not f.endswith(".py"): continue
        if f in skip: continue
        name = os.path.splitext(f)[0]
        a = pyclbr.readmodule(name, [directory])
        for (k, v) in a.items():
            if parent not in [s.name for s in v.super if s != "object"]:
                continue
            fp, pathname, desc = imp.find_module(name, [directory])
            module = imp.load_module(name, fp, pathname, desc)
            fp.close()
            descendents.append(getattr(module, k))
    sys.path.pop(0)
    return descendents

def strcmp(Astr, Bstr):
    a = " ".join(s[:4].lower() for s in Astr.split())
    b = " ".join(s[:4].lower() for s in Bstr.split())
    return a == b

def getopt(opt, kwds, default=None, pop=False):
    for key in kwds:
        if strcmp(key, opt):
            if pop:
                return kwds.pop(key)
            return kwds[key]
    return default

def Int(x):
    return int(float(x))

def Float(x):
    return float(x)

def Array(x):
    return np.array(x)

def dof_id(dof):
    try:
        return {"X": 0, "Y": 1, "Z": 2}[dof.upper()]
    except AttributeError:
        return dof

def Range(*args, **kwargs):
    return np.array(range(*args), dtype=np.int) + kwargs.get("offset", 1)

def dist(a, b):
    return math.sqrt(np.dot(a - b, a - b))

def load_file(filename, disp=0, reload=False):
    """Load a python module by filename

    Parameters
    ----------
    filename : str
        path to python module

    Returns
    -------
    py_mod : module
        import python module

    """
    from os.path import isfile, split, splitext, sep
    from core.product import AFEPY_D

    if not isfile(filename):
        raise IOError("{0}: no such file".format(filename))

    path, base = split(filename)
    name = splitext(base)[0]
    if AFEPY_D in path:
        d = "_".join(path.replace(AFEPY_D+sep, "").split(sep))
        long_name = "{0}_{1}".format(d, name)
    else:
        long_name = name

    # if reload was requested, remove the module from sys.modules
    if reload:
        try:
            del sys.modules[long_name]
        except KeyError:
            pass

    # return already loaded module
    module = sys.modules.get(long_name)
    if module is None:
        fp, pathname, (_s, _m, ty) = imp.find_module(name, [path] + sys.path)
        if ty != imp.PY_SOURCE:
            # not Python source, can't do anything with this module
            fp.close()
            return None

        try:
            module = imp.load_module(long_name, fp, pathname, (_s, _m, ty))
        finally:
            if fp:
                fp.close()

    if disp:
        return module, long_name

    return module

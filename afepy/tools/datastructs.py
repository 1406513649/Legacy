from copy import copy
from numpy import zeros, array, asarray, ndarray, empty, object as npobject

SCALAR = 0
VECTOR = 1
SYMTEN = 2
ARRAY = 3


def xkeys(name, type, keys, num_dim, ndi, nshr):
    """Generate key names for variable 'name' based on variable type

    """
    n = name.title()
    if type == SCALAR:
        if not keys:
            keys = [n]

    elif type == VECTOR:
        if not keys:
            keys = [n + "_%s"%(dof) for dof in "xyz"[:num_dim]]

    elif type == SYMTEN:
        if not keys:
            comps = ["xx", "yy", "zz"][:ndi] + ["xy", "yz", "xz"][:nshr]
            keys = [n + "_%s"%(comp) for comp in comps]

    elif type == ARRAY:
        assert keys is not None
        keys = [key.title() for key in keys]

    else:
        raise ValueError("unknown variable type")

    return keys

class Variable:
    def __init__(self, name, type, keys, ivals):
        self.name = name
        self.type = type
        self.keys = keys
        self.ivals = ivals

class AttrArray:
    """Array like object to hold material data. Data are accessible by either
    index or attribute name. For example, the stress array is accessible by

    a = AttrArray(...)
    a.stress

    """
    def __init__(self, *args):
        if args:
            variables, num_dim, ndi, nshr = args
            self._ix = {}
            self.keys = []
            start = 0
            data = []
            self.names = [v.name.lower() for v in variables]
            for v in variables:
                keys = xkeys(v.name, v.type, v.keys, num_dim, ndi, nshr)
                self.keys.extend(keys)
                nc = len(keys)
                self._ix[v.name.lower()] = slice(start, start+nc)
                self._ix.update([(k, i+start) for (i, k) in enumerate(keys)])
                if v.ivals is not None:
                    assert len(v.ivals) == nc
                    data.extend(v.ivals)
                else:
                    data.extend([0.] * nc)
                start += nc
            self.data = array(data)

    def __str__(self):
        s = ", ".join("{0:g}".format(x) for x in self.data)
        s = ", ".join(self.names)
        return "AttrArray({0})".format(s)

    def __repr__(self):
        return self.__str__()

    def __len__(self):
        return len(self.data)

    def __coerce__(self):
        return self.data.__coerce__()

    def _idx(self, arg):
        if isinstance(arg, (int, slice)):
            return arg
        try:
            return self._ix[arg]
        except KeyError:
            return None

    def __getattr__(self, key):
        idx = self._idx(key)
        if idx is None:
            if key.lower() == "statev":
                return None
            raise AFEPYError("{0} is not a valid variable".format(key))
        try:
            return self.data.__getitem__(idx)
        except ValueError:
            return self.__dict__[key]

    def __getitem__(self, i):
        return self.data.__getitem__(i)

    def __setitem__(self, key, value):
        idx = self._idx(key)
        self.data.__setitem__(idx, value)

    def __copy__(self):
        cls = self.__class__
        result = cls()
        result._ix = dict(self._ix.items())
        result.names = list(self.names)
        result.keys = list(self.keys)
        result.data = self.data.copy()
        return result

    def copy(self):
        return self.__copy__()

class BlockData:
    """Data container for element block data

    """
    def __init__(self, elements):


        num_elem = len(elements)
        num_int_pts = elements[0].integration.num_point
        self.data = empty((2, num_elem, num_int_pts), dtype=npobject)
        self.data.fill(0.)

        varz = elements[0].variables
        nc = elements[0].num_coord
        ndi = elements[0].ndi
        nshr = elements[0].nshr
        for i in range(num_elem):
            for j in range(num_int_pts):
                self.data[0, i, j] = AttrArray(varz, nc, ndi, nshr)
                self.data[1, i, j] = AttrArray(varz, nc, ndi, nshr)

        self.keys = list(self.data[0, 0, 0].keys)

    def __getitem__(self, arg):
        return self.data.__getitem__(arg)

    def recursive_copy(self, i, j, key=None):
        _, num_elem, num_int_pts = self.data.shape
        for a in range(num_elem):
            for b in range(num_int_pts):
                if key is None:
                    self.data[i, a, b] = self.data[j, a, b].copy()
                else:
                    x = getattr(self.data[i, a, b], key)
                    y = getattr(self.data[j, a, b], key)
                    x[:] = y.copy()

    def advance(self, key=None):
        self.recursive_copy(0, 1, key=key)

    def reset(self, key=None):
        self.recursive_copy(1, 0, key=key)

    def __getitemx__(self, arg):
        return self.data[arg]

if __name__ == "__main__":
    class C: pass
    E = C()
    E.integration = C()
    E.integration.num_point = 4
    E.num_coord = 2
    E.ndi = 2
    E.nshr = 1
    E.variables = (Variable("STRESS", SYMTEN, None, None),
                   Variable("STRAIN", SYMTEN, None, None),
                   Variable("STATEV", ARRAY, ("SV1", "SV2", "SV3"), (1,2,3)))
    data = BlockData([E])

    e = data[1, 0, 1].strain
    d = data[1, 0, 1].stress
    e[:] = [1,2,3]
    d[:] = [3,4,5]
    print data[0, 0, 1].strain
    print data[1, 0, 1].strain
    print
    print data[0, 0, 1].stress
    print data[1, 0, 1].stress
    print

    data.advance()
    e = data[1, 0, 1].strain
    d = data[1, 0, 1].stress
    e[:] = [4,5,6]
    d[:] = [6,7,8]

    print data[0, 0, 1].strain
    print data[1, 0, 1].strain
    print
    print data[0, 0, 1].stress
    print data[1, 0, 1].stress

    data.advance("stress")

    print
    print data[0, 0, 1].strain
    print data[1, 0, 1].strain
    print
    print data[0, 0, 1].stress
    print data[1, 0, 1].stress

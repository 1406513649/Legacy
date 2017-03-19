TINY = 1.E-12
import numpy as np
try:
    from scipy.sparse import coo_matrix
except ImportError:
    class coo_matrix:
        def __init__(self, (data, (row, col)), shape):
            self.a = np.zeros(shape)
            for (i, a) in enumerate(data):
                self.a[row[i],0] += a
        def todense(self):
            return self.a

class SparseVector(object):
    def __init__(self, arg, shape, dtype=float):
        self.shape = shape
        self.dtype = dtype

        self.row = []
        self.data = []

        if arg is not None:
            try:
                data, row = arg
            except:
                raise TypeError('invalid input format')
            self.append(data, row)

    def __add__(self, other, _fac=1.):
        if isinstance(other, SparseVector):
            row = other.row
            data = other.data
        elif isinstance(other, float):
            row = range(self.shape)
            data = np.ones(self.shape) * other
        else:
            row = range(len(other))
            data = other
        self.append(data, row)
        return self

    def __sub__(self, other):
        return self.__add__(other, _fac=-1.)

    def __iadd__(self, other):
        return self.__add__(other)

    def __isub__(self, other):
        return self.__sub__(other)

    def __mul__(self, other):
        try:
            other = self.dtype(other)
        except TypeError:
            raise TypeError("unsupported operand type(s) for *: "
                            "{0} and 'SparseVector'".format(type(other)))
        self.data = [other * x for x in self.data]
        return self

    def __rmul__(self, other):
        return self.__mul__(other)

    def __setitem__(self, row, data):
        if isinstance(row, int):
            row, data = [row], [data]
        elif not isinstance(row, (list, tuple,  np.ndarray)):
            raise TypeError("wrong data type")
        self.append(data, row)

    def __getitem__(self, arg):
        """This method always returns 0.  Huh??? Always returns 0?

        Because we sum all rows when the SparseVector is converted to an
        array, returning the actual value right now would result in double
        dipping when an array is desired in the future.

        """
        if isinstance(arg, int):
            return 0.
        elif isinstance(arg, (list, tuple, np.ndarray)):
            return [0.] * len(arg)
        raise TypeError("wrong data type")

    def appendx(self, data, row):
        assert len(row) == len(data)
        w = np.where(np.abs(data) > TINY)
        self.row.extend(np.asarray(row)[w])
        self.data.extend(np.asarray(data)[w])

    def append(self, data, row):
        assert len(row) == len(data)
        for (i, a) in enumerate(data):
            if abs(a) <= TINY:
                continue
            self.row.append(row[i])
            self.data.append(a)

    def asarray(self):
        arr = coo_matrix((self.data, (self.row, [0]*len(self.row))),
                         shape=(self.shape,1))
        return np.array(arr.todense()).ravel()

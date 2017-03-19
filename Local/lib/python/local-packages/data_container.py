import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import cPickle as pickle
import textwrap


np.set_printoptions(precision=2, threshold=100)

class DataContainer(object):
    """Holder for data.  Data expected to be a numpy array.

    """
    def __init__(self, ID, **kwargs):
        """

        Parameters
        ----------
        ID : str
            DataContainer ID
        kwargs : dict
            Any container level meta data

        """
        self._n = 0
        self.ID = " ".join(ID.replace("-", " ").split()).strip()
        self.__meta__ = {}
        self.__meta__.update(kwargs)
        self.__container__ = {}
        pass

    def no_member(self, name):
        raise ValueError("{0}: no such member in data container".format(name))

    def already_exists(self, name):
        raise ValueError("{0} already put in to data container".format(name))

    def put(self, name, data, **kwargs):
        """Put new member in data container

        Parameters
        ----------
        name : str
            name of member
        data : array
            initial data
        kwargs : dict
            any other info to store

        Notes
        -----
        Items put in the data container can be retrieved by the get method, or
        directly through the 'name' attribute.

        """
        name = " ".join(name.replace("-", " ").split()).strip()
        if name in self.members():
            self.already_exists(name)
        self.__container__[name] = {"data": data, "index": self._n}
        self.__container__[name].update(**kwargs)
        if "label" not in self.__container__[name]:
            self.__container__[name]["label"] = name
        self._n += 1
        name = "_".join(name.split()).upper()
        setattr(self, name, data)
        return

    def get(self, name, default=None, item="data"):
        """Get data of member of data container

        Parameters
        ----------
        name : [str, int]
            name or integer id of member to get
        default : None
            default data if name is not a member

        """
        name = self._get_name(name)
        if not name:
            return default
        try:
            val = self.__meta__[name]
        except KeyError:
            val = self.__container__[name].get(item)
        return val

    def members(self):
        """Return list of members

        Notes
        -----
        List of members is returned in order put in to the container
        """
        return self.meta_members() + self.data_members()

    def data_members(self):
        """Return list of data members

        Notes
        -----
        List of data members is returned in order put in to the container
        """
        return sorted(self.__container__,
                      key=lambda k: self.__container__[k]["index"])

    def meta_members(self):
        return self.__meta__.keys()

    def summary(self, *names):
        """Write a summary

        """
        sp = "  "
        _summary = [self.ID]
        meta = self.meta_members()
        data = self.data_members()
        _summary.append("{0}META Data: {1}".format(sp, ", ".join(meta)))
        _summary.append("{0}PUT Data: {1}".format(sp, ", ".join(data)))
        N = max(len(x) for x in meta)
        _summary.append("\n{0}META Data Details".format(sp))
        for k in meta:
            indent = sp * 2 + " " * N + "  "
            v = textwrap.fill(self.get(k), subsequent_indent=indent)
            _summary.append("{3}{0:>{1}s}: {2}".format(k, N, v, sp*2))

        if not names:
            names = self.data_members()

        _summary.append("\n{0}PUT Data Details".format(sp))
        for _name in names:
            name = self._get_name(_name)
            if name is None:
                self.no_member(_name)
            _summary.append("{1}{0}".format(name, sp*2))
            N = max(len(x) for x in self.__container__[name].keys())
            for key, value in self.__container__[name].items():
                _summary.append("{3}{0:>{1}s}: {2}".format(key, N, value, sp*3))
        return "\n".join(_summary)

    def dump(self, f=None):
        """Dump data container to file f

        Parameters
        ----------
        f : str
            file name.  if not specified, ID is used

        Notes
        -----
        f is opened without checking existence. Any file by the same name will
        be overwritten.

        """
        if f is None:
            f = "_".join(self.ID.split()) + ".pdb"
        with open(f, "w") as fobj:
            pickle.dump(self, fobj, protocol=pickle.HIGHEST_PROTOCOL)
        return

    def write(self, f, *args):
        """Write data container to file f

        Parameters
        ----------
        f : str
            Filename to write
        args : unpacked tuple
            Names of members to write

        Notes
        -----
        1) File existence is not checked. If f already exists, it will be
           overwritten
        2) If no args are given, all data is written in order put

        """
        if f is None:
            f = "_".join(self.ID.split()) + ".dat"
        if not args:
            args = self.data_members()
        data = self.join(*args)
        N = max(max(len(x) for x in args), 12)
        n = int(float(N) / 2.)
        head = " " + " ".join("{0:{1}s}".format(x.upper(), N+1) for x in args)
        with open(f, "w") as fobj:
            fobj.write(head + "\n")
            for row in data:
                row = " ".join("{0: {1}.{2}E}".format(x, N, n) for x in row)
                fobj.write(row + "\n")
        return

    def join(self, *args):
        """Join 1D arrays in to 2D array

        Parameters
        ----------
        args : unpacked tuple
            Names of members to join

        Notes
        -----
        1) If no args are given, all data is joined in order put

        """
        data = []
        if not args:
            args = self.data_members()
        for arg in args:
            dat = self.get(arg)
            if dat is None:
                self.no_member(arg)
            data.append(dat)
        return np.column_stack(data)

    def _get_name(self, s):
        """Get the name of the member

        """
        idx = None if not isinstance(s, (float, int)) else int(s)
        for key in self.members():
            if idx is not None:
                if idx == self.__container__[key]["index"]:
                    return key
            elif key.lower() == s.lower():
                return key
        else:
            return None

    def plot(self, *args):
        """Plot the members

        Parameters
        ----------
        args : unpacked tuple
            Members to plot

        Notes
        -----
        1) If len(args) > 2, multiple plots are created, each consecutive arg
           being plotted vs. arg[0]
        2) If no args are given, all members will be plotted vs. first member
           put

        """
        if not args:
            x = self._get_name(0)
            others = [i for i in self.members() if i != x]
        else:
            x = self._get_name(args[0])
            if not x:
                self.no_member(args[0])
            others = args[1:]

        if not others:
            others = [i for i in self.members() if i != x]

        xdat = self.get(x)
        for y in others:
            ydat = self.get(y)
            plt.clf()
            plt.xlabel(x)
            plt.ylabel(y)
            plt.plot(xdat, ydat)
            plt.show()
        return


def load(f):
    """Load the pickle file f

    Parameters
    ----------
    f : str
        File name to load

    Notes
    -----
    This method is a companion to DataContainer.dump

    """
    with open(f) as fobj:
        data = pickle.load(fobj)
    return data


if __name__ == "__main__":
    data = DataContainer(ID="Test")
    data.put("x", np.arange(6))
    data.put("y", np.linspace(-3., 3., 6))
    print data.members()
    data.dump("foo.pkl")
    data.write("foo.dat", "x", "y", "y", "x")
    data.write("foo.dat2")
    print data.get("x", item="label")
    print data.get("x")
    data.plot()

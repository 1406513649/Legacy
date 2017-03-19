#!/usr/bin/env python
import os
import sys
import textwrap
import argparse
import numpy as np
import scipy.io as sio
import scipy.constants as sc
import matplotlib.pyplot as plt

np.set_printoptions(precision=2, threshold=100)

def logmes(message): sys.stdout.write(message + "\n")

def convert_to_si(a):
    b = a
    if a.units == "G":
        b.data = a.data * sc.g
        b.units = "m/sec/sec"
    elif a.units == "ft/sec":
        b.data = a.data * 0.3048
        b.units = "m/sec"
    return b


class NetCDF(object):
    def __init__(self, f, tosi=False, n=1):
        self.f = sio.netcdf.netcdf_file(f, "r")
        self.filename = os.path.realpath(self.f.filename)
        self.filedir = os.path.dirname(self.filename)
        self.ID = os.path.splitext(os.path.basename(self.filename))[0]
        self.tosi = tosi
        self.plots = []
        self._n = n

        # list of variables, we want time first.
        variables, time = [], None
        for variable in self.f.variables:
            if variable.lower() == "time":
                time = variable
            else:
                variables.append(variable)
        self.variables = sorted(variables)
        if time is not None:
            self.variables.insert(0, time)

    def __del__(self):
        self.f.close()

    def attributes(self, attribute=None):
        if attribute is None:
            return self.f._attributes
        return self.f._attributes[attribute]

    def members(self, member=None):
        """Return variables of netcdf object, if time is in the list, return
        it first

        """
        if member is None:
            return self.variables
        return self.f.variables[member]

    def get_formatted_data(self, data_only=False):
        """Return an array with all of the netcdf data

        """
        head, data, units = [], [], []
        time = self.members("TIME")
        head.append("'TIME'")
        data.append(np.array(time.data))
        units.append("'[{0}]'".format(time.units))
        for member in self.members():
            if member.lower() == "time":
                continue
            x = self.members(member)
            if self.tosi:
                x = convert_to_si(x)
            head.append("'{0}'".format(member.upper()))
            data.append(np.array(x.data))
            units.append("'[{0}]'".format(x.units))
        data = np.column_stack(data)
        L = max(len(x) for x in head)
        head = " ".join("{0:{1}s}".format(x, L) for x in head)
        units = " ".join("{0:{1}s}".format(x, L) for x in units)
        if data_only:
            return data
        return head, units, data

    def write(self, upper=None, overwrite=False):
        """Write netcdf file to ascii data file

        Parameters
        ----------
        upper : float
            If specified, upper limit on time

        """
        head, units, data = self.get_formatted_data()
        f = os.path.join(self.filedir, self.ID + ".dat")
        if not overwrite:
            if os.path.isfile(f):
                fnam, fext = os.path.splitext(f)
                for i in range(100):
                    fmv = "{0}.{1:03d}{2}".format(fnam, i, fext)
                    if not os.path.isfile(fmv):
                        break
                logmes("Moving {0} to {1}".format(f, fmv))
                os.rename(f, fmv)

        logmes("Writing {0} [netcdf] to {1} [ascii]".format(
                os.path.basename(self.filename), os.path.basename(f)))

        L = min(max(len(x) for x in head.split()), 12)
        l = int(float(L) / 2.)
        with open(f, "w") as fobj:
            fobj.write("# {0}\n# {1}\n".format(head, units))
            for row in data[::self._n]:
                if upper is not None and row[0] > upper:
                    break
                row = "  " + " ".join("{0: <{1}.{2}E}".format(x, L, l) for x in row)
                fobj.write(row + "\n")
        return

    def summary(self):
        """Write a summary

        """
        sp = "  "
        _summary = [self.ID]

        attributes = self.attributes()
        data = self.members()
        _summary.append("{0}ATTRIBUTES: {1}".format(sp, ", ".join(attributes)))
        _summary.append("{0}VARIABLES: {1}".format(sp, ", ".join(data)))

        N = 0 if not attributes else max(len(x) for x in attributes)
        _summary.append("\n{0}ATTRIBUTE Details".format(sp))
        for attribute in attributes:
            I = sp * 2 + " " * N + "  "
            v = textwrap.fill(str(self.attributes(attribute)), subsequent_indent=I)
            _summary.append("{3}{0:>{1}s}: {2}".format(attribute, N, v, sp*2))
            continue

        members = self.members()
        _summary.append("\n{0}VARIABLE Details".format(sp))
        for member in members:
            x = self.members(member)
            if self.tosi:
                x = convert_to_si(x)
            _summary.append("{0}{1}".format(sp * 2, member))
            _summary.append("{0}{1:>{2}s}: {3}".format(
                    sp*3, "data", N, x.data))
            _summary.append("{0}{1:>{2}s}: {3}".format(
                    sp*3, "length", N, len(x.data)))
            for item in ["title", "legend", "label", "units",
                         "description", "desc", "shape", "dims"]:
                try: attr = getattr(x, item)
                except AttributeError: continue
                si = len("{0}{1:>{2}s}: ".format(sp*3, item, N))
                attr = textwrap.fill(str(attr), subsequent_indent=" " * si)
                _summary.append("{0}{1:>{2}s}: {3}".format(sp*3, item, N, attr))
        return "\n".join(_summary)

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
            x = "TIME"
            others = [i for i in self.members() if i != x]
        else:
            x = args[0]
            if x not in self.members():
                sys.exit("{0}: not a variable".format(x))
            others = args[1:]

        if not others:
            others = [i for i in self.members() if i != x]

        xvar = x
        x = self.members(xvar)
        if self.tosi:
            x = convert_to_si(x)

        for yvar in others:
            f = "_".join("{0} {1} vs {2}.pdf".format(self.ID, xvar, yvar).split())
            pdf = os.path.join(self.filedir, f)
            y = self.members(yvar)
            if self.tosi:
                y = convert_to_si(y)
            plt.clf()
            plt.xlabel(x.label + " ({0})".format(x.units))
            plt.ylabel(y.label + " ({0})".format(y.units))
            try:
                plt.title(textwrap.fill(y.title))
            except AttributeError:
                pass
            plt.plot(x.data[::self._n], y.data[::self._n], label=y.legend)
            plt.legend(loc="best")
            plt.savefig(pdf, transparent=True)
            self.plots.append(pdf)
        return

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(prog="ncread.py")
    parser.add_argument("-w", action="store_true", default=False,
                        help="Write ascii dat file [default: %(default)s]")
    parser.add_argument("-W", action="store_true", default=False,
                        help=("Same as -w, but overwrite dat file if it exists "
                              "[default: %(default)s]"))
    parser.add_argument("-u", type=float, default=None,
                        help=("Upper limit on time in written data "
                              "(-w implied) [default: %(default)s]"))
    parser.add_argument("-p", action="store_true", default=False,
                        help="Create plots [default: %(default)s]")
    parser.add_argument("-o", action="store_true", default=False,
                        help="Open plots [default: %(default)s]")
    parser.add_argument("-s", action="store_true", default=False,
                        help="Print summary of file [default: %(default)s]")
    parser.add_argument("-c", action="store_true", default=False,
                        help="Convert to SI [default: %(default)s]")
    parser.add_argument("-n", default=1, type=int,
                        help="Use every n data points [default: %(default)s]")
    parser.add_argument("files", nargs="+", help="Netcdf files to open")
    args = parser.parse_args(argv)

    if "all" in args.files:
        d = os.getcwd()
        args.files = [os.path.join(d, x) for x in os.listdir(d)
                      if x.endswith(".ncdf") or x.endswith(".nc")]

    for i, f in enumerate(args.files):
        if not os.path.isfile(f):
            fnam, fext = os.path.splitext(f)
            if not fext and os.path.isfile(f + ".nc"):
                args.files[i] = f + ".ncdf"
                continue
            parser.error("{0}: no such file".format(f))

    if args.u or args.W:
        args.w = True

    if args.o:
        args.p = True

    # open netcdf file
    for f in args.files:

        netcdf = NetCDF(f, tosi=args.c, n=args.n)

        if not any([args.s, args.p, args.w]):
            logmes(netcdf.summary())

        if args.s:
            logmes(netcdf.summary())

        if args.p:
            netcdf.plot()

            if args.o:
                import re, subprocess
                files = " ".join(re.escape(x) for x in netcdf.plots)
                subprocess.call("open {0}".format(files), shell=True)

        if args.w:
            netcdf.write(upper=args.u, overwrite=args.W)

if __name__ == "__main__":
    main()

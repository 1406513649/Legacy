#!/usr/bin/env python
import argparse
import os
import sys
import re
import numpy as np
import math

X = os.path.basename(__file__)
DEBUG = False

manpage = """\
DESCRIPTION
  extract and process columns from a file. {0} is intended for quickly cutting
  columns of data from files by name or column number and performing
  elementary operations on the columns. Column names and numbers must begin
  with '$' (or the optional prefix character). When running from a command
  line, this may require proper quoting, ie.

  % {0} file '$cmd' ['$cmd2'...]

EXAMPLES
  Print columns 2 and 3 from file

  % {0} file '$2' '$3'

  Print columns 'time' and 'height'

  % {0} file '$time' '$height'

  Print columns 'time' multiplied by 2 and 'height' multiplied by 'width'

  % {0} file '$time * 2' '$height * $width'

  Data shifted by .0012 s. and truncated to 2e-4 s.
  % datread.py x18.dat '$1-.0012' '$remainder' --limits='0:2e-4'

""".format(X)


def _sqrt(a): return np.sqrt(a)
_sqrt.__doc__ = np.sqrt.__doc__
def _max(a): return np.amax(a)
_max.__doc__ = np.amax.__doc__
def _min(a): return np.amin(a)
_min.__doc__ = np.amin.__doc__
def _stdev(a): return np.std(a)
_stdev.__doc__ = np.std.__doc__
def _abs(a): return np.abs(a)
_abs.__doc__ = np.abs.__doc__
def _ave(a): return np.average(a)
_ave.__doc__ = np.average.__doc__
def _sin(a): return np.sin(a)
_sin.__doc__ = np.sin.__doc__
def _cos(a): return np.cos(a)
_cos.__doc__ = np.cos.__doc__
def _tan(a): return np.tan(a)
_tan.__doc__ = np.tan.__doc__
def _asin(a): return np.arcsin(a)
_asin.__doc__ = np.arcsin.__doc__
def _acos(a): return np.arccos(a)
_acos.__doc__ = np.arccos.__doc__
def _atan(a): return np.arctan(a)
_atan.__doc__ = np.arctan.__doc__
def _atan2(a): return np.arctan2(a)
_atan2.__doc__ = np.arctan2.__doc__
def _log(a): return np.log(a)
_log.__doc__ = np.log.__doc__
def _exp(a): return np.exp(a)
_exp.__doc__ = np.exp.__doc__
def _floor(a): return np.floor(a)
_floor.__doc__ = np.floor.__doc__
def _ceil(a): return np.ceil(a)
_ceil.__doc__ = np.ceil.__doc__
def _help(x): return x.__doc__


__globals__ = {"__builtins__": None}
__locals__ = {"sqrt": _sqrt, "max": _max, "min": _min, "stdev": _stdev,
              "std": _stdev, "sin": _sin, "cos": _cos, "tan": _tan,
              "asin": _asin, "acos": _acos, "atan": _atan, "atan2": _atan2,
              "pi": math.pi, "log": _log, "exp": _exp, "floor": _floor,
              "ceil": _ceil, "abs": _abs, "ave": _ave, "average": _ave, "np": np,
              "G": 9.80665, "help": _help, "inf": np.inf, "nan": np.nan}


class Data(object):

    def __init__(self, f, c="#", ci=False, zerobased=True, prefix="$",
                 limits=[None, None], verbosity=1, drange=[0, None],
                 cmnthead=False, float_fmt=None):
        """Data class reads and stores columnar data from f. The data can then
        be parsed through other methods.

        """
        # check input
        if not os.path.isfile(f):
            error("{0}: {1}: no such file".format(X, os.path.basename(f)))
        self._f = os.path.basename(f)
        self._c = c
        self.cmnthead = cmnthead
        self._ci = ci # case insensitive
        self._zb = zerobased
        self.prefix = prefix
        self.postfix = r"+-*\^)" + self.prefix
        self.limits = limits
        self.drange = drange
        self.verbosity = int(verbosity)
        self.float_fmt = float_fmt

        # get the header
        with open(f, "r") as fobj:
            first = fobj.readline()
            second = fobj.readline()
        self.h0 = self._c if first.strip()[0] == self._c else ""
        self._header, self._units = self.parse_header(first, second)
        if self._ci:
            self._header = [x.lower() for x in self._header]

        # get the data
        n = 1 if self._header else 0
        self._data = loadtxt(f, skiprows=n, comments=c)

        # header is now known, set up the columns
        self.name2col = dict([(name, i) for i, name in enumerate(self._header)])

        self._nrows, self._ncols = self._data.shape
        if self._header and self._ncols != len(self._header):
            print self._header
            error("Number of columns does not match length of header")

        self.eval_arrays = [None, []]
        self.eval_strings = [None, []]
        self.eval_scalars = [None, []]

    def Int(self, x, y=0):
        """Convert an item to an iteger, with possible offset y

        This method differs from the builtin int by converting first to a
        float and returning None if the object is not a number.
        """
        try:
            return int(float(x)) + y
        except ValueError:
            return None
        except TypeError:
            return None

    def eval_command_line(self, cmds):
        """Evaluate the command line requests

        Parameters
        ----------
        cmds : list
          List of commands

        Returns
        -------
        None

        Examples
        --------
        It is perhaps easiest to describe cmds by some examples

        1) Read and print columns 1, 2, and 8:
           cmd = [$1, $2, $8]
        2) Read and print columns labeled foo and bar
           cmd = [$foo, $bar]
        3) Read and print foo multiplied by bar
           cmd = [$foo * $bar]
        4) Read and print the maximum of column 1 and foo
           cmd = [max($1), max($foo)]

        """
        beg = re.escape(self.prefix)
        end = re.escape(self.postfix)
        regex = r"({0}.*?)([{1}]|{2}|$)".format(beg, end, self.prefix)

        # look for special keywords
        if "{0}all".format(self.prefix) in cmds:
            cmds = ["${0}".format(x+1) for x in range(self._ncols)]
        elif "{0}remainder".format(self.prefix) in cmds:
            cmds = cmds[:cmds.index("$remainder")]
            inc = []
            for cmd in cmds:
                inc.extend([self.idx(x[0]) for x in re.findall(regex, cmd)])
            cmds.extend("${0}".format(x+1) for x in range(self._ncols)
                        if x not in inc)

        # replace all '$item' column requests with the actual column of data
        # also replace all '$I' where I is an integer id with the name
        cmds_to_eval = []
        _cmds = [x for x in cmds]

        # apply range
        start, stop = self.drange
        for i, cmd in enumerate(cmds):
            _cmd = cmd
            matches = re.findall(regex, cmd)
            for match in matches:
                pattern = re.escape(match[0])
                col = self.columns(match[0].strip())[start:stop]
                repl = "np.array({0})".format(col.tolist())
                cmd = re.sub(pattern, repl, cmd, count=1)
                _cmds[i] = re.sub(pattern, self.colname(match[0].strip()), _cmd)
            cmds_to_eval.append(cmd)

        # loop through previously modified commands and evaluate them. Return
        # as sensible an error message as we can if the evaluation fails.
        arrays, scalars, strings = [], [], []
        for i, cmd in enumerate(cmds_to_eval):
            try:
                result = eval(cmd, __globals__, __locals__)
            except Exception, err:
                # bad command, try to give the user an idea of where it is
                if "msg" in dir(err):
                    errmsg = err.msg
                else:
                    errmsg = err.message
                line = "% {0} {1} {2}".format(
                    X, self._f, " ".join(["'{0}'".format(x) for x in cmds]))
                bad = cmds[i]
                m = re.search(re.escape(bad), line)
                s, e = m.start(), m.end()
                sys.stderr.write(
                    "\n{5}\n{0}{3}{1: ^{2}s}{4}\n"
                    .format(" " * s, "1", (e - s - 1), "<", ">", line))
                error("{0} at 1".format(errmsg))

            # store array, scalar, and string results separately.
            if isinstance(result, np.ndarray):
                arrays.append((_cmds[i], result))
            elif isinstance(result, (np.float, np.float64, float, int)):
                scalars.append((_cmds[i], result))
            else:
                strings.append((_cmds[i], result))

        # store the command and associated results
        try:
            a, b = zip(*arrays)
            b = np.array(b).T

            # apply limits
            if any(self.limits):
                l, u = self.limits
                rows = []
                for row in b:
                    if l is not None and row[0] < l:
                        continue
                    if u is not None and row[0] - u > 1e-16:
                        break
                    rows.append(row)
                b = np.array(rows)
            self.eval_arrays = (a, b)
        except ValueError:
            pass

        try:
            a, b = zip(*scalars)
            self.eval_scalars = (a, np.array(b))
        except ValueError:
            pass

        try:
            a, b = zip(*strings)
            self.eval_strings = (a, b)
        except ValueError:
            pass

        return

    def evaluated_cmds_and_arrays(self):
        """Return the cmd:result combo"""
        return self.eval_arrays

    def evaluated_cmds_and_scalars(self):
        """Return the cmd:result combo"""
        return self.eval_scalars

    def evaluated_cmds_and_strings(self):
        """Return the cmd:result combo"""
        return self.eval_strings

    def evaluated_arrays(self):
        """Return just the result from the cmd:result combo"""
        return self.eval_arrays[1]

    def evaluated_scalars(self):
        """Return just the result from the cmd:result combo"""
        return self.eval_scalars[1]

    def evaluated_strings(self):
        """Return just the result from the cmd:result combo"""
        return self.eval_strings[1]

    def parse_header(self, firstline, second):
        """Check if first line is a header - used to get columns by name"""
        header = split(firstline, c=self._c, isstring=True)
        units = split(second, c=self._c, isstring=True)
        return header, units

    def idx(self, item):
        """Given a '$item', return the appropriate column index"""

        _it = item.lstrip(self.prefix)
        _idx = self.Int(_it, -1)
        if _idx is None:
            if self._ci:
                _it = _it.lower()
            _idx = self.Int(self.name2col.get(_it))
        if _idx is None:
            error("{0}: no such column.  valid column names are:\n {1}"
                  .format(item, ", ".join(self._header)))
        if _idx > self._ncols:
            error("{0} not in columns".format(item))
        return _idx

    def colname(self, item):
        """Given a '$item', return the column name"""
        return self._header[self.idx(item)]

    def columns(self, *args):
        """Return the column of data given the integer column number"""
        if not args:
            idxs = range(self._ncols)
        else:
            idxs = [self.idx(x) for x in args]
        if len(idxs) == 1:
            idxs = idxs[0]
        return self._data[:, idxs]

    def header(self, asstring=False):
        """Return the header, using a comment character as the first character
        if the original had it"""
        head = [x.split() for x in self._header]
        # quote names with spaces
        if max(len(x) for x in head) > 1:
            head = ["'{0}'".format(" ".join(x)) for x in head]
        else:
            head = ["{0}".format(" ".join(x)) for x in head]

        if asstring:
            header = "{0} {1}".format(self.h0, " ".join(head))
        else:
            header = head
        return header

    def print_evaluated_arrays(self, print_column_numbers=False, skiprows=[],
                               print_header=False, nl=0, step=1, end=None):
        """Print evaluated arrays"""
        cmds, data = self.evaluated_cmds_and_arrays()

        if not len(data):
            return
        if nl:
            cout("\n" * nl)

        head = [x.upper().split() for x in cmds]
        if max(len(x) for x in head) > 1:
            head = ["'{0}'".format(" ".join(x).strip()) for x in head]
        else:
            head = ["{0}".format(" ".join(x).strip()) for x in head]

        w = max(max([len(x) for x in head]), 12)
        n = len(str(self._nrows + 1)) if print_column_numbers else 0
        out = "{{0: >{0}d}}: {{1}}".format(n) if n else "{1}"
        if self.verbosity > 0:
            cout("{0}: Evaluated Arrays".format(self._f))
        if print_header:
            c = "{0} ".format(self._c) if self.cmnthead else ""
            cout(c + out.format(0, " ".join("{0:{1}s}".format(
                            "".join(x.split()), w) for x in head)))

        if self.float_fmt:
            fmt = self.float_fmt
        else:
            fmt = "{0}.6E".format(w)
        for i in range(0, data.shape[0], step):
            row = data[i]
            if i + 1 in skiprows:
                continue
            cout(out.format(
                    i + 1, " ".join(["{0: {1}}".format(x, fmt) for x in row])))
            continue
        if end is not None:
            cout(end)

    def print_evaluated_scalars(self, print_header=False, nl=0):
        """Print evaluated scalars"""
        cmds, data = self.evaluated_cmds_and_scalars()
        if not len(data):
            return
        if nl:
            cout("\n" * nl)
        w = max(max([len(x) for x in cmds]), 12)
        if self.verbosity > 0:
            cout("{0}: Evaluated Scalars".format(self._f))
        if print_header:
            cout("{0}".format(
                    " ".join("{0:{1}s}".format(x.upper(), w) for x in cmds)))
        cout("{0}".format(" ".join(["{0: <{1}.6E}".format(x, w) for x in data])))
        return

    def print_evaluated_strings(self, nl=0):
        """Print evaluated strings"""
        cmds, data = self.evaluated_cmds_and_strings()
        if not len(data):
            return
        if nl:
            cout("\n" * nl)
        for i, cmd in enumerate(cmds):
            cout(cmd)
            cout(data[i])
        return


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="File to parse")
    parser.add_argument("cmds", nargs="*",
        help="Columns to process from file by column number or name")
    parser.add_argument("-v", default=1, type=int,
        help="Verbosity [default: %(default)s]")
    parser.add_argument("-C", default=False, action="store_true",
        help="Comment header in output [default: %(default)s]")
    parser.add_argument("--skiprows", action="append", default=[],
        help="Rows to skip [default: %(default)s]")
    parser.add_argument("-r", action="store_true", default=False,
        help="Print row numbers [default: %(default)s]")
    parser.add_argument("-n", type=int, default=1,
        help="Print every n lines [default: %(default)s]")
    parser.add_argument("-c", default="#",
        help="Comment character [default: %(default)s]")
    parser.add_argument("--no-header", default=False, action="store_true",
        help="Do not print header [default: %(default)s]")
    parser.add_argument("-H", default=False, action="store_true",
        help="Print man page and exit [default: %(default)s]")
    parser.add_argument("--prefix", default="$",
        help="Column number and name prefix [default: %(default)s]")
    parser.add_argument("--cols", default=False, action="store_true",
        help="Print column number:name and exit [default: %(default)s]")
    parser.add_argument("--limits", default=None,
        help=("Limits to operate on.  Specify as --limits='low:high' "
                       "[default: %(default)s]"))
    parser.add_argument("--range", default=None,
        help=("Range.  Specify as --range='start:stop' " "[default: %(default)s]"))
    parser.add_argument("--end", default=None,
        help=("Add to end (e.g. --end=exit for alegra "
              "include files) [default: %(default)s]"))
    parser.add_argument("--fmt", default="12.6E",
        help="Float point number format [default: %(default)s]")
    parser.add_argument("--dbg", default=False, action="store_true")

    if "-H" in argv:
        sys.exit("{0}\n{1}".format(parser.format_help(), manpage))

    args = parser.parse_args(argv)

    global DEBUG
    DEBUG = args.dbg

    limits = [None, None]
    if args.limits is not None:
        if ":" not in args.limits:
            parser.error("Invalid limits specification {0}".format(args.limits))
        try:
            l, u = [x.strip() for x in args.limits.split(":")]
        except ValueError:
            parser.error("Invalid limits specification {0}".format(args.limits))
        l = None if not l else eval(l, __globals__, __locals__)
        u = None if not u else eval(u, __globals__, __locals__)
        print l, u
        limits = [l, u]

    drange = [0, None]
    if args.range is not None:
        if ":" not in args.range:
            parser.error("Invalid range specification {0}".format(args.range))
        try:
            start, stop = [x.strip() for x in args.range.split(":")]
        except ValueError:
            parser.error("Invalid range specification {0}".format(args.range))
        start = 0 if not start else int(start)
        stop = None if not stop else int(stop)
        drange = [start, stop]

    data = Data(args.file, c=args.c, ci=True, zerobased=False, prefix=args.prefix,
                limits=limits, verbosity=args.v, drange=drange, cmnthead=args.C,
                float_fmt=args.fmt)

    if args.cols or not args.cmds:
        # print column: name
        header = data.header()
        mw = max([len(x) for x in header])
        nr = len(str(len(header)))
        cout("File: {0}".format(data._f))
        cout("Number of variables: {0}".format(len(header)))
        cout("Variables:")
        for i, name in enumerate(data.header()):
            cout("  {0: >{1}d}: {2}".format(i+1, nr, name.upper()))
        return

    # evaluate the command line
    if not args.cmds:
        error("Nothing to do")

    data.eval_command_line(args.cmds)

    data.print_evaluated_arrays(print_column_numbers=args.r,
                                print_header=not args.no_header,
                                skiprows=args.skiprows, step=args.n,
                                end=args.end)
    data.print_evaluated_scalars(print_header=not args.no_header, nl=1)
    data.print_evaluated_strings(nl=1)

    return


def split(line, c="#", d=r"\s", isstring=False):
    has_quotes = re.search(r'''["']''', line)
    if has_quotes:
        pat = re.compile(r'''((?:[^{0}"']|"[^"]*"|'[^']*')+)'''.format(d))
    else:
        pat = re.compile(r"{0}{{1,}}".format(d))

    line = line.split(c, 1)
    try:
        split_up = pat.split(line[1])
    except IndexError:
        split_up = pat.split(line[0])

    repl_quotes = lambda s: s.replace("'", "").replace('"', "").strip()
    split_up = [repl_quotes(x) for x in split_up if x.strip()]

    if isstring:
        # if split_up are all numbers, return an empty list
        try:
            [float(x) for x in split_up]
            split_up = []
        except ValueError:
            pass
    return split_up

def error(message):
    """Exit with error message"""
    if not DEBUG:
        raise SystemExit("{0}: {1}".format(X, message.rstrip()))
    raise ValueError(message)

def cout(message):
    """Write message"""
    if not message:
        return
    print message.rstrip()

def loadtxt(f, skiprows=0, comments="#"):
    """Load text from output files """
    if not os.path.isfile(f):
        error("{0}: {1}: no such file".format(X, os.path.basename(f)))
    lines = []
    for line in open(f, "r").readlines()[skiprows:]:
        try:
            line = [float(x) for x in line.split(comments, 1)[0].split()]
        except ValueError:
            break
        if not line:
            continue
        if not lines:
            ncols = len(line)
        if len(line) < ncols:
            break
        if len(line) > ncols:
            error("inconsistent data")
        lines.append(line)
    return np.array(lines)

if __name__ == "__main__":
    main(sys.argv[1:])

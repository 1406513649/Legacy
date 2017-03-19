#!/usr/bin/env python
import argparse
import os
import sys
import re
import numpy as np

X = os.path.basename(__file__)

def main(argv, stream=None):
    desc = """\
description: cut columns from a file.  {0} is intended for quickly cutting
columns of data from files by column number. """.format(X)
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("file", type=argparse.FileType(mode="r"), help="File")
    parser.add_argument("cols", nargs="+", type=int,
                        help="Columns to cut from file by column number")
    parser.add_argument("--skiprows", action="append", default=[],
                        help="Rows to skip [default %(default)s]")
    parser.add_argument("-n", action="store_true", default=False,
                        help="Print row numbers [default %(default)s]")
    parser.add_argument("-c", action="store", default="#",
                        help="Comment character [default %(default)s]")
    parser.add_argument("-H", action="store_true", default=False,
                        help="Do not print header [default %(default)s]")
    args = parser.parse_args(argv)

    if stream is None:
        stream = open(os.devnull, "a")

    lines = args.file.readlines()
    cols = [col - 1 for col in args.cols]
    M = max_width(lines, cols)
    n = len(str(len(lines)))
    out = "{0: >{1}d}: {2:s}\n" if args.n else "{2}\n"
    alllines = []
    for i, line in enumerate(lines):
        if i == 0:
            if args.H:
                continue
            line = split(line, c=args.c, isstring=True)
        else:
            line = line.split(args.c, 1)[0].split()

        if not line:
            continue

        if i in args.skiprows:
            continue

        line = ["{0:{1}s}".format(line[col], M) for col in cols]
        stream.write(out.format(i, n, "{0}".format(" ".join(line), M)))
        alllines.append(line)

    return np.array(alllines)

def max_width(lines, cols):
    mw = -1
    for line in lines:
        for i, item in enumerate(line.split()):
            if i in cols:
                mw = max(mw, len(item))
    return mw

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

if __name__ == "__main__":
    main(sys.argv[1:], stream=sys.stdout)

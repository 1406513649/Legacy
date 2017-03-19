import os
import sys
import inspect
import subprocess
import re

import numpy as np

def whoami():
    """ return name of calling function """
    return inspect.stack()[1][3]


def who_is_calling():
    """return the name of the calling function"""
    stack = inspect.stack()[2]
    return "{0}.{1}".format(
        os.path.splitext(os.path.basename(stack[1]))[0], stack[3])


def errors(_errors=[0], _increment=False, _reset=False):
    if _reset:
        _errors[0] = 0
        return
    if _increment:
        _errors[0] += 1
        return
    return _errors[0]


def report_error(message, count=True, anonymous=False, caller=None,
                 sysexit=True, pre="ERROR: "):
    """Report error to screen and write to log file if open"""
    if count:
        errors(_increment=True)
    message = "{0}{1}".format(pre, message)
    if not anonymous:
        if caller is None:
            caller = who_is_calling()
        message = message + " [reported by: {0}]\n".format(caller)
    if sysexit:
        raise SystemExit(message)
    sys.stderr.write(message)
    return


def file_not_found(f, count=True, sysexit=True):
    message = "{0}: no such file".format(f)
    caller = who_is_calling()
    report_error(message, caller=caller, count=count, sysexit=sysexit)
    return


def directory_not_found(f, count=True, sysexit=True):
    message = "{0}: no such directory".format(f)
    caller = who_is_calling()
    report_error(message, caller=caller, count=count, sysexit=sysexit)
    return


def loadtxt(f, skiprows=0, skipcols=None, comments="#", skipinf=False,
            cols=None, only=None):
    """Load text from output files

    Parameters
    ----------
    f : str
        File path
    skiprows : int
        skip first skiprows rows
    comments : str
        Comment character
    skipinf : bool
        Skip any rows with inf
    cols : list
        return only these columns
    only : list [deprecated]
        same as cols
    Returns
    -------
    data : array_like
        np array of data

    Comments
    --------

    This function is similar to np.loadtxt, but with fewer options and we stop
    reading the file if columns in a row are missing and return what we have
    up until there. np.loadtxt returns an error.

    """
    from numpy import inf, nan

    if not os.path.isfile(f):
        file_not_found(f)
    lines = []

    if skipcols is None:
        skipcols = []
    if not isinstance(skipcols, (list, tuple)):
        skipcols = [skipcols]
    skipcols = [int(i - 1) for i in skipcols]

    if only is not None:
        print "*** warning: only: deprecated option to loadtxt"

    if cols is not None and only is not None:
        report_error("cols and only cannot be specified together")
    elif only is not None:
        cols = only

    if cols is None:
        cols = []
    if not isinstance(cols, (list, tuple)):
        cols = [cols]
    cols = [int(i - 1) for i in cols]

    for rawline in open(f, "r").readlines()[skiprows:]:
        try:
            line = [eval(x) for x in rawline.split(comments, 1)[0].split()]
        except NameError, ValueError:
            break
        if not line:
            continue
        if skipinf and inf in line:
            continue
        if skipcols:
            line = [line[i] for i in range(len(line)) if i not in skipcols]
        if cols:
            line = [line[i] for i in range(len(line)) if i in cols]
        if not lines:
            ncols = len(line)
        if len(line) < ncols:
            break
        if len(line) > ncols:
            report_error("inconsistent data")
        lines.append(line)
        continue
    lines = np.array(lines)
    return lines


def mask_max(data, m):
    if m is None:
        m = np.inf
    return np.array(abs(data) < m)


def mask_outliers(data, m=2):
    return abs(data - np.median(data)) < m * np.std(data)


def remove_outliers(data, m=2):
    """Reject outliers from a numpy array"""
    return data[mask_outliers(data, m=m)]


def call(*cmd):
    return subprocess.call(" ".join(cmd), shell=True)


def find_in_path(exe):
    exe = os.path.basename(exe)
    for dirpath in os.getenv("PATH").split(os.pathsep):
        if exe in os.listdir(dirpath):
            return os.path.join(dirpath, exe)
    report_error("{0}: not found in path".format(exe))
    return

def find_app(App):
    apps = []
    app = " ".join(App.split()).lower()
    # Search directories, listed in order of precedence
    for p in [os.path.expanduser("~/Applications"), "/opt/macports/Applications", "/Applications"]:
        for ddf in os.walk(p):
            if not ddf[0].endswith(".app"):
                continue
            if App == os.path.splitext(os.path.basename(ddf[0]))[0]:
                return ddf[0]
            elif app in ddf[0].lower() and ddf[0].endswith(".app"):
                apps.append(ddf[0])
            del ddf[1][:]
    if not apps:
        return None
    # Sort, returning newest
    return sorted(apps, key=lambda x: os.path.basename(x))[-1]

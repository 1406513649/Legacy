#!/usr/bin/env python
"""Configure wasatch

"""
import os
import re
import sys
import imp
import shutil
import argparse
import subprocess
from distutils import sysconfig

def logmes(message, end="\n"):
    sys.stdout.write("{0}{1}".format(message, end))
    sys.stdout.flush()

def logerr(message, end="\n", errors=[0]):
    if message == "_inquire_":
        return errors[0]
    sys.stdout.write("*** setup: error: {0}{1}".format(message, end))
    errors[0] += 1

def logwrn(message, end="\n", warnings=[0]):
    if message == "_inquire_":
        return warnings[0]
    sys.stdout.write("*** setup: warning: {0}{1}".format(message, end))
    warnings[0] += 1

def stop(msg=""):
    sys.exit("setup: error: Stopping due to previous errors. {0}".format(msg))


def main(argv=None):
    """Setup the wasatch executable

    """
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-bytecode", default=False,
        action="store_true", help="Write python byte code [default: %(default)s]")
    args = parser.parse_args(argv)

    # module level variables
    fpath = os.path.realpath(__file__)
    fdir, fnam = os.path.split(fpath)
    pypath = [fdir]

    tools = os.path.join(fdir, "toolset")
    src = os.path.join(fdir, "src")

    path = os.getenv("PATH", "").split(os.pathsep)
    logmes("setup: wasatch 0.0.1")

    # --- system
    logmes("checking host platform", end="... ")
    platform = sys.platform
    logmes(platform)
    sys.dont_write_bytecode = not args.write_bytecode

    # --- python
    logmes("setup: checking python interpreter")
    logmes("path to python executable", end="... ")
    py_exe = os.path.realpath(sys.executable)
    logmes(py_exe)

    # --- python version
    logmes("checking python version", end="... ")
    (major, minor, micro, relev, ser) = sys.version_info
    logmes("python {0}.{1}.{2}.{3}".format(*sys.version_info))
    if (major != 3 and major != 2) or (major == 2 and minor < 6):
        logerr("python >= 2.6 required")

    # --- 64 bit python?
    logmes("checking for 64 bit python", end="... ")
    if sys.maxsize < 2 ** 32:
        logmes("no")
        logerr("wasatch requires 64 bit python (due to exowrap)")
        make_exowrap = False
    else: logmes("yes")

    # --- numpy
    logmes("checking whether numpy is importable", end="... ")
    try:
        import numpy
        logmes("yes")
    except ImportError:
        logerr("no")

    # --- scipy
    logmes("checking whether scipy is importable", end="... ")
    try:
        import scipy
        logmes("yes")
    except ImportError:
        logerr("no")

    if logerr("_inquire_"):
        stop("Resolve before continuing")

    pypath = os.pathsep.join(x for x in pypath if x)
    for path in pypath:
        if path not in sys.path:
            sys.path.insert(0, path)

    # --- executables
    logmes("setup: writing executable scripts")
    name = "wasatch"
    wasatch = os.path.join(tools, name)
    pyfile = os.path.join(src, "wasatch.py")

    # remove the executable first
    remove(wasatch)
    pyopts = "" if not sys.dont_write_bytecode else "-B"
    logmes("writing {0}".format(os.path.basename(wasatch)), end="...  ")
    with open(wasatch, "w") as fobj:
        fobj.write("#!/bin/sh -f\n")
        fobj.write("export PYTHONPATH={0}\n".format(pypath))
        fobj.write("PYTHON={0}\n".format(py_exe))
        fobj.write("PYFILE={0}\n".format(pyfile))
        fobj.write("$PYTHON {0} $PYFILE $*\n".format(pyopts))
    os.chmod(wasatch, 0o750)
    logmes("done")

    py = os.path.join(tools, "wpython")
    remove(py)
    logmes("writing {0}".format(os.path.basename(py)), end="...  ")
    with open(py, "w") as fobj:
        fobj.write("#!/bin/sh -f\n")
        fobj.write("PYTHONPATH={0}\n".format(pypath))
        fobj.write("{0} {1} $*".format(py_exe, pyopts))
    os.chmod(py, 0o750)
    logmes("done")

    # --- configuration files
    write_config(fdir, True)
    logmes("writing __runopt__.py", end="... ")
    with open(os.path.join(fdir, "__runopt__.py"), "w") as fobj:
        fobj.write("""\
# runtime options
debug = False
sqa = False
reducedint = False
verbosity = 1""")
    logmes("written")

    logmes("setup: checking executables")
    os.chdir(os.path.join(fdir, "extra/inputs"))
    from src.wasatch import main as wasatch
    logmes("checking for basic functionality", end="... ")
    retval = wasatch("-v 0 quad4-1el.inp".split())
    wasatch("-v 0 --cleanall quad4-1el.inp".split())
    if retval == 0:
        logmes("yes")
    else:
        logmes("no")
        logerr("wasatch script not functional")

    if logerr("_inquire_"):
        stop()

    logmes("setup: Setup complete")
    return

def write_config(fdir, exodus):
    logmes("writing __config__.py", end="... ")
    with open(os.path.join(fdir, "__config__.py"), "w") as fobj:
        fobj.write("""\
ROOT = {0}
# configre options
exodus = {1}
""".format(repr(fdir), exodus))
    logmes("written")


def remove(paths):
    """Remove paths"""
    if not isinstance(paths, (list, tuple)):
        paths = [paths]

    for path in paths:
        pyc = path + ".c" if path.endswith(".py") else None
        try: os.remove(path)
        except OSError: pass
        try: os.remove(pyc)
        except OSError: pass
        except TypeError: pass
        continue
    return


if __name__ == "__main__":
#    if sys.argv[0] != FNAM:
#        raise SystemExit(
#            "configure.py must be executed from {0}".format(fdir))
    main()

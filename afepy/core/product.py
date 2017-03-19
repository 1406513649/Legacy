import os
from os.path import realpath, dirname, join, isfile, isdir, expanduser

SUPPRESS_USER_ENV = 0
AFEPY_D = dirname(dirname(realpath(__file__)))
MAT_D = join(AFEPY_D, "material")
assert isdir(MAT_D)
PKG_D = join(AFEPY_D, "lib")
MAT_LIB_DIRS = [MAT_D]

# User configuration
f = "afepyrc"
if isfile(f):
    RCFILE = realpath(f)
else:
    RCFILE = os.getenv("AFEPYRC") or expanduser("~/.{0}".format(f))

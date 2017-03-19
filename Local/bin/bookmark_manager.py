#!/usr/bin/env python
import os
import sys
import re
from os.path import join, expanduser, dirname, realpath, abspath, \
    isdir, isfile, basename, splitext
from subprocess import Popen, PIPE
from collections import OrderedDict
from argparse import (ArgumentParser, RawDescriptionHelpFormatter,
                      SUPPRESS, RawTextHelpFormatter, REMAINDER)

HOME = expanduser("~")
D = dirname(realpath(__file__))
UPRE = r"^[u]+$"
PPRE = r"^[p]+$"
IPRE = r"^[0-9]+$"
PWD = os.getenv("PWD", Popen("pwd", stdout=PIPE).communicate()[0].strip())
SCRATCH = os.getenv("MYSCRATCH", '<ENV_NOT_DEFINED>')
LOCAL = os.getenv("DOT_LOCAL", os.path.expanduser("~/.local.d"))
FY = os.getenv("FY", '<ENV_NOT_DEFINED>')
DEVEL = os.getenv("DEVELOPER", '<ENV_NOT_DEFINED>')
SSH = 'ssh -AX '
MODE = None

HONOR = ['CELLAR', 'DOCUMENTS', 'MODULESHOME', 'TEXMFHOME',
         'UNISONLOC', 'DEVELOPER', 'FY', 'DOT_LOCAL', 'MODULEPATH_ROOT',
         'MY_APPLICATIONS', 'APPLICATIONS', 'MY_MODULEPATH_ROOT',
         'MYSCRATCH', 'HOME']
ENVIRON = OrderedDict([(k, os.getenv(k)) for k in HONOR if os.getenv(k)])

def dump(d, f, is_dict=1):
    with open(f, 'w') as fh:
        if is_dict:
            fh.write('\n'.join('{0} {1}'.format(k,d[k]) for k in sorted(d)))
        else:
            fh.write('\n'.join('{0}'.format(x) for x in d))


def load(f, is_dict=1):
    if is_dict:
        def split(line):
            if sys.version_info[0] == 2:
                return [x.strip() for x in line.split(None, 1)]
            return [x.strip() for x in line.split(maxsplit=1)]
        return dict([split(x) for x in open(f) if x.split()])
    return [x.strip() for x in open(f)]

def sub_envar_in_to_path(path, check_path=0):
    if SSH in path:
        return path
    if check_path:
        path = expand_envar_in_path(path)
        if not isdir(path):
            if verbosity:
                printc("Path {0!r} does not exist".format(path))
            return None
    for (envar, env_path) in ENVIRON.items():
        path = path.replace(env_path, '{{{0}}}'.format(envar))
    return path

class EnvVarDoesNotExist(Exception):
    def __init__(self, path):
        rx = re.compile(r'{(?P<e>.*)}')
        match = rx.search(path)
        if not match:
            self.envar = path
        else:
            self.envar = match.group('e')
        super(EnvVarDoesNotExist, self).__init__(path)

def expand_envar_in_path(path):
    if SSH in path:
        return path
    try:
        return realpath(path.format(**os.environ))
    except KeyError:
        if MODE == 'list':
            return path
        raise EnvVarDoesNotExist(path)

def printc(string):
    sys.stderr.write("{0}\n".format(string))

def which(name):
    path = os.path.realpath(name)
    if os.access(path, os.X_OK):
        return path
    n = os.path.basename(name)
    for d in os.environ.get("PATH", "").split(os.pathsep):
        x = os.path.join(d, n)
        if os.access(x, os.X_OK):
            return x

class GoToHistory:
    db_file = join(HOME, '.cdhistory')
    length = 50
    def __init__(self):
        try:
            self.db = load(self.db_file, 0)
        except IOError:
            self.db = []

    def __iter__(self):
        return self.db.__iter__()

    def get(self, i):
        try:
            return expand_envar_in_path(self.db[i])
        except IndexError:
            raise KeyError

    def dump(self):
        dump(self.db, self.db_file, 0)

    def save(self, d):
        d = sub_envar_in_to_path(d)
        if d in self.db:
            self.db.pop(self.db.index(d))
        self.db.append(d)
        self.db = self.db[-self.length:]
        self.dump()

    def write(self, stream=sys.stderr):
        for (i, d) in enumerate(self.db):
            stream.write("{0: 3d}: {1}\n".format(i+1, expand_envar_in_path(d)))

class GoToDB:
    db_file = join(HOME, '.bookmarks')
    defaults = {"home": HOME,
                "loc": LOCAL,
                "dt": join(HOME, "Desktop"),
                "dl": join(HOME, "Downloads"),
                "fy": FY,
                "dev": DEVEL,
                "docs": join(HOME, "Documents"),
                "etc": join(LOCAL, 'etc'),
                "scr": SCRATCH}
    if FY:
        defaults["proj"] = join(FY, "Projects")

    def __init__(self):
        self.db = self.read_db()

    def __iter__(self):
        return self.db.keys().__iter__()

    def __getitem__(self, key):
        return expand_envar_in_path(self.db[key])

    def read_db(self):
        db = dict(self.defaults)
        try:
            db.update(load(self.db_file))
        except IOError:
            pass
        return db

    def get(self, arg=None):
        if arg is None:
            return self.db
        if arg not in self.db:
            return None
        try:
            return expand_envar_in_path(self.db[arg])
        except EnvVarDoesNotExist as e:
            printc('Envar does not exist {0!r}'.format(e.envar))
            sys.exit(1)

    def save(self, key, path, envar, remote=False, force=False):
        """Save directory to bookmark with key"""

        if remote:
            self.db[key] = SSH + path
            self.dump()
            return

        if envar:
            # set the key to the environment variable
            self.db[key] = "{{{0}}}".format(path)
            self.dump()
            return

        if not isdir(path):
            printc("{0}: no such directory".format(path))
            return
        path = realpath(path)

        regex = r"^[up0-9]+$"
        if re.search(regex, key) or key in self.defaults:
            printc("{0}: reserved key".format(key))
            return

        # save directory, replacing paths
        path = sub_envar_in_to_path(path)
        if path in self.db.values():
            K = self.get_key(path)
            if K in self.defaults:
                d = expand_envar_in_path(path)
                printc("{0} is a default directory ({1})".format(d, K))
                return
            elif not force:
                d = expand_envar_in_path(path)
                printc("{0} is already saved ({1})".format(d, K))
                return
            self.db.pop(K, None)
        self.db[key] = path
        self.dump()
        return

    def dump(self):
        # sanitize before dumping
        db = {}
        for (k, v) in self.db.items():
            p = sub_envar_in_to_path(v)
            if p is None:
                continue
            db[k] = p
        dump(db, self.db_file)
        return

    def clean(self, key=None, path=None, dump=1, v=1):
        """Clean bookmarks of duplicate directory paths and nonexistent paths

        """
        if path is not None:
            key = self.get_key(path)

        if key is not None:
            if v:
                printc("clean_bookmarks: removing key: {0}".format(key))
            self.db.pop(key, None)
            if dump:
                self.dump()
            return

        pop = []
        for (k, d) in self.db.items():
            if d in [_d for (_k, _d) in self.db.items()
                     if _k != k and k not in self.defaults]:
                # skip repeated
                pop.append(k)
                if v:
                    d = expand_envar_in_path(d)
                    printc("removing duplicate: {0}: {1}".format(k, d))
                continue
            if not isdir(expand_envar_in_path(d)):
                # skip nonexistent
                pop.append(k)
                if v:
                    d = expand_envar_in_path(d)
                    printc("removing nonexistent: {0}: {1}".format(k, d))
                continue
        for k in pop:
            self.db.pop(k)

        if dump:
            self.dump()
        return

    def get_key(self, d):
        """Return the bookmarks key for directory d"""
        d = sub_envar_in_to_path(d)
        for (key, path) in self.db.items():
            if path == d:
                return key

gotohis = GoToHistory()
gotodb = GoToDB()

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    usage = "usage: go [-halswe] <dir|file|key|u[u[u...]]|p|?>"
    description = """
description:
visit (go) to a directory.

positional argument (one of the following)
  dir          Directory to visit
  file         File whose directory will be visited
  key          Go to location bookmarked as key
  u[u[u...]]   Go up len($@) directories
  p[p[p...]]   Go back len($@) directories in history
  ?            List the key (if any) pointing to PWD

optional arguments
  -h, --help     Show this help message and exit [default: False]
  -a             Follow symlinks [default: False]
  -d KEY         Purge KEY from database [default: None]
  --purge        Purge database of nonexistent locations [default: None]
  -l, --list     List keys in bookmarks [default: False]
  -k             Go to key, not directory [default: False]
  -e             Go to key, key is environment variable [default: False]
  -w KEY         Go to directory containing executable KEY [default: False]
  --md           Make directory if it does not exist [default: False]
  --cdhis, --his Write the cd history to the console [default: False]
  -s, --set KEY  Set (save) directory to the bookmarks database
  -f, --force    Force behavior instead of raising an error [default: False]
  --set-remote   Set remote host name to which go will ssh [default: False]
"""
    p = ArgumentParser(description=description, usage=usage, add_help=False,
                       formatter_class=RawDescriptionHelpFormatter)
    p.add_argument("-h", "--help", action="store_true", default=False)
    p.add_argument("-a", action="store_true", default=False,
        help="Follow symlinks [default: %(default)s]")
    p.add_argument("-d", default=None)
    p.add_argument("--purge", action="store_true", default=False)
    p.add_argument("-l", "--list", action="store_true", default=False)
    p.add_argument("-k", action="store_true", default=False)
    p.add_argument("-w", action="store_true", default=False)
    p.add_argument("--md", action="store_true", default=False)
    p.add_argument("-e", action="store_true", default=False)
    p.add_argument("--cdhis", "--his", action="store_true", default=False)
    p.add_argument("-s", "--set", nargs='+')
    p.add_argument("-f", "--force", action="store_true", default=False)
    p.add_argument("--set-remote", nargs=2)
    p.add_argument("goto", nargs="*", help=SUPPRESS)
    args = p.parse_args(argv)
    global MODE

    if args.help:
        sys.exit(usage + "\n\n" + description)

    if args.cdhis:
        gotohis.write()
        return 0

    if args.set or args.set_remote:
        MODE = 'set'
        envar, remote = False, False
        if args.set_remote:
            key, d = args.set_remote
            remote = True
        else:
            if len(args.set) == 2:
                key, d = args.set
                envar = True
            elif len(args.set) == 1:
                key, d = args.set[0], PWD
            else:
                raise ValueError("Expected len(set) == 1 or == 2)")
        gotodb.save(key, d, envar, force=args.force, remote=remote)
        return 0

    if args.d:
        MODE = 'clean'
        sys.exit(gotodb.clean(args.d))

    if args.purge:
        MODE = 'purge'
        sys.exit(gotodb.clean())

    if args.list:
        MODE = 'list'
        string = []
        for k in sorted(gotodb):
            string.append("{0:10s} {1}".format(k, gotodb[k]))
        sys.stderr.write("\n".join(string))
        return 0

    if not args.goto:
        sys.exit(p.error("Too few arguments"))

    MODE = 'goto'
    arg = args.goto[0]
    if arg == "?":
        key = gotodb.get_key(PWD)
        if key is None:
            sys.exit("{0}: not in bookmarks".format(PWD))
        sys.exit('Book mark for {0} => {1}'.format(PWD, key))

    elif args.md:
        d = arg
        if not isdir(d):
            os.makedirs(d)

    elif args.e:
        d = os.getenv(arg, None)
        if d is None:
            sys.exit("no environment variable {0}".format(arg))

    elif args.w:
        # find directory of executable
        p = which(arg)
        if p is None:
            sys.exit('executable {0!r} not found'.format(arg))
        d = os.path.dirname(p)

    elif isdir(arg) and not args.k:
        d = abspath(arg)

    elif isdir(" ".join(args.goto)) and not args.k:
        # spaces in directory name - argh!
        d = abspath(" ".join(args.goto))

    elif re.search(UPRE, arg):
        d = abspath(join(PWD, "../" * len(arg)))

    elif re.search(PPRE, arg):
        d = gotohis.get(-len(arg))

    elif re.search(IPRE, arg):
        i = int(arg) - 1
        try:
            d = gotohis.get(i)
        except KeyError:
            sys.exit("{0}: not in go history".format(arg))

    elif isfile(arg) and not args.k:
        if arg == "gohere":
            d = abspath(open(arg).readline().strip())
        elif args.a:
            d = dirname(realpath(arg))
        else:
            d = abspath(dirname(arg))

    else:
        d = gotodb.get(args.goto[0])
        if d is None:
            # See if maybe we want to go to a directory but got lazy typing
            dirs = [d for d in os.listdir(os.getcwd()) if isdir(d)]
            for d in dirs:
                if arg[:3] == d[:3]:
                    break
            else:
                printc("{0}: key not in bookmarks".format(args.goto[0]))
                return

        if SSH in d:
            print(d)
            return 0

        elif not isdir(d):
            printc('bookmarks key points to nonexistent directory: {0!r}'.format(d))
            sys.exit(gotodb.clean(args.goto[0]))

        d += os.path.sep + os.path.sep.join(args.goto[1:])

    if not isdir(d):
        printc('No such file or directory: {0!r}'.format(d))
        return 0

    gotohis.save(PWD)
    n = len(os.listdir(d))
    if n < 40:
        print('cd "{0}" ; ls -F'.format(d))

    else:

        print('cd "{0}"'.format(d))

    return 0

if __name__ == "__main__":
    sys.exit(main())

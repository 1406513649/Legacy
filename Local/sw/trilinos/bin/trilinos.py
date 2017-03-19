#!/usr/bin/env python
"""\
This script was written to help configuring Trilinos to build on Mac OS X,
where it has been traditionally more difficult than on Linux. At the time of
this writing, Trilinos will build without error using default arguments to this
script, but many MueLu and some Stokhos tests fail on OS X. Most of the default
options came from running the TriBITS checkin-tests-sems.sh script and
modifying enabled packages until Trilinos built without error (and wDocumentsithout
having to pass -k to make).

MODULES
This script uses environment modules to set correct paths to TPL include and
library directories. If run on a machine with Sandia's SEMS modules installed,
they should be found and TPLs setup. If using your own modules, pass the
--without-sems-env argument.

DEPENDENCIES
This script does not resolve all dependencies - that is the job of cmake. As a
result, if packages and enabled/disabled explicitly, a case can develop where
dependencies are not satisfied and cmake cannot configure Trilinos.

CONFIGURE (--configure)
Defines packages/TPLs/options for building Trilinos. A shell script
'do-configure' is written to the build directory that contains the current
configuration. Unless the --skip-configure switch is passed, do-configure is
also executed.

DASHBOARD (--dashboard)
Configures and makes a 'dashboard' build/test of Trilinos. Results of the
build/test step are transmitted to Trilinos CDash server. This build enables
many more packages and tests than is practical for development and exists
mostly to test Trilinos on OS X nightly via a cron job.

"""
from __future__ import print_function
import os
import re
import sys
import glob
import time
import stat
import shutil
import pickle
import logging
import datetime
import platform
import textwrap
import xml.dom.minidom as xdom
from collections import OrderedDict
from subprocess import Popen, check_output, STDOUT, PIPE
from argparse import ArgumentParser, RawDescriptionHelpFormatter
try:
    from configparser import ConfigParser, SectionProxy
except ImportError:
    from ConfigParser import ConfigParser, SectionProxy

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
if PY3:
    string_types = str, bytes
else:
    string_types = basestring,

if '--debug-script' in sys.argv[1:]:
    sys.argv.remove('--debug-script')
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)s: %(message)s')
else:
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)s: %(message)s')

DARWIN = 'darwin'
LINUX = 'linux'
D = os.path.dirname(os.path.realpath(__file__))
ETC = os.path.join(D, '../etc')

# --------------------------------------------------------------------- Section #
# General purpose utility functions
class colors:
    """Colorize a string"""
    regex = re.compile(r'{(?P<c>\w+):(?P<s>.*)}')
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ENDC = '\033[0m'
    @classmethod
    def format_string(cls, string):
        match = cls.regex.search(string)
        dikt = dict(red=cls.RED, blue=cls.BLUE,
                    green=cls.GREEN, yellow=cls.YELLOW,
                    bold=cls.BOLD, endc=cls.ENDC,
                    underline=cls.UNDERLINE,)
        if match:
            x = dikt[match.group('c')] + match.group('s') + cls.ENDC
            string = string[:match.start()] + x + string[match.end():]
        return string

def emit(self, record):
    """Monkey-patch a colored stream"""
    record.msg = colors.format_string(record.msg)
    self.stream.write(self.format(record)+'\n')
    self.flush()
logging.StreamHandler.emit = emit

def get_platform():
    """Return a symbolic constant for the current platform """
    if LINUX in sys.platform.lower():
        return LINUX
    elif DARWIN in sys.platform.lower():
        return DARWIN
    else:
        raise Exception('{0}: unknown platform'.format(sys.platform))

def available_cpu_count():
    """ Number of available virtual or physical CPUs on this system"""
    try:
        import multiprocessing
        return multiprocessing.cpu_count()
    except (ImportError, NotImplementedError):
        pass
    # BSD
    try:
        sysctl = subprocess.Popen(['sysctl', '-n', 'hw.ncpu'],
                                  stdout=subprocess.PIPE)
        num_cpu = int(sysctl.communicate()[0])
        if num_cpu > 0:
            return num_cpu
    except (OSError, ValueError):
        pass
    # Linux
    try:
        num_cpu = open('/proc/cpuinfo').read().count('processor\t:')
        if num_cpu > 0:
            return num_cpu
    except IOError:
        pass
    raise Exception('Can not determine number of CPUs on this system')

def remove(path):
    """Remove a path"""
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.isfile(path):
        os.remove(path)
    elif os.path.islink(path):
        os.unlink(path)
    else:
        raise Exception('Unknown path type!')
    return 0

def create_directory(directory, wipe_if_exists=0):
    if os.path.isdir(directory):
        if not wipe_if_exists:
            return directory
        remove(directory)
    os.makedirs(directory)
    return directory

def is_writeable(path):
    """Is the path writeable?"""
    return os.path.exists(path) and os.access(path, os.W_OK)

def is_executable(path):
    """Is the path executable?"""
    return os.path.exists(path) and os.access(path, os.X_OK)

def make_executable(filename):
    """Make the file executable"""
    st = os.stat(filename)
    os.chmod(filename, st.st_mode | stat.S_IEXEC)

def get_changed_files(src_dir, num_commit=None):
    """Get list of files (under git version control) changed"""
    git = which('git', required=1)
    git_dir = os.path.join(src_dir, '.git')
    if not os.path.isdir(git_dir):
        raise Exception('{0} is not a git directory'.format(src_dir))
    command = [git,
               '--git-dir={0}'.format(git_dir),
               '--work-tree={0}'.format(src_dir),
               'diff', '--name-only']
    if num_commit is not None:
        command.append('HEAD~{0}'.format(num_commit))
    output = decode_str(check_output(command))
    changed_files = [x for x in output.split('\n') if x.split()]
    return changed_files

def unique(a, sort=0):
    """Return only unique elements of a"""
    _unique = list(set(a))
    if sort:
        _unique = sorted(_unique)
    return _unique

def filter_list(a, b, sort=0):
    """Return all items in a that are not in b"""
    b = unique(b)
    filtered = [x for x in a if x not in b]
    if not sort:
        return filtered
    return sorted(filtered)

def which(exe, env=None, default=None, required=0):
    """Find path to executable exe on PATH"""
    env = env or os.environ
    for p in env.get('PATH', '').split(os.pathsep):
        filename = os.path.join(p, exe)
        if os.path.isfile(filename) and is_executable(filename):
            return str(filename)
    if required:
        raise Exception('Executable {0} not found'.format(exe))
    return default

def find_lib(lib, platform=None, env=None):
    key = 'LD_LIBRARY_PATH'
    platform = platform or PLATFORM
    if platform == DARWIN:
        key = 'DY' + key
    env = env or os.environ
    libpath = env.get(key, '').split(os.pathsep)
    libpath.extend(['/usr/lib', '/usr/lib64'])
    regex = r'lib{0}\.(a|dylib|so|la)$'.format(lib)
    for p in libpath:
        if not os.path.isdir(p):
            continue
        for f in os.listdir(p):
            if re.search(regex, f):
                return os.path.join(p, f)
    return None

def onoff(b):
    """Return the CMake boolean ON or OFF"""
    return {True: 'ON', False: 'OFF'}[bool(b)]

def wrap_list(the_list, space='    ', sort=0):
    """Line wrap a list to make it print all pretty"""
    if sort:
        the_list = sorted(the_list)
    s = ', '.join(the_list)
    return space + textwrap.fill(s, subsequent_indent=space)

def to_minutes(seconds):
    """Convert seconds to minutes"""
    return seconds / 60.

def split(arg, sep=None):
    """Split arg on sep. Only non-empty characters are included in the returned
       list
    """
    return [x.strip() for x in arg.split(sep) if x.split()]

def call(command, filename=None, env=None, cwd=None, errfile=None):
    """Wrapper around subprocess.Popen. If the optional filename is passed,
       open a file with that name and write stdout and stderr to it. env and
       cwd are passed directly to Popen

    """
    if not isinstance(command, (list,)):
        command = command.split()

    # stdout [re]direction
    fown = False
    if filename == os.devnull:
        fh = open(os.devnull, 'a')
    elif filename is not None:
        fh = open(filename, 'w')
        fown = True
    else:
        fh = sys.stdout

    # stderr [re]direction
    fe_own = False
    if errfile is not None:
        fe = open(errfile, 'w')
        fe_own = True
    else:
        fe = STDOUT

    # Call the command
    p = Popen(command, stdout=fh, stderr=fe, env=env, cwd=cwd)
    p.wait()

    if fown: fh.close()
    if fe_own: fe.close()

    if p.returncode != 0:
        if fown:
            err_msg = ''.join(open(filename, 'r').readlines()[-2:])
        else:
            stdout, stderr = p.communicate()
            err_msg = stdout if stderr is None else stderr
        raise SystemExit('The command {0} failed with the following '
                         'error:\n{1}'.format(' '.join(command), err_msg))

    return 0

def clean_build_directory(bld_dir):
    """Clean the Trilinos build directory"""
    pats_to_remove = ('CMake*', '*.cmake', 'CPack*', 'CTest*',
                      'DartConfig*', 'LICENSE.txt', 'Makefile*',
                      'README.txt', 'Testing', 'TrilinosConfig*',
                      'TrilinosRepVersion.txt', 'Trilinos_version.h',
                      'commonTools', 'do-configure', 'last_lib_dymmy.c',
                      'loaded_modules.sh', 'packages', 'test.gxl')
    for pat_to_remove in pats_to_remove:
        for item in glob.glob(os.path.join(bld_dir, pat_to_remove)):
            remove(item)

# --------------------------------------------------------------------- Section #
# ConfigParser monkey patching
def Bool(item):
    """Convert item in to a boolean"""
    item = str(item).strip()
    if item.lower() in ('false', 'off', '0'):
        return False
    elif item.lower() in ('true', 'on', '1'):
        return True
    return None

def List(item):
    """Separate item in to a list on ','"""
    return split(item, ',')

def Int(item):
    """Convert item in to an integer"""
    try:
        return int(float(item))
    except ValueError:
        return None

def Float(item):
    """Convert item in to an float"""
    try:
        return float(item)
    except ValueError:
        return None

def get2(self, key, priority=None, default=None, t=str):
    """Monkey patched method to SectionProxy of a ConfigParser object
       Emulates the 'get' method, but takes an optional type.

    Parameters
    ----------
    key : str
        The key to retrieve
    priority : type [None]
        Use this value over the default if not None
    default : type [None]
        The default value
    t : function [str]
        The function to convert the value of key

    Returns
    -------
    val : type [str]
        The value of the configuration option

    """
    val = self.get(key)
    if val is None:
        if priority is None:
            return default
        return priority
    val = t(str(val))
    if val is None:
        raise Exception('Unknown value {0!r} for '
                        'option {1}.{2}'.format(val, self.name, key))
    return val

def get_bool(self, thekey, priority=None, default=None):
    """Get a boolean type from the configuration"""
    if priority is None:
        returnval = Bool(default)
    else:
        returnval = Bool(priority)
    for (key, val) in self.items():
        if thekey == key:
            returnval = Bool(val)
        elif 'with_' + thekey == key:
            returnval = Bool(val)
        elif 'without_' + thekey == key:
            returnval = not Bool(val)
    return returnval

def get_int(self, key, priority=None, default=None):
    """Get an integer type from the configuration"""
    return self.get2(key, priority=priority, default=default, t=Int)

def get_float(self, key, priority=None, default=None):
    """Get a float type from the configuration"""
    return self.get2(key, priority=priority, default=default, t=Float)

def get_list(self, key, priority=None, default=None):
    """Get a list from the configuration"""
    return self.get2(key, priority=priority, default=default, t=List)

def get_section(self, section):
    if section not in self:
        self.add_section(section)
    return self[section]

ConfigParser.get_section = get_section
SectionProxy.get2 = get2
SectionProxy.get_bool = get_bool
SectionProxy.get_int = get_int
SectionProxy.get_float = get_float
SectionProxy.get_list = get_list

# --------------------------------------------------------------------- Section #
# TPL management
def get_default_tpls(disable, platform=None):
    """Return the default enabled/disabled TPLs """

    # MPI is not included in the list of TPLs because it is controlled by a
    # configuration switch (MPI defaults to ON)
    platform = platform or PLATFORM
    all_tpls = ['BLAS', 'LAPACK', 'Zlib', 'Netcdf', 'HDF5',
                'ParMETIS', 'Boost', 'BoostLib', 'SuperLU',
                'Scotch', 'Pthread', 'BinUtils', 'CSparse',
                'GLM', 'Matio', 'METIS', 'X11']

    # Default TPLs to disable.
    disabled_tpls = ['BinUtils', 'CSparse', 'Matio', 'METIS',
                     'X11', 'GLM']

    if platform == DARWIN:
        disabled_tpls.extend(['Pthread', 'Scotch'])

    if disable:
        disabled_tpls.extend(disable)

    enabled_tpls = filter_list(all_tpls, disabled_tpls)
    return enabled_tpls, disabled_tpls

def get_tpl_info(environ, tpl_name):
    """Return the version, include, and library directories for tpl_name

    prefix is blank by default, but a value of SEMS_ is passed to find SEMS modules.

    TPLs are assumed to provide:
    - prefix<TPLNAME>_ROOT
    - prefix<TPLNAME>_INCLUDE_PATH
    - prefix<TPLNAME>_LIBRARY_PATH
    environment variables

    """
    prefix = 'SEMS_' if any(['SEMS_' in x for x in environ]) else ''
    TPL = tpl_name.upper()
    if TPL == 'BOOSTLIB':
        # Boost and BoostLib are same library (more or less)
        TPL = 'BOOST'
    root = environ.get(prefix + TPL + '_ROOT')
    if not bool(root):
        if TPL in ('BLAS', 'LAPACK', 'PTHREAD', 'MPI'):
            # provided by OS, let CMake find the necessary data
            return None
        else:
            errmsg = 'TPL {0!r} not properly configured'.format(tpl_name)
            raise RuntimeError(errmsg)
    else:
        inc_d = environ.get(prefix + TPL + '_INCLUDE_PATH')
        lib_d = environ.get(prefix + TPL + '_LIBRARY_PATH')
    return root, inc_d, lib_d

# --------------------------------------------------------------------- Section #
# Global options
PLATFORM = get_platform()

# --------------------------------------------------------------------- Section #
# Main environment class
class EnvironmentNotFoundError(Exception): pass
class Environment:
    """The environment manager.  Manages environment variables, modules, etc."""
    dump_filename = 'Environment.p'
    def __init__(self, src_dir, bld_dir,
                 moduleshome, modulecmd, modulepath, initialization_modules,
                 with_snl_proxy=False, environ=None):
        """Initialize the environment

        Parameters
        ----------
        src_dir : str
            The Trilinos source directory
        bld_dir : str
            The Trilinos build directory
        moduleshome : str [None]
            The base directory of the modules installation
        modulepath : str [None]
            Additional path to add to MODULEPATH
        with_snl_proxy : bool [False]
            Use the Sandia proxy settings

        """

        self.environ = {}
        self.src_dir = src_dir
        self.bld_dir = bld_dir

        # Create a default clean environment
        logging.info('Creating a clean (reproducible) environment')
        path = ['/usr/bin', '/usr/sbin', '/bin', '/sbin']
        if os.path.isdir('/opt/X11/bin'):
            path.append('/opt/X11/bin')

        self.environ = {'PATH': os.pathsep.join(path),
                        'SHELL': '/bin/bash',
                        'HOME': os.path.expanduser('~/'),}

        if environ is not None:
            self.environ.update(environ)

        logging.info('Initializing modules')
        self.modules = EnvironmentModules(moduleshome, modulecmd, modulepath)
        self.modules.initialize(self.environ)

        # Load the initialization modules
        if self.modules.using_sems:
            # Let SEMs know we are loading
            self.environ['SEMS_LOADING'] = '1'
            self.environ['SEMS_MODULEFILES_ROOT'] = '/projects/sems/modulefiles'

        if initialization_modules:
            s = wrap_list(initialization_modules, space='  ')
            logging.info('Loading the following initialization modules:')
            for item in s.split('\n'):
                logging.info('{green:%s}' % item)
        for module in initialization_modules:
            self.modules.eval('load', module, self.environ)

        logging.info('Done initializing modules')
        self.environ.pop('SEMS_LOADING', None)

        with_snl_proxy = with_snl_proxy or self.on_sandia_network()
        if with_snl_proxy:
            logging.info('Adding SNL proxy settings to the environment')
            proxy = 'wwwproxy.sandia.gov:80'
            self.environ['http_proxy'] = proxy
            self.environ['https_proxy'] = proxy
            self.environ['ftp_proxy'] = proxy

    def __iter__(self): return iter(self.environ)
    def keys(self): return self.environ.keys()
    def values(self): return self.environ.values()
    def items(self): return self.environ.items()

    def getenv(self, key, default=None):
        return self.environ.get(key, default)

    def setenv(self, key, value):
        self.environ[key] = value

    def get(self, key, default=None):
        return self.getenv(key, default=default)

    @classmethod
    def Read(cls, bld_dir):
        """Initialize the environment from previous"""
        filename = os.path.join(bld_dir, cls.dump_filename)
        if not os.path.isfile(filename):
            raise EnvironmentNotFoundErrr()
        with open(filename, 'rb') as fh:
            obj = pickle.load(fh)
        return obj

    def dump(self):
        """Write a pickled representation of self"""
        self.dump_modules()
        filename = os.path.join(self.bld_dir, self.dump_filename)
        with open(filename, 'wb') as fh:
            pickle.dump(self, fh)

    def dump_modules(self):
        """Dump modules loaded to a file for later loading"""
        filename = os.path.join(self.bld_dir, 'loaded_modules.sh')
        logging.info('Writing loaded modules {green:%s}' % filename)
        lines = ['#!/bin/sh']
        lines.append('module purge')

        compiler = mpi = None
        loaded_modules = self.environ['LOADEDMODULES'].split(os.pathsep)
        for module in loaded_modules:
            if 'gcc' in module:
                compiler = module
            elif 'clang' in module:
                compiler = module
            if 'openmpi' in module:
                mpi = module
            elif 'mpich' in module:
                mpi = module
            lines.append('module load {0}'.format(module))
        lines.append('export TRILINOS_DIR={0}'.format(self.src_dir))
        lines.append('export TRILINOS_BUILD={0}'.format(self.bld_dir))
        libvar = 'LD_LIBRARY_PATH'
        if PLATFORM == DARWIN:
            libvar = 'DY' + libvar
        lines.append('export {0}=$TRILINOS_BUILD/lib:${0}'.format(libvar))

        # Change the terminal title
        string = '{0}, {1}'.format(compiler, mpi)
        lines.append('echo -ne "\033]0;(Trilinos {0})\007"'.format(string))

        with open(filename, 'w') as fh:
            fh.write('\n'.join(lines))
            logging.info('Making {green:%s} executable' % filename)
            make_executable(filename)

    @staticmethod
    def on_sandia_network(with_snl_proxy=False):
        """Determine if script is being run on a computer connected to the Sandia
           network

        """
        logging.info('Checking if connected to Sandia network')
        if not with_snl_proxy:
            # first check if snl proxy envars are defined
            for key in ('https_proxy', 'http_proxy', 'ftp_proxy'):
                if 'sandia.gov' in os.getenv(key, ''):
                    with_snl_proxy = True
                    break
            else:
                node = platform.node()
                if 'sandia.gov' in node:
                    with_snl_proxy = True
                elif re.search(r'^cee[(rws)(\-build)(\-compute)]', node):
                    with_snl_proxy = True

        if with_snl_proxy:
            logging.info('Connected to Sandia network')
        else:
            logging.info('Could not determine if connected '
                         'Sandia network (assuming not)')
        return with_snl_proxy

    def load_module(self, module):
        self.modules.eval('load', module, self.environ)

# --------------------------------------------------------------------- Section #
# Environment modules
class EnvironmentModules:
    """Class that uses the installed environment modules to modify the internal
    environment."""

    def __init__(self, moduleshome, modulecmd, modulepath):

        moduleshome = os.path.expanduser(moduleshome)
        assert os.path.isdir(moduleshome)
        self.moduleshome = moduleshome

        modulecmd = os.path.expanduser(modulecmd)
        assert os.path.isfile(modulecmd)
        self.modulecmd = modulecmd

        self.modulepath  = os.path.join(self.moduleshome, 'modulefiles')
        for p in modulepath.split(os.pathsep):
            p = os.path.expanduser(p)
            if not os.path.isdir(p):
                raise Exception('Nonexistent directory in modulepath')
            self.modulepath += os.pathsep + p

        self.using_sems = '/projects/sems' in self.modulepath

        logging.info('Modules summary:')
        logging.info('  MODULESHOME={green:%s}' % (self.moduleshome))
        logging.info('  MODULECMD={green:%s}' % (self.modulecmd))
        logging.info('  MODULEPATH={green:%s}' % (self.modulepath))

    def initialize(self, environ):
        """Add the modulepath to the environ dictionary"""
        environ['MODULESHOME'] = self.moduleshome
        environ['MODULEPATH'] = self.modulepath

        # Get the module version
        version = re.search(r'(?P<v>[0-9]\.[0-9]\.[0-9]+)', self.moduleshome)
        if not version:
            version = 'None'
        else:
            version = version.group('v')
        environ['MODULE_VERSION_STACK'] = version
        environ['MODULE_VERSION'] = version
        environ['LOADEDMODULES'] = ''
        return None

    def eval(self, subcmd, arg, environ):
        """Evaluate the module sub command subcmd in the environment specified
           by the dictionary environ. The environ dictionary is changed in place.

        """
        if not environ.get('MODULEPATH'):
            raise Exception('MODULEPATH environment variable must be defined')

        def strip(item):
            """Strip beginning/ending quotations"""
            item = item.strip()
            if item[0] == '"' and item[-1] == '"':
                # strip quotations
                item = item[1:-1]
            # SEMs uses <NAME> as an identifier, but < gets escaped, so remove
           # the escape character
            item = re.sub(r'[\\]+', '', item)
            return item

        # Run the command with the bash shell module command. It does not
        # matter which shell is used, and the bash shell output is easily
        # parsed.
        command = [self.modulecmd, 'bash', '--silent', subcmd, arg]
        p = Popen(command, env=environ, stderr=PIPE, stdout=PIPE)
        p.wait()
        stdout, stderr = p.communicate()
        if stderr.split():
            # An error occurred
            cmd = ' '.join(command)
            raise Exception('The following error occurred while attempting '
                            'to execute {0}\n{1}'.format(cmd, stderr))

        # modulecmd writes output to stdout which is then `eval`d if run by a
        # shell. We mimic the behavior by capturing stdout and putting it in to
        # a dictionary that can be used to update the caller's environment.
        updated_environ = {}
        stdout = decode_str(stdout)
        stdout = ''.join(x for x in stdout.split('\n') if x.split())
        previous = None
        for item in stdout.split(';'):
            if not item.split():
                continue
            item = item.strip()
            if item.startswith('export '):
                key, value = previous.split('=', 1)
                updated_environ[key.strip()] = strip(value)
            previous = item
        environ.update(updated_environ)
        return None

# --------------------------------------------------------------------- Section #
# Trilinos package management
class TrilinosPackage:
    """Trilinos package class"""
    def __init__(self, **kwds):
        self.name = kwds.pop('name')
        self.type = kwds.pop('type')
        self.dirname = kwds.pop('dir')
        self.parent = kwds.pop('parent')
        self.is_parent = not bool(self.parent)
        for (key, val) in kwds.items():
            setattr(self, key, val)

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def dependencies(self, tpls=False, tests=False, optional=False,
                     disp=0):

        if tpls:
            lib_req = self.lib_required_dep_tpls or []
            lib_opt = self.lib_optional_dep_tpls or []
            test_req = self.test_required_dep_tpls or []
            test_opt = self.test_optional_dep_tpls or []
        else:
            lib_req = self.lib_required_dep_packages or []
            lib_opt = self.lib_optional_dep_packages or []
            test_req = self.test_required_dep_packages or []
            test_opt = self.test_optional_dep_packages or []

        if disp:
            suffix = 'tpls' if tpls else 'pkgs'
            d = {'required_{0}'.format(suffix): lib_req,
                 'optional_{0}'.format(suffix): lib_opt,
                 'test_req_{0}'.format(suffix): test_req,
                 'test_opt_{0}'.format(suffix): test_opt}
            return d

        if optional:
            lib_req.extend(lib_opt)
        if tests:
            lib_req.extend(test_req)
        if tests and optional:
            lib_req.extend(test_opt)
        return unique(lib_req, sort=1)

class TrilinosPackages:
    def __init__(self, src_dir, env=None):
        self.src_dir = src_dir
        self.all_packages = self.find_packages(src_dir, env=env)
        self.enabled_pkgs = []
        self.disabled_pkgs = []

    def __iter__(self):
        for p in self.all_packages:
            yield p

    def __getitem__(self, key):
        p = self.get(key)
        if p is None:
            raise KeyError(key)
        return p

    def __contains__(self, key):
        return key in [p.name for p in self.all_packages]

    def get(self, key, dirname=0):
        for p in self.all_packages:
            if dirname:
                if p.dirname == key:
                    return p
            elif p.name == key:
                return p
        return None

    def cleanup_disabled_packages(self):
        disabled_pkgs = []
        disabled_names = [p.name for p in self.disabled_pkgs]
        for (i, p) in enumerate(self.disabled_pkgs):
            if p.parent in disabled_names:
                continue
            if p not in disabled_pkgs:
                disabled_pkgs.append(p)
        self.disabled_pkgs = disabled_pkgs

    def get_packages_from_changed_files(self, num_commit=None):
        changed_packages = []
        changed_files = get_changed_files(self.src_dir, num_commit=num_commit)
        for changed_file in changed_files:
            x_f = changed_file.split(os.path.sep)
            if x_f[0] != 'packages':
                logging.warning('Changed file {0} is not in the  '
                                'Trilinos/packages '
                                'directory'.format(changed_file))
                continue
            filename = changed_file
            while True:
                filename = os.path.dirname(filename)
                if not filename or filename == os.path.sep:
                    break
                package = self.get(filename, dirname=1)
                if package is not None:
                    break
            if package is None:
                raise Exception('Could not determine package for '
                                'file {0}'.format(changed_file))
            if package not in changed_packages:
                changed_packages.append(package)

        # Now that changed packages have been determined, determine the full
        # list of packages, including those dependent on changed packages
        affected_packages = []
        changed_package_names = [p.name for p in changed_packages]
        for p in self.all_packages:
            lib_dep = p.lib_required_dep_packages or []
            test_dep = p.test_required_dep_packages or []
            for dep in lib_dep + test_dep:
                if dep in changed_package_names:
                    affected_packages.append(p)
                    break

        for p in affected_packages:
            if p not in changed_packages:
                changed_packages.append(p)
        return changed_packages

    def apply_profile(self, profile, do_not_enable=None, platform=None):
        """Get the packages to enable/disable

        Parameters
        ----------
        profile : str
            The package profile
        platform : str
            The computing platform (os)

        """
        platform = platform or PLATFORM
        uprofile = None if not profile else profile.upper()
        if uprofile in (None, 'PT', 'DEFAULT'):
            enabled_pkgs = self.primary_tested()
        elif uprofile == 'ST':
            enabled_pkgs = self.primary_tested() + self.secondary_tested()
        elif uprofile == 'EX':
            enabled_pkgs = self.primary_tested() + self.secondary_tested() + self.experimental()
        elif uprofile.startswith('PRE-PUSH'):
            x = profile.split(':')
            if len(x) == 2:
                profile, num_commit = x
                num_commit = int(num_commit)
            elif len(x) == 1:
                num_commit = None
            else:
                raise Exception('pre-push profile accepts only 1 {0!r}'.format(':'))

            # Determine changed files and packages to test
            enabled_pkgs = self.get_packages_from_changed_files(num_commit)

        elif uprofile == 'TPETRA':
            tpetra_stack = ['Tpetra', 'TpetraCore', 'Ifpack2', 'Amesos2',
                            'Galeri', 'MueLu', 'Zoltan2', 'Belos', 'Xpetra',
                            'Sacado',
                            # Because Amesos2 depends on Amesos which depends
                            # on Epetra. If Epetra is enabled, Sacado requires
                            # EpetraExt
                            'Amesos', 'Epetra', 'EpetraExt']
            enabled_pkgs = [self[x] for x in tpetra_stack]
        else:
            raise Exception('Unknown package profile {0!r}'.format(profile))

        # List of packages to NOT enable
        do_not_enable = do_not_enable or []
        do_not_enable.extend(['KokkosExample', 'MeshingGenie',])
        if platform == DARWIN:
            # NOTE: STK and TrilinosCouplings are important packages - but STK
            # does not build on OS X (presently) and TrilinosCouplings leads to
            # many failed tests.
            do_not_enable.extend(['ROL', 'STK', 'TrilinosCouplings'])

        if uprofile == 'TPETRA':
            do_not_enable.extend(['SEACAS', 'Shards', 'FEI', 'Moertel', 'Panzer',
                                  'ThreadPool', 'OptiPack', 'Rythmos', 'STK',
                                  'Intrepid'])

        if 'STK' in do_not_enable:
            do_not_enable.extend([p.name for p in self.all_packages
                                  if 'STK' in p.name])

        if 'SEACAS' in do_not_enable:
            do_not_enable.extend([p.name for p in self.all_packages
                                  if 'SEACAS' in p.name])

        self.disabled_pkgs = [self.get(x) for x in do_not_enable if self.get(x)]
        self.enabled_pkgs = [p for p in enabled_pkgs
                             if p.name not in do_not_enable]

        return None

    def is_enabled(self, key):
        """Is key enabled?"""
        for p in self.enabled_pkgs:
            if p.name == key or p.parent == key:
                return True
        return False

    def disable_tpl_dep_pkgs(self, disabled_tpls, tests=False, optional=False):
        """Disable any packages that depend on disabled TPLs"""
        all_deps = {}
        for p in self.all_packages:
            if p not in self.enabled_pkgs:
                continue
            deps = p.dependencies(tpls=True, tests=tests, optional=optional)
            if not deps:
                continue
            for dep in deps:
                all_deps.setdefault(dep, []).append(p.name)

        to_remove = []
        for disabled_tpl in disabled_tpls:
            packages = all_deps.get(disabled_tpl)
            if not packages:
                continue
            s1 = ','.join(packages)
            s2 = disabled_tpl
            logging.info('Disabling {green:%s} because '
                         'TPL {green:%s} is disabled' % (s1, s2))
            to_remove.extend(packages)
        to_remove = unique(to_remove)
        self.disable_by_name(to_remove)

    def enable_by_name(self, enabled_pkg_names):
        """Enable TPLs in enabled_pkg_names"""
        for p in self.all_packages:
            if p.name in enabled_pkg_names:
                if p not in self.enabled_pkgs:
                    self.enabled_pkgs.append(p)
                if p in self.disabled_pkgs:
                    self.disabled_pkgs.remove(p)

    def disable_by_name(self, disabled_pkg_names):
        """Disable TPLs in enabled_pkg_names"""
        for p in self.all_packages:
            if p.name in disabled_pkg_names:
                if p not in self.disabled_pkgs:
                    self.disabled_pkgs.append(p)
                if p in self.enabled_pkgs:
                    self.enabled_pkgs.remove(p)

    def filter_by_type(self, p_type, names=0, parents=0):
        packages = [p for p in self.all_packages if p.type == p_type]
        if names:
            return sorted([p.name for p in packages])
        if parents:
            return [p for p in packages if p.is_parent]
        return packages

    def primary_tested(self, names=0, parents=0):
        return self.filter_by_type('PT', names=names, parents=parents)

    def secondary_tested(self, names=0, parents=0):
        return self.filter_by_type('ST', names=names, parents=parents)

    def experimental(self, names=0, parents=0):
        return self.filter_by_type('EX', names=names, parents=parents)

    def packages(self, names=0, parent=0):
        """Return a list of packages

        Parameters
        ----------
        names : bool [False]
            Return names only
        parent : bool [False]
            Return only those packages that are parent packages

        """
        if names:
            return sorted([p.name for p in self.all_packages])
        if parent:
            return [p for p in self.all_packages if p.is_parent]
        return self.all_packages

    def dependencies(self, key, tests=False, optional=False, tpls=False):
        """Get the list of dependencies for the package 'key'

        Parameters
        ----------
        key : str
            The name of the package
        tpls : bool [False]
            Return TPL dependencies
        tests : bool [False]
            Return testing dependencies
        optional : bool [False]
            Return optional dependencies

        Returns
        -------
        deps : list of package

        """
        p = self[key]
        deps = p.dependencies(tests=tests, optional=optional)
        all_deps = [x for x in deps]
        while 1:
            new_deps = []
            for dep in deps:
                p2 = self[dep]
                these_deps = p2.dependencies(tpls=False,
                                             tests=tests,
                                             optional=optional)
                if not these_deps:
                    continue
                for this_dep in these_deps:
                    if this_dep not in new_deps:
                        new_deps.append(this_dep)
            if not new_deps:
                break
            all_deps.extend(new_deps)
            deps = new_deps
        all_deps = unique(all_deps, sort=1)

        if tpls:
            tpls = []
            for dep in all_deps:
                p = self[dep]
                tpls.extend(p.dependencies(tpls=True, tests=tests,
                                           optional=optional))
            all_deps = unique(tpls, sort=1)

        return all_deps

    def write_dotfile(self, filename, tests=False, optional=False,
                      highlight=None):
        """Write a graphviz dot file

        Parameters
        ----------
        filename : str
            The filename to write
        tests : bool [False]
            Include test dependencies
        optional : bool [False]
            Include optional dependencies
        highlight : list
            List of packages to highlight

        Returns
        -------
        None

        Comments
        --------
        The highlight parameter is useful for highlighting different software
        stacks. For example, a Tpetra solver stack could specify

        highlight = ['Tpetra', 'Ifpack2', 'Amesos2', 'MueLu', 'Zoltan2', 'Belos']

        """
        try:
            from graphviz import Digraph
        except ImportError as e:
            logging.error('graphviz module is necessary to generate dot files')
            raise e

        # Graph colors
        grain = '#D7CEC7'
        blackboard = '#565656'
        oxblood = '#76323F'
        tan = '#C09F80'
        yellow = '#FCC02A'

        logging.info('Generating graphviz file: {green:%s}' % filename)
        dot = Digraph(engine='neato')
        dot.graph_attr['rankdir'] = 'TB'
        dot.graph_attr['size'] = "11,8.5"
        dot.graph_attr['margin'] = '0.5'
        dot.graph_attr['layout'] = 'dot'
        dot.graph_attr['nodesep'] = '.01'
        dot.graph_attr['start'] = '16'
        dot.graph_attr['overlap'] = 'false'
        dot.graph_attr['splines'] = 'true'
        dot.graph_attr['pack'] = 'true'
        dot.graph_attr['sep'] = '0.1'
        dot.edge_attr.update(arrowhead='vee', arrowsize='1')
        packages = self.packages(parent=1)
        highlight = highlight or []

        if highlight:
            stack = Digraph('stack')
            stack.body.append('color=black')
            dot.subgraph(stack)

        pt_color = oxblood
        st_color = tan
        ex_color = grain
        highlighted = yellow
        fontcolor = 'white'

        if highlight is not None:
            highlight = [x.upper() for x in highlight]

        def get_deps(p, tests, optional):
            return self.dependencies(p.name, tpls=False,
                                     tests=tests, optional=optional)

        for p in packages:
            if p.name == 'NewPackage':
                continue
            if p.name.upper() in highlight:
                attrs = {'shape': 'diamond', 'style': 'filled',
                         'fillcolor': highlighted, 'fontsize': '12',
                         'fontname': 'times-bold', 'fontcolor': 'white'}
            elif p.type == 'PT':
                attrs = {'shape': 'diamond', 'style': 'filled',
                         'fillcolor': pt_color, 'fontsize': '12',
                         'fontcolor': fontcolor}
            elif p.type == 'ST':
                attrs = {'shape': 'rectangle', 'style': 'filled',
                         'fillcolor': st_color, 'fontsize': '12',
                         'fontcolor': fontcolor}
            elif p.type == 'EX':
                attrs = {'shape': 'oval', 'style': 'filled',
                         'fillcolor': ex_color, 'fontsize': '12',
                         'fontcolor': fontcolor}
            else:
                raise Exception('Unknown type {0!r}'.format(p.type))
            n = dot.node(p.name, **attrs)
            deps = get_deps(p, tests, optional)
            for p2 in self.all_packages:
                if p2.parent == p.name:
                    deps2 = get_deps(p2, tests, optional)
                    if deps2:
                        deps.extend(deps2)
            deps = unique(deps)
            parent_deps = []
            for dep in deps:
                p1 = self[dep]
                if p1.is_parent:
                    parent_deps.append(p1.name)
                else:
                    parent_deps.append(p1.parent)
            deps = unique(parent_deps)
            for dep in deps:
                if dep == p.name:
                    continue
                dot.edge(p.name, dep)
#        with open(filename, 'w') as fh:
#            fh.write(dot.source)

        filename = os.path.realpath(filename)
        dirname = os.path.dirname(filename)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

        dot.render(filename)
        logging.info('Done generating graphviz file')

    @staticmethod
    def find_packages(src_dir, env=None):
        """Create and read the Trilinos dependencies XML file and return a list
        of all the Trilinos packages

        """
        logging.info('Finding Trilinos packages and their dependencies')
        def get_value(el, key, _split=1):
            value = str(el.getElementsByTagName(key)[0].getAttribute('value'))
            if not value:
                return None
            if not _split:
                return value.strip()
            return [str(x) for x in split(value, ',')]

        filename = create_trilinos_package_dependencies(src_dir, env=env)
        if not os.path.isfile(filename):
            raise Exception('Could not find Trilinos package '
                            'dependency file {0!r}'.format(f))

        logging.info('Parsing the Trilinos package dependencies file')
        packages = []
        keys = ['LIB_REQUIRED_DEP_PACKAGES', 'LIB_OPTIONAL_DEP_PACKAGES',
                'TEST_REQUIRED_DEP_PACKAGES', 'TEST_OPTIONAL_DEP_PACKAGES',
                'LIB_REQUIRED_DEP_TPLS', 'LIB_OPTIONAL_DEP_TPLS',
                'TEST_REQUIRED_DEP_TPLS', 'TEST_OPTIONAL_DEP_TPLS',]
        doc = xdom.parse(filename)
        root = doc.getElementsByTagName('PackageDependencies')[0]
        for p in root.getElementsByTagName('Package'):
            dikt = {'name': str(p.getAttribute('name').strip()),
                    'type': str(p.getAttribute('type').strip()),
                    'dir': str(p.getAttribute('dir').strip()),}
            for key in keys:
                dikt[key.lower()] = get_value(p, key)
            dikt['parent'] = get_value(p, 'ParentPackage', _split=0)
            packages.append(TrilinosPackage(**dikt))
        logging.info('Done finding the Trilinos packages (and dependencies)')
        return packages


# --------------------------------------------------------------------- Section #
# Create the Trilinos package dependencies
def create_trilinos_package_dependencies(src_dir, bld_dir=os.getcwd(),
                                         env=None):
    """Create an XML file with the Trilinos dependency graph

    Parameters
    ----------
    src_dir : str
        The Trilinos source directory
    bld_dir : str [PWD]
        The Trilinos build directory

    Returns
    -------
    filename : str
        The path to the XML dependencies file

    """
    project = 'Trilinos'
    assert os.path.isdir(src_dir)
    tribits = os.path.join(src_dir, 'cmake/tribits')
    assert os.path.isdir(tribits), tribits
    cmake_script = os.path.join(tribits,
                                'ci_support/TribitsDumpDepsXmlScript.cmake')
    assert os.path.isfile(cmake_script)
    logging.info('Creating the Trilinos dependencies graph')

    filename = os.path.join(bld_dir, '{0}Dependencies.xml'.format(project))
    logging.info('Trilinos dependencies graph file: {green:%s}' % filename)
    command = [which('cmake', env=env, required=1),
               '-DPROJECT_NAME=Trilinos',
               '-DPROJECT_SOURCE_DIR={0}'.format(src_dir),
               '-D{0}_TRIBITS_DIR={1}'.format(project, tribits),
               '-D{0}_PRE_REPOSITORIES='.format(project),
               '-D{0}_EXTRA_REPOSITORIES='.format(project),
               '-D{0}_DEPS_XML_OUTPUT_FILE={1}'.format(project, filename),
               '-P', cmake_script]
    logging.info('Done creating the Trilinos dependencies graph')
    call(command, cwd=bld_dir, filename=os.devnull)
    return filename

# --------------------------------------------------------------------- Section #
# User configuration
def get_default_configuration_file(bld_dir, default_config_file=None):
    """Get the default configuration file

    Returns
    -------
    default_config_file : str
        Realpath to the configuration file

    Notes
    -----
    There a few possible values for default configuration file

    On Darwin the options are:
      1. Macports
      3. SEMS
    On Linux the options are:
      1. SEMS

    """
    isdir = lambda d: os.path.isdir(os.path.expanduser(d))
    isfile = lambda f: os.path.isfile(os.path.expanduser(f))

    # Environment variables take precedence
    if default_config_file is not None:
        if not os.path.isfile(default_config_file):
            if os.path.isfile(os.path.join(ETC, default_config_file)):
                default_config_file = os.path.join(ETC, default_config_file)
        if not os.path.isfile(default_config_file):
            raise Exception('DEFAULT_TRILINOS_CFG file not found')

    elif isfile(os.path.join(bld_dir, 'Default.cfg')):
        default_config_file = os.path.join(bld_dir, 'Default.cfg')

    elif PLATFORM == DARWIN:
        default_config_file = PLATFORM.title() + '-MP.cfg'

    else:
        default_config_file = PLATFORM.title() + '-SEMS.cfg'

    default_config_file = os.path.join(ETC, default_config_file)
    assert os.path.isfile(default_config_file)
    return default_config_file

def get_user_configuration(config_file, default_config_file=None,
                           bld_dir=os.getcwd(), v=1):
    """Read the user configuration"""
    # Get the configuration
    verbose = abs(v) > 0

    logging.info('Looking for user configuration')
    parser = ConfigParser(allow_no_value=True)
    parser.optionxform = lambda option: option # retain case sensitivity

    default_config_file = get_default_configuration_file(bld_dir,
        default_config_file=default_config_file)
    if verbose:
        logging.info('Loading default configuration file: '
                     '{green:%s}' % default_config_file)
    parser.read(default_config_file)

    if not config_file:
        if os.getenv('TRILINOS_CFG') is not None:
            config_file = os.environ['TRILINOS_CFG']

    if config_file:
        if not os.path.isfile(config_file):
            # Look for config file in known locations
            for d in (bld_dir, ETC):
                f = os.path.join(d, config_file)
                if os.path.isfile(f):
                    config_file = f
                    break
    else:
        # No config file is explicitly given, give precedence to ./Trilinos.cfg
        if os.path.isfile('Trilinos.cfg'):
            config_file = 'Trilinos.cfg'

    if config_file:
        if not os.path.isfile(config_file):
            raise Exception('Configuration file {0!r} does '
                            'not exist'.format(config_file))
        if verbose:
            s1 = config_file
            logging.info('Loading user configuration file: {green:%s}' % config_file)
        parser.read(config_file)

    if not os.path.isfile(os.path.join(bld_dir, 'Default.cfg')):
        with open(os.path.join(bld_dir, 'Default.cfg'), 'w') as fh:
            fh.write(open(default_config_file).read())

    return parser

# --------------------------------------------------------------------- Section #
# Main command line interface
def main():
    """Setup trilinos"""
    default_false = ' [default: False]'
    num_cpu_avail = int(available_cpu_count() / 2.)
    parser = ArgumentParser(description=__doc__,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('--src-dir',
        default=None,
        help='Trilinos source directory ' \
             '[default: TRILINOS_DIR environment variable]')
    parser.add_argument('--bld-dir',
        default=os.getcwd(),
        help='Trilinos build directory [default: %(default)s]')
    parser.add_argument('-f', '--configuration-file',
        default=None, dest='configuration_file',
        help='Name of user configuration file [default: Trilinos.cfg]')
    parser.add_argument('-F', '--default-configuration-file',
        default=None, dest='default_config_file',
        help='Name of default configuration file [default: <Platform>.cfg]')

    # --- Configuration Options --- #
    p1 = parser
    description = 'Configure Trilinos'
    p1.add_argument('-c', '--configure', action='store_true', default=False,
                    help=description+default_false)
    p1.add_argument('--skip-configure', default=None, action='store_true',
                    help='Write do-configure but skip the actual ' \
                         'configuration [default: False]')

    p2 = parser
    description = 'Dashboard build of Trilinos'
    p2.add_argument('--dashboard', action='store_true', default=False,
                    help=description+default_false)
    p2.add_argument('--nightly-base-dir', default='/scratch/trilinos/nightly',
          help='Base directory to clone and run tests [default: %(default)s]')
    p2.add_argument('--with-modules-home', default=None,
          help='Base directory to look for the Modules install. ' \
               'If installed by Homebrew, it will be auto-detected')
    p2.add_argument('--with-snl-proxy', default=False, action='store_true',
          help='Run git commands with the snl http[s] proxies ' \
                'set [default: %(default)s]')
    p2.add_argument('--with-git', default='/usr/bin/git',
          help='Path to alternative git executable [default: %(default)s]')
    p2.add_argument('--with-make', default='/usr/bin/make',
          help='Path to alternative make executable [default: %(default)s]')
    p2.add_argument('--with-testing-branch', default='develop',
          help='Trilinos branch to test [default: %(default)s]')

    # Build options
    p3 = parser
    description = 'Build after successful configure'
    p3.add_argument('-b', '--build', action='store_true', default=False,
                    help=description+default_false)
    p3.add_argument('--num-make-jobs', default=None, type=int,
                    help='Number of simultaneous make jobs ' \
                    '[default: {0}]'.format(num_cpu_avail))
    p3.add_argument('--tolerant-build', dest='tolerant',
                    default=None, action='store_true',
                    help='Tolerant make build ' \
                    '(add -k to make options) [default: False]')
    p3.add_argument('--install', default=None, action='store_true',
                    help='Install after successful build [default: False]')

    # Test options
    p4 = parser
    description = 'After building, test Trilinos'
    p4.add_argument('--test', action='store_true', default=False,
                    help=description+default_false)
    p4.add_argument('--num-ctest-jobs', default=None, type=int,
                    help='Number of simultaneous ctest jobs ' \
                    '[default: {0}]'.format(num_cpu_avail))
    p4.add_argument('--ctest-options', default=None,
                    help='Extra options to be sent to cmake')

    p5 = parser
    description = 'Generate graphviz .dot files for Trilinos dependencies'
    p5.add_argument('--gv', '--dependency-graph',
                    dest='dependency_graph',
                    action='store_true', default=False,
                    help=description+default_false)

    p6 = parser
    description = """Generate list of dependencies for package."""
    p6.add_argument('--deps', '--dependencies',
                    dest='dependencies', action='store_true', default=False,
                    help=description+default_false)
    p6.add_argument('--package', action='append', help='Package name[s]')
    p6.add_argument('--optional-deps', default=None, action='store_true',
                    help='Show optional dependencies [default: False]')

    args = parser.parse_args()

    # Source and build directories
    src_dir = args.src_dir
    if src_dir is None:
        # Look for the Trilinos source directory. If not given, look in the
        # TRILINOS_DIR environment variable
        src_dir = os.getenv('TRILINOS_DIR')
        if src_dir is None:
            raise Exception('TRILINOS_DIR must be defined if '
                            '--src-dir is not specified')
    src_dir = os.path.realpath(os.path.expanduser(src_dir))
    if not os.path.isdir(src_dir):
        raise Exception('Source directory {0!r} does not exist'.format(src_dir))
    bld_dir = os.path.expanduser(args.bld_dir)

    if args.configure:
        configure_trilinos(src_dir, bld_dir,
                           skip_configure=args.skip_configure,
                           config_file=args.configuration_file,
                           default_config_file=args.default_config_file)

    if args.build:
        build_trilinos(bld_dir, config_file=args.configuration_file,
                       default_config_file=args.default_config_file,
                       tolerant=args.tolerant, num_make_jobs=args.num_make_jobs,
                       install=args.install)
        return 0

    if args.dashboard:
        # Check that the nightly base directory is writeable
        logging.info('Checking the nightly-base-dir exists and is writeable')
        nightly_base_dir = os.path.expanduser(args.nightly_base_dir)
        if not is_writeable(nightly_base_dir):
            raise Exception('nightly-base-dir must exist and be writable')
        logging.info('nightly-base-dir exists and is writeable')

        make_dashboard(src_dir, nightly_base_dir, git=args.with_git,
                       make=args.with_make, numproc=args.j,
                       with_snl_proxy=args.with_snl_proxy,
                       testing_branch=args.with_testing_branch)
        return 0

    if args.dependency_graph:
        write_graphviz_files(src_dir)
        return 0

    if args.test:
        test_trilinos(bld_dir, config_file=args.configuration_file,
                      default_config_file=args.default_config_file,
                      num_ctest_jobs=args.num_ctest_jobs,
                      ctest_options=args.ctest_options)
        return 0

    if args.dependencies:
        print_dependencies(src_dir, args.package,
                           show_optional_deps=args.optional_deps)
        return 0

    return 0

# --------------------------------------------------------------------- Section #
# Configure Trilinos
def configure_trilinos(src_dir, bld_dir, profile=None, skip_configure=None,
                       config_file=None, default_config_file=None,
                       cmake_opts=None):
    """Configure Trilinos. Most arguments can be specified through the
       configuration file

    Parameters
    ----------
    src_dir : str
        The path to the Trilinos source directory
    bld_dir : str
        The path to the Trilinos build directory
    profile : str [None]
        The package profile
    skip_configure : bool [False]
        Skip the actual configuration (just write the do-configure script)
    config_file : str [None]
        File name of the configuration file

    Comments
    --------
    Every option can also be specified in the configuration file. Values
    given in passed arguments take precedence over values in the configuration
    file.

    """
    start_time = time.time()
    logging.info('Configuring Trilinos')

    # Verify source directory
    if not os.path.isdir(src_dir):
        raise Exception('Trilinos source directory does not exist')
    logging.info('Trilinos source directory: {green:%s}' % (src_dir))
    logging.info('Trilinos build directory: {green:%s}' % (bld_dir))

    parser = get_user_configuration(config_file, default_config_file, bld_dir)
    config = parser.get_section('configure')

    with_snl_proxy = config.get_bool('snl_proxy', default=False)

    user_env = {}
    for (key, val) in parser.get_section('configure.environment').items():
        if val is None:
            val = os.getenv(key)
        user_env[key] = val

    # Configure the environment/environment modules
    es = '{0} must be defined in modules.configure section'.format
    cfg_modules = parser.get_section('modules.configure')
    cfg_modules_load = parser.get_section('modules.load')

    moduleshome = cfg_modules.get2('moduleshome')
    assert bool(moduleshome), es('moduleshome')
    modulecmd = cfg_modules.get2('modulecmd')
    assert bool(modulecmd), es('modulecmd')
    modulepath = cfg_modules.get2('modulepath')
    assert bool(modulepath), es('modulepath')
    init_modules = cfg_modules_load.get_list('initialization_modules')
    assert bool(init_modules), es('initialization_modules')

    environ = Environment(src_dir, bld_dir,
                          moduleshome, modulecmd, modulepath, init_modules,
                          with_snl_proxy=with_snl_proxy,
                          environ=user_env)

    # Get modules to load from configuration
    modules_to_load = OrderedDict()
    compiler = cfg_modules_load.get2('compiler')
    assert bool(compiler), 'Compiler module not defined'
    modules_to_load['compiler'] = compiler

    mpi = None
    with_mpi = config.get_bool('mpi', default=True)
    if with_mpi:
        mpi = cfg_modules_load.get2('mpi')
        assert bool(mpi), 'Compiler module not defined'
        modules_to_load['mpi'] = mpi

    for (name, module) in cfg_modules_load.items():
        if name in ('initialization_modules', 'compiler', 'mpi'):
            continue
        if not module or module.lower() == 'none':
            continue
        modules_to_load[name.lower()] = module

    # cmake executable -> this one must exist!
    if 'cmake' in modules_to_load:
        environ.load_module(modules_to_load.pop('cmake'))
    logging.info('Finding cmake executable')
    cmake = which('cmake', env=environ.environ, required=1)
    logging.info('cmake executable found ({green:%s})' % (cmake))

    # Ninja!
    with_ninja_generator = config.get_bool('ninja_generator', default=False)
    if with_ninja_generator:
        logging.info('Finding ninja executable')
        ninja = which('ninja', env=environ.environ, required=1)
        logging.info('ninja executable found ({green:%s})' % ninja)

    # Enabled/disabled packages
    profile = config.get2('profile', default=None)
    enabled_pkg_names = config.get_list('enabled_pkgs')
    disabled_pkg_names = config.get_list('disabled_pkgs')
    if (profile and enabled_pkg_names):
        raise Exception('profile and enabled_pkgs are mutually exclusive')

    trilinos_pkgs = TrilinosPackages(src_dir, env=environ.environ)
    if enabled_pkg_names:
        trilinos_pkgs.enable_by_name(enabled_pkg_names)
        if disabled_pkg_names:
            trilinos_pkgs.disable_by_name(disabled_pkg_names)
    else:
        if not profile:
            profile = 'default'
        logging.info('Using package profile {green:%s}' % (profile))
        trilinos_pkgs.apply_profile(profile, do_not_enable=disabled_pkg_names,
                                    platform=PLATFORM)

    # Enabled/disabled TPLs
    enabled_tpls = config.get_list('enabled_tpls')
    disabled_tpls = config.get_list('disabled_tpls')
    if not enabled_tpls:
        enabled_tpls, disabled_tpls = get_default_tpls(disabled_tpls,
                                                       platform=PLATFORM)

    if PLATFORM == DARWIN:
        # SEMS does not provide Scotch on Darwin
        do_not_enable = ['Scotch', 'METIS']
        enabled_tpls = [x for x in enabled_tpls if x not in do_not_enable]
        for tpl in do_not_enable:
            if tpl not in disabled_tpls:
                disabled_tpls.append(tpl)

    # Make sure all required TPLs are enabled
    with_tests = config.get_bool('tests', default=True)
    with_optional_deps = config.get_bool('optional_deps', default=False)
    for enabled_pkg in trilinos_pkgs.enabled_pkgs:
        tpl_deps = enabled_pkg.dependencies(tpls=True, tests=with_tests)
        for tpl_dep in tpl_deps:
            if tpl_dep in disabled_tpls:
                disabled_tpls.remove(tpl_dep)
            if tpl_dep not in enabled_tpls and tpl_dep != 'MPI':
                enabled_tpls.append(tpl_dep)

    trilinos_pkgs.cleanup_disabled_packages()
    trilinos_pkgs.disable_tpl_dep_pkgs(disabled_tpls, tests=with_tests,
                                       optional=with_optional_deps)

    # Warn about TPLs that don't have a module
    known_no_modules = ('BLAS', 'LAPACK', 'PTHREAD', 'BOOSTLIB')
    for tpl in enabled_tpls:
        if tpl.lower() not in modules_to_load:
            if tpl.upper() not in known_no_modules:
                logging.warning('No module defined for TPL {red:%s}' % tpl)

    logging.info('Loading the following environment modules:')
    s = wrap_list(modules_to_load.values(), space='  ')
    for item in s.split('\n'):
        logging.info('{green:%s}' % item)

    for (name, module) in modules_to_load.items():
        logging.debug('Loading module {green:%s}' % compiler)
        environ.load_module(module)

    logging.info('Done loading environment modules')
    loaded_modules = environ.environ['LOADEDMODULES'].split(os.pathsep)
    s = wrap_list(loaded_modules, space='  ')
    logging.debug('Loaded modules:')
    for item in s.split('\n'):
        logging.debug('{green:%s}' % item)

    logging.info('Setting up cmake environment')
    options = OrderedDict()

    # Set up the installation prefix and TriBITS directory
    if os.path.isdir(bld_dir):
        logging.info('Cleaning build directory')
        clean_build_directory(bld_dir)
        logging.info('Build directory cleaned')
    else:
        logging.info('Creating build directory')
        create_directory(bld_dir)
    options['CMAKE_INSTALL_PREFIX'] = bld_dir
    tribits = os.path.join(src_dir, 'cmake/tribits')
    options['Trilinos_TRIBITS_DIR:PATH'] = tribits

    # Testing options
    options['Trilinos_ENABLE_TESTS:BOOL'] = onoff(with_tests)
    if with_tests:
        logging.info('Enabling Trilinos tests')
        test_categories = config.get2('test_categories', default='BASIC')
        with_secondary_tests = config.get_bool('secondary_tests', default=False)
        test_timeout = config.get_float('test_timeout', default=600.)
        options['Trilinos_TEST_CATEGORIES:STRING'] = test_categories
        options['Trilinos_TRACE_ADD_TEST:BOOL'] = onoff(True)
        state = with_secondary_tests
        options['Trilinos_ENABLE_SECONDARY_TESTED_CODE:BOOL'] = onoff(state)
        options['DART_TESTING_TIMEOUT:STRING'] = test_timeout

    options['Trilinos_ALLOW_NO_PACKAGES:BOOL'] = onoff(False)

    # Shared libraries and link flags
    with_shared_libs = config.get_bool('shared_libs', default=True)
    options['BUILD_SHARED_LIBS:BOOL'] = onoff(with_shared_libs)
    extra_link_flags = []
    logging.debug('Looking for extra link libraries')
    for x in ('gomp', 'dl'):
        libx = find_lib(x, env=environ)
        if not libx:
            continue
        extra_link_flags.append(x)
        logging.debug('  %s: {green:%s}' % (x, libx))
    if with_shared_libs:
        x = 'ldl'
        libx = find_lib(x, env=environ)
        if libx:
            extra_link_flags.append(x)
            logging.debug('  %s: {green:%s}' % (x, libx))
    if extra_link_flags:
        extra_link_flags = ' '.join(['-l'+x for x in extra_link_flags])
        options['Trilinos_EXTRA_LINK_FLAGS'] = extra_link_flags

    with_debug = config.get_bool('debug', default=True)
    with_tests = config.get_bool('tests', default=True)
    if config.get_bool('tribits_std_settings', default=False):
        # Standard TriBITS configuration files. Most of the options in these
        # files are reflected in this script, but they are included for
        # completeness.
        files = []
        if with_debug:
            files.append('cmake/std/MpiReleaseDebugSharedPtSettings.cmake')
        if with_tests:
            files.append('cmake/std/BasicCiTestingSettings.cmake')
        if files:
            key = 'Trilinos_CONFIGURE_OPTIONS_FILE:STRING'
            options[key] = ','.join(files)

    # Debug options
    release_type = 'DEBUG' if with_debug else 'RELEASE'
    options['CMAKE_BUILD_TYPE:STRING'] = config.get2(
        'release_type', default=release_type)
    if with_debug:
        options['Trilinos_ENABLE_DEBUG:BOOL'] = onoff(with_debug)
        options['Trilinos_ENABLE_DEBUG_SYMBOLS:BOOL'] = onoff(with_debug)
        options['Teuchos_ENABLE_DEBUG:BOOL'] = onoff(with_debug)
        if trilinos_pkgs.is_enabled('Kokkos'):
            options['Kokkos_ENABLE_DEBUG:BOOL'] = onoff(with_debug)
        if trilinos_pkgs.is_enabled('Tpetra'):
            options['Tpetra_ENABLE_DEBUG:BOOL'] = onoff(with_debug)

    # More package options, again, the defaults came from checkin-tests-sems.sh
    with_complex = config.get_bool('complex', default=False)
    if with_complex:
        options['Teuchos_ENABLE_COMPLEX:BOOL'] = onoff(True)
        options['Tpetra_INST_COMPLEX_DOUBLE:BOOL'] = onoff(True)

    options['Teuchos_ENABLE_DEFAULT_STACKTRACE:BOOL'] = onoff(False)
    state = config.get_bool('all_pkgs', default=False)
    options['Trilinos_ENABLE_ALL_PACKAGES:BOOL'] = onoff(state)
    state = config.get_bool('all_optional_pkgs', default=False)
    options['Trilinos_ENABLE_ALL_OPTIONAL_PACKAGES:BOOL'] = onoff(state)
    state = config.get_bool('all_forward_dep_pkgs', default=False)
    options['Trilinos_ENABLE_ALL_FORWARD_DEP_PACKAGES:BOOL'] = onoff(state)
    #options['Trilinos_DISABLE_ENABLED_FORWARD_DEP_PACKAGES:BOOL'] = onoff(True)
    state = config.get_bool('explicit_instantiation', default=True)
    options['Trilinos_ENABLE_EXPLICIT_INSTANTIATION:BOOL'] = onoff(state)
    options['Trilinos_SHOW_DEPRECATED_WARNINGS:BOOL'] = onoff(True)

#    if PLATFORM == DARWIN:
#        options['TPL_ENABLE_CUDA:BOOL'] = onoff(False)
#        if trilinos_pkgs.is_enabled('Tpetra'):
#            options['Tpetra_INST_CUDA:BOOL'] = onoff(False)
#        if trilinos_pkgs.is_enabled('Kokkos'):
#            options['Kokkos_ENABLE_Cuda_UVM:BOOL'] = onoff(False)

    with_openmp = config.get_bool('openmp',
                                  default=False if PLATFORM==DARWIN else True)
    options['Trilinos_ENABLE_OpenMP'] = onoff(state)

    checked_stl = config.get_bool('checked_stl', default=True)
    options['Trilinos_ENABLE_CHECKED_STL:BOOL'] = onoff(checked_stl)

    # Compiler options. I believe these are more strict than what
    # checkin-tests-sems.sh uses. If using the intel compiler, these may need
    # to be modified (this script assumes gcc)
    options['CMAKE_CXX_FLAGS:STRING'] = '-Wall --pedantic -O3'
    options['CMAKE_C_FLAGS:STRING'] = '-Wall --pedantic -O3'

    # Look for a Fortran compiler. If it is found, and with_fortran was
    # requested, build with Fortran by default. If using intel, change
    # 'gfortran' in the which command to 'ifort' (this script assumes gcc)
    fc = os.getenv('FC') or which('gfortran', env=environ.environ)
    without_fortran = config.get_bool('fortran', default=True)
    with_fortran = (fc is not None) and (not without_fortran)

    #if with_fortran:
    #    options['Trilinos_EXTRA_LINK_FLAGS'] += ' -lgfortran'

    # C++ 11 support
    with_cxx11 = config.get_bool('cxx11', default=True)
    options['Trilinos_ENABLE_CXX11:BOOL'] = onoff(with_cxx11)
    if with_cxx11:
        # This flag may need to be modified if using clang, this script assumes
        # gcc
        #tjfulle:options['Trilinos_CXX11_FLAGS:STRING'] = '-std=c++11'
        pass

    # Set up compilers with/without MPI
    options['TPL_ENABLE_MPI:BOOL'] = onoff(with_mpi)
    if with_mpi:
        # determine the MPI root directory
        for (key, val) in environ.environ.items():
            if key in ('SEMS_MPI_ROOT', 'MPI_HOME'):
                break
        else:
            raise Exception('MPI_HOME not found')
        options['MPI_BASE_DIR:PATH'] = environ.environ[key]
        mpicxx, mpicc = environ.environ['MPICXX'], environ.environ['MPICC']
        options['CMAKE_CXX_COMPILER:FILEPATH'] = mpicxx
        options['CMAKE_C_COMPILER:FILEPATH'] = mpicc
        #if with_fortran:
        #    mpif90 = environ.environ['MPIF90']
        #    options['CMAKE_Fortran_COMPILER:FILEPATH'] = mpif90
    else:
        cxx, cc =  environ.environ['CXX'], environ.environ['CC']
        options['CMAKE_CXX_COMPILER:FILEPATH'] = cxx
        options['CMAKE_C_COMPILER:FILEPATH'] = cc
        #if with_fortran:
        #    f90 = environ.environ['F90']
        #    options['CMAKE_Fortran_COMPILER:FILEPATH'] = f90

    # Enabled and disabled packages
    s1 = str(len(trilinos_pkgs.enabled_pkgs))
    logging.info('Explicity enabling the following '
                 '{green:%s} Trilinos packages:' % s1)
    s = wrap_list([p.name for p in trilinos_pkgs.enabled_pkgs], space='  ',
                  sort=1)
    for item in s.split('\n'):
        logging.info('{green:%s}' % item)
    for enabled_pkg in trilinos_pkgs.enabled_pkgs:
        options['Trilinos_ENABLE_{0}:BOOL'.format(enabled_pkg.name)] = 'ON'

    s1 = str(len(trilinos_pkgs.disabled_pkgs))
    logging.info('Explicitly disabling the following '
                 '{yellow:%s} Trilinos packages:' % s1)
    s = wrap_list([p.name for p in trilinos_pkgs.disabled_pkgs],
                  space='  ', sort=1)
    for item in s.split('\n'):
        logging.info('{yellow:%s1}' % item)
    for disabled_pkg in trilinos_pkgs.disabled_pkgs:
        options['Trilinos_ENABLE_{0}:BOOL'.format(disabled_pkg.name)] = 'OFF'

    s1 = str(len(enabled_tpls))
    logging.info('Explicitly enabling the following {green:%s} TPLs:' % s1)
    s = wrap_list(enabled_tpls, space='  ', sort=1)
    for item in s.split('\n'):
        logging.info('{green:%s}' % item)
    for enabled_tpl in enabled_tpls:
        tpl_info = get_tpl_info(environ, enabled_tpl)
        options['TPL_ENABLE_{0}:BOOL'.format(enabled_tpl)] = onoff(True)
        if tpl_info is None:
            continue
        options['{0}_INCLUDE_DIRS:PATH'.format(enabled_tpl)] = tpl_info[1]
        options['{0}_LIBRARY_DIRS:PATH'.format(enabled_tpl)] = tpl_info[2]

    s1 = str(len(disabled_tpls))
    logging.info('Explicitly disabling the following {yellow:%s} TPLs:' % s1)
    s = wrap_list(disabled_tpls, space='  ', sort=1)
    for item in s.split('\n'):
        logging.info('{yellow:%s}' % item)
    for disabled_tpl in disabled_tpls:
        options['TPL_ENABLE_{0}:BOOL'.format(disabled_tpl)] = onoff(False)

    if 'Ifpack2' in trilinos_pkgs.enabled_pkgs:
        options['Ifpack2_Cheby_belos_MPI_1_DISABLE:BOOL'] = onoff(True)

    if 'Piro' in trilinos_pkgs.enabled_pkgs:
        options['Piro_EpetraSolver_MPI_4_DISABLE:BOOL'] = onoff(True)

    # Look for raw cmake options to disable
    cfg_opt = parser.get_section('configure.disable')
    if cfg_opt:
        for (key,val) in cfg_opt.items():
            for x in split(val, ','):
                options['-D{0}_ENABLE_{1}:BOOL'.format(key, x)] = 'OFF'

    # Look for raw cmake options to enable
    cfg_opt = parser.get_section('configure.enable')
    if cfg_opt:
        for (key,val) in cfg_opt.items():
            for x in split(val, ','):
                options['-D{0}_ENABLE_{1}:BOOL'.format(key, x)] = 'ON'

    if cmake_opts is None:
        cmake_opts = parser.get_section('configure.cmake')

    if cmake_opts is not None:
        for (key, val) in cmake_opts.items():
            options[key] = val

    # Change to the build directory and write the do-configure file
    do_configure = os.path.join(bld_dir, 'do-configure')
    logging.info('Writing configuration script to {green:%s}' % do_configure)
    with open(do_configure, 'w') as fh:
        fh.write('#!/bin/sh\n')
        fh.write(cmake + ' \\\n')
        if with_ninja_generator:
            fh.write('-GNinja \\\n')
        for (key, value) in options.items():
            try:
                if len(value.split()) > 1:
                    # put quotations around compound values
                    value = '"{0}"'.format(value)
            except AttributeError:
                pass
            fh.write('-D{0}={1} \\\n'.format(key, value))
        fh.write(src_dir)

    # make do-configure executable (pythonic version of chmod +x do-configure)
    logging.info('Making {green:%s} exectuable' % (do_configure))
    make_executable(do_configure)

    # Write the modules used to a file so that the environment can be
    # duplicated
    environ.dump()

    if skip_configure:
        # Just write the file and return
        logging.info('Trilinos cmake configuration written '
                     'to {green:%s}' % do_configure)
        t = to_minutes(time.time() - start_time)
        logging.info('Done (configure not performed) ({0:.2f} min.)'.format(t))
        return environ

    # Do the configuration!
    logging.info('Executing {green:%s}' % (do_configure))
    logfile = os.path.join(bld_dir, 'configure.out')
    logging.info('Configure log file: {green:%s}' % logfile)
    returncode = call([do_configure], env=environ.environ,
                      cwd=bld_dir, filename=logfile)
    if returncode != 0:
        raise Exception('Configure failed')

    filename = os.path.join(bld_dir, 'configure.success')
    with open(filename, 'w') as fh:
        fh.write('')
    t = to_minutes(time.time() - start_time)
    logging.info('Configure done ({0:.2f} min.)'.format(t))

    return environ

# --------------------------------------------------------------------- Section #
# Build Trilinos
def build_trilinos(bld_dir, config_file=None, num_make_jobs=None,
                   default_config_file=None, tolerant=None, install=None):
    """Build Trilinos.

    Parameters
    ----------
    bld_dir : str
        The path to the Trilinos build directory
    config_file : str [None]
        File name of the configuration file
    num_make_jobs : int [None]
        Number of simultaneous make jobs
    tolerant : bool [None]
        Tolerant make build (add -k to make command)
    install : bool [None]
        Install after successful build

    Comments
    --------
    Every option can also be specified in the configuration file. Values
    given in passed arguments take precedence over values in the configuration
    file.

    """
    start_time = time.time()
    logging.info('Building Trilinos')

    if not os.path.isfile('configure.success'):
        raise Exception('Trilinos must first be configured')

    # Get the configuration
    parser = get_user_configuration(config_file, default_config_file, bld_dir)
    config = parser.get_section('build')

    logging.info('Looking for previous environment configuration')
    try:
        environ = Environment.Read(bld_dir)
    except EnvironmentNotFoundError:
        raise Exception('Previous environment configuration not found.  '
                        'Trilinos must be first configured (with this script).')
    logging.info('Previous environment configuration found')

    if os.path.isfile(os.path.join(bld_dir, 'build.ninja')):
        # Ninja!
        exe = 'ninja'
        command = [which(exe, env=environ.environ, required=1)]
    else:
        # Make
        exe = 'make'
        num_cpu_avail = int(available_cpu_count() / 2.)
        num_make_jobs = config.get_int('num_make_jobs',
                                       default=num_cpu_avail, priority=num_make_jobs)
        command = [which(exe, env=environ.environ, required=1),
                   '-j{0}'.format(num_make_jobs)]
        tolerant = config.get_bool('tolerant', default=False, priority=tolerant)
        if tolerant:
            command.append('-k')

    build_success = os.path.join(bld_dir, 'build.success')
    if os.path.isfile(build_success):
        os.remove(build_success)

    logging.info('Building with: {green:%s}' % exe)
    if exe == 'make':
        s1 = str(num_make_jobs)
        logging.info('Number of simultaneous make jobs: {green:%s}' %s1)

    outfile = os.path.join(bld_dir, 'build.out')
    errfile = os.path.join(bld_dir, 'build.err')
    logging.info('Build log file: {green:%s}' % outfile)
    logging.info('Build error file: {green:%s}' % errfile)

    returncode = call(command, env=environ.environ,
                      cwd=bld_dir, filename=outfile, errfile=errfile)

    if returncode != 0:
        raise Exception('Build failed')

    with open(build_success, 'w') as fh:
        fh.write('')
    t = to_minutes(time.time() - start_time)
    logging.info('Build done ({0:.2f} min.)'.format(t))

    install = config.get_bool('install', default=False, priority=install)
    if install:
        command.append('install')
        logging.info('Installing')
        outfile = os.path.join(bld_dir, 'install.out')
        logging.info('Install log file: {green:%s}' % outfile)
        returncode = call(command, env=environ.environ,
                          cwd=bld_dir, filename=outfile)
        if returncode != 0:
            raise Exception('Install failed')
        logging.info('Install done')

    return 0

# --------------------------------------------------------------------- Section #
# Write graphviz files
def write_graphviz_files(src_dir):
    """Write the Trilinos GraphViz files

   Parameters
   ----------
   src_dir : str
       The Trilinos source directory

    """
    logging.info('Generating Trilinos dependency graphs for visualization')
    packages = TrilinosPackages(src_dir)
    basename = 'TrilinosDependencyGraph'
    packages.write_dotfile(basename + '.dot')

    tpetra_stack = ['Tpetra', 'Ifpack2', 'Amesos2', 'MueLu', 'Zoltan2', 'Belos']
    packages.write_dotfile(basename + '_TpetraSolverStack.dot',
                           highlight=tpetra_stack)
    epetra_stack = ['AztecOO', 'ML', 'Zoltan', 'Epetra', 'EpetraExt',
                    'Ifpack', 'Amesos', 'Isorropia', 'Thyra', 'Stratimikos']
    packages.write_dotfile(basename + '_EpetraSolverStack.dot',
                           highlight=epetra_stack)

    packages.write_dotfile(basename + '_WithOptionalDeps.dot',
                           optional=True)

    packages.write_dotfile(basename + '_WithOptionalDeps_WithTests.dot',
                           optional=True, tests=True)

    packages.write_dotfile(basename + '_WithTests.dot',
                           tests=True)
    logging.info('Done generating Trilinos dependency graphs')
    return 0

# --------------------------------------------------------------------- Section #
# Make a dashboard build
def make_dashboard(src_dir, nightly_base_dir, git='/usr/bin/git',
                   make='/usr/bin/make', with_snl_proxy=None,
                   testing_branch='develop', numproc=None):

    if numproc is None:
        numproc = int(available_cpu_count() * .75)

    # Check the git executable
    logging.info('Checking that git exists and is executable')
    if not is_executable(git):
        raise Exception('git command must exist and be executable')
    logging.info('{0} exists and is executable'.format(git))

    # Check the make executable
    logging.info('Checking that make exists and is executable')
    if not is_executable(make):
        raise Exception('make command must exist and be executable')
    logging.info('{0} exists and is executable'.format(make))

    # Create directory to run tests
    today = datetime.datetime.now().strftime("%Y.%m.%d")
    nightly_dir = os.path.join(nightly_base_dir, today)
    logging.info('Creating the nightly test directory at {0}'.format(nightly_dir))
    create_directory(nightly_dir, wipe_if_exists=1)

    # clone the repository
    url = 'https://github.com/trilinos/Trilinos.git'
    logging.info('Cloning the Trilinos git repository from {0}'.format(url))
    src_dir = os.path.join(nightly_dir, 'source')
    command = [git, 'clone', url, src_dir]
    logfile = os.path.join(nightly_dir, 'clone.log')
    # Minimal environment to clone
    environ = {
        'PATH': '/usr/bin:/usr/sbin:/bin:/sbin:/opt/X11/bin:/usr/local/bin',
        'HOME': os.path.expanduser('~/'),
        'SHELL': '/bin/bash',}
    with_snl_proxy = with_snl_proxy or Environment.on_sandia_network()
    if with_snl_proxy:
        proxy = 'wwwproxy.sandia.gov:80'
        environ['http_proxy'] = proxy
        environ['https_proxy'] = proxy
    call(command, filename=logfile, env=environ)
    logging.info('The Trilinos repository has been '
                 'cloned to {0}'.format(src_dir))
    # The checkin script looks for TRILINOS_DIR
    environ['TRILINOS_DIR'] = src_dir

    # Checkout the testing branch
    branch = testing_branch
    logging.info('Checking out the {0!r} branch'.format(branch))
    git_dir = os.path.join(src_dir, '.git')
    command = [git,
               '--git-dir={0}'.format(git_dir),
               '--work-tree={0}'.format(src_dir)]
    command.extend(['checkout', branch])
    call(command, filename=os.devnull, env=environ)
    logging.info('The {0!r} branch is checked out'.format(branch))

    # Make the checkin directory and run the checkin script
    build_dir = os.path.join(nightly_dir, 'build')
    logging.info('Creating the nightly build directory at {0}'.format(build_dir))
    create_directory(build_dir, wipe_if_exists=1)

    cmake_opts = {'-DCTEST_BUILD_FLAGS=-j{0}'.format(numproc),
                  '-DCTEST_PARALLEL_LEVEL={0}'.format(numproc)}
    environ = configure_trilinos(src_dir, build_dir, profile='PT',
                                 cmake_opts=cmake_opts)

    # Build the dashboard package
    command = [make, 'dashboard']
    logging.info('Making the dashboard package in {0}'.format(build_dir))
    logfile = os.path.join(nightly_dir, 'make.dashboard.out')
    call(command, filename=logfile, env=environ, cwd=build_dir)
    logging.info('Done making the dashboard package')

    return 0

def test_trilinos(bld_dir, config_file=None, num_ctest_jobs=None, verbose=1,
                  default_config_file=None, ctest_options=None):
    start_time = time.time()
    logging.info('Testing Trilinos')

    if not os.path.isfile('build.success'):
        raise Exception('Trilinos must first be built')

    # Get the configuration
    parser = get_user_configuration(config_file, default_config_file, bld_dir)
    config = parser.get_section('test')

    logging.info('Looking for previous environment configuration')
    try:
        environ = Environment.Read(bld_dir)
    except EnvironmentNotFoundError:
        raise Exception('Previous environment configuration not found.  '
                        'Trilinos must be first configured (with this script).')
    logging.info('Previous environment configuration found')

    # Make
    exe = 'ctest'
    num_cpu_avail = int(available_cpu_count() / 2.)
    num_ctest_jobs = config.get_int('num_ctest_jobs',
                                    default=num_cpu_avail, priority=num_ctest_jobs)
    command = [which(exe, env=environ.environ, required=1),
               '-j{0}'.format(num_ctest_jobs)]

    ctest_options = config.get2('ctest_options', priority=ctest_options)
    if ctest_options is not None:
        if isinstance(ctest_options, string_types):
            ctest_options = split(ctest_options, sep=' ')
        command.extend(ctest_options)

    outfile = errfile = None
    if not verbose:
        outfile = os.path.join(bld_dir, 'test.out')
        errfile = os.path.join(bld_dir, 'test.err')
        logging.info('Test log file: {green:%s}' % outfile)
        logging.info('Test error file: {green:%s}' % errfile)

    if PLATFORM == DARWIN:
        environ.setenv('OMPI_MCA_oob_tcp_if_exclude', 'lo,cscotun0')
        environ.setenv('OMPI_MCA_btl_tcp_if_exclude', 'lo,cscotun0')

    returncode = call(command, filename=outfile, errfile=errfile,
                      env=environ.environ, cwd=bld_dir)

    if returncode != 0:
        raise Exception('Test failed')

def print_dependencies(src_dir, packages, show_optional_deps=None):
    trilinos_pkgs = TrilinosPackages(src_dir)
    for package in packages:
        deps = trilinos_pkgs.dependencies(package, optional=show_optional_deps)
        logging.info('Dependencies for {green:%s}' % package)
        s1 = wrap_list(deps)
        for line in s1.split('\n'):
            logging.info(line)

def decode_str(x):
    if x is None:
        return None
    try:
        return x.decode('utf-8', 'ignore')
    except (AttributeError, TypeError):
        return x

if __name__ == '__main__':
    sys.exit(main())

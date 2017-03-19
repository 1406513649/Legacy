family('compiler')
# Determine platform
darwin = system_is_darwin()
if darwin:
  platform = 'Darwin10.11-x86_64'
else:
  platform = 'rhel6-x86_64'

name = self.name
upname = name.upper()
version = self.version
whatis("Module for " + name + " " + version)

# Find this modules binaries
prefix = os.path.join('/projects/sems/install', platform,
                      'sems/compiler', name, version, 'base')
if not os.path.isdir(prefix):
    log_error('Load error: ' + prefix + ' does not exist')

# Setup MODULEPATH for packages built by this compiler stack
MODULEPATH_ROOT = getenv('MY_MODULEPATH_ROOT')
MODULEPATH_C = os.path.join(MODULEPATH_ROOT, 'sems', platform, 'compiler')
if not os.path.isdir(MODULEPATH_C):
    log_error('Load error: ' + MODULEPATH_C + ' does not exist')

MODULEPATH = os.path.join(MODULEPATH_C, name, version)
if not os.path.isdir(MODULEPATH):
    log_error('Load error: ' + MODULEPATH + ' does not exist')
prepend_path("MODULEPATH", MODULEPATH)

# This modules paths
PATH = os.path.join(prefix, 'bin')
LIBRARY_PATH = os.path.join(prefix, 'lib')
LIBRARY_PATH64 = os.path.join(prefix, 'lib64')
INCLUDE_PATH = os.path.join(prefix, 'include')
MANPATH = os.path.join(prefix, 'share/man')

# Set the environment
if not os.path.isdir(PATH):
    log_error(name + '  bin directory not found')
prepend_path('PATH', PATH)

# Darwin requires different LD_LIBRARY_PATH environment
if not os.path.isdir(LIBRARY_PATH):
    log_error(name + '  lib directory not found')

LD_LIBRARY_PATH = 'LD_LIBRARY_PATH'
if darwin:
    LD_LIBRARY_PATH = 'DY' + LD_LIBRARY_PATH

if os.path.isdir(LIBRARY_PATH64):
    prepend_path(LD_LIBRARY_PATH, LIBRARY_PATH64)
prepend_path(LD_LIBRARY_PATH, LIBRARY_PATH)

if os.path.isdir(MANPATH):
    prepend_path('MANPATH', MANPATH)

# Set up the compiler specific environment
setenv('COMPILER', name)
setenv('COMPILER_VER', version)
cc = cxx = fc = None
if upname == 'GCC':
    cc, cxx, fc = 'gcc', 'g++', 'gfortran'
elif upname == 'INTEL':
    cc, cxx, fc = 'icc', 'icc', 'ifort'
elif upname == 'CLANG':
    cc, cxx = 'clang', 'clang++'

setenv('CC', os.path.join(PATH, cc))
setenv('CXX', os.path.join(PATH, cxx))
setenv('SERIAL_CC', os.path.join(PATH, cc))
setenv('SERIAL_CXX', os.path.join(PATH, cxx))

if fc is not None:
    setenv('FC', os.path.join(PATH, fc))
    setenv('F77', os.path.join(PATH, fc))
    setenv('F90', os.path.join(PATH, fc))

    setenv('SERIAL_FC', os.path.join(PATH, fc))
    setenv('SERIAL_F77', os.path.join(PATH, fc))
    setenv('SERIAL_F90', os.path.join(PATH, fc))

set_alias('gcc', os.path.join(PATH, cc))
set_alias('g++', os.path.join(PATH, cxx))
if fc is not None:
    set_alias('f90', os.path.join(PATH, fc))
    set_alias('f77', os.path.join(PATH, fc))

# SEMS specific environment variables
setenv('SEMS_' + upname + '_ROOT', prefix)
setenv('SEMS_' + upname + '_VERSION', version)
setenv('SEMS_' + upname + '_LIBRARY_PATH', LIBRARY_PATH)
setenv('SEMS_' + upname + '_INCLUDE_PATH', INCLUDE_PATH)

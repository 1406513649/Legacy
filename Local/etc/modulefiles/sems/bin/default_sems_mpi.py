prereq_any('gcc', 'intel', 'clang')
family('mpi')

# Determine platform
darwin = system_is_darwin()
if darwin:
    platform = 'Darwin10.11-x86_64'
else:
    platform = 'rhel6-x86_64'

name = self.name
upname = name.upper()
version = self.version

compiler = getenv('COMPILER')
compiler_version = getenv('COMPILER_VER')
prefix = os.path.join('/projects/sems/install', platform, 'sems/compiler',
                  compiler, compiler_version, name, version)
if not os.path.isdir(prefix):
    log_error('Load Error: ' + prefix + ' does not exist')

# Setup MODULEPATH for packages built by this MPI stack
MODULEPATH_ROOT = getenv('MY_MODULEPATH_ROOT')
MODULEPATH_C = os.path.join(MODULEPATH_ROOT, 'sems', platform, 'mpi',
                              compiler, compiler_version)
if not os.path.isdir(MODULEPATH_C):
    log_error('Load error: ' + MODULEPATH_C + ' does not exist')

MODULEPATH = os.path.join(MODULEPATH_C, name, version)
if not os.path.isdir(MODULEPATH):
    log_error('Load error: ' + MODULEPATH + ' does not exist')
prepend_path('MODULEPATH', MODULEPATH)

# This modules paths
PATH = os.path.join(prefix, 'bin')
MANPATH = os.path.join(prefix, 'share/man')
LIBRARY_PATH = os.path.join(prefix, 'lib')
LIBRARY_PATH2 = os.path.join(prefix, 'lib/openmpi')
INCLUDE_PATH = os.path.join(prefix, 'include')
if not os.path.isdir(INCLUDE_PATH):
    INCLUDE_PATH = os.path.join(INCLUDE_PATH, name)

# Set the environment
if not os.path.isdir(PATH):
    log_error(name + ' bin directory not found')
prepend_path('PATH', PATH)

if os.path.isdir(LIBRARY_PATH2):
    prepend_path('LD_LIBRARY_PATH', LIBRARY_PATH2)
    prepend_path('MPI_LIBRARY_PATH', LIBRARY_PATH2)

if os.path.isdir(LIBRARY_PATH):
    prepend_path('LD_LIBRARY_PATH', LIBRARY_PATH)
    prepend_path('MPI_LIBRARY_PATH', LIBRARY_PATH)

if os.path.isdir(MANPATH):
    append_path('MANPATH', MANPATH)

# Set up the MPI specific environment
setenv('MPI_BIN', PATH)
setenv('MPIHOME', prefix)
setenv('MPI_HOME', prefix)
setenv('MPI_NAME', name)
setenv('MPI_VERSION', version)
setenv('MPI_INCLUDE_PATH', INCLUDE_PATH)

setenv('MPICC', os.path.join(PATH, 'mpicc'))
setenv('MPICXX', os.path.join(PATH, 'mpicxx'))

if os.path.isfile(os.path.join(PATH, 'mpif90')):
    setenv('MPIFC', os.path.join(PATH, 'mpif90'))
    setenv('MPIF77', os.path.join(PATH, 'mpif77'))
    setenv('MPIF90', os.path.join(PATH, 'mpif90'))

if not os.path.isfile(os.path.join(PATH, 'mpicc')):
    log_error('MPI C compilers not found')

# SEMS specific environment variables
setenv('SEMS_' + upname + '_ROOT', prefix)
setenv('SEMS_' + upname + '_VERSION', version)
setenv('SEMS_' + upname + '_LIBRARY_PATH', LIBRARY_PATH)
setenv('SEMS_' + upname + '_INCLUDE_PATH', INCLUDE_PATH)

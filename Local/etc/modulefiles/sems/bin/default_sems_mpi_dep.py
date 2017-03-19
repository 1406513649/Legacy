prereq('openmpi')

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

mpi_name = getenv('MPI_NAME')
mpi_version = getenv('MPI_VERSION')

# Find this modules binaries
prefix = os.path.join('/projects/sems/install', platform, 'sems/tpl',
                      name, version, compiler, compiler_version, mpi_name,
                      mpi_version, 'parallel')
if not os.path.isdir(prefix):
    log_error('Load Error: ' + prefix + ' does not exist')

# This modules paths
PATH = os.path.join(prefix, 'bin')
MANPATH = os.path.join(prefix, 'share/man')
LIBRARY_PATH = os.path.join(prefix, 'lib')
INCLUDE_PATH = os.path.join(prefix, 'include')

# Set the environment
if os.path.isdir(PATH):
    prepend_path('PATH', PATH)

if os.path.isdir(LIBRARY_PATH):
    prepend_path('LD_LIBRARY_PATH', LIBRARY_PATH)

if os.path.isdir(MANPATH):
    prepend_path('MANPATH', MANPATH)

# SEMS specific environment variables
setenv('SEMS_' + upname + '_ROOT', prefix)
setenv('SEMS_' + upname + '_VERSION', version)
setenv('SEMS_' + upname + '_LIBRARY_PATH', LIBRARY_PATH)
setenv('SEMS_' + upname + '_INCLUDE_PATH', INCLUDE_PATH)

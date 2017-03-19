prereq_any('gcc', 'intel', 'clang')
family('mpi')

-- Determine platform
local uname = string.lower(capture('uname -a'))
local darwin = uname:find('darwin')
local platform
if darwin then
  platform = 'Darwin10.11-x86_64'
else
  platform = 'rhel6-x86_64'
end

local name = myModuleName()
local upname = name:upper()
local version = myModuleVersion()

compiler = os.getenv('COMPILER')
compiler_version = os.getenv('COMPILER_VER')
prefix = pathJoin('/projects/sems/install', platform, 'sems/compiler',
                  compiler, compiler_version, name, version)
if not isDir(prefix) then
  LmodError('Load Error: ' .. prefix .. ' does not exist')
end

-- Setup MODULEPATH for packages built by this MPI stack
local MODULEPATH_ROOT = os.getenv('MY_MODULEPATH_ROOT')
local MODULEPATH_C = pathJoin(MODULEPATH_ROOT, 'sems', platform, 'mpi',
                              compiler, compiler_version)
if not isDir(MODULEPATH_C) then
  LmodError('Load error: ' .. MODULEPATH_C .. ' does not exist')
end
local MODULEPATH = pathJoin(MODULEPATH_C, name, version)
if not isDir(MODULEPATH) then
  LmodError('Load error: ' .. MODULEPATH .. ' does not exist')
end
prepend_path('MODULEPATH', MODULEPATH)

-- This modules paths
local PATH = pathJoin(prefix, 'bin')
local MANPATH = pathJoin(prefix, 'share/man')
local LIBRARY_PATH = pathJoin(prefix, 'lib')
local LIBRARY_PATH2 = pathJoin(prefix, 'lib/openmpi')
local INCLUDE_PATH = pathJoin(prefix, 'include')
if not isDir(INCLUDE_PATH) then
  INCLUDE_PATH = pathJoin(INCLUDE_PATH, name)
end

-- Set the environment
if not isDir(PATH) then
  LmodError(name .. ' bin directory not found')
end
prepend_path('PATH', PATH)

-- Darwin requires different LD_LIBRARY_PATH environment
local LD_LIBRARY_PATH = 'LD_LIBRARY_PATH'
if darwin then
  LD_LIBRARY_PATH = 'DY' .. LD_LIBRARY_PATH
end
if isDir(LIBRARY_PATH2) then
  prepend_path(LD_LIBRARY_PATH, LIBRARY_PATH2)
  prepend_path('MPI_LIBRARY_PATH', LIBRARY_PATH2)
end
if isDir(LIBRARY_PATH) then
  prepend_path(LD_LIBRARY_PATH, LIBRARY_PATH)
  prepend_path('MPI_LIBRARY_PATH', LIBRARY_PATH)
end

if isDir(MANPATH) then
  append_path('MANPATH', MANPATH)
end

-- Set up the MPI specific environment
setenv('MPI_BIN', PATH)
setenv('MPIHOME', prefix)
setenv('MPI_HOME', prefix)
setenv('MPI_NAME', name)
setenv('MPI_VERSION', version)
setenv('MPI_INCLUDE_PATH', INCLUDE_PATH)

setenv('MPICC', pathJoin(PATH, 'mpicc'))
setenv('MPICXX', pathJoin(PATH, 'mpicxx'))

if isFile(pathJoin(PATH, 'mpif90')) then
  setenv('MPIFC', pathJoin(PATH, 'mpif90'))
  setenv('MPIF77', pathJoin(PATH, 'mpif77'))
  setenv('MPIF90', pathJoin(PATH, 'mpif90'))
end

if not isFile(pathJoin(PATH, 'mpicc')) then
  LmodError('MPI C compilers not found')
end

-- SEMS specific environment variables
setenv('SEMS_' .. upname .. '_ROOT', prefix)
setenv('SEMS_' .. upname .. '_VERSION', version)
setenv('SEMS_' .. upname .. '_LIBRARY_PATH', LIBRARY_PATH)
setenv('SEMS_' .. upname .. '_INCLUDE_PATH', INCLUDE_PATH)

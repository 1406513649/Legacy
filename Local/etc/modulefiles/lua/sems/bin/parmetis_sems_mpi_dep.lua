prereq('openmpi')

-- Determine platform
uname = string.lower(capture('uname -a'))
darwin = uname:find('darwin')
local platform
if darwin then
  platform = 'Darwin10.11-x86_64'
else
  platform = 'rhel6-x86_64'
end

local name = myModuleName()
local upname = name:upper()
local variant
local version = myModuleVersion()
if version:find('_') then
  version, variant = version:match("([^_]+)_([^_]+)")
  if variant == '64' then
    variant = '64bit_parallel'
  elseif variant == '32' then
    variant = '32bit_parallel'
  else
    LModError('Unknown ' .. name .. ' variant "' .. variant .. '"')
  end
else
  variant = 'parallel'
end

compiler = os.getenv('COMPILER')
compiler_version = os.getenv('COMPILER_VER')

mpi_name = os.getenv('MPI_NAME')
mpi_version = os.getenv('MPI_VERSION')

-- Find this modules binaries
prefix = pathJoin('/projects/sems/install', platform, 'sems/tpl',
                  name, version, compiler, compiler_version, mpi_name,
                  mpi_version, variant)
if not isDir(prefix) then
  LmodError('Load Error: ' .. prefix .. ' does not exist')
end

-- This modules paths
PATH = pathJoin(prefix, 'bin')
MANPATH = pathJoin(prefix, 'share/man')
LIBRARY_PATH = pathJoin(prefix, 'lib')
INCLUDE_PATH = pathJoin(prefix, 'include')

-- Set the environment
if isDir(PATH) then
  prepend_path('PATH', PATH)
end

-- Darwin requires different LD_LIBRARY_PATH environment
local LD_LIBRARY_PATH = 'LD_LIBRARY_PATH'
if darwin then
  LD_LIBRARY_PATH = 'DY' .. LD_LIBRARY_PATH
end
if isDir(LIBRARY_PATH) then
  prepend_path(LD_LIBRARY_PATH, LIBRARY_PATH)
end

if isDir(MANPATH) then
  prepend_path('MANPATH', MANPATH)
end

setenv('SEMS_' .. upname .. '_ROOT', prefix)
setenv('SEMS_' .. upname .. '_VERSION', version)
setenv('SEMS_' .. upname .. '_LIBRARY_PATH', LIBRARY_PATH)
setenv('SEMS_' .. upname .. '_INCLUDE_PATH', INCLUDE_PATH)

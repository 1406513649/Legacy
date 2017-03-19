family('compiler')

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
whatis("Module for " .. name .. " " .. version)

-- Find this modules binaries
local prefix = pathJoin('/projects/sems/install', platform,
                        'sems/compiler', name, version, 'base')
if not isDir(prefix) then
  LmodError('Load error: ' .. prefix .. ' does not exist')
end

-- Setup MODULEPATH for packages built by this compiler stack
local MODULEPATH_ROOT = os.getenv('MY_MODULEPATH_ROOT')
local MODULEPATH_C = pathJoin(MODULEPATH_ROOT, 'sems', platform, 'compiler')
if not isDir(MODULEPATH_C) then
  LmodError('Load error: ' .. MODULEPATH_C .. ' does not exist')
end
local MODULEPATH = pathJoin(MODULEPATH_C, name, version)
if not isDir(MODULEPATH) then
  LmodError('Load error: ' .. MODULEPATH .. ' does not exist')
end
prepend_path("MODULEPATH", MODULEPATH)

-- This modules paths
local PATH = pathJoin(prefix, 'bin')
local LIBRARY_PATH = pathJoin(prefix, 'lib')
local LIBRARY_PATH64 = pathJoin(prefix, 'lib64')
local INCLUDE_PATH = pathJoin(prefix, 'include')
local MANPATH = pathJoin(prefix, 'share/man')

-- Set the environment
if not isDir(PATH) then
  LmodError(name .. '  bin directory not found')
end
prepend_path('PATH', PATH)

-- Darwin requires different LD_LIBRARY_PATH environment
if not isDir(LIBRARY_PATH) then
  LmodError(name .. '  lib directory not found')
end
local LD_LIBRARY_PATH = 'LD_LIBRARY_PATH'
if darwin then
  LD_LIBRARY_PATH = 'DY' .. LD_LIBRARY_PATH
end
if isDir(LIBRARY_PATH64) then
  prepend_path(LD_LIBRARY_PATH, LIBRARY_PATH64)
end
prepend_path(LD_LIBRARY_PATH, LIBRARY_PATH)

if isDir(MANPATH) then
  prepend_path('MANPATH', MANPATH)
end

-- Set up the compiler specific environment
setenv('COMPILER', name)
setenv('COMPILER_VER', version)
local cc, cxx, fc
if upname == 'GCC' then
  cc, cxx, fc = 'gcc', 'g++', 'gfortran'
elseif upname == 'INTEL' then
  cc, cxx, fc = 'icc', 'icc', 'ifort'
elseif upname == 'CLANG' then
  cc, cxx = 'clang', 'clang++'
end
setenv('CC', pathJoin(PATH, cc))
setenv('CXX', pathJoin(PATH, cxx))
setenv('SERIAL_CC', pathJoin(PATH, cc))
setenv('SERIAL_CXX', pathJoin(PATH, cxx))

if not (fc == nil)  then
  setenv('FC', pathJoin(PATH, fc))
  setenv('F77', pathJoin(PATH, fc))
  setenv('F90', pathJoin(PATH, fc))

  setenv('SERIAL_FC', pathJoin(PATH, fc))
  setenv('SERIAL_F77', pathJoin(PATH, fc))
  setenv('SERIAL_F90', pathJoin(PATH, fc))
end

set_alias('gcc', pathJoin(PATH, cc))
set_alias('g++', pathJoin(PATH, cxx))
set_alias('f90', pathJoin(PATH, fc))
set_alias('f77', pathJoin(PATH, fc))

-- SEMS specific environment variables
setenv('SEMS_' .. upname .. '_ROOT', prefix)
setenv('SEMS_' .. upname .. '_VERSION', version)
setenv('SEMS_' .. upname .. '_LIBRARY_PATH', LIBRARY_PATH)
setenv('SEMS_' .. upname .. '_INCLUDE_PATH', INCLUDE_PATH)

-- Determine platform
local uname = string.lower(capture("uname -a"))
local darwin = uname:find("darwin")
local platform
if darwin then
  platform = 'Darwin10.11-x86_64'
else
  platform = 'rhel6-x86_64'
end

local name = myModuleName()
local upname = name:upper()
local version = myModuleVersion()

-- Find this modules binaries
local prefix = pathJoin('/projects/sems/install', platform,
                        'sems/utility', name, version)
if not isDir(prefix) then
  LmodError('Load Error: ' .. prefix .. ' does not exist')
end

-- This modules paths
local PATH = pathJoin(prefix, 'bin')
local LIBRARY_PATH = pathJoin(prefix, 'lib')
local INCLUDE_PATH = pathJoin(prefix, 'include')
local MANPATH = pathJoin(prefix, 'share/man')

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

-- SEMS specific environment variables
setenv('SEMS_' .. upname .. '_ROOT', prefix)
setenv('SEMS_' .. upname .. '_VERSION', version)
setenv('SEMS_' .. upname .. '_LIBRARY_PATH', LIBRARY_PATH)
setenv('SEMS_' .. upname .. '_INCLUDE_PATH', INCLUDE_PATH)

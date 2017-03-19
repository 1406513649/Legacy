family('compiler')

local name = myModuleName()
local upname = name:upper()
local version = myModuleVersion()
local major = version:sub(1,1)
local minor = version:sub(3,3)
local uname = string.lower(capture('uname -a'))
local darwin = uname:find('darwin')

local prefix = os.getenv('MACPORTS_ROOT')
if not isDir(prefix) then
  LmodError('Load Error: ' .. prefix .. ' does not exist')
end

-- Set up MODULEPATH so that modules dependent on this compiler can be found
local MY_MODULEPATH_ROOT = os.getenv('MY_MODULEPATH_ROOT')
local MODULEPATH = pathJoin(MY_MODULEPATH_ROOT,
                            'macports/compiler', name, version)
prepend_path('MODULEPATH', MODULEPATH)

-- Set the environment
local PATH = pathJoin(prefix, 'bin')
prepend_path('PATH', PATH)

local LIBRARY_PATH = pathJoin(prefix, 'lib')
-- This modules paths
if not isDir(LIBRARY_PATH) then
  LmodError('Load Error: ' .. LIBRARY_PATH .. ' does not exist')
end

if darwin then
  prepend_path('DYLD_LIBRARY_PATH', LIBRARY_PATH)
else
  prepend_path('LD_LIBRARY_PATH', LIBRARY_PATH)
end
prepend_path('LIBRARY_PATH', LIBRARY_PATH)

-- Set the MANPATH
append_path('MANPATH', pathJoin(prefix, 'share/man'))


-- Set the compiler environment
setenv('COMPILER', name)
setenv('COMPILER_VER', version)

local CC  = pathJoin(prefix, 'bin', name)
local CXX  = pathJoin(prefix, 'bin', name .. '++')
local CPP  = pathJoin(prefix, 'bin', name .. ' -E')

setenv('CC', CC)
set_alias('gcc', CC)
set_alias('cc',  CC)

setenv('CXX', CXX)
set_alias('g++', CXX)
set_alias('c++', CXX)

set_alias('cpp', CPP)
set_alias('ld',  CC)

-- Module environment variables
setenv(upname .. '_ROOT', prefix)
setenv(upname .. '_VERSION', version)
setenv(upname .. '_LIBRARY_PATH', LIBRARY_PATH)
setenv(upname .. '_INCLUDE_PATH', pathJoin(prefix, 'include'))

-- Activate this compiler in Macports
command = '/opt/macports/bin/port select --set %s mp-%s-%s.%s'
execute{cmd=command:format(name, name, major, minor), modeA={'load'}}

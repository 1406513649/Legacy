family('compiler')

whatis('Module for intel compiler')

local uname = string.lower(capture("uname -a"))
local darwin = uname:find("darwin")

local platform = 'Darwin10.11-x86_64'
local d, name = splitFileName(myModuleName()) -- :sub(6)
local upname = name:upper()
local version = myModuleVersion()

local root = '/opt/intel'
local prefix = pathJoin(root, 'compilers_and_libraries_2017.0.102/mac')
if not isDir(prefix) then
  LmodError('Load error: ' .. prefix .. ' does not exist')
end

-- Load the gcc compiler
load('sems/gcc')

-- Include directories
prepend_path('CPATH', pathJoin(prefix, 'daal/include'))
prepend_path('CPATH', pathJoin(prefix, 'tbb/include'))
prepend_path('CPATH', pathJoin(prefix, 'mkl/include'))
prepend_path('CPATH', pathJoin(prefix, 'ipp/include'))

-- PATH variable
prepend_path('PATH', pathJoin(root, 'documentation_2017/en/debugger/gdb-ia/man'))
prepend_path('PATH', pathJoin(root, 'debugger_2017/gdb/intel64/bin'))
prepend_path('PATH', pathJoin(prefix, 'bin'))
prepend_path('PATH', pathJoin(prefix, 'bin/intel64'))

-- LIBRARY path
if darwin then
  LIBRARY_PATH_ENV = 'DYLD_LIBRARY_PATH'
else
  LIBRARY_PATH_ENV = 'LD_LIBRARY_PATH'
end
prepend_path(LIBRARY_PATH_ENV, pathJoin(prefix, 'daal/../tbb/lib'))
prepend_path(LIBRARY_PATH_ENV, pathJoin(prefix, 'daal/lib'))
prepend_path(LIBRARY_PATH_ENV, pathJoin(prefix, 'tbb/lib'))
prepend_path(LIBRARY_PATH_ENV, pathJoin(prefix, 'mkl/lib'))
prepend_path(LIBRARY_PATH_ENV, pathJoin(prefix, 'compiler/lib'))
prepend_path(LIBRARY_PATH_ENV, pathJoin(prefix, 'ipp/lib'))

-- MANPATH
prepend_path('MANPATH', pathJoin(prefix, 'share/man'))

-- Intel license file
setenv('INTEL_LICENSE_FILE', pathJoin(root, 'licenses/SNL_SITE_LICENSE.lic'))

setenv('IPPROOT', pathJoin(prefix, 'ipp'))
setenv('MKLROOT', pathJoin(prefix, 'mkl'))
setenv('INCLUDE', pathJoin(prefix, 'mkl/include'))

setenv('TBBROOT', pathJoin(prefix, 'tbb'))
setenv('DAALROOT', pathJoin(prefix, 'daal'))
setenv('INTEL_PYTHONHOME', '/opt/intel/debugger_2017/python/intel64/')
setenv('CLASSPATH', pathJoin(prefix, 'daal/lib/daal.jar'))

prepend_path('NLSPATH', pathJoin(root, 'debugger_2017/gdb/intel64/share/locale/%l_%t/%N'))
prepend_path('NLSPATH', pathJoin(prefix, 'mkl/lib/locale/%l_%t/%N'))
prepend_path('NLSPATH', pathJoin(prefix, 'compiler/lib/locale/en_US/%N'))

setenv('CC', 'icc')
setenv('CXX', 'icpc')
setenv('FC', 'ifort')
setenv('F77', 'ifort')
setenv('F90', 'ifort')

setenv('SERIAL_CC', 'icc')
setenv('SERIAL_CXX', 'icpc')
setenv('SERIAL_FC', 'ifort')
setenv('SERIAL_F77', 'ifort')
setenv('SERIAL_F90', 'ifort')

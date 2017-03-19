family('compiler')

whatis('Module for intel compiler')

darwin = system_is_darwin()
platform = 'Darwin10.11-x86_64'
d, name = os.path.split(self.name)
upname = name.upper()
version = self.version

root = '/opt/intel'
prefix = os.path.join(root, 'compilers_and_libraries_2017.0.102/mac')
if not os.path.isdir(prefix):
  log_error('Load error: ' + prefix + ' does not exist')

# Load the gcc compiler
load('sems/gcc')

# Include directories
prepend_path('CPATH', os.path.join(prefix, 'daal/include'))
prepend_path('CPATH', os.path.join(prefix, 'tbb/include'))
prepend_path('CPATH', os.path.join(prefix, 'mkl/include'))
prepend_path('CPATH', os.path.join(prefix, 'ipp/include'))

# PATH variable
prepend_path('PATH', os.path.join(root, 'documentation_2017/en/debugger/gdb-ia/man'))
prepend_path('PATH', os.path.join(root, 'debugger_2017/gdb/intel64/bin'))
prepend_path('PATH', os.path.join(prefix, 'bin'))
prepend_path('PATH', os.path.join(prefix, 'bin/intel64'))

# LIBRARY path
if darwin:
  LIBRARY_PATH_ENV = 'DYLD_LIBRARY_PATH'
else:
  LIBRARY_PATH_ENV = 'LD_LIBRARY_PATH'
prepend_path(LIBRARY_PATH_ENV, os.path.join(prefix, 'daal/../tbb/lib'))
prepend_path(LIBRARY_PATH_ENV, os.path.join(prefix, 'daal/lib'))
prepend_path(LIBRARY_PATH_ENV, os.path.join(prefix, 'tbb/lib'))
prepend_path(LIBRARY_PATH_ENV, os.path.join(prefix, 'mkl/lib'))
prepend_path(LIBRARY_PATH_ENV, os.path.join(prefix, 'compiler/lib'))
prepend_path(LIBRARY_PATH_ENV, os.path.join(prefix, 'ipp/lib'))

# MANPATH
prepend_path('MANPATH', os.path.join(prefix, 'share/man'))

# Intel license file
setenv('INTEL_LICENSE_FILE', os.path.join(root, 'licenses/SNL_SITE_LICENSE.lic'))

setenv('IPPROOT', os.path.join(prefix, 'ipp'))
setenv('MKLROOT', os.path.join(prefix, 'mkl'))
setenv('INCLUDE', os.path.join(prefix, 'mkl/include'))

setenv('TBBROOT', os.path.join(prefix, 'tbb'))
setenv('DAALROOT', os.path.join(prefix, 'daal'))
setenv('INTEL_PYTHONHOME', '/opt/intel/debugger_2017/python/intel64/')
setenv('CLASSPATH', os.path.join(prefix, 'daal/lib/daal.jar'))

prepend_path('NLSPATH', os.path.join(root, 'debugger_2017/gdb/intel64/share/locale/%l_%t/%N'))
prepend_path('NLSPATH', os.path.join(prefix, 'mkl/lib/locale/%l_%t/%N'))
prepend_path('NLSPATH', os.path.join(prefix, 'compiler/lib/locale/en_US/%N'))

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

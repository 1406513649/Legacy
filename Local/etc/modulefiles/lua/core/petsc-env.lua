local HOME = os.getenv('HOME')
local DOT_LOCAL = os.getenv('DOT_LOCAL')
local uname = string.lower(capture('uname -a'))
local darwin = uname:find('darwin')

-- Location of PETSc
local PETSC_DIR = pathJoin(HOME, 'Development/PETSc/petsc')
setenv('PETSC_DIR', PETSC_DIR)
prepend_path('PYTHONPATH', pathJoin(PETSC_DIR, 'bin'))
prepend_path('PATH', pathJoin(DOT_LOCAL, 'sw/petsc/bin'))

-- PETSc architecture
if darwin then
  setenv('PETSC_ARCH', 'arch-darwin-gcc-real-opt')
else
  setenv('PETSC_ARCH', 'arch-linux-gcc-real-opt')
end


-- Load other modules
unload('anaconda/3.5')
load('anaconda/2.7')
if darwin then
  load('macports')
  load('gcc')
  load('openmpi')
else
  load('sems-env')
  load('gcc/4.7.2')
  load('openmpi/1.8.7')
end

HOME = getenv('HOME')
DOT_LOCAL = getenv('DOT_LOCAL')
darwin = system_is_darwin()

# Location of PETSc
PETSC_DIR = os.path.join(HOME, 'Development/PETSc/petsc')
setenv('PETSC_DIR', PETSC_DIR)
prepend_path('PYTHONPATH', os.path.join(PETSC_DIR, 'bin'))
prepend_path('PATH', os.path.join(DOT_LOCAL, 'sw/petsc/bin'))

# PETSc architecture
if darwin:
    setenv('PETSC_ARCH', 'arch-darwin-gcc-real-opt')
else:
    setenv('PETSC_ARCH', 'arch-linux-gcc-real-opt')

# Load other modules
unload('anaconda/3.5')
load('anaconda/2.7')
if darwin:
    load('macports')
    load('gcc')
    load('openmpi')
else:
    load('sems-env')
    load('gcc/4.7.2')
    load('openmpi/1.8.7')

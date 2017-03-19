
-- Load the correct compilers
load('macports')
load('gcc/4.9.4')
load('openmpi/1.10.3')

-- Correct python versions
unload('anaconda/3.5')
load('anaconda/2.7')

-- Set environemntal variables
local SIERRA_DIR = pathJoin(os.getenv('DEVELOPER'), 'Sierra')
local SIERRA_SNTOOLS = pathJoin(SIERRA_DIR, 'toolset')

local SIERRA_SYSTEM = 'darwin'
local SIERRA_COMPILER = 'gcc'
local SIERRA_COMPILER_VERSION = '4.9'
local SIERRA_MPI = 'openmpi'
local SIERRA_MPI_VERSION = '1.10.3'

setenv('SIERRA_MPI', SIERRA_MPI)
setenv('SIERRA_MACHINE', SIERRA_SYSTEM)
setenv('SIERRA_SYSTEM', SIERRA_SYSTEM)
setenv('SIERRA_COMPILER', SIERRA_COMPILER)
setenv('SIERRA_COMPILER_VERSION', SIERRA_COMPILER_VERSION)
setenv('SIERRA_PLATFORM', SIERRA_SYSTEM .. '-' ..
                          SIERRA_COMPILER .. '-' ..
                          SIERRA_COMPILER_VERSION .. '-' ..
                          SIERRA_MPI .. '-' ..
                          SIERRA_MPI_VERSION)
setenv('SIERRA_SNTOOLS_PATH', SIERRA_SNTOOLS)
prepend_path('PATH', pathJoin(SIERRA_SNTOOLS, 'sntools/engine'))
prepend_path('PATH', pathJoin(SIERRA_SNTOOLS, 'contrib'))
prepend_path('PATH', pathJoin(SIERRA_SNTOOLS, 'sntools/job_scripts',
                              SIERRA_SYSTEM, SIERRA_MPI))

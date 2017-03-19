prereq('trilinos-env')

local UNAME = string.lower(capture('uname -a'))
local darwin =  UNAME:find('darwin')
local HOME = os.getenv('HOME')

local branch = myModuleVersion()
local TRILINOS_HOME = os.getenv('TRILINOS_HOME')
if not isDir(TRILINOS_HOME) then
  LmodError('TRILINOS_HOME envar not properly set')
end
local ROOT = pathJoin(TRILINOS_HOME, '..')
local compiler = os.getenv('COMPILER')
local compiler_version = os.getenv('COMPILER_VER')
local mpi_name = os.getenv('MPI_NAME')
local mpi_version = os.getenv('MPI_VERSION')

if mode() == 'load' then
  local x = pathJoin(ROOT, 'Scripts/get-current-branch')
  local current_branch = capture(x):gsub('%s+', '')
  if not (current_branch == 'current') and not (current_branch == branch) then
    message = "The '" .. current_branch .. "' branch is checked out, " .. "not the '" .. branch .. "'.  Module/branch mismatching " .. "could lead to unexpected build errors."
    if branch == 'master' then
      LmodError(message)
    else
      LmodWarning(message)
    end
  end
  if compiler == nil or compiler_version == nil then
    LmodError('COMPILER module not loaded')
  end
  if mpi_name == nil or mpi_version == nil then
    LmodError('MPI module not loaded')
  end
end

if mode() == 'load' then
  trilinos_prefix = nil
  if darwin then
    trilinos_prefix = pathJoin(ROOT, 'Builds/Branches', branch,
                             compiler, compiler_version, mpi_name, mpi_version)
  end

  if trilinos_prefix == nil then
    LmodError('Load Error: unknown Trilinos platform')
  end
end

if mode() == 'load' then
  if not isDir(trilinos_prefix) then
    -- LmodError('Load Error: ' .. prefix .. ' does not exist')
    capture('mkdir -p ' .. trilinos_prefix)
  end
end

-- Load the correct modules
sems = not (os.getenv('MY_SEMS_MODULES') == nil)
if sems then
  load('sems-cmake/2.8.12')
  load('sems-superlu/4.3')
  load('sems-netcdf/4.3.2')
  load('sems-zlib/1.2.8')
  load('sems-boost/1.59.0')
  load('sems-hdf5/1.8.12')
  load('sems-parmetis/4.0.3_64bit')
else
  load('cmake')
  load('superlu')
  load('boost')
  load('zlib')
  load('hdf5')
  load('netcdf')
  load('pnetcdf')
  load('metis')
  load('scotch')
  load('parmetis')
end

-- Environment variables to set
prepend_path('DYLD_LIBRARY_PATH', pathJoin(trilinos_prefix, 'lib'))
setenv('TRILINOS_BUILD', trilinos_prefix)

local command = os.getenv('SET_TERM_TITLE_EXE') .. " Trilinos \\(" .. branch .. ", " .. compiler .. compiler_version .. ", " .. mpi_name .. mpi_version ..  "\\)"
execute {cmd=command, modeA={'load'}}

-- LDFLAGS:  -L/usr/local/opt/openblas/lib
-- CPPFLAGS: -I/usr/local/opt/openblas/include

""" A docstring
"""
import re
import os
import sys
import hashlib

raise Exception("Should not use anymore")

MODULEFILES = '/Users/tjfulle/Local/etc/modulefiles'

def main():
    """Docstring"""
    write_homebrewed_modules()
    write_my_modules()

def write_my_modules():
    # look for compiler
    compilers = ['/opt/clang/3.9.0',
                 '/opt/clang/4.0',
                 '/usr/local/Cellar/gcc49/4.9.3',
                 '/usr/local/Cellar/gcc53/5.3.0',
                 '/usr/local/Cellar/gcc5/5.4.0',
                 '/usr/local/Cellar/gcc/6.2.0']

    for compiler in compilers:
        assert os.path.isdir(compiler)
        c_split = compiler.split(os.path.sep)
        compiler_version = c_split[-1]
        compiler_name = 'gcc' if 'gcc' in c_split[-2] else 'clang'
        write_compiler_modules(compiler_name, compiler_version)
        write_mpi_modules(compiler_name, compiler_version)

    moduletext = module_trilinos()
    modulepath = os.path.join(MODULEFILES, 'software/sw_trilinos/trilinos/develop.lua')
    if not os.path.isdir(os.path.dirname(modulepath)):
        os.makedirs(os.path.dirname(modulepath))
    for rem_f in os.listdir(os.path.dirname(modulepath)):
        os.remove(os.path.join(os.path.dirname(modulepath), rem_f))
    with open(modulepath, 'w') as fh:
        fh.write(moduletext)
    default_symlink(modulepath)
    with open(os.path.join(os.path.dirname(modulepath), 'master.lua'), 'w') as fh:
        fh.write(moduletext)

    return

def default_symlink(filepath):
    cwd = os.getcwd()
    d, f = os.path.split(filepath)
    os.chdir(d)
    os.symlink(f, 'default')
    os.chdir(cwd)

def write_compiler_modules(compiler_name, compiler_version, tpls=None):
    """Docstring"""
    module_base_path = os.path.join(MODULEFILES, 'compiler',
                                    compiler_name, compiler_version)
    if compiler_version == 'apple':
        compiler_app_prefix = '/usr/local/Cellar'
    else:
        compiler_app_prefix = os.path.join('/opt/apps/compiler',
                                           compiler_name, compiler_version)
    print(module_base_path)
    tpls = tpls or os.listdir(compiler_app_prefix)
    for tpl_name in tpls:
        tpl_d = os.path.join(compiler_app_prefix, tpl_name)
        if not os.path.isdir(tpl_d):
            print('***Warning: TPL {0} not found'.format(tpl_name))
            continue

        if tpl_name == 'open-mpi':
            tpl_name = 'openmpi'

        module_d = os.path.join(module_base_path, tpl_name)

        # Remove any other module files
        if not os.path.isdir(module_d):
            os.makedirs(module_d)
        for rem_f in os.listdir(module_d):
            os.remove(os.path.join(module_d, rem_f))

        for tpl_v in os.listdir(tpl_d):
            # The module path
            print('\t' + tpl_name + '-' + tpl_v)
            if not os.path.isdir(module_d):
                os.makedirs(module_d)
            modulepath = os.path.join(module_d, tpl_v+'.lua')
            if tpl_name == 'openmpi':
                if compiler_version == 'apple':
                    moduletext = module_openmpi_brew()
                else:
                    moduletext = module_openmpi()
            else:
                if compiler_version == 'apple':
                    moduletext = module_compiler_generic_brew()
                else:
                    moduletext = module_compiler_generic()
            with open(modulepath, 'w') as fh:
                fh.write(moduletext)

        if tpl_name == 'openmpi' and compiler_version != 'apple':
            src = os.path.join(module_d, '1.10.4.lua')
            if not os.path.isfile(src):
                src = os.path.join(module_d, '1.6.5.lua')
            default_symlink(src)

    return 0

def write_mpi_modules(compiler_name, compiler_version, tpls=None):
    """Docstring"""
    if compiler_version == 'apple':
        openmpi = 'open-mpi'
        compiler_app_prefix = '/usr/local/Cellar'
    else:
        openmpi = 'openmpi'
        compiler_app_prefix = os.path.join('/opt/apps/compiler',
                                           compiler_name, compiler_version)

    mpi_versions = os.listdir(os.path.join(compiler_app_prefix, openmpi))
    for mpi_version in mpi_versions:
        if compiler_version == 'apple':
            mpi_app_prefix = '/usr/local/Cellar'
        else:
            mpi_app_prefix = os.path.join('/opt/apps/mpi',
                                          compiler_name, compiler_version,
                                          'openmpi', mpi_version)
        if not os.path.isdir(mpi_app_prefix):
            continue

        module_base_path = os.path.join(MODULEFILES, 'mpi',
                                        compiler_name, compiler_version,
                                        'openmpi', mpi_version)

        print(module_base_path)
        tpls = tpls or os.listdir(mpi_app_prefix)
        for tpl_name in tpls:
            tpl_d = os.path.join(mpi_app_prefix, tpl_name)
            if not os.path.isdir(tpl_d):
                continue
            module_d = os.path.join(module_base_path, tpl_name)
            if not os.path.isdir(module_d):
                os.makedirs(module_d)
            # Remove any other module files
            for rem_f in os.listdir(module_d):
                os.remove(os.path.join(module_d, rem_f))
            # Now get the versions
            for tpl_v in os.listdir(tpl_d):
                # The module path
                print('\t' + tpl_name + '-' + tpl_v)
                if not os.path.isdir(module_d):
                    os.makedirs(module_d)

                if tpl_name == 'parmetis' and compiler_version != 'apple':
                    moduletext = module_compiler_mpi_parmetis()
                    modulepath = os.path.join(module_d, tpl_v+'_32bit.lua')
                    with open(modulepath, 'w') as fh:
                        fh.write(moduletext)
                    modulepath = os.path.join(module_d, tpl_v+'_64bit.lua')
                    with open(modulepath, 'w') as fh:
                        fh.write(moduletext)
                    default_symlink(modulepath)
                elif compiler_version == 'apple':
                    moduletext = module_compiler_mpi_generic_brew()
                    modulepath = os.path.join(module_d, tpl_v+'.lua')
                    with open(modulepath, 'w') as fh:
                        fh.write(moduletext)
                else:
                    moduletext = module_compiler_mpi_generic()
                    modulepath = os.path.join(module_d, tpl_v+'.lua')
                    with open(modulepath, 'w') as fh:
                        fh.write(moduletext)

    return 0

def write_homebrewed_modules():
    tpls = ["boost", "hdf5", "open-mpi", "zlib", "netcdf", "superlu"]
    write_compiler_modules('clang', 'apple', tpls=tpls)
    tpls = ['boost', 'parmetis', 'superlu_dist']
    write_mpi_modules('clang', 'apple', tpls=tpls)

def hash_file(filename):
    """Docstring"""
    hash1 = hashlib.md5()
    text = ''.join(x.strip() for x in open(filename).readlines()).encode('utf-8')
    hash1.update(text)
    return hash1.hexdigest()

def gather_unique_modules():
    """Docstring"""
    # Gather compiler modules
    lua_files = {}
    for (dirname, _, files) in os.walk('compiler'):
        for filename in files:
            if not filename.endswith('.lua'):
                continue
            filepath = os.path.join(dirname, filename)
            lua_files[filepath] = hash_file(filepath)
    unique_hashes = []
    unique_lua_files = []
    for (filename, filehash) in lua_files.items():
        if filehash not in unique_hashes:
            unique_hashes.append(filehash)
            unique_lua_files.append(filename)
    print(unique_lua_files)
    print(len(unique_lua_files))
    print(len(lua_files))

def module_matmodlab():
    """Docstring"""
    return """\
local name = myModuleName()
local version = myModuleVersion()
local develop = os.getenv("DEVELOPER")
local home = os.getenv("HOME")
local prefix = pathJoin(develop, "MaterialsModeling/ModelDrivers/matmodlab")

if (not isDir(prefix)) then
  LmodError("Load Error: " .. prefix .. " does not exist")
end

conflict("intel")

setenv("MATMODLAB", prefix)
prepend_path("PYTHONPATH", prefix)

local kmm = pathJoin(develop, 'MaterialsModeling/MaterialModels/kayenta')
if isDir(kmm) then
  prepend_path('MML_USERENV', pathJoin(kmm, 'hosts/matmodlab/mml_userenv.py'))
end

-- Use matmodlab environment
remove_path('PATH', '/anaconda/3.5/bin')

local p1 = pathJoin(home, '.conda/envs/matmodlab')
local p2 = pathJoin(p1, 'bin')
if not isDir(p1) then
  LmodError("Load Error: " .. p1 .. " does not exist")
end
if not isDir(p2) then
  LmodError("Load Error: " .. p2 .. " does not exist")
end

setenv('CONDA_DEFAULT_ENV', 'matmodlab')
setenv('CONDA_ENV_PATH', p1)
prepend_path('PATH', p2)"""

def module_compiler_generic_brew():
    return module_compiler_generic_brew_pre() + module_generic_post()

def module_compiler_mpi_generic_brew():
    return module_compiler_generic_brew_pre() + module_generic_post()

def module_compiler_generic():
    return module_compiler_generic_pre() + module_generic_post()

def module_compiler_mpi_generic():
    return module_compiler_mpi_generic_pre() + module_generic_post()

def module_compiler_mpi_parmetis():
    return module_compiler_mpi_parmetis_pre() + module_generic_post()

def module_compiler_generic_pre():
    """Docstring"""
    return """\
-- Darwin requires different LD_LIBRARY_PATH environment
local uname = string.lower(capture('uname -a'))
local darwin = uname:find('darwin')

-- Find this modules binaries
local name = myModuleName()
local upname = name:upper()
local version = myModuleVersion()

local compiler = os.getenv('COMPILER')
local compiler_version = os.getenv('COMPILER_VER')
local prefix = pathJoin('/opt/apps/compiler',
                        compiler, compiler_version, name, version)
if not isDir(prefix) then
  LmodError('Load Error: ' .. prefix .. ' does not exist')
end
"""

def module_compiler_mpi_generic_pre():
    return """\
-- Darwin requires different LD_LIBRARY_PATH environment
local uname = string.lower(capture('uname -a'))
local darwin = uname:find('darwin')

-- Find this modules binaries
local name = myModuleName()
local upname = name:upper()
local version = myModuleVersion()
local compiler = os.getenv('COMPILER')
local compiler_version = os.getenv('COMPILER_VER')
local mpi_name = os.getenv('MPI_NAME')
local mpi_version = os.getenv('MPI_VERSION')
local prefix = pathJoin('/opt/apps/mpi', compiler, compiler_version,
                        mpi_name, mpi_version, name, version)
if not isDir(prefix) then
  LmodError('Load Error: ' .. prefix .. ' does not exist')
end
"""
def module_compiler_generic_brew_pre():
    """Docstring"""
    return """\
-- Darwin requires different LD_LIBRARY_PATH environment
local uname = string.lower(capture('uname -a'))
local darwin = uname:find('darwin')

-- Find this modules binaries
local name = myModuleName()
local upname = name:upper()
local version = myModuleVersion()

local compiler = os.getenv('COMPILER')
local compiler_version = os.getenv('COMPILER_VER')
local prefix = pathJoin('/usr/local/Cellar', name, version)
if not isDir(prefix) then
  LmodError('Load Error: ' .. prefix .. ' does not exist')
end
"""

def module_compiler_mpi_parmetis_pre():
    return """\
-- Darwin requires different LD_LIBRARY_PATH environment
local uname = string.lower(capture('uname -a'))
local darwin = uname:find('darwin')

-- Find this modules binaries
local name = myModuleName()
local upname = name:upper()
local v = myModuleVersion()
local version = v:sub(1,5)
local bit = v:sub(7,11)
local compiler = os.getenv('COMPILER')
local compiler_version = os.getenv('COMPILER_VER')
local mpi_name = os.getenv('MPI_NAME')
local mpi_version = os.getenv('MPI_VERSION')
local prefix = pathJoin('/opt/apps/mpi', compiler, compiler_version,
                        mpi_name, mpi_version, name, version, bit)
if not isDir(prefix) then
  LmodError('Load Error: ' .. prefix .. ' does not exist')
end
"""

def module_generic_post():
    return """\
-- Set the environment
setenv(upname .. '_ROOT', prefix)
setenv(upname .. '_VERSION', version)

-- Executable path
local PATH = pathJoin(prefix, 'bin')
if isDir(PATH) then
  prepend_path('PATH', PATH)
end

-- Library path
local LIBRARY_PATH = pathJoin(prefix, 'lib')
if isDir(LIBRARY_PATH) then
  if darwin then
    prepend_path('DYLD_LIBRARY_PATH', LIBRARY_PATH)
  else
    prepend_path('LD_LIBRARY_PATH', LIBRARY_PATH)
  end
  prepend_path('LIBRARY_PATH', LIBRARY_PATH)
  setenv(upname .. '_LIBRARY_PATH', LIBRARY_PATH)
end

-- This modules paths
local MANPATH = pathJoin(prefix, 'share/man')
if isDir(MANPATH) then
  append_path('MANPATH', MANPATH)
end

local INCLUDE_PATH = pathJoin(prefix, 'include')
if isDir(INCLUDE_PATH) then
  setenv(upname .. '_INCLUDE_PATH', INCLUDE_PATH)
elseif isDir(pathJoin(INCLUDE_PATH, name)) then
  setenv(upname .. '_INCLUDE_PATH', pathJoin(INCLUDE_PATH, name))
end"""


def module_openmpi():
    """Docstring"""
    module_mpi = """\
prereq_any('clang', 'gcc', 'intel')
family('mpi')

{0}

-- Setup Modulepath for packages built by this MPI stack
local mroot = os.getenv('MY_MODULEPATH_ROOT')
local mdir = pathJoin(mroot, 'mpi', compiler,
                      compiler_version, name, version)
prepend_path('MODULEPATH', mdir)

{1}

-- Extra mpi library paths
local LIBRARY_PATH_2 = pathJoin(prefix, 'lib/openmpi')
if isDir(LIBRARY_PATH) then
  if darwin then
    prepend_path('DYLD_LIBRARY_PATH', LIBRARY_PATH_2)
  else
    prepend_path('LD_LIBRARY_PATH', LIBRARY_PATH_2)
  end
  prepend_path('LIBRARY_PATH', LIBRARY_PATH_2)
end

-- Set up the MPI specific environment
setenv('MPI_VERSION', version)
prepend_path('MPI_LIBRARY_PATH', LIBRARY_PATH_2)
prepend_path('MPI_LIBRARY_PATH', LIBRARY_PATH)
setenv('MPI_INCLUDE_PATH', INCLUDE_PATH)

setenv('MPI_NAME', name)
setenv('MPIHOME', prefix)
setenv('MPI_HOME', prefix)
setenv('MPI_VERSION', version)
setenv('MPI_BIN', PATH)
setenv('MPICC', pathJoin(MPI_BIN, 'mpicc'))
setenv('MPICXX', pathJoin(MPI_BIN, 'mpicxx'))
if isFile(pathJoin(MPI_BIN, 'mpif90')) then
  setenv('MPIFC', pathJoin(MPI_BIN, 'mpif90'))
  setenv('MPIF77', pathJoin(MPI_BIN, 'mpif77'))
  setenv('MPIF90', pathJoin(MPI_BIN, 'mpif90'))
end""".format(module_compiler_generic_pre(), module_generic_post())
    return module_mpi

def module_openmpi_brew():
    """Docstring"""
    module_mpi = """\
prereq_any('clang', 'gcc', 'intel')
family('mpi')

{0}

-- Setup Modulepath for packages built by this MPI stack
local mroot = os.getenv('MY_MODULEPATH_ROOT')
local mdir = pathJoin(mroot, 'mpi', compiler, 'clang/apple')
prepend_path('MODULEPATH', mdir)

{1}

-- Extra mpi library paths
local LIBRARY_PATH_2 = pathJoin(prefix, 'lib/openmpi')
if isDir(LIBRARY_PATH) then
  if darwin then
    prepend_path('DYLD_LIBRARY_PATH', LIBRARY_PATH_2)
  else
    prepend_path('LD_LIBRARY_PATH', LIBRARY_PATH_2)
  end
  prepend_path('LIBRARY_PATH', LIBRARY_PATH_2)
end

-- Set up the MPI specific environment
setenv('MPI_VERSION', version)
prepend_path('MPI_LIBRARY_PATH', LIBRARY_PATH_2)
prepend_path('MPI_LIBRARY_PATH', LIBRARY_PATH)
setenv('MPI_INCLUDE_PATH', INCLUDE_PATH)

setenv('MPI_NAME', name)
setenv('MPIHOME', prefix)
setenv('MPI_HOME', prefix)
setenv('MPI_VERSION', version)
setenv('MPI_BIN', PATH)
setenv('MPICC', pathJoin(MPI_BIN, 'mpicc'))
setenv('MPICXX', pathJoin(MPI_BIN, 'mpicxx'))
if isFile(pathJoin(MPI_BIN, 'mpif90')) then
  setenv('MPIFC', pathJoin(MPI_BIN, 'mpif90'))
  setenv('MPIF77', pathJoin(MPI_BIN, 'mpif77'))
  setenv('MPIF90', pathJoin(MPI_BIN, 'mpif90'))
end""".format(module_compiler_generic_brew_pre(), module_generic_post())
    return module_mpi

def module_trilinos():
    return """\
prereq('sw/trilinos')

local UNAME = string.lower(capture('uname -a'))
local darwin =  UNAME:find('darwin')
local HOME = os.getenv('HOME')

local branch = myModuleVersion()
local TRILINOS_HOME = os.getenv('TRILINOS_HOME')
local ROOT = pathJoin(TRILINOS_HOME, '..')
local compiler = os.getenv('COMPILER')
local compiler_version = os.getenv('COMPILER_VER')
local mpi_name = os.getenv('MPI_NAME')
local mpi_version = os.getenv('MPI_VERSION')

if mode() == 'load' then
  local x = pathJoin(ROOT, 'Scripts/get-current-branch')
  local current_branch = capture(x):gsub('%s+', '')
  if not (current_branch == branch) then
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

if darwin then
  prefix = pathJoin(ROOT, 'Builds/Branches', branch,
                    compiler, compiler_version, mpi_name, mpi_version)
  PYTHONPATH = '/usr/local/lib/python2.7/site-packages'
else
  LmodError('Load Error: unknown Trilinos platform')
end

if not isDir(prefix) then
  LmodError('Load Error: ' .. prefix .. ' does not exist')
end
local LIBRARY_PATH = pathJoin(prefix, 'lib')

-- Load the correct modules
load('cmake')

-- Compiler dependent
load('superlu')
load('netcdf')
load('zlib')

-- MPI dependent
load('boost')
load('hdf5')
load('parmetis')

-- Environment variables to set
local PYTHONPATH_ENV = 'PYTHONPATH'
local TRILINOS_BUILD_ENV = 'TRILINOS_BUILD'
if darwin then
  LIBRARY_PATH_ENV = 'DYLD_LIBRARY_PATH'
else
  LIBRARY_PATH_ENV = 'LD_LIBRARY_PATH'
end

prepend_path(PYTHONPATH_ENV, PYTHONPATH)
prepend_path(LIBRARY_PATH_ENV, LIBRARY_PATH)
setenv(TRILINOS_BUILD_ENV, prefix)

local command = os.getenv('SET_TERM_TITLE_EXE') .. " Trilinos \\\\(" .. branch .. ", " .. compiler .. compiler_version .. ", " .. mpi_name .. mpi_version ..  "\\\\)"
execute {cmd=command, modeA={'load'}}

-- LDFLAGS:  -L/usr/local/opt/openblas/lib
-- CPPFLAGS: -I/usr/local/opt/openblas/include"""

if __name__ == '__main__':
    main()

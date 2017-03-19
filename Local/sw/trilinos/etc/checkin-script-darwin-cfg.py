# -*- mode: python -*-
import re
import os
import sys
import imp
import multiprocessing as mp

__all__ = ['configuration', 'defaults']

def which(exe_name, environ=None):
    """Find an executable"""
    if not exe_name:
        return None
    environ = environ or os.environ
    for path in environ.get('PATH', '').split(os.pathsep):
        filepath = os.path.join(path, exe_name)
        if os.path.isfile(filepath) and os.access(filepath, os.X_OK):
            return filepath
    return None

def write_cmake_opts(filename, options):
    with open(filename + '.config', 'w') as fh:
        for option in options:
            if re.search('(?i)\-D[a-z]', option):
                option = re.sub('\-D', '-D ', option)
            fh.write(option + '\n')

# This script also expects the TRILINOS_HOME and TRILINOS_BUILD environment
# variable to exist and for it to point to the Trilinos source.
src_d = os.getenv('TRILINOS_HOME')
assert src_d is not None and os.path.isdir(src_d), 'TRILINOS_HOME not set'
build_dir = os.getenv('TRILINOS_BUILD')
module_prefix = ''  # 'SEMS_'
build_prefix = 'X_'

# import the base trilinos config file. The strategy of this configuration file
# is to ADD to the base configuration
default_config_filename = 'project-checkin-test-config.py'
pathname = os.path.join(src_d, default_config_filename)
base_config = imp.load_source(default_config_filename, pathname)
configuration = base_config.configuration

enable_fortran = os.getenv('checkin_enable_fortran', False)
debug_only = os.getenv('checkin_debug_only', False)
extra_tpetra_types = os.getenv('check_extra_tpetra_types', False)
serial_only = os.getenv('checkin_serial_only', False)
run_all_builds = os.getenv('checkin_all', False)
run_defaults = os.getenv('checkin_defaults', False)

# Define packages to be enabled and disabled
enabled_pkgs = ['TpetraCore', 'Ifpack2', 'Belos', 'Amesos2',
                'Zoltan2', 'Xpetra', 'MueLu', 'Stokhos', 'Sacado']
disabled_pkgs = ['SEACAS', 'STK', 'Shards', 'FEI', 'ROL', 'Moertel', 'Panzer',
                 'ThreadPool', 'OptiPack', 'Rythmos', 'Intrepid', 'PyTrilinos']

# Define TPLS to be enabled and disabled
enabled_tpls = ['BLAS', 'LAPACK', 'Zlib', 'Netcdf', 'HDF5',
                'ParMETIS', 'Boost'] #, 'BoostLib']
disabled_tpls = ['SuperLU', 'CSparse', 'METIS']

# NOTE: Pthread and BinUtils are disabled in the default configuration

# ---------------------------------------------- common cmake configuration --- #
onoff = lambda x: {True: 'ON', False: 'OFF'}[bool(x)]
common = ['-DBUILD_SHARED_LIBS:BOOL=ON',
#          '-DTPL_ENABLE_CUDA:BOOL=OFF',
#          '-DKokkos_ENABLE_Cuda_UVM:BOOL=OFF',
#          '-DTpetra_INST_CUDA=OFF',
#          '-DTrilinos_ENABLE_OpenMP:BOOL=OFF',
#          '-DTrilinos_SHOW_DEPRECATED_WARNINGS:BOOL=ON',
          '-DTrilinos_ENABLE_Fortran:BOOL={0}'.format(onoff(enable_fortran)),
#          '-DTeuchos_ENABLE_COMPLEX:BOOL=ON',
#          '-DTpetra_INST_COMPLEX_DOUBLE:BOOL=ON',
          '-DCMAKE_CXX_FLAGS:STRING="-Wall --pedantic"',
          '-DTrilinos_CXX11_FLAGS:STRING="-std=c++11"',
          '-DTrilinos_ENABLE_CXX11:BOOL=ON',
          '-DTrilinos_ENABLE_EXPLICIT_INSTANTIATION:BOOL=ON',
]

# Append TPL filepaths to the common configuration options
for tpl in enabled_tpls:
    TPL = 'BOOST' if tpl == 'BoostLib' else tpl.upper()
    version = os.getenv(module_prefix + TPL + '_VERSION')
    if not bool(version):
        if TPL in ('ZLIB', 'BLAS', 'LAPACK'):
            # TPL's provided by the OS
            continue
        else:
            msg  = tpl + ' TPL environment not configured properly. '
            msg += 'If using a module environment manager, be sure to load '
            msg += 'any TPL modules before running this script'
            raise AssertionError(msg)
    else:
        inc = os.getenv(module_prefix + TPL + '_INCLUDE_PATH')
        lib = os.getenv(module_prefix + TPL + '_LIBRARY_PATH')
    common.append('-DTPL_ENABLE_{0}:BOOL=ON'.format(tpl))
    if inc is not None:
        common.append('-D{0}_INCLUDE_DIRS:FILEPATH="{1}"'.format(tpl, inc))
    if lib is not None:
        common.append('-D{0}_LIBRARY_DIRS:FILEPATH="{1}"'.format(tpl, lib))

# Explicitly enable/disable TPLs
for tpl in disabled_tpls:
    common.append('-DTPL_ENABLE_{0}:BOOL=OFF'.format(tpl))

# Add the default common options
common = configuration['cmake']['common'] + common

# ---------------------------------------------------------- default builds --- #
cxx = which(os.getenv('CXX'))
cc = which(os.getenv('CC'))
fc = which(os.getenv('FC'))
assert cxx is not None and cc is not None, 'CXX and/or CC not set'

mpi_home = os.getenv('MPI_HOME')
assert os.path.isdir(mpi_home), 'MPI_HOME not set'
mpicxx = which(os.getenv('MPICXX'))
mpicc = which(os.getenv('MPICC'))
assert mpicxx is not None and mpicc is not None, 'MPIXX and/or MPICC not set'
mpi_inc = os.path.join(mpi_home, 'include')
if enable_fortran:
    mpicc = which(os.getenv('MPIFC'))
    assert mpifc is not None, 'MPIF not set'

# Add options for builds that I want.  The builds are built off of the default
# builds (MPI_DEBUG and SERIAL_RELEASE)
my_builds = dict(configuration['cmake']['default-builds'])
default_builds = list(my_builds.keys())
print my_builds
my_builds['MPI_DEBUG'].extend(['-DCMAKE_BUILD_TYPE:STRING=DEBUG',
                               '-DTPL_ENABLE_MPI:BOOL=ON',
                               '-DKokkos_ENABLE_DEBUG:BOOL=ON',
                               '-DTeuchos_ENABLE_DEBUG:BOOL=ON',
                               '-DMPI_BASE_DIR:PATH={0}'.format(mpi_home),
                               '-DMPI_CXX_INCLUDE_PATH:PATH={0}'.format(mpi_inc),
                               '-DMPI_CXX_COMPILER:FILEPATH={0}'.format(mpicxx),
                               '-DMPI_C_COMPILER:FILEPATH={0}'.format(mpicc),
                               '-DMPI_C_INCLUDE_PATH:PATH={0}'.format(mpi_inc),])
if enable_fortran:
    my_builds['MPI_DEBUG'].extend([
        '-DMPI_Fortran_COMPILER:FILEPATH={0}'.format(mpifc),
        '-DMPI_Fortran_INCLUDE_PATH:PATH={0}'.format(mpi_inc),])

my_builds['SERIAL_RELEASE'].extend([
    '-DCMAKE_CXX_COMPILER:FILEPATH="{0}"'.format(cxx),
    '-DCMAKE_C_COMPILER:FILEPATH="{0}"'.format(cc)])
if enable_fortran:
    opt = '-DCMAKE_Fortran_COMPILER:FILEPATH={0}'.format(fc)
    build['SERIAL_RELEASE'].append(opt)

# Add aditional builds
x = my_builds['MPI_DEBUG']

if extra_tpetra_types:
    my_builds['MPI_DEBUG_INT_INT_OFF'] = x + ['-DTpetra_INST_INT_INT=OFF']
    my_builds['MPI_DEBUG_INT_LONG_LONG_OFF'] =  x + ['-DTpetra_INST_INT_LONG_LONG=OFF']

for (build_name, build_options) in my_builds.items():
    this_build_options = common + build_options
    continue
    if 'SERIAL_RELEASE' in build_name:
        # disable HDF5 and ParMETIS
        this_build_options = [x for x in common
                              if 'HDF5' not in x.upper()
                              and 'PARMETIS' not in x.upper()]
        this_build_options.extend(['-DTPL_ENABLE_HDF5=OFF',
                                   '-DTPL_ENABLE_ParMETIS=OFF',])
        this_build_options.extend(build_options)
    else:
        this_build_options = common + build_options

    # Set the install prefix
    prefix = os.path.join(build_dir, build_prefix+build_name)
    with open(build_prefix + build_name + '.config', 'w') as fh:
        fh.write('\n'.join(this_build_options) + '\n')
        fh.write('-DCMAKE_INSTALL_PREFIX={0}'.format(prefix))

    if build_name not in default_builds:
        continue
    # write out the default build options, stripping TPL_ENABLE...
    this_build_options = [opt for opt in this_build_options
                          if 'TPL_ENABLE' not in opt]
    prefix = os.path.join(build_dir, build_name)
    with open(build_name + '.config', 'w') as fh:
        fh.write('\n'.join(this_build_options) + '\n')
        fh.write('-DCMAKE_INSTALL_PREFIX={0}'.format(prefix))

# I don't need to send an email to the world since the push is going to my fork
configuration['defaults'].pop('--send-email-to-on-push', None)

# ---------------------------------------------------- command line options --- #
defaults = {}

# Source directory
defaults['src-dir'] = src_d

# Explicitly enable and disable packages
defaults['enable-packages'] = ','.join(enabled_pkgs)
defaults['disable-packages'] = ','.join(disabled_pkgs)

# cmake and ctest options
cpu_count = None
for arg in sys.argv[1:]:
    if arg.startswith('-j'):
        break
else:
    defaults['j'] = min(16, mp.cpu_count())
defaults['ctest-timeout'] = 600

# Adjust default behavior for interacting with the repository
#defaults['allow-no-pull'] = True
#defaults['configure'] = True
#defaults['build'] = True
#defaults['test'] = True

# configure, build, test, but do not pull
# This option is roughly equivalent to uncommenting the previous lines
#defaults['local-do-all'] = True

# pull, configure, build, test
#defaults['do-all'] = True

defaults['no-enable-fwd-packages'] = True
defaults['enable-all-packages'] = 'off'

# Builds to run
if run_all_builds:
    x_builds = list(my_builds.keys())
elif debug_only:
    x_builds = [b for b in my_builds.keys() if 'DEBUG' in b]
elif serial_only:
    x_builds = [b for b in my_builds.keys() if 'SERIAL' in b]
else:
    x_builds = ['MPI_DEBUG', 'SERIAL_RELEASE']
defaults['extra-builds'] = ','.join(build_prefix+b for b in x_builds)

print('Extra builds: {0}'.format(defaults['extra-builds']))
if not run_defaults:
    defaults['default-builds'] = ""  # Just run extras
    print('Default builds: None')
else:
    print('Default builds: {0}'.format(','.join(default_builds)))

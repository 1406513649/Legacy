#!/opt/apps/anaconda/3.5/bin/python
"""A docstring

"""
from __future__ import print_function
import os
import re
import sys
import shutil
from argparse import ArgumentParser

def listdir(directory, key=lambda x: True, join=0):
    items = [x for x in os.listdir(directory) if key(os.path.join(directory, x))]
    if join:
        items = [os.path.join(directory, x) for x in items]
    return items

p = ArgumentParser()
p.add_argument('--platform', choices=('linux', 'darwin'),
               default=sys.platform.lower(),
               help='Platform [default: %(default)s]')
args = p.parse_args()

darwin = 'darwin' in args.platform.lower()
if darwin:
    SYSTEM = 'Darwin10.11-x86_64'
else:
    SYSTEM = 'rhel6-x86_64'

if os.path.isdir('/opt/sems'):
    if darwin:
        SEMS_BASE = '/opt/sems/darwin/projects/sems'
    else:
        SEMS_BASE = '/opt/sems/linux/projects/sems'
else:
    SEMS_BASE = '/projects/sems'
SEMS_INSTALL_DIR = os.path.join(SEMS_BASE, 'install/{0}/sems'.format(SYSTEM))
SEMS_TPL = os.path.join(SEMS_INSTALL_DIR, 'tpl')
SEMS_UTIL = os.path.join(SEMS_INSTALL_DIR, 'utility')
SEMS_COMPILER = os.path.join(SEMS_INSTALL_DIR, 'compiler')
D = os.environ['MY_MODULEPATH_ROOT']
MODULEFILES = os.path.join(D, 'sems', SYSTEM)
ROOT_D = os.path.dirname(os.path.realpath(__file__))

# Gather compiler versions
COMPILERS = {}
for compiler_name in listdir(SEMS_COMPILER, os.path.isdir):
    dd1 = os.path.join(SEMS_COMPILER, compiler_name)
    for compiler_version in listdir(dd1, os.path.isdir):
        if not re.search(r'[0-9]+\.[0-9]+', compiler_version):
            raise Exception('Unexpected compiler '
                            'version {0}'.format(compiler_version))
        COMPILERS.setdefault(compiler_name, []).append(compiler_version)

MPI_VERSIONS = {}
for (compiler_name, compiler_versions) in COMPILERS.items():
    for compiler_version in compiler_versions:
        compiler = os.path.sep.join([compiler_name, compiler_version])
        dd1 = os.path.join(SEMS_COMPILER, compiler)
        for mpi_vendor in listdir(dd1, os.path.isdir):
            if mpi_vendor == 'base':
                continue
            dd2 = os.path.join(SEMS_COMPILER, compiler, mpi_vendor)
            MPI_VERSIONS[compiler] = ['{0}/{1}'.format(mpi_vendor, x)
                                      for x in os.listdir(dd2)]
# Gather Utility installs
UTILITY_VERSIONS = {}
for util_name in listdir(SEMS_UTIL, os.path.isdir):
    if 'tex' in util_name:
        continue
    dd1 = os.path.join(SEMS_UTIL, util_name)
    for util_version in listdir(dd1, os.path.isdir):
        if not re.search(r'[0-9]+\.[0-9]+', util_version):
            raise Exception('Unexpected utility '
                            'version {0}'.format(util_version))
        UTILITY_VERSIONS.setdefault(util_name, []).append(util_version)

python_tpls = ['astroid', 'dateutil', 'logilab', 'matplotlib',
               'numpy', 'pylint', 'pyparsing', 'pytz', 'scipy',
               'scons', 'setuptools', 'six', 'beautifulsoup4',
               'gprof2dot']

# Determine install dirs for TPLS
TPLS = os.listdir(SEMS_TPL)
TPL_BASE_VERSIONS = {}
TPL_MPI_VERSIONS = {}
for tpl in TPLS:
    if tpl in python_tpls:
        continue
    tpl_base_dir = os.path.join(SEMS_TPL, tpl)
    tpl_versions = os.listdir(tpl_base_dir)
    for tpl_version in tpl_versions:
        tpl_v_s = os.path.join(tpl, tpl_version)
        for (compiler_name, compiler_versions) in COMPILERS.items():
            if 'python' in compiler_name:
                continue
            for compiler_version in compiler_versions:
                compiler = os.path.sep.join([compiler_name, compiler_version])
                tpl_c_d = os.path.join(tpl_base_dir, tpl_version, compiler)
                if not os.path.isdir(tpl_c_d):
                    print('***Warning: {0} not configured for {1}'.format(
                        tpl, compiler))
                    continue
                if 'base' in os.listdir(tpl_c_d):
                    key = (compiler, tpl, tpl_version)
                    TPL_BASE_VERSIONS[key] = os.path.join(tpl_c_d, 'base')

                for mpi in MPI_VERSIONS[compiler]:
                    dd = os.path.join(tpl_c_d, mpi)
                    if not os.path.isdir(dd):
                        continue
                    dd1 = os.path.join(dd, 'parallel')
                    assert os.path.isdir(dd1)
                    key = (compiler, mpi, tpl, tpl_version)
                    TPL_MPI_VERSIONS[key] = dd1

CORE_MODULE_DIR = os.path.join(MODULEFILES, 'core')
if os.path.isdir(CORE_MODULE_DIR):
    shutil.rmtree(CORE_MODULE_DIR)

MPI_MODULE_DIR = os.path.join(MODULEFILES, 'mpi')
if os.path.isdir(MPI_MODULE_DIR):
    shutil.rmtree(MPI_MODULE_DIR)

COMPILER_MODULE_DIR = os.path.join(MODULEFILES, 'compiler')
if os.path.isdir(COMPILER_MODULE_DIR):
    shutil.rmtree(COMPILER_MODULE_DIR)

SEMS_PREFIX = ''  # 'sems-'

for (compiler_name, compiler_versions) in COMPILERS.items():
    for compiler_version in compiler_versions:
        module_d = os.path.join(CORE_MODULE_DIR, SEMS_PREFIX+compiler_name)
        if not os.path.isdir(module_d):
            os.makedirs(module_d)
        if compiler_name == 'python':
            source = os.path.join(ROOT_D, 'default_sems_python.lua')
        else:
            source = os.path.join(ROOT_D, 'default_sems_compiler.lua')
        module = os.path.join(module_d, compiler_version + '.lua')
        shutil.copyfile(source, module)
        print(compiler_name, compiler_version, end=': ')
        print(module)

for (util_name, util_versions) in UTILITY_VERSIONS.items():
    for util_version in util_versions:
        module_d = os.path.join(CORE_MODULE_DIR, SEMS_PREFIX+util_name)
        if not os.path.isdir(module_d):
            os.makedirs(module_d)
        source = os.path.join(ROOT_D, 'default_sems_util.lua')
        module = os.path.join(module_d, util_version + '.lua')
        shutil.copyfile(source, module)
        print(util_name, util_version, end=': ')
        print(module)

for (key, path) in TPL_BASE_VERSIONS.items():
    compiler, tpl, tpl_version = key
    module_d = os.path.join(COMPILER_MODULE_DIR, compiler,
                            SEMS_PREFIX+tpl)
    if not os.path.isdir(module_d):
        os.makedirs(module_d)
    source = os.path.join(ROOT_D, 'default_sems_compiler_dep.lua')
    module = os.path.join(module_d, tpl_version + '.lua') #'base.lua')
    shutil.copyfile(source, module)
    print(tpl, tpl_version, end=': ')
    print(module)

for (key, path) in TPL_MPI_VERSIONS.items():
    compiler, mpi, tpl, tpl_version = key
    module_d = os.path.join(MPI_MODULE_DIR, compiler, mpi,
                            SEMS_PREFIX+tpl)
    if not os.path.isdir(module_d):
        os.makedirs(module_d)
    if 'parmetis' not in tpl:
        source = os.path.join(ROOT_D, 'default_sems_mpi_dep.lua')
        module = os.path.join(module_d, tpl_version+'.lua') # 'parallel.lua')
        shutil.copyfile(source, module)
        print(tpl, tpl_version, end=': ')
        print(module)
    else:
        source = os.path.join(ROOT_D, 'parmetis_sems_mpi_dep.lua')
        #for x in ('', '64bit_', '32bit_'):
        for x in ('', '_64', '_32'):
            #module = os.path.join(module_d, x + 'parallel.lua')
            module = os.path.join(module_d, tpl_version+x+'.lua')
            shutil.copyfile(source, module)
            print(tpl, tpl_version, end=': ')
            print(module)

    # MPI module
    mpi_name, mpi_version = mpi.split(os.path.sep)
    module_d = os.path.join(COMPILER_MODULE_DIR,
                            compiler, SEMS_PREFIX+mpi_name)
    if not os.path.isdir(module_d):
        os.makedirs(module_d)
    source = os.path.join(ROOT_D, 'default_sems_mpi.lua')
    module = os.path.join(module_d, mpi_version+'.lua')
    shutil.copyfile(source, module)
    print(key[-3], end=': ')
    print(module)

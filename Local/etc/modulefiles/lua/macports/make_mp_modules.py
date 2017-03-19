#!/usr/bin/env python
import os
import re
from subprocess import check_output

PREFIX = '/opt/local'
installed_ports = check_output('/opt/local/bin/port installed', shell=True).decode('utf-8')
blessed_ports = ('openmpi', 'boost', 'metis', 'pnetcdf', 'netcdf',
                 'hdf5', 'parmetis', 'scotch', 'SuiteSparse', 'superlu')

def openmpi_file_contents(port_full_version, filename):
    s = ["-- Lua module for macports installed software",
         "prereq_any('clang', 'gcc', 'intel')",
         "family('mpi')",
         "name = myModuleName()",
         "upname = name:upper()",
         "version = myModuleVersion()",
         "version_s = version:sub(1,6) -- strip the final _?",
         "prefix = '{0}'".format(PREFIX),
         "if not isDir(prefix) then",
         "    LmodError('prefix ' .. prefix .. ' does not exist')",
         "end",
         "port_full_version = '{0}'".format(port_full_version),
         "-- set up MODULEPATH for MPI dependent modules",
         "mroot = os.getenv('MY_MODULEPATH_ROOT')",
         "c = os.getenv('COMPILER')",
         "cv = os.getenv('COMPILER_VER')",
         "cM = cv:sub(1,1)",
         "cm = cv:sub(3,3)",
         "mdir = pathJoin(mroot, 'macports/mpi', c, cv, name, version_s)",
         "if not isDir(mdir) then",
         "  LmodError(mdir .. ': Directory does not exist')",
         "end",
         "prepend_path('MODULEPATH', mdir)",
         "LIBRARY_PATH = pathJoin(prefix, 'lib')",
         "prepend_path('LIBRARY_PATH', LIBRARY_PATH)",
         "prepend_path('DYLD_LIBRARY_PATH', LIBRARY_PATH)",
         "if (cM == '6' and c == 'gcc') then",
         "    qname = name .. '-gcc6'",
         "    LIBRARY_PATH = LIBRARY_PATH .. name .. '-' .. cM",
         "else",
         "    qname = name .. '-' .. c .. cM .. cm",
         "    LIBRARY_PATH = LIBRARY_PATH .. name .. '-' .. cM .. cm",
         "end",
         "if isDir(LIBRARY_PATH) then",
         "    prepend_path('LIBRARY_PATH', LIBRARY_PATH)",
         "    prepend_path('DYLD_LIBRARY_PATH', LIBRARY_PATH)",
         "end",
         "-- MPI specific environments",
         "setenv('MPI_NAME', name)",
         "setenv('MPIHOME', prefix)",
         "setenv('MPI_HOME', prefix)",
         "setenv('MPI_VERSION', version_s)",
         "setenv('MPI_BIN', pathJoin(prefix, 'bin'))",
         "setenv('MPI_LIBRARY_PATH', pathJoin(prefix, 'lib'))",
         "setenv('MPI_INCLUDE_PATH', pathJoin(prefix, 'include'))",
         "setenv('MPICC', pathJoin(prefix, 'bin/mpicc'))",
         "setenv('MPICXX', pathJoin(prefix, 'bin/mpicxx'))",
         "setenv('OMPI_MCA_oob_tcp_if_exclude', 'lo,cscotun0')",
         "setenv('OMPI_MCA_btl_tcp_if_exclude', 'lo,cscotun0')",
         "if isFile(pathJoin(prefix, 'bin/mpif90')) then",
         "    setenv('MPIFC', pathJoin(prefix, 'bin/mpif90'))",
         "    setenv('MPIF77', pathJoin(prefix, 'bin/mpif77'))",
         "    setenv('MPIF90', pathJoin(prefix, 'bin/mpif90'))",
         "end",
         "-- Standard port environment variables",
         "setenv(upname .. '_ROOT', prefix)",
         "setenv(upname .. '_VERSION', version_s)",
         "setenv(upname .. '_INCLUDE_PATH', pathJoin(prefix, 'include'))",
         "setenv(upname .. '_LIBRARY_PATH', pathJoin(prefix, 'lib'))",
         "-- Activate the software",
         "local deactivate  = 'port deactivate %s %s'",
         "execute{cmd=deactivate:format(name, port_full_version), modeA={'unload'}}",
         "local activate = 'port select --set mpi %s-fortran'",
         "execute{cmd=activate:format(qname), modeA={'load'}}"]
    print('Writing ' + filename)
    write_file(filename, "\n".join(s))
    return

def file_contents(port, port_full_version, filename):
    if port == 'openmpi':
        return openmpi_file_contents(port_full_version, filename)
    s = ["-- Lua module for macports installed software",
         "name = myModuleName()",
         "upname = name:upper()",
         "version = myModuleVersion()",
         "prefix = '{0}'".format(PREFIX),
         "if not isDir(prefix) then",
         "    LmodError('prefix ' .. prefix .. ' does not exist')",
         "end",
         "port_full_version = '{0}'".format(port_full_version),
         "LIBRARY_PATH = pathJoin(prefix, 'lib')",
         "prepend_path('LIBRARY_PATH', LIBRARY_PATH)",
         "prepend_path('DYLD_LIBRARY_PATH', LIBRARY_PATH)",
         "-- Standard port environment variables",
         "setenv(upname .. '_ROOT', prefix)",
         "setenv(upname .. '_VERSION', version)",
         "setenv(upname .. '_LIBRARY_PATH', pathJoin(prefix, 'lib'))",
         "setenv(upname .. '_INCLUDE_PATH', pathJoin(prefix, 'include'))",
         "-- Activate the software",
         "local deactivate  = 'port deactivate %s %s'",
         "execute{cmd=deactivate:format(name, port_full_version), modeA={'unload'}}",
         "local activate = 'port activate %s %s'",
         "execute{cmd=activate:format(name, port_full_version), modeA={'load'}}"]
    print('Writing ' + filename)
    write_file(filename, "\n".join(s))
    return

def write_file(filepath, contents):
    dirname, filename = os.path.split(filepath)
    root, ext = os.path.splitext(filename)
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
    with open(filepath, 'w') as fh:
        fh.write(contents)
    return

def main():
    d = os.environ['MY_MODULEPATH_ROOT']
    compilers = {'clang38': 'clang/3.8', 'gcc6': 'gcc/6.3', 'gcc49': 'gcc/4.9.4'}
    prefix = os.path.join(d, 'macports')
    for item in installed_ports.split('\n')[1:]:

        item = [x.strip() for x in item.split()]
        if not item:
            continue

        # Get the version
        port, port_full_version = item[:2]
        if port.startswith('openmpi'):
            port, compiler_short_name = port.split('-')
            compiler_d = compilers[compiler_short_name]
        elif port not in blessed_ports:
            continue
        else:
            for (compiler_short_name, compiler_d) in compilers.items():
                if compiler_short_name in port_full_version:
                    break
            else:
                raise Exception('compiler not found for {0}'.format(item))

        version = re.split('[\+\-]', port_full_version)[0][1:]
        compiler, compiler_version = compiler_d.split('/')
        if 'openmpi' in port_full_version and not port == 'openmpi':
            xp = os.path.join(prefix, 'mpi', compiler_d, 'openmpi/1.10.3')
        else:
            xp = os.path.join(prefix, 'compiler', compiler_d)
        v = version.split('_', 1)[0].strip()
        filename = os.path.join(xp, port, v + '.lua')
        s = file_contents(port, port_full_version, filename)

    for other_port in ('zlib @1.2.11_0', 'cmake @3.7.2_0'):
        port, port_full_version = other_port.split()
        version = port_full_version[1:]
        v = version.split('_', 1)[0].strip()
        filename = os.path.join(prefix, 'core', port, v + '.lua')
        compiler, compiler_version = compiler_d.split('/')
        s = file_contents(port, port_full_version, filename)


if __name__ == '__main__':
    main()

    # github.com/dumerrill/merge-spmv

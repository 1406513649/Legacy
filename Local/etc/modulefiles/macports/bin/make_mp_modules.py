#!/usr/bin/env python
import os
import re
from subprocess import check_output

PREFIX = '/opt/local'
installed_ports = check_output('/opt/local/bin/port installed',
                               shell=True).decode('utf-8')
compiler_ports = ('gcc', 'clang')
blessed_ports = ('openmpi', 'boost', 'metis', 'pnetcdf', 'netcdf',
                 'hdf5', 'parmetis', 'scotch', 'SuiteSparse', 'superlu')

def file_contents(port, port_full_version, filename):
    if port == 'openmpi':
        template_file = './default_mpi_module.py.in'
    elif 'boost' in port:
        template_file = './default_boost_module.py.in'
    else:
        template_file = './default_module.py.in'
    s = open(template_file).read()
    s = s.format(prefix=PREFIX, port_full_version=port_full_version)
    print('Writing ' + filename)
    write_file(filename, s)
    return

def write_gcc_module(prefix, port, version, port_full_version):
    filename = os.path.join(prefix, 'core/gcc', version + '.py')
    template_file = './default_gcc_module.py.in'
    major, minor = version.split('.')[:2]
    s = open(template_file).read()
    s = s.format(prefix=PREFIX, port_full_version=port_full_version,
                 version=version,
                 major=major, minor=minor, port_name=port)
    print('Writing ' + filename)
    write_file(filename, s)

def write_clang_module(prefix, port, version, port_full_version):
    filename = os.path.join(prefix, 'core/clang', version + '.py')
    template_file = './default_clang_module.py.in'
    major, minor = version.split('.')[:2]
    s = open(template_file).read()
    s = s.format(prefix=PREFIX, port_full_version=port_full_version,
                 version=version,
                 major=major, minor=minor, port_name=port)
    print('Writing ' + filename)
    write_file(filename, s)


def write_file(filepath, contents):
    dirname, filename = os.path.split(filepath)
    root, ext = os.path.splitext(filename)
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
    filepath = os.path.join(dirname, filename)
    with open(filepath, 'w') as fh:
        fh.write(contents)
    return

def main():
    d = os.environ['MY_MODULEPATH_ROOT']
    prefix = os.path.join(d, 'macports')

    compilers = {}
    for item in installed_ports.split('\n')[1:]:
        # Determine installed compilers
        item = [x.strip() for x in item.split()]
        if not item:
            continue
        # Get the version
        port, port_full_version = item[:2]
        version = re.split('[\+\-]', port_full_version)[0][1:]
        if '_select' in port:
            continue
        if port.startswith('gcc'):
            if port == 'gcc6':
                version = version[:3]
            compilers[port] = 'gcc/{0}'.format(version)
            write_gcc_module(prefix, port, version, port_full_version)
        elif port.startswith('clang'):
            version = version[:3]
            key = 'clang' + version[0] + version[2]
            compilers[key] = 'clang/{0}'.format(version)
            write_clang_module(prefix, port, version, port_full_version)

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
        filename = os.path.join(xp, port, v + '.py')
        s = file_contents(port, port_full_version, filename)

    for other_port in ('zlib @1.2.11_0', 'cmake @3.7.2_0'):
        port, port_full_version = other_port.split()
        version = port_full_version[1:]
        v = version.split('_', 1)[0].strip()
        filename = os.path.join(prefix, 'core', port, v + '.py')
        compiler, compiler_version = compiler_d.split('/')
        s = file_contents(port, port_full_version, filename)


if __name__ == '__main__':
    main()

    # github.com/dumerrill/merge-spmv

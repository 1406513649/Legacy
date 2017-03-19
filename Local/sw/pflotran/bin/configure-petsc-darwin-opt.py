#!/usr/bin/env python
import sys
import os

def main():
    petsc_dir = os.getenv('PETSC_DIR')
    if petsc_dir is None:
        sys.exit('PETSC_DIR not set')
    config_dir = os.path.join(petsc_dir, 'config')
    if not os.path.isdir(config_dir):
        sys.exit('Cannot find config dir, are you sure PETS_DIR is right?')

    mpi_home = os.getenv('MPI_HOME')
    if mpi_home is None:
        sys.exit('MPI_HOME not set')

    sys.path.insert(0, os.path.abspath('config'))
    import configure

    configure_options = [
      '--with-mpi-dir={0}'.format(mpi_home),
#      '--with-hdf5-dir=/opt/local',
#      '--with-blas-lapack-dir=/usr/lib',
      '--with-metis-dir=/opt/local',
      '--with-parmetis-dir=/opt/local',
      '--with-debugging=1',
      '--COPTFLAGS=-O3',
      '--CXXOPTFLAGS=-O3',
      '--FOPTFLAGS=-O3',
      '--PETSC_ARCH=arch-darwin-gcc-real-opt',
    ]
    configure.petsc_configure(configure_options)

if __name__ == '__main__':
    main()

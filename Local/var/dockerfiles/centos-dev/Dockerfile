# build docker container using
#   docker build -t centos:dev .
# run the container using
#   docker run -i -t centos:dev /bin/bash
#
# This image contains a basic CentOS with a standard development environment
# (compilers, MPI, ...)
#
FROM centos:latest
RUN yum -y install redhat-lsb-core which less \
                   environment-modules wget \
                   automake make gcc gcc-fortran gcc-c++ openmpi openmpi-devel \
                   blas blas-devel lapack lapack-devel atlas atlas-devel boost boost-devel \
                   git git-all doxygen && yum clean all

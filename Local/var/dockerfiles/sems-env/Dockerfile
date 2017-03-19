# build docker container using
#   docker build -t centos:sems .
# run the container using
#   docker run -i -t centos:sems /bin/bash
#
# This image contains a basic CentOS with a standard development environment
# (compilers, MPI, ...)
#
FROM centos:dev
ADD projects.tar.gz /
RUN echo '. /projects/modulefiles/utils/sems-modules-init.sh' > /etc/profile.d/sems-modules.sh && rm -f /projects.tar.gz

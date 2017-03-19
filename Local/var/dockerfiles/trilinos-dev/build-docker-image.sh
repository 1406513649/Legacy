#!/bin/sh
TRILINOS_ROOT=/Users/tjfulle/Developer/Trilinos
/usr/local/bin/docker rmi -f trilinos-dev
(cd $TRILINOS_ROOT && /opt/local/bin/gnutar czf trilinos.tar.gz Source/)
mv $TRILINOS_ROOT/trilinos.tar.gz .
/usr/local/bin/docker build -t trilinos-dev .

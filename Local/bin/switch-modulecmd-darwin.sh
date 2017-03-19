#!/bin/bash

if [ -f /opt/apps/modules/Modules/3.2.10/bin/modulecmd ]; then
    TMOD_CMD=/opt/apps/modules/Modules/3.2.10/bin/modulecmd
else
    echo modulecmd not found
    exit 1
fi

module unuse ${DOT_LOCAL}/etc/modulefiles/core
module purge
module(){ eval `${TMOD_CMD} bash "$@"`; }
export -f module

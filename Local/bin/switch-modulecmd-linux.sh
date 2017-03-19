#!/bin/bash

elif [ -f /usr/local/modules/3.2.10/Modules/3.2.10/bin/modulecmd ]; then
    TMOD_CMD=/usr/local/modules/3.2.10/Modules/3.2.10/bin/modulecmd
else
    echo modulecmd not found
    exit 1
fi

module purge
module unuse ${HOME}/.local.d/etc/modulefiles/core
module unuse ${HOME}/.swx/apps/lmod/modulefiles/Linux:
module unuse ${HOME}/.swx/apps/lmod/modulefiles/Core:
module unuse ${HOME}/.swx/apps/lmod/lmod/modulefiles/Core
module unuse /opt/apps/modulefiles/Darwin
moduel unuse /opt/apps/modulefiles/Core
module unuse /opt/apps/lmod/lmod/modulefiles/Core

module(){ eval `${TMOD_CMD} bash "$@"`; }
export -f module

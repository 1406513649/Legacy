#!/usr/bin/env python
from __future__ import print_function
import os
from argparse import ArgumentParser
p = ArgumentParser()
p.add_argument('path')
p.add_argument('-e', '--exists', default=False, action='store_true',
               help='Print paths in green (exists) or red (does not exist)')
args = p.parse_args()
path = os.getenv(args.path.strip(), '').split(os.pathsep)
green = '\033[92m'
red = '\033[91m'
endc = '\033[0m'
print(args.path + ':')
for item in path:
    if args.exists:
        if not os.path.exists(item):
            item = red + item + endc
        else:
            item = green + item + endc
    print(item)

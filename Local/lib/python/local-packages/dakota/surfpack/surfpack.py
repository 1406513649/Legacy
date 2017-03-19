#!/usr/bin/env python

import os
import sys
from os.path import splitext
from argparse import ArgumentParser
from subprocess import Popen, STDOUT
try:
    from shutil import which
except ImportError:
    import distutils.spawn.find_executable as which


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    p = ArgumentParser()
    p.add_argument('sps_file', help='surfpack surface definition file')
    p.add_argument('params', nargs='+', help='evaluation points')
    p.add_argument('--prefix', 
            help='Output filename prefix [default: prefix(sps_file)]')
    args = p.parse_args(argv)
    params = []
    for p in args.params:
        try:
            k, p = p.split('=')
            params.append((k.strip(), float(p)))
        except ValueError:
            params.append(float(p))
    eval_surfpack_surface(args.sps_file, params, prefix=args.prefix)


def eval_surfpack_surface(sps_file, params, remove=False, prefix=None):

    surfpack = which('surfpack')
    if not surfpack:
        raise OSError('surfpack executable not found')

    prefix = prefix or splitext(sps_file)[0]

    # Write out the points file
    points_file = prefix + '_points.dat'
    param_names, param_values = [], []
    for (i, p) in enumerate(params):
        try:
            name, value = p
        except ValueError:
            name, value = 'x_{0}'.format(i+1), p
        param_names.append(name)
        param_values.append(value)

    with open(points_file, 'w') as fh:
        fh.write('% ' + ' '.join(param_names) + '\n')
        fh.write(' '.join('{0:.18f}'.format(float(x)) for x in param_values))

    # Output file
    out_file = prefix + '_points_eval.spd'

    # Contents of the .spk file
    spk_file = prefix + '_surfpack.spk'
    with open(spk_file, 'w') as fh:
        fh.write("Load[name=data, file='{0}', ".format(points_file))
        fh.write("n_predictors={0}, n_responses=0]\n".format(len(params)))
        fh.write("Load[name=ns, file='{0}']\n".format(sps_file))
        fh.write("Evaluate[surface=ns, data=data]\n")
        fh.write("Save[data=data, file='{0}']\n".format(out_file))

    command = '{0} {1}'.format(surfpack, spk_file)
    proc = Popen(command.split(), stdout=open(os.devnull, 'a'), stderr=STDOUT)
    proc.wait()

    if proc.returncode != 0:
        return None

    response = float(open(out_file).readlines()[1].split()[-1])

    if remove:
        os.remove(spk_file)
        os.remove(points_file)
        os.remove(out_file)

    return response


if __name__ == '__main__':
    sys.exit(main())

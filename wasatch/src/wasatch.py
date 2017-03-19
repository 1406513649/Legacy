import os
import sys
import argparse
import time
import numpy as np
import shutil

np.set_printoptions(precision=4)

D, F = os.path.split(os.path.realpath(__file__))

# The parser directory must be added to the path so that the parse tables are
# imported properly
sys.path.append(os.path.join(D, "parser"))

import __runopt__ as ro
import __config__ as cfg
from src.base.errors import WasatchError
import src.fem.core.fe_model as fem
sys.tracebacklimit = 20


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--chk-mesh", default=False, action="store_true",
        help="Stop to check mesh before running simulation [default: %(default)s]")
    parser.add_argument("--piecewise", default=False, action="store_true",
        help="""Print the piecewise solution as a function of x
                [default: %(default)s""")
    parser.add_argument("--dbg", default=False, action="store_true",
        help="Debug mode [default: %(default)s]")
    parser.add_argument("--sqa", default=False, action="store_true",
        help="SQA mode [default: %(default)s]")
    parser.add_argument("-v", default=None, type=int,
        help="Verbosity [default: %(default)s]")
    parser.add_argument("--wm", default=False, action="store_true",
        help="Write mesh to ascii file [default: %(default)s]")
    parser.add_argument("-j", default=1, type=int,
        help="Number of proccesses to run simultaneously [default: %(default)s]")
    parser.add_argument("-E", default=False, action="store_true",
        help="Write exodus file [default: %(default)s]")
    parser.add_argument("--clean", default=False, action="store_true",
        help="Clean simulation output [default: %(default)s]")
    parser.add_argument("--cleanall", default=False, action="store_true",
        help="Clean all simulation output [default: %(default)s]")
    parser.add_argument("--profile", default=False, action="store_true",
        help="Run the simulation in a profiler [default: %(default)s]")
    parser.add_argument("-d", nargs="?", default=None, const="_RUNID_",
        help="Directory to run analysis [default: %(default)s]")
    args = parser.parse_args(argv)

    if args.profile:
        raise WasatchError("Profiling must be run from __main__")

    # set some simulation wide configurations
    ro.debug = args.dbg
    ro.sqa = args.sqa
    ro.verbosity = args.v
    if not cfg.exodus:
        cfg.exodus = args.E

    if args.clean or args.cleanall:
        from src.base.utilities import clean_wasatch
        clean_wasatch(os.path.splitext(args.file)[0], args.cleanall)
        return 0

    ti = time.time()

    infile = args.file
    if args.d is not None:
        fdir, fname = os.path.split(os.path.realpath(args.file))
        if args.d == "_RUNID_":
            d = os.path.join(fdir, os.path.splitext(fname)[0])
        else:
            d = os.path.realpath(args.d)
        try: os.makedirs(d)
        except OSError: pass
        infile = os.path.join(d, fname)
        try: os.remove(infile)
        except: pass
        shutil.copyfile(args.file, infile)
        os.chdir(d)

    fe_model = fem.FEModel.from_input_file(infile, verbosity=args.v)

    if args.wm:
        fe_model.mesh.write_ascii(fe_model.runid)

    if args.chk_mesh:
        fe_model.logger.write("See {0} for initial mesh".format(
                fe_model.runid + ".exo"))
        resp = raw_input("Continue with simulation? (Y/N) [N]: ")
        stop = not {"Y": True}.get(resp.upper().strip(), False)
        if stop:
            return 0

    try:
        retval = fe_model.solve(nproc=args.j)
    except KeyboardInterrupt:
        sys.stderr.write("\nKeyboard interrupt\n")
        retval = -1

    tf = time.time()
    fe_model.logger.write("wasatch: total simulation time: {0:.2f}s".format(
            tf - ti))
    fe_model.logger.close()
    return retval

if __name__ == "__main__":
    try:
        sys.argv.remove("--profile")
    except ValueError:
        sys.exit(main())
    import cProfile as profile
    sys.exit(profile.run("main()", "wasatch.prof"))

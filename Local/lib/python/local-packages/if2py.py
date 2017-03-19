import os
import sys
import shutil
from numpy.distutils.misc_util import Configuration
from numpy.distutils.system_info import get_info
from numpy.distutils.core import setup

D = os.path.dirname(os.path.realpath(__file__))

def f2py(name, sources, signature, fc, incd, destd=None, disp=0):
    """Build material model with Numpy distutils

    """

    if destd is None:
        destd = os.path.join(D, "../lib")

    config = Configuration(name, parent_package="", top_path="")
    if signature:
        sources.insert(0, signature)

    extra_kwargs = get_info("lapack_opt", notfound_action=2)
    extra_kwargs["extra_compile_args"].extend(["-fPIC", "-shared"])

    config.add_extension(name, sources=sources,
                         include_dirs=[incd], **extra_kwargs)

    if disp == 0:
        f = os.devnull
    else:
        f = "f2py.con"

    hold = [x for x in sys.argv]
    fc = "--f77exec={0} --f90exec={0}".format(fc)
    sys.argv = "./setup.py config_fc {0} build_ext -i".format(fc).split()

    errors = 0
    with open(f, "w") as sys.stdout:
        with open(f, "a") as sys.stderr:
            try:
                setup(**config.todict())
            except (BaseException, Exception) as e:
                errors += 1
                msg = e.message

    sys.argv = [x for x in hold]
    sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__
    sys.stdout.flush()
    sys.stderr.flush()

    if errors:
        print "failed to build {0} with f2py\n{1}".format(name, msg)

    try:
        shutil.rmtree("build")
    except OSError:
        pass

    if destd != D and not errors:
        shutil.move(name + ".so", os.path.join(destd, name + ".so"))

    return errors

if __name__ == "__main__":
    name = sys.argv[1]
    built = f2py(name, [name + ".f90"], None, "gfortran", os.getcwd())

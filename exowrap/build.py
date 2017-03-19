#!/usr/bin/env python
import os
import re
import sys
import shutil
import tarfile
import argparse
from subprocess import call, STDOUT, PIPE, check_output
from datetime import datetime
import xml.dom.minidom as xdom

from _exoconst import D, prefix, pyexodusii_library


def which(exe, path=os.getenv("PATH")):
    for d in path.split(os.pathsep):
        x = os.path.join(d, exe)
        if os.path.isfile(x):
            return x


def extract(f, d):
    tar = tarfile.open(f)
    tar.extractall(path=d)
    tar.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", default=False, action="store_true",
        help="Rebuild all components [default: %(default)s]")
    parser.add_argument("--fc", default=which("gfortran"),
        help="Path to fortran compiler [default: %(default)s]")
    parser.add_argument("--build", default=[], action="append",
        help="Components to build [default: ALL]")
    parser.add_argument("--no-test", default=False, action="store_true",
        help="Do not test after building [default: ALL]")
    parser.add_argument("--test", default=False, action="store_true",
        help="Run test and exit [default: ALL]")
    args = parser.parse_args(sys.argv[1:])

    if args.test:
        return test()

    if not args.build:
        components = {"netcdf": args.rebuild,
                      "exodus": args.rebuild,
                      "pyexodusii": args.rebuild}

    else:
        components = {}
        if any("netcdf" in _ for _ in args.build):
            components["netcdf"] = True
        if "exodus" in args.build:
            components["exodus"] = True
        if any(("exowrap" in _ or "pyexodus" in _) for _ in args.build):
            components["pyexodusii"] = True

    if not components:
        sys.exit("no components to build")

    errors = build_exowrap(components, args.fc)
    if errors:
        return errors

    if not args.no_test:
        errors += test()

    return errors


def build_exowrap(components, fc):

    cwd = os.getcwd()
    os.chdir(D)

    # create build directory
    if not os.path.isdir(prefix):
        os.makedirs(prefix)

    errors = 0

    if "netcdf" in components:
        errors += build_netcdf(fc, components["netcdf"])

    if "exodus" in components:
        errors += build_exodusii(fc, components["exodus"])

    if "pyexodusii" in components:
        errors += build_pyexodusii(fc, components["pyexodusii"])

    os.chdir(cwd)

    return errors


def test():
    cout("Testing installation")
    if not os.path.isfile(pyexodusii_library):
        cout("*** error: pyexodusii library not found")
        return 1
    sys.path.insert(0, os.path.dirname(pyexodusii_library))
    try:
        import pyexodusii as exolib
    except ImportError as e:
        # By this point, the library exists, we just couldn't import it. Check
        # known reasons.
        if re.search(r"libnetcdf.*", e.message):
            cout("Set LD_LIBRARY_PATH={0} to load netcdf shared "
                 "object files".format(prefix + "/lib"))
            return -1
        return 1

    try:
        from exoreader import ExodusIIReader
    except ImportError:
        cout("*** error: failed to import exoreader")
        return 1

    f = "tests/sample.exo"
    exofile = ExodusIIReader.new_from_exofile(f)
    exofile.summary()
    cout("Test successful")
    return 0


def build_pyexodusii(fc, rebuild):
    from numpy.distutils.core import setup
    from numpy.distutils.misc_util import Configuration
    from numpy.distutils.system_info import get_info

    if os.path.isfile(pyexodusii_library) and not rebuild:
        return 0

    pyexodusii_src_d = os.path.join(prefix, "src/pyexodusii")
    try: shutil.rmtree(pyexodusii_src_d)
    except OSError: pass
    os.makedirs(pyexodusii_src_d)

    # set sys.argv for distutils
    sys.argv = ["./setup.py", "config_fc",
                "--f77exec={0}".format(fc),
                "--f90exec={0}".format(fc),
                "build_ext", "--inplace"]

    # fix up sources
    source = os.path.join(pyexodusii_src_d, "exowrap.f90")
    errors = write_fortran_source(source)
    if errors:
        sys.exit("*** error: pyexodus source file not created")

    sources = [source]
    libraries = ["exoIIv2for", "exodus", "netcdf"]
    libdirs = [os.path.join(prefix, "lib")]

    # configuration dictionary
    config = Configuration("pyexodusii", parent_package="", top_path="")
    config.add_extension("pyexodusii", sources=sources,
                         libraries=libraries,
                         library_dirs=libdirs,
                         extra_compile_args=["-fPIC", "-shared", "-static"],
                         f2py_options=["--quiet"])

    cout("building the ExodusII python wrapper")

    # f2py writes to console, redirect
    con = os.path.join(pyexodusii_src_d, "pyexodusii.con")
    sys.stdout = open(con, "w")
    sys.stderr = open(con, "a")

    # build with setup tools
    setup(**config.todict())

    sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__

    # check if built and stage
    basename = os.path.basename(pyexodusii_library)
    if os.path.isfile(os.path.join(D, basename)):
        shutil.move(os.path.join(D, basename), pyexodusii_library)
        errors = 0
        cout("ExodusII python wrapper built")
    else:
        cout("ExodusII python wrapper NOT built")
        errors = 1

    return errors


def build_netcdf(fc, rebuild):
    """Build the netcdf library

    """
    if os.path.isfile(os.path.join(prefix, "lib/libnetcdf.a")) and not rebuild:
        return 0

    # extract netcdf to build directory
    netcdf = "netcdf-4.3.0"
    archive = os.path.join(D, "src", netcdf + ".tar.gz")
    netcdf_src_d = os.path.join(prefix, "src", netcdf)
    try: shutil.rmtree(netcdf_src_d)
    except OSError: pass
    extract(archive, os.path.dirname(netcdf_src_d))

    # move to directory and configure netcdf
    os.chdir(netcdf_src_d)
    conf = " ".join(["./configure --enable-shared --disable-netcdf-4 ",
                     "--disable-fsync --disable-dap --disable-cdmremote",
                     "--prefix={0}".format(prefix)])
    cmds = [conf, "make -j8", "make install"]
    cout("building the NetCDF libraries")
    f = "netcdf.con"
    env = {"PATH": os.getenv("PATH"), "FC": fc, }
    with open(f, "w") as fobj:
        for cmd in cmds:
            ret = call(cmd.split(), env=env, stdout=fobj, stderr=STDOUT)
            if ret != 0:
                cout("*** error: failed to build netcdf, see {0}".format(f))
                return ret

    cout("NetCDF libraries built")

    # move back
    os.chdir(D)

    return 0


def build_exodusii(fc, rebuild):
    """Build the exodusii library, linking with netcdf

    """
    if os.path.isfile(os.path.join(prefix, "lib/libexodus.a")) and not rebuild:
        return 0

    exodus = "exodus-4.68"
    archive = os.path.join(D, "src/exodus-4.68.tar.gz")
    exodus_src_d = os.path.join(prefix, "src", exodus)
    try: shutil.rmtree(exodus_src_d)
    except OSError: pass
    extract(archive, os.path.dirname(exodus_src_d))

    # move to directory and build exodus
    os.chdir(exodus_src_d)

    env = {"EXOWRAP_PREFIX_DIR": prefix, "PATH": os.getenv("PATH"), "FC": fc, }
    f = "exodus.con"
    cmds = ["clean", "all", "install"]
    cout("building the ExodusII libraries")
    with open(f, "w") as fobj:
        for cmd in cmds:
            cmd = "make -f Makefile.exowrap " + cmd
            ret = call(cmd.split(), env=env, stdout=fobj, stderr=STDOUT)
            if ret != 0:
                cout("*** error: failed to build exodus, see {0}".format(f))
                return ret

    cout("ExodusII libraries built")

    os.chdir(D)
    return 0


def write_fortran_source(source):
    """Read the libexoIIv2for library to determine the fortran name mangling and
    apply to the template file

    """
    # read in the template
    lines = open(os.path.join(D, "src/pyexodusii/exowrap.src"), "r").read()
    procs = dict((x, None)
                 for x in re.findall(r"<-(?P<proc>ex[a-z0-9_]+)->", lines))

    # read and determine procedure names from libexoIIv2for.a. This method may
    # be highly platform dependent due to the use of nm. On BSD Unix (Mac OS
    # X), nm -P libname.a produces output as:
    # symbol_name T 0 0

    # So, the following regular expression searches for any procedure of the
    # form
    # [_]ex[a-z0-9_]+
    out = check_output(["nm", "-P", os.path.join(prefix, "lib/libexoIIv2for.a")])
    regex = re.compile(r"[_]?(?P<proc>ex[a-z0-9_]+)\s+")
    mangled = regex.findall(out)

    # compare the two lists of procedure names
    for proc in procs:
        # find the mangled version
        for (i, p) in enumerate(mangled):
            p = p.rstrip("_")
            if p.startswith(proc) and len(p) - len(proc) <= 1:
                del mangled[i]
                procs[proc] = p
                break

    # make the replacement
    errors = 0
    for (pat, repl) in procs.items():
        if not repl:
            cout("*** error: {0}: no mangled replacement".format(pat))
            errors += 1
            pat = repl
        lines = re.sub(r"<-{0}->".format(pat), repl, lines)

    # write the source
    if errors:
        return errors

    with open(os.path.join(source), "w") as fobj:
        fobj.write(lines)

    return errors


def cout(message):
    sys.__stdout__.write(message + "\n")


if __name__ == '__main__':
    sys.exit(main())

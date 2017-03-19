import re
import os
from tools.configurer import cfgparse
from tools.errors import AFEPYError
from tools.logger import Logger
import tools.xpyclbr as xpyclbr
from tools.misc import load_file
from core.product import MAT_LIB_DIRS, SUPPRESS_USER_ENV

def find_materials():
    """Find material models

    """
    logger = Logger("console")

    errors = []
    mat_libs = {}
    rx = re.compile(r"(?:^|[\\b_\\.-])[Mm]at")
    a = ["MaterialModel", "AbaqusMaterial"]
    # gather and verify all files
    search_dirs = [d for d in MAT_LIB_DIRS]
    if not SUPPRESS_USER_ENV:
        for user_mat in cfgparse("materials"):
            user_mat = os.path.realpath(user_mat)
            if user_mat not in search_dirs:
                search_dirs.append(user_mat)

    # go through each item in search_dirs and generate a list of material
    # interface files. if item is a directory gather all files that match rx;
    # if it's a file, add it to the list of material files
    for item in search_dirs:
        if os.path.isfile(item):
            d, files = os.path.split(os.path.realpath(item))
            files = [files]
        elif os.path.isdir(item):
            d = item
            files = [f for f in os.listdir(item) if rx.search(f)]
        else:
            logger.warn("{0} no such directory or file, skipping".format(d),
                               report_who=1)
            continue
        files = [f for f in files if f.endswith(".py")]

        if not files:
            logger.warn("{0}: no mat files found".format(d), report_who=1)

        # go through files and determine if it's an interface file. if it is,
        # load it and add it to mat_libs
        for f in files:
            module = f[:-3]
            try:
                libs = xpyclbr.readmodule(module, [d], ancestors=a)
            except AttributeError as e:
                errors.append(e.args[0])
                logger.error(e.args[0])
                continue
            for lib in libs:
                if lib in mat_libs:
                    logger.error("{0}: duplicate material".format(lib))
                    errors.append(lib)
                    continue
                module = load_file(libs[lib].file)
                mat_class = getattr(module, libs[lib].class_name)
                if not mat_class.name:
                    raise AFEPYError("{0}: material name attribute "
                                     "not defined".format(lib))
                libs[lib].mat_class = mat_class
                mat_libs.update({mat_class.name.lower(): libs[lib]})

    if errors:
        raise AFEPYError(", ".join(errors))

    return mat_libs

matdb = find_materials()

materials = {}

def Material(model=None, parameters=None, name=None, density=None):
    if name is None:
        for i in range(1, 100):
            name = "Material-{0}".format(len(materials)+i)
            if name not in materials:
                break
        else:
            raise AFEPYError("Maximum number of materials exceeded")

    material = matdb.get(model.lower()).mat_class
    if material is None:
        raise AFEPYError("'{0}' is not a material".format(model))
    if isinstance(parameters, dict):
        parameters = material.parse_parameters(parameters)
    mat = material(parameters)
    materials[name] = mat
    mat.density = density or 1.
    return mat

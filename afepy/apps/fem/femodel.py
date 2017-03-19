import os
import time as ti
import numpy as np
from numpy import array, ones, zeros
from collections import OrderedDict

from fem import *
from tools.logger import Logger
from tools.exomgr import ExodusIIManager
from tools.misc import getopt, Int, Float, dof_id
from tools.errors import AFEPYError as AFEPYError
from mesh import Mesh

# solvers
from snls import StaticNewtonSolver
from dls import DynamicLinearSolver

INI = "Initial-Step"

class StepRepository(OrderedDict):
    pass

class Step:
    def __init__(self, name, step_type, solver_name, **kwargs):
        self.name = name
        self.dbcs = []
        self.cfs = []
        self.nbcs = []
        self.solver = None

        if self.name != INI:
            SN = solver_name.upper()
            ST = step_type.upper()
            if ST == "STATIC":
                solver = {"NONLINEAR": StaticNewtonSolver,
                          "LINEAR": StaticLinearSolver}.get(SN)
            elif step_type.upper() == "DYNAMIC":
                solver = {"LINEAR": DynamicLinearSolver}.get(SN)
            else:
                raise AFEPYError("step must be one of static or dynamic")
            if solver is None:
                raise AFEPYError("'{0}': unkown solver type".format(solver_name))
            self.solver = solver(**kwargs)

    def DisplacementBC(self, nodeset=None, dofs=None, mag=None, nodes=None,
                       region=None):
        self.dbcs.append({"nodeset": nodeset, "dofs": dofs, "mag": mag,
                          "nodes": nodes, "region": region})

    def Load(self, load_type, **kwargs):
        LT = load_type.upper()
        if LT == "CF":
            self.cfs.append(kwargs)

        elif LT == "T":
            try:
                sideset = kwargs["sideset"]
                components = kwargs["components"]
            except KeyError:
                raise AFEPYError("Load type 'T' expected "
                                 "'sideset, components' keywords")
            self.nbcs.append([sideset, components])

        else:
            raise AFEPYError("unknown load type")

class FEModel(object):

    def __init__(self, name="Untitled", outd=None, title=None):

        self.T0 = ti.time()
        self.outd = outd or os.getcwd()
        self.name = name
        self.title = title

        # Set up the logger
        filename = os.path.join(self.outd, self.name + ".log")
        self.logger = Logger(self.name, filename=filename)

        # assign some defaults
        self.steps = StepRepository()
        self.steps[INI] = Step(INI, None, None)
        self.materials = OrderedDict()
        self.mesh = None

        self.nodal_disp = None
        self.solved = False

        pass

    def run(self):
        """Solve the system of equations

           Ku = F

        Notes
        -----
        K is the global finite element stiffness
        F is the global finite element load
        u is the unkown nodal displacement vector

        """
        self.TI = ti.time()

        # The mesh must inherit from the mesh.Mesh abstract base class
        self.mesh.finalize()

        V = FunctionSpace(self.mesh)

        # Do some checks
        if not self.steps:
            raise AFEPYError("a required step has not been created")

        dbcs = [DirichletBC(V, **bc) for bc in self.steps[INI].dbcs]

        step_key = self.steps.keys()[1]
        step = self.steps[step_key]

        # Create dirichlet boundary conditions
        dbcs.extend([DirichletBC(V, **bc) for bc in step.dbcs])

        # Concetrated forces
        F = PointSourceVector(V, step.cfs)

        # Create Neumann boundary conditions
        nbcs = [NeumannBC(V, *nbc) for nbc in step.nbcs]

        # Allocate storage for element block quantities
        num_node = self.mesh.num_node
        num_dof_per_node = self.mesh.element_blocks[0].num_dof_per_node

        # Defaults
        num_elem = self.mesh.num_elem
        num_elem_block = len(self.mesh.element_blocks)

        # Element variables
        fdata = [eb.data for eb in self.mesh.element_blocks]
        funcs = [eb.func for eb in self.mesh.element_blocks]

        self.exo = ExodusIIManager()
        self.setup_exo()

        time = 0.

        u = Function(V)
        args = (V, funcs, fdata, time, dbcs, nbcs, F, u, self.exo, self.logger)

        self.logger.info("Starting AFEPY simulation for: "
                         "{0}".format(self.name), end="\n\n")

        description = self.steps[step_key].solver.desc
        num_step = self.steps[step_key].solver.options.increments
        tol = self.steps[step_key].solver.options.tolerance
        maxit = self.steps[step_key].solver.options.maxiters
        relax = self.steps[step_key].solver.options.relax
        period = self.steps[step_key].solver.options.period
        self.logger.write_intro(description, num_step, tol, maxit, relax,
                                time, period, num_dof_per_node, num_elem, num_node)
        try:
            self.steps[step_key].solver.solve(*args)
            self.solved = True
        except AFEPYError as err:
            self.logger.error(err.args[0])

        self.TF = ti.time()

        self.logger.info("Total time: {0:.2f}s".format(self.TF-self.T0))
        self.logger.info("Total solution time: {0:.2f}s".format(self.TF-self.TI))

        self.mesh.set_nodal_disp(u)

        if self.solved:
            self.logger.info("Analysis completed successfully", beg="\n")
        else:
            self.logger.info("Analysis did not complete", beg="\n")

        self.exo.finish()
        self.logger.finish()
        return

    def setup_exo(self):
        num_dim = self.mesh.num_dim
        coords = self.mesh.coords
        connect = self.mesh.connect

        elem_blks = []
        elem_data = []

        i = 0
        for elem_blk in self.mesh.element_blocks:
            neeb = elem_blk.num_elem
            evn = elem_blk.data.keys
            elem_blks.append([elem_blk.exo_id, elem_blk.elem_ids,
                              elem_blk.elem_type,
                              elem_blk.num_node_per_elem, evn])
            elem_data.append([elem_blk.exo_id, neeb,
                              zeros((neeb, len(evn)))])
            i += 1

        nodesets = self.mesh.nodesets_exo
        sidesets = self.mesh.sidesets_exo

        elem_num_map = self.mesh.elem_num_map

        self.exo.put_init(self.name, num_dim, coords, connect, elem_blks,
                          nodesets, sidesets, None, elem_data,
                          elem_num_map, d=self.outd, title=self.title)

    # ----------------- Factory type methods for the model ----------------- #
    def Step(self, name=None, type=None, solver=None, **solveopts):
        if len(self.steps) > 1:
            raise AFEPYError("only one load step currently supported")
        if name is None:
            i = 1
            while True:
                name = "Step-{0}".format(i)
                if name not in self.steps:
                    break
                i += 1
                if i > 50:
                    raise AFEPYError("maximum steps exceeded")
        if name in self.steps:
            raise AFEPYError("'{0}' already a step".format(name))
        self.steps[name] = Step(name, type, solver, **solveopts)
        return self.steps[name]

    def StaticStep(self, name=None, **solveopts):
        return self.Step(name, "static", "nonlinear", **solveopts)

    def LinearStep(self, name=None, **solveopts):
        return self.Step(name, "static", "linear", **solveopts)

    def DynamicStep(self, name=None, solver="linear", **solveopts):
        return self.Step(name, "dynamic", "linear", **solveopts)

    # --- Material
    def Mesh(self, *args, **kwargs):
        self.mesh = Mesh(*args, **kwargs)
        return self.mesh

    def ElementBlock(self, name=None, elements="ALL", material=None,
                     elem_type=None, exo_id=None, **elem_opts):
        if self.mesh is None:
            raise AFEPYError("mesh must be created before "
                             "assigning element blocks")

        block = self.mesh.ElementBlock(name, elements, exo_id=exo_id)

        if elem_type is None and material is None:
            return block

        self.set_properties("BLOCK", block.name, material=material,
                            elem_type=elem_type, **elem_opts)

        return block

    def set_properties(self, entity, name, **props):
        ITEM = entity.upper()
        if ITEM == "BLOCK":
            try:
                block = self.mesh.blocks[name]
            except KeyError:
                raise AFEPYError("{0} is not an element block".format(name))
            try:
                material = props.pop("material")
                elem_type = props.pop("elem_type")
            except KeyError:
                raise AFEPYError("required keywords 'material, elem_type' missing")
            if hasattr(material, "matmodel"):
                mat = material
            else:
                mat = self.materials.get(material)
            if mat is None:
                raise AFEPYError("{0}: not a model material".format(material))
            block.set_properties(material=mat, elem_type=elem_type, **props)

        else:
            raise AFEPYError("unknown entitity '{0}'".format(entity))

    def Sideset(self, name=None, surfaces=None, region=None, exo_id=None):
        if self.mesh is None:
            raise AFEPYError("mesh must be created before assigning sidesets")
        if surfaces is not None:
            for (i, item) in enumerate(surfaces):
                try: elem, face = item
                except ValueError: raise AFEPYError("bad sideset definition")
                # zero based mesh.  element number is not offset since it is
                # taken care of by the element mapping
                surfaces[i][1] -= 1
        sideset = self.mesh.Sideset(name, surfaces=surfaces, region=region,
                                    exo_id=exo_id)
        return sideset

    def Nodeset(self, name=None, nodes=None, region=None, exo_id=None):
        if self.mesh is None:
            raise AFEPYError("mesh must be created before assigning nodesets")
        nodeset = self.mesh.Nodeset(name, nodes=nodes, region=region,
                                    exo_id=exo_id)
        return nodeset

    # --- Boundary conditions
    def DisplacementBC(self, nodeset=None, dofs=None, mag=None, nodes=None,
                       region=None, step=INI):
        self.steps[step].DisplacementBC(nodeset=nodeset, dofs=dofs, mag=mag,
                                        nodes=nodes, region=region)

    def Load(self, type=None, step=None, **kwargs):
        if step is None:
            raise AFEPYError("missing required keyword 'step'")
        if step not in self.steps:
            raise AFEPYError("'{0}' not an analysis step".format(step))
        if step.lower() == INI.lower():
            raise AFEPYError("cannot apply load to initial step")
        self.steps[step].Load(type, **kwargs)

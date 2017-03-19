import os
import sys
import numpy as np
from scipy.interpolate import griddata

import __config__ as cfg
from src.base.utilities import clean_wasatch
from src.base.errors import WasatchError, UserInputError
from src.base.tensor import NSYMM
from src.fem.element.element import Element, STRESS, XTRA
from src.fem.element.elements import Quad4, DEFAULT_ELEMENTS


class RVE(Element):
    name = "RVE"
    eid = 20
    nnodes = None
    ncoord = None
    ndof = None
    def __init__(self, lmnid, nodes, coords, material, mat_params, perturbed,
                 *args, **kwargs):

        import src.fem.core.fe_model as fem

        # Find parent and child elements
        parent = kwargs.get("ParentElement")
        if parent is None:
            raise UserInputError("RVE element expected a parent element")
        parent = DEFAULT_ELEMENTS.get(parent.upper())
        if parent not in (Quad4,):
            raise WasatchError("RVE requires Quad4 parent element")
        self.name = parent.name

        # The analysis driver
        analysis_driver = kwargs.get("AnalysisDriver")
        if analysis_driver is None:
            raise UserInputError("No rve driver specified for RVE")
        analysis_driver = analysis_driver.upper()
        if analysis_driver not in ("WASATCH",):
            raise UserInputError("{0}: unsupported rve driver")
        self.analysis_driver = analysis_driver

        ki = kwargs.get("KeepIntermediateResults")
        if ki is not None:
            ki = {"FALSE": 0, "TRUE": 1}.get(ki.upper(), 1)
        self.wipe_intermediate = not bool(ki)

        template = kwargs.get("InputTemplate")
        if template is None:
            raise UserInputError("RVE element expected an input template")
        if not os.path.isfile(template):
            raise UserInputError("{0}: no such template file".format(template))
        self.input_template_file = template
        self.template = open(template, "r").read()

        # RVE inherits from parent.  Is there a better way to do this?
        self.parent = parent(lmnid, nodes, coords, material, mat_params, perturbed,
                             *args, **kwargs)
        self.bndry = self.parent.bndry
        self.nnodes = self.parent.nnodes
        self.ncoord = self.parent.ncoord
        self.ndof = self.parent.ndof
        self.dim = self.parent.dim
        self.ngauss = self.parent.ngauss
        self.cornernodes = self.parent.cornernodes
        self.facenodes = self.parent.facenodes
        self.gauss_coords = self.parent.gauss_coords
        self.gauss_weights = self.parent.gauss_weights

        # Find the refinement level and form the child mesh
        self.refinement = kwargs.get("Refinement", 10)
        self.generate_child_mesh_info(coords)

        self.end_state = None

        super(RVE, self).__init__(lmnid, nodes, coords, material, mat_params,
                                  perturbed, *args, **kwargs)

        # setup FEModel object for the entire RVE simulation
        wasatch_input = self.generate_wasatch_input(0., np.zeros((self.nnodes, 3)))
        runid = "{0}_EID={1}_RVE".format(kwargs["RUNID"], lmnid)
        self.rve_model = fem.FEModel.from_input_string(
            runid, wasatch_input, rundir=os.getcwd())

    def calc_shape(self, lcoord):
        return self.parent.calc_shape(lcoord)

    def calc_shape_deriv(self, lcoord):
        return self.parent.calc_shape_deriv(lcoord)

    def nface_nodes(self, face=None):
        return self.parent.nface_nodes(face)

    def face_nodes(self, face):
        return self.parent.face_nodes(face)

    def topomap(self, dom):
        return self.parent.topomap(dom)

    def volume(self, coords):
        return self.parent.volume(coords)

    def update_rve_state(self, t, dt, coords, u, du):
        if self.analysis_driver == "WASATCH":
            self.wasatch_rve_driver(t, dt, coords, u, du)

    def wasatch_rve_driver(self, t, dt, coords, u, du):

        # Set up FEModel for just this step
        import src.fem.core.fe_model as fem
        wasatch_input = self.generate_wasatch_input(t, u + du)
        runid = "RVE_{0}_{1:.4f}".format(self.lmnid, t)
        rve_model_t = fem.FEModel.from_input_string(
            runid, wasatch_input, rundir=os.getcwd())

        # set up to get and save data from this simulation
        if self.end_state is not None:
            # Load data from previous state
            for i, element in enumerate(rve_model_t.mesh.elements()):
                element.data[0, :] = self.end_state["ELEMENT DATA"][i]

        # solve for this step
        self.end_state = rve_model_t.solve(disp=1)

        # <--- Average element data from RVE to parent

        # Save the stiffness - average of all stiffnesses
        self.kel = np.average([el.kel for el in rve_model_t.mesh.elements()],
                              axis=0)

        # <--- Interpolate the values of stress and internal state

        # deformed coordinates of parent element
        xp = np.zeros((self.nnodes, self.ndof))
        for i in range(self.nnodes):
            xp[i] = coords[i] + u[i]
            continue

        # Coordinates of Gauss points on grid
        grid = np.zeros((self.nnodes, self.ndof))
        for j, xi in enumerate(self.gauss_coords):
            N = self.calc_shape(xi)
            grid[j, 0] = np.sum([xp[i, 0] * N[i] for i in range(len(N))])
            grid[j, 1] = np.sum([xp[i, 1] * N[i] for i in range(len(N))])

        # Points on child grid
        xyz = self.end_state["NODAL COORDINATES"]

        # Interpolate nodal stresses
        nodal_stresses = self.end_state["NODAL STRESSES"]
        for i, idx in enumerate(range(STRESS, STRESS + NSYMM)):
            self.data[1, 0:self.ngauss, idx] = griddata(
                xyz[:, [0, 1]], nodal_stresses[:, i], grid, method="cubic")

        # Interpolate nodal states
        # see notes in lento about nodal states
        # nodal_states = self.end_state["NODAL STATES"]
        # for i, idx in enumerate(range(XTRA, XTRA + self.material.nxtra)):
        #     self.data[1, 0:self.ngauss, idx] = griddata(
        #         xyz[:, [0, 1]], nodal_states[:, i], grid, method="cubic")
        # --->

        # Save the end state from the previous run to the RVE model and dump
        # it
        for i, element in enumerate(self.rve_model.mesh.elements()):
            element.data[0, :] = self.end_state["ELEMENT DATA"][i]

        if self.wipe_intermediate:
            clean_wasatch(runid, cleanall=True)

        return

    def dump_rve_end_state(self):
        self.rve_model.dump_time_step_data(
            self.end_state["TIME"],
            self.end_state["DT"],
            self.end_state["DISPLACEMENT"])

    def stiffness(self, dt, coords, du):
        return self.kel

    def generate_wasatch_input(self, t, u):
        wasatch_input = self.template.format(
            XMIN=self.xmin, XLEN=self.xlen, XINT=self.xint,
            YMIN=self.ymin, YLEN=self.ylen, YINT=self.yint,
            TTERM=t,
            X0Y0=" ".join("{0}".format(x) for x in self.ccoords[0]),
            X1Y0=" ".join("{0}".format(x) for x in self.ccoords[1]),
            X1Y1=" ".join("{0}".format(x) for x in self.ccoords[2]),
            X0Y1=" ".join("{0}".format(x) for x in self.ccoords[3]),
            X0Y0_X=u[0, 0], X0Y0_Y=u[0, 1],
            X1Y0_X=u[1, 0], X1Y0_Y=u[1, 1],
            X1Y1_X=u[2, 0], X1Y1_Y=u[2, 1],
            X0Y1_X=u[3, 0], X0Y1_Y=u[3, 1])
        return wasatch_input

    def generate_child_mesh_info(self, coords):
        # Create specification of inline mesh of the form
        # ETYPE [xmin, [[ID, Length, Interval],

        xpoints = coords[:, 0]
        xmin = np.amin(xpoints)
        xmax = np.amax(xpoints)
        xlen = xmax - xmin
        xint = int(float(self.refinement) / xlen)
        xblocks = [xmin, [[1, xlen, xint]]]

        ypoints = coords[:, 1]
        ymin = np.amin(ypoints)
        ymax = np.amax(ypoints)
        ylen = ymax - ymin
        yint = int(float(self.refinement) / ylen)
        yblocks = [ymin, [[1, ylen, yint]]]

        zpoints = coords[:, 2]
        zmin = np.amin(zpoints)
        zmax = np.amax(zpoints)
        zlen = zmax - zmin
        zint = 0 if not zlen else int(float(self.refinement) / zlen)
        zblocks = [zmin, [[1, zlen, zint]]]

        self.cconn = np.arange(4)
        self.ccoords = np.array(coords)
        self.xmin, self.xlen, self.xint = xmin, xlen, xint
        self.ymin, self.ylen, self.yint = ymin, ylen, yint
        self.zmin, self.zlen, self.zint = zmin, zlen, zint

        return

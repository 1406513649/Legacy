import sys
import numpy as np
from numpy import zeros, ones, sqrt, dot
from numpy.linalg import lstsq

from core.func import Function
from tools.errors import AFEPYError
from tools.lapackjac import linsolve
from tools.logger import ConsoleLogger as logger


HEAD = """\
 Step  Frame  Iteration   Load   Time   Time  Correction  Residual  Tolerance
                Number   Factor         Step"""
ITER_FMT = ("{0:=4}  {8:=4}     {1:=4}       {2:.2f}    {3:.2f}  {4:.2f}   "
            "{5:.2E}   {6:.2E}   {7:.2E}")

def StaticNonlinearSolve(V, data, node_bcs, tractions=None, F=None, period=1.,
                         increments=5, maxiters=10, tolerance=1.E-4, relax=1.):
    """Assemble and solve the system of equations

    Parameters
    ----------

    Notes
    -----
    Assembles and solves

                  Ku = F

    where

    K is the global finite element stiffness
    F is the global finite element load
    u is the unkown nodal displacement vector

    """

    # Allocate storage
    u = data.Zeros()
    if F is None:
        F = data.Zeros()

    dtime = period / float(increments)

    logger.write_intro("Static, nonlinear", increments, tolerance,
                       maxiters, relax, 0., period, V.num_dim, V.num_elem,
                       V.num_node)
    logger.info(HEAD)
    istep = 1
    for iframe in range(increments):
        kframe = iframe + 1

        load_fac = float(kframe) / float(increments)
        err1 = 1.

        # Newton-Raphson loop
        for nit in range(maxiters):

            # Update element states
            V.update_kinematics(data, u, dtime)
            A = V.stiffness(data, u, data.time, dtime, kframe)
            R = V.residual(data, u)
            q = V.force(tractions) + F

            # Compute global force
            rhs = load_fac * q - R

            # Enforce displacement boundary conditions
            V.apply_bcs(data, node_bcs, A, rhs, u, fac=load_fac)

            # --- Solve for the nodal displacement
            du = linsolve(A, rhs)

            # --- update displacement increment
            u += relax * du

            # --- Check convergence
            dusq = dot(u, u)
            err1 = dot(du, du)
            if dusq != 0.:
                err1 = sqrt(err1 / dusq)
            err2 = sqrt(dot(rhs, rhs)) / float(V.num_dof)

            message = ITER_FMT.format(istep, nit+1, load_fac, data.time, dtime,
                                      err1, err2, tolerance, kframe)
            logger.info(message)

            if err1 < tolerance or err2 < tolerance:
                break

            continue

        else:
            raise AFEPYError("Failed to converge on step {0}, "
                             "frame {1}".format(istep, kframe))

        data.time += dtime
        data += u

    logger.write("Simulation completed successfully\n")
    logger.write("=" * 78)
    return

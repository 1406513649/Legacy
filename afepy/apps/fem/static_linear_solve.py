from numpy import dot, zeros, zeros_like, ones
from numpy.linalg import lstsq

from tools.lapackjac import linsolve
from tools.errors import AFEPYError
from tools.logger import ConsoleLogger as logger
from core.source_term import SourceTerm

HEAD = """\
 Step  Frame  Iteration   Load   Time   Time  Correction  Residual  Tolerance
                Number   Factor         Step"""
ITER_FMT = ("{0:=4}     {4}        {4}       {1:.2f}   {2:.2f}   {3:.2f}"
            "       {4}         {4}          {4}")

def StaticLinearSolve(V, data, node_bcs, tractions=None, F=None, period=1.):
    """Assemble and solve the system of equations

    Notes
    -----
    Assembles and solves

                  Ku = F

    where

    K is the global finite element stiffness
    F is the global finite element load
    u is the unkown nodal displacement vector

    """
    logger.write_intro("Static, direct", 1, None, None, None,
                       0., period, V.num_dim, V.num_elem, V.num_node)
    kstep = 1
    logger.write(HEAD)

    # Allocate storage
    u = data.Zeros()
    q = SourceTerm(V)

    if F is not None:
        q += F

    # Get initial estimate of element stiffnesses
    A = V.stiffness(data, u, 0., period, 0)

    # Reset state
    data.reset()

    # Compute global force
    q += V.force(tractions)

    # Enforce displacement boundary conditions
    B = A.copy()
    V.apply_bcs(data, node_bcs, A, q, u)

    # --- Solve for the nodal displacement
    u = linsolve(A, q)

    message = ITER_FMT.format(1, 1, data.time, period, "-")
    logger.info(message)

    # Updating stress and strains is a post process
    V.update_kinematics(data, u, period)
    V.update_material(data, u, 0., period, 1)

    data.time += period
    data += u

    logger.write("Simulation completed successfully\n")
    logger.write("=" * 78)

    return

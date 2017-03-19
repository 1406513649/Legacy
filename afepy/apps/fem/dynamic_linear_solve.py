from numpy import dot, zeros, ones, eye, diag
from numpy.linalg import lstsq

from tools.errors import AFEPYError
from tools.lapackjac import linsolve
from tools.logger import ConsoleLogger as logger


HEAD = """\
 Step  Increment Time   Time
                        Step"""
ITER_FMT = "{0:=4}    {1:=4}     {2:.2f}   {3:.2f}"


def ExplicitLinearSolve(V, u, node_bcs, tractions, F=None, period=1.,
                        a=.5, b=0., increments=50.):
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
    lumped_mass = 1
    alpha, beta = a, b

    du = u.Zeros()
    if F is None:
        F = u.Zeros()
    v = zeros((2, du.shape[0]))
    a = zeros((2, du.shape[0]))
    dtime = period / float(increments)

    # Get initial estimate of element stiffnesses
    A = V.stiffness(u, du, u.time, period, 0)
    M = V.mass(lumped_mass=lumped_mass)

    # Reset state
    u.reset()

    logger.write_intro("Dynamic, linear", increments, None,
                       None, None, 0., period, V.num_dim, V.num_elem,
                       V.num_node)
    logger.write(HEAD)

    # Compute global force
    F += V.force(tractions)

    # Enforce displacement boundary conditions
    V.apply_bcs(u, node_bcs, A, F, du)

    # adjusted mass and initial acceleration
    Mk = M + .5 * beta * dtime * dtime * A
    a[0] = linsolve(M, -dot(A, u.u) + F)

    istep = 1
    for n in range(increments):
        kstep = n + 1

        # update residual
        uu = u.u + dtime * v[0] + .5 * (1. - beta) * dtime * dtime * a[0]
        rn = F - dot(A, uu)

        # update acceleration
        if lumped_mass:
            a[1] = rn / diag(Mk)
        else:
            a[1] = linsolve(Mk, rn)

        # update velocity
        v[1] = v[0] + dtime * (1. - alpha * a[0] + alpha * a[1])

        # increment in displacement
        du[:] = dtime * v[0] + .5 * dtime * dtime * ((1. - beta) * a[0]
                                                     + beta * a[1])

        # Update element states
        A = V.stiffness(u, du, u.time, dtime, kstep)

        v[0] = v[1]
        a[0] = a[1]

        u.time += dtime
        u += du

        message = ITER_FMT.format(istep, n+1, u.time, dtime)
        logger.info(message)

    logger.write("Simulation completed successfully\n")
    logger.write("=" * 78)
    return

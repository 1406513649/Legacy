try:
    import scipy.linalg.flapack as flapack
except ImportError:
    flapack = None
from numpy import asarray
import numpy.linalg as la
from tools.errors import AFEPYError
from tools.logger import ConsoleLogger as logger

def linsolve(A, b, symmetric=True):
    """Interface to the lapack dposv solve function in scipy.linalg

    Parameters
    ----------
    A : ndarray
        Real, symmetric, positive-definite matrix (the stiffness matrix)
    b : ndarray
        RHS of system of equations

    Returns
    -------
    c : ndarray
    x : ndarray
        Solution to A x = b
    info : int
        info < 0 -> bad input
        info = 0 -> solution is in x
        ifno > 0 -> singular matrix

    Notes
    -----
    dposv solves the system of equations A x = b using lapack's dposv
    procedure. This interface function is used to avoid the overhead of
    calling down in to scipy, converting arrays to fortran order, etc.

    """
    try:
        F = b.asarray()
    except AttributeError:
        F = asarray(b)

    use_np_solve = not symmetric or flapack == None
    x, info = None, 1
    if not use_np_solve:
        c, x, info = flapack.dposv(A, F, lower=0, overwrite_a=0, overwrite_b=0)
        if info < 0:
            raise AFEPYError("illegal value in {0}-th argument of "
                             "internal dposv".format(-info))
        if info != 0:
            use_np_solve = True

    if use_np_solve:
        try:
            x = la.solve(A, F)
            info = 0
        except la.LinAlgError:
            pass

    if info > 0:
        logger.warn("linsolve failed, using least squares "
                    "to solve system")
        x = la.lstsq(A, F)[0]

    return x

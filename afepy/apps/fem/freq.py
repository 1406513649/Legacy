from numpy import dot, zeros, sqrt, array
from numpy.linalg import inv, svd

from tools.errors import AFEPYError
from tools.logger import ConsoleLogger as logger


HEAD = """\
 Step  Increment Time   Time
                        Step"""
ITER_FMT = "{0:=4}    {1:=4}     {2:.2f}   {3:.2f}"


def ModeShapes(V, u, node_bcs):
    """Assemble and solve the system of equations

    Parameters
    ----------

    Notes
    -----

    """
    lumped_mass = 1

    # Get initial estimate of element stiffnesses
    du = u.Zeros()
    F = u.Zeros()
    A = V.stiff(u, u.time, 1., du, 0)
    M = V.mass(lumped_mass=1)
    V.apply_bcs(u, du, node_bcs, A, F)

    rtm = sqrt(M)
    irtm = inv(rtm);
    H = dot(dot(irtm, A), irtm)
    Q, Lambda, QQ = svd(H)

    # Sort eigenvalues into order
    elist = array(sorted([Lambda[i,i] for i in range(V.num_dof)]))
    print elist[:10]

    # Can specify which (non rigid body) mode to extract below
    for mode in range(4):
        for i in range(V.num_dof):
            if Lambda[i,i] - elist[mode+3*ndof] ** 2 < 0.00000001:
                mn = i

        u.u[:] = dot(irtm, Q[mn, :])

        scale = 3.;
        for i in range(V.num_node):
            for j in range(V.num_dof_per_node):
                x[i, j] = V.X[i, j] + scale * u[V.num_dor_per_node*i+j]


    return

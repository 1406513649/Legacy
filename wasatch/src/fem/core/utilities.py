import sys
import time
import numpy as np
import scipy.linalg.flapack as flapack

import __runopt__ as ro

def intro(integration, runid, nsteps, tol, maxit, relax, tstart, tterm,
          ndof, nelems, nnode, elements):

    # Look for any RVE elements to write extra info about
    rve_info = ""
    rve_elements = [element for element in elements
                    if element.rve_model is not None]
    if rve_elements:
        rve_info = """
Summary of RVE elements
======= == === ========
  number of RVE elements = {0}
""".format(len(rve_elements))

        for i, rve_element in enumerate(rve_elements):
            rve_info += """
  RVE # {0}
  --- -{6}
  rve analysis driver = {1}
    parent element ID = {2}
  parent element type = {3}
      intput template = {4}
  rve mesh refinement = {5}
""".format(i + 1, rve_element.analysis_driver, rve_element.parent.lmnid,
           rve_element.parent.name, rve_element.input_template_file,
           rve_element.refinement, "-" + "-" * len(str(i+1)))

    return """\
Starting Wasatch simulation for {1}

Summary of simulation input
======= == ========== =====

  Integration type
  ----------- ----
    {0}

  Control information
  ------- -----------
    number of load steps = {2:d}
               tolerance = {3:8.6f}
      maximum iterations = {4:d}
              relaxation = {5:8.6f}
              start time = {6:8.6f}
        termination time = {7:8.6f}

  Mesh information
  ---- -----------
    number of dimensions = {8:d}
      number of elements = {9:d}
      number of vertices = {10:d}
{11}
""".format(integration, runid, nsteps, tol, maxit, relax, tstart, tterm,
           ndof, nelems, nnode, rve_info)


def update_element_states(t, dt, X, elements, connect, u, du):
    """Update the stress and state variables

    Parameters
    ----------
    dt : real
        Time step

    X : array like, (i, j,)
        ith coord of jth node, for i=1...ncoord; j=1...nnode

    connect : array_like, (i, j,)
        List of nodes on the jth element

    elements : array_like, (i,)
        Array of element class instances

    du : array_like, (i, 1)
        Nodal displacement increments

    Returns
    -------

    """
    maxnodes = np.amax([x.nnodes for x in elements])
    ndof = elements[0].ndof
    ncoord = elements[0].ncoord
    X_e = np.zeros((maxnodes, ncoord))
    du_e = np.zeros((maxnodes, ndof))
    u_e = np.zeros((maxnodes, ndof))

    if ro.debug:
        ti = time.time()
        sys.stdout.write("*** entering: "
                         "fe.core.utilities.update_element_states\n")

    # Loop over all the elements
    for element in elements:
        lmn = element.lmnid
        # Extract coords of nodes,  DOF for the current element
        for a in range(element.nnodes):
            X_e[a, :ncoord] = X[connect[lmn, a], :ncoord]
            du_e[a, :ndof] = [du[ndof * connect[lmn, a] + i] for i in range(ndof)]
            u_e[a, :ndof] = [u[ndof * connect[lmn, a] + i] for i in range(ndof)]
            continue
        element.update_state(t, dt, X_e, u_e, du_e)
        continue # lmn

    if ro.debug:
        sys.stdout.write("***  exiting: "
                         "fem.core.utilities.update_element_states (%.2fs)\n"
                         % (time.time() - ti))
    return


def linsolve(a, b):
    """Interface to the lapack dposv solve function in scipy.linalg

    Parameters
    ----------
    a : ndarray
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
    if ro.debug:
        ti = time.time()
        sys.stdout.write('*** entering: fem.core.lento.linsolve\n')

    c, x, info = flapack.dposv(a, b, lower=0, overwrite_a=0, overwrite_b=0)

    if ro.debug:
        sys.stdout.write('***  exiting: fem.core.lento.linsolve (%.2f)s\n'
                         % (time.time() - ti) )

    return c, x, info

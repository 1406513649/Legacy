from numpy import *

from core.femspace import FiniteElementSpace
from core.dirichlet import DirichletBC
from core.neumann import NeumannBC
from core.func import Function
from core.source_term import PointSource, SourceTerm
from core.solution import SolutionSpace

from mesh import Mesh
from material import Material
from elem import FiniteElement
from tools.exomgr import ExodusIIFile
from tools.misc import Range
from tools.lapackjac import linsolve

# Application specific imports
from apps.fem.static_linear_solve import StaticLinearSolve
from apps.fem.static_nonlin_solve import StaticNonlinearSolve
from apps.fem.dynamic_linear_solve import ExplicitLinearSolve
from apps.fem.freq import ModeShapes

from numpy import set_printoptions
def pprecision(n):
    set_printoptions(n)

from tools.errors import opts
def raise_e():
    opts.raise_e = not opts.raise_e

def verbosity(n):
    from tools.logger import ConsoleLogger
    ConsoleLogger.set_verbosity(n)

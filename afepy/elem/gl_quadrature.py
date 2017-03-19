"""Properties and shape functions defining Gauss-Legendre quadrature"""
from numpy import zeros

class IntegrationProperties(object):

    def __init__(self, num_coord, num_el_node, reduced=False):
        self.num_point = self.ng(num_coord, num_el_node, reduced=reduced)
        self.points = self.ip(num_coord, num_el_node, self.num_point)
        self.weights = self.iw(num_coord, num_el_node, self.num_point)

        # Mass properties
        self.num_mass_point = self.nmp(num_coord, num_el_node)
        self.mass_weights = self.iw(num_coord, num_el_node, self.num_mass_point)
        self.mass_points = self.ip(num_coord, num_el_node, self.num_mass_point)

    @staticmethod
    def ng(num_coord, num_el_node, reduced=False):
        """Number of integration points """
        key = (num_coord, num_el_node)
        if reduced:
            n = {(1, num_el_node): 1,
                 (2, 4): 1, (2, 8): 4,
                 (3, 8): 1, (3, 20): 8}[key]
        else:
            n = {(1, num_el_node): num_el_node,
                 (2, 3): 1, (2, 6): 3, (2, 4): 4, (2, 8): 9,
                 (3, 4): 1, (3, 10): 4, (3, 8): 8, (3, 20): 27}[key]
        return n

    @staticmethod
    def nmp(num_coord, num_el_node):
        """Number of integration points for mass matrices"""
        key = (num_coord, num_el_node)
        n = {(1, num_el_node): num_el_node,
             (2, 3): 4, (2, 6): 7, (2, 4): 4, (2, 8): 9,
             (3, 4): 4, (3, 10): 5, (3, 8): 27, (3, 20): 27}[key]
        return n

    @staticmethod
    def ip(num_coord, num_el_node, num_point):
        """Defines positions of integration points"""
        xi = zeros((num_point, num_coord))

        # --- 1D elements
        if num_coord == 1:
            if num_point ==1:
                xi[0,0] = 0.

            elif num_point == 2:
                xi[0,0] = -0.5773502692
                xi[1,0] =  0.5773502692

            elif num_point == 3:
                xi[0,0] = -0.7745966692
                xi[1,0] =  0.0
                xi[2,0] =  0.7745966692

        # --- 2D elements
        elif num_coord == 2:

            # Triangular elements
            if num_el_node in (3, 6):
                if num_point == 1:
                    xi[0,0] = 1. / 3.
                    xi[0,1] = 1. / 3.

                elif num_point == 3:
                    xi[0,0] = 0.6
                    xi[0,1] = 0.2
                    xi[1,0] = 0.2
                    xi[1,1] = 0.6
                    xi[2,0] = 0.2
                    xi[2,1] = 0.2

                elif num_point == 4:
                    xi[0,0] = 1. / 3.
                    xi[0,1] = 1. / 3.
                    xi[1,0] = 0.6
                    xi[1,1] = 0.2
                    xi[2,0] = 0.2
                    xi[2,1] = 0.6
                    xi[3,0] = 0.2
                    xi[3,1] = 0.2

                elif num_point == 7:
                    xi[0,0] = 1. / 3.0
                    xi[0,1] = xi[0,0]
                    xi[1,0] = 0.0597158717
                    xi[1,1] = 0.4701420641
                    xi[2,0] = xi[1,1]
                    xi[2,1] = xi[1,0]
                    xi[3,0] = xi[1,1]
                    xi[3,1] = xi[1,1]
                    xi[4,0] = 0.7974269853
                    xi[4,1] = 0.1012865073
                    xi[5,0] = xi[4,1]
                    xi[5,1] = xi[4,0]
                    xi[6,0] = xi[4,1]
                    xi[6,1] = xi[4,1]

            # Rectangular elements
            elif num_el_node in (4, 8):

                if num_point == 1:
                    xi[0,0] = 0.
                    xi[0,1] = 0.

                elif num_point == 4:
                    xi[0,0] = -0.5773502692
                    xi[0,1] =  xi[0,0]
                    xi[1,0] = -xi[0,0]
                    xi[1,1] =  xi[0,0]
                    xi[2,0] =  xi[0,0]
                    xi[2,1] = -xi[0,0]
                    xi[3,0] = -xi[0,0]
                    xi[3,1] = -xi[0,0]

                elif num_point == 9:
                    xi[0,0] = -0.7745966692
                    xi[0,1] =  xi[0,0]
                    xi[1,0] =  0.0
                    xi[1,1] =  xi[0,0]
                    xi[2,0] = -xi[0,0]
                    xi[2,1] =  xi[0,0]
                    xi[3,0] =  xi[0,0]
                    xi[3,1] =  0.0
                    xi[4,0] =  0.0
                    xi[4,1] =  0.0
                    xi[5,0] = -xi[0,0]
                    xi[5,1] =  0.0
                    xi[6,0] =  xi[0,0]
                    xi[6,1] = -xi[0,0]
                    xi[7,0] =  0.0
                    xi[7,1] = -xi[0,0]
                    xi[8,0] = -xi[0,0]
                    xi[8,1] = -xi[0,0]

        # --- 3D elements
        elif num_coord == 3:

            if num_el_node == (4, 10):

                if num_point == 1:
                    xi[0,0] = 0.25
                    xi[0,1] = 0.25
                    xi[0,2] = 0.25

                elif num_point == 4:
                    xi[0,0] = 0.58541020
                    xi[0,1] = 0.13819660
                    xi[0,2] = xi[0,1]
                    xi[1,0] = xi[0,1]
                    xi[1,1] = xi[0,0]
                    xi[1,2] = xi[0,1]
                    xi[2,0] = xi[0,1]
                    xi[2,1] = xi[0,1]
                    xi[2,2] = xi[0,0]
                    xi[3,0] = xi[0,1]
                    xi[3,1] = xi[0,1]
                    xi[3,2] = xi[0,1]

                elif num_point == 5:
                    xi[0,0] = 0.25
                    xi[0,1] = 0.25
                    xi[0,2] = 0.25
                    xi[1,0] = 0.5
                    xi[1,1] = 1. / 6.
                    xi[1,2] = 1. / 6.
                    xi[2,0] = 1. / 6.
                    xi[2,1] = 0.5
                    xi[2,2] = 1. / 6.
                    xi[3,0] = 1. / 6.
                    xi[3,1] = 13819660. / 6.
                    xi[3,2] = 0.5
                    xi[4,0] = 1. / 6.
                    xi[4,1] = 1. / 6.
                    xi[4,2] = 1. / 6.

            elif num_el_node in (8, 20):
                if num_point == 1:
                    xi[0,0] = 0.
                    xi[0,1] = 0.
                    xi[0,2] = 0.

                elif num_point == 8:
                    xx = [-0.5773502692, 0.5773502692]
                    for k in range(2):
                        for j in range(2):
                            for i in range(2):
                                n = 4 * k  +  2 * j + i
                                xi[n,0] = xx[i]
                                xi[n,1] = xx[j]
                                xi[n,2] = xx[k]

                elif num_point == 27:
                    xx = [-0.7745966692, 0., 0.7745966692]
                    for k in range(3):
                        for j in range(3):
                            for i in range(3):
                                n = 9 * k + 3 * j + i
                                xi[n,0] = xx[i]
                                xi[n,1] = xx[j]
                                xi[n,2] = xx[k]
        return xi

    @staticmethod
    def iw(num_coord, num_el_node, num_point):
        """Defines integration weights"""
        w = zeros(num_point)

        # --- 1D elements
        if num_coord == 1:
            if num_point == 1:
                w[0] = 2.
            elif num_point == 2:
                w[:] = [1., 1.]
            elif num_point == 3:
                w[:] = [0.555555555, 0.888888888, 0.555555555]

        # --- 2D elements
        elif num_coord == 2:

            # Triangular elements
            if num_el_node in (3, 6):
                if num_point == 1:
                    w[0] = 0.5
                elif num_point == 3:
                    w[0] = 1. / 6.
                    w[1] = 1. / 6.
                    w[2] = 1. / 6.
                elif num_point == 4:
                    w[:] = [-27. / 96., 25. / 96., 25 / 96., 25 / 96.]

            # Rectangular elements
            elif num_el_node in (4, 8):

                if num_point == 1:
                    w[0] = 4.
                elif num_point == 4:
                    w[:] = [1., 1., 1., 1.]
                elif num_point == 9:
                    ww = [0.555555555, 0.888888888, 0.55555555555]
                    for j in range(3):
                        for i in range(3):
                            n = 3 * j + i
                            w[n] = ww[i] * ww[j]

        # --- 3D elements
        elif num_coord == 3:
            if num_el_node in (4, 10):
                if num_point == 1:
                    w[0] = 1. / 6.
                elif num_point == 4:
                    w[:] = [1. / 24., 1. / 24., 1. / 24.,1. / 24.]
            elif num_el_node in (8, 20):
                    if num_point == 1:
                        w[0] = 8.
                    elif num_point == 8:
                        w[:] = [1., 1., 1., 1., 1., 1., 1., 1.]
                    elif num_point == 27:
                        ww = [0.555555555, 0.888888888, 0.55555555555]
                        for k in range(3):
                            for j in range(3):
                                for i in range(3):
                                    n = 9 * k + 3 * j + i
                                    w[n] = ww[i] * ww[j] * ww[k]

        return w

class ShapefunctionPrototype:
    """ Shape function definitions for several element types """
    def __init__(self, num_coord, num_el_node):
        self.num_coord = num_coord
        self.num_el_node = num_el_node
        self.eval = self._eval(num_coord, num_el_node)
        self.grad = self._grad(num_coord, num_el_node)

    def _eval(self, num_coord, num_el_node):
        """Formats and returns a function that can later be used to evaluate
        the shape function at xi"""
        num_el_node = self.num_el_node
        num_coord = self.num_coord
        assert num_coord in (1, 2, 3)

        f = zeros(num_el_node)

        # --- 1D elements
        if num_coord == 1:
            if num_el_node==2:
                def evalf(xi):
                    f[:] = 0.
                    x, = xi[:1]
                    f[0] = 0.5 * (1. - x)
                    f[1] = 0.5 * (1. + x)
                    return f

            elif num_el_node == 3:
                def evalf(xi):
                    f[:] = 0.
                    x, = xi[:1]
                    f[0] =  -0.5 * x * (1. - x)
                    f[1] =  0.5 * x * (1. + x)
                    f[2] = (1. - x) * (1. + x)
                    return f

        #  --- 2D elements
        elif num_coord == 2:

            # Linear triangle
            if num_el_node == 3:
                def evalf(xi):
                    f[:] = 0.
                    x, y = xi[:2]
                    f[0] = x
                    f[1] = y
                    f[2] = 1. - x - y
                    return f

            # Quadratic triangle
            elif num_el_node == 6:
                def evalf(xi):
                    f[:] = 0.
                    x, y = xi[:2]
                    xx = 1. - x - y
                    f[0] = (2. * x - 1.) * x
                    f[1] = (2. * y - 1.) * y
                    f[2] = (2. * xx - 1.) * xx
                    f[3] = 4. * x * y
                    f[4] = 4. * y * xx
                    f[5] = 4. * xx * x
                    return f

            # Linear quad
            elif num_el_node == 4:
                def evalf(xi):
                    f[:] = 0.
                    x, y = xi[:2]
                    f[0] = 0.25 * (1. - x) * (1. - y)
                    f[1] = 0.25 * (1. + x) * (1. - y)
                    f[2] = 0.25 * (1. + x) * (1. + y)
                    f[3] = 0.25 * (1. - x) * (1. + y)
                    return f

            # Quadratic quad
            elif num_el_node == 8:
                def evalf(xi):
                    f[:] = 0.
                    x, y = xi[:2]
                    f[0] = -0.25 * (1. - x) * (1. - y) * (1. + x + y)
                    f[1] =  0.25 * (1. + x) * (1. - y) * (x - y - 1.)
                    f[2] =  0.25 * (1. + x) * (1. + y) * (x + y - 1.)
                    f[3] =  0.25 * (1. - x) * (1. + y) * (y - x - 1.)
                    f[4] =  0.5 * (1. - x * x) * (1. - y)
                    f[5] =  0.5 * (1. + x) * (1. - y * y)
                    f[6] =  0.5 * (1. - x * x) * (1. + y)
                    f[7] =  0.5 * (1. - x) * (1. - y * y)
                    return f

        #  --- 3D elements
        elif num_coord==3:

            # Linear tet
            if num_el_node == 4:
                def evalf(xi):
                    f[:] = 0.
                    x, y, z = xi[:3]
                    f[0] = 1. - x - y - z
                    f[1] = x
                    f[2] = y
                    f[3] = z
                    return f

            # Quadratic tet
            elif num_el_node == 10:
                def evalf(xi):
                    f[:] = 0.
                    x, y, z = xi[:3]
                    xx = 1. - x - y - z
                    f[0] = (2. * x - 1.) * x
                    f[1] = (2. * y - 1.) * y
                    f[2] = (2. * z - 1.) * z
                    f[3] = (2. * xx - 1.) * xx
                    f[4] = 4. * x * y
                    f[5] = 4. * y * z
                    f[6] = 4. * z * x
                    f[7] = 4. * x * xx
                    f[8] = 4. * y * xx
                    f[9] = 4. * z * xx
                    return f

            # Linear hex
            elif num_el_node == 8:
                def evalf(xi):
                    f[:] = 0.
                    x, y, z = xi[:3]
                    f[0] = (1. - x) * (1. - y) * (1. - z) / 8.
                    f[1] = (1. + x) * (1. - y) * (1. - z) / 8.
                    f[2] = (1. + x) * (1. + y) * (1. - z) / 8.
                    f[3] = (1. - x) * (1. + y) * (1. - z) / 8.
                    f[4] = (1. - x) * (1. - y) * (1. + z) / 8.
                    f[5] = (1. + x) * (1. - y) * (1. + z) / 8.
                    f[6] = (1. + x) * (1. + y) * (1. + z) / 8.
                    f[7] = (1. - x) * (1. + y) * (1. + z) / 8.
                    return f

            # Quadratic hex
            elif num_el_node == 20:
                def evalf(xi):
                    f[:] = 0.
                    x, y, z = xi[:3]
                    f[0] = (1.-x)*(1.-y)*(1.-z)*(-x-y-z-2.)/8.
                    f[1] = (1.+x)*(1.-y)*(1.-z)*(x-y-z-2.)/8.
                    f[2] = (1.+x)*(1.+y)*(1.-z)*(x+y-z-2.)/8.
                    f[3] = (1.-x)*(1.+y)*(1.-z)*(-x+y-z-2.)/8.
                    f[4] = (1.-x)*(1.-y)*(1.+z)*(-x-y+z-2.)/8.
                    f[5] = (1.+x)*(1.-y)*(1.+z)*(x-y+z-2.)/8.
                    f[6] = (1.+x)*(1.+y)*(1.+z)*(x+y+z-2.)/8.
                    f[7] = (1.-x)*(1.+y)*(1.+z)*(-x+y+z-2.)/8.
                    f[8] = (1. - x ** 2) * (1. - y) * (1. - z) / 4.
                    f[9] = (1. + x) * (1. - y ** 2) * (1. - z) / 4.
                    f[10] = (1. - x ** 2) * (1. + y) * (1. - z) / 4.
                    f[11] = (1. - x) * (1. - y ** 2) * (1. - z) / 4.
                    f[12] = (1. - x ** 2) * (1. - y) * (1. + z) / 4.
                    f[13] = (1. + x) * (1. - y ** 2) * (1. + z) / 4.
                    f[14] = (1. - x ** 2) * (1. + y) * (1. + z) / 4.
                    f[15] = (1. - x) * (1. - y ** 2) * (1. + z) / 4.
                    f[16] = (1. - x) * (1. - y) * (1. - z ** 2) / 4.
                    f[17] = (1. + x) * (1. - y) * (1. - z ** 2) / 4.
                    f[18] = (1. + x) * (1. + y) * (1. - z ** 2) / 4.
                    f[19] = (1. - x) * (1. + y) * (1. - z ** 2) / 4.
                    return f

        return evalf

    def _grad(self, num_coord, num_el_node):
        """Formats and returns a function that can later be used to evaluate
        the shape function derivative at xi"""

        df = zeros((num_coord, num_el_node))

        # --- 1D elements
        if num_coord == 1:

            if num_el_node == 2:
                def evalg(xi):
                    df[:,:] = 0.
                    x, = xi[:1]
                    df[0,0] =  0.5
                    df[0,1] = -0.5
                    return df

            elif num_el_node == 3:
                def evalg(xi):
                    df[:,:] = 0.
                    x, = xi[:1]
                    df[0,0] =  -0.5 + x
                    df[0,1] =   0.5 + x
                    df[0,2] =  -2. * x
                    return df

        #  --- 2D elements
        elif num_coord == 2:

            # Linear triangle
            if num_el_node == 3:
                def evalg(xi):
                    df[:,:] = 0.
                    x, y = xi[:2]
                    df[0,0] =  1.
                    df[0,2] = -1.

                    df[1,1] =  1.
                    df[1,2] = -1.
                    return df

            # Quadratic triangle
            elif num_el_node == 6:
                def evalg(xi):
                    df[:,:] = 0.
                    x, y = xi[:2]
                    xx = 1. - x - y
                    df[0,0] =  4. * x - 1.
                    df[0,2] = -(4. * xx - 1.)
                    df[0,3] =  4. * y
                    df[0,4] = -4. * y
                    df[0,5] =  4. * xx - 4. * x

                    df[1,1] =  4. * y - 1.
                    df[1,2] = -(4. * xx - 1.)
                    df[1,3] =  4. * x
                    df[1,4] = -4. * x
                    df[1,5] =  4. * xx - 4. * y
                    return df

            # Linear quad
            elif num_el_node == 4:
                def evalg(xi):
                    df[:,:] = 0.
                    x, y = xi[:2]
                    df[0,0] = -0.25 * (1. - y)
                    df[0,1] =  0.25 * (1. - y)
                    df[0,2] =  0.25 * (1. + y)
                    df[0,3] = -0.25 * (1. + y)

                    df[1,0] = -0.25 * (1. - x)
                    df[1,1] = -0.25 * (1. + x)
                    df[1,2] =  0.25 * (1. + x)
                    df[1,3] =  0.25 * (1. - x)
                    return df

            # Quadratic quad
            elif num_el_node == 8:
                def evalg(xi):
                    df[:,:] = 0.
                    x, y = xi[:2]
                    df[0,0] =  0.25 * (1. - y) * (2. * x + y)
                    df[0,1] =  0.25 * (1. - y) * (2. * x - y)
                    df[0,2] =  0.25 * (1. + y) * (2. * x + y)
                    df[0,3] =  0.25 * (1. + y) * (2. * x - y)
                    df[0,4] = -x * (1. - y)
                    df[0,5] =  0.5 * (1. - y * y)
                    df[0,6] = -x * (1. + y)
                    df[0,7] = -0.5 * (1. - y * y)

                    df[1,0] =  0.25 * (1. - x) * (x + 2. * y)
                    df[1,1] =  0.25 * (1. + x) * (2. * y - x)
                    df[1,2] =  0.25 * (1. + x) * (2. * y + x)
                    df[1,3] =  0.25 * (1. - x) * (2. * y - x)
                    df[1,4] = -0.5 * (1. - x * x)
                    df[1,5] = -(1. + x) * y
                    df[1,6] =  0.5 * (1. - x * x)
                    df[1,7] = -(1. - x) * y
                    return df

        # --- 3D elements
        elif num_coord == 3:

            # Linear tet
            if num_el_node == 4:
                def evalg(xi):
                    df[:,:] = 0.
                    x, y, z = xi[:3]
                    df[0,0] = -1.
                    df[0,1] =  1.

                    df[1,0] = -1.
                    df[1,2] =  1.

                    df[2,0] = -1.
                    df[2,3] =  1.
                    return df

            # Quadratic tet
            elif num_el_node == 10:
                def evalg(xi):
                    df[:,:] = 0.
                    x, y, z = xi[:3]
                    xx = 1. - x - y - z
                    df[0,0] =  (4. * x - 1.)
                    df[0,3] = -(4. * xx - 1.)
                    df[0,4] =  4. * y
                    df[0,6] =  4. * z
                    df[0,7] =  4. * (xx - x)
                    df[0,8] = -4. * y
                    df[0,9] = -4. * z * xx

                    df[1,1] =  (4. * y - 1.)
                    df[1,3] = -(4. * xx - 1.)
                    df[1,4] =  4. * x
                    df[1,5] =  4. * z
                    df[1,7] = -4. * x
                    df[1,8] =  4. * (xx - y)
                    df[1,9] = -4. * z

                    df[2,2] =  (4. * z - 1.)
                    df[2,3] = -(4. * xx - 1.)
                    df[2,5] =  4. * y
                    df[2,6] =  4. * x
                    df[2,7] = -4. * x
                    df[2,8] = -4. * y
                    df[2,9] =  4. * (xx - z)
                    return df

            # Linear hex
            elif num_el_node == 8:
                def evalg(xi):
                    df[:,:] = 0.
                    x, y, z = xi[:3]
                    df[0,0] = -(1. - y) * (1. - z) / 8.
                    df[0,1] =  (1. - y) * (1. - z) / 8.
                    df[0,2] =  (1. + y) * (1. - z) / 8.
                    df[0,3] = -(1. + y) * (1. - z) / 8.
                    df[0,4] = -(1. - y) * (1. + z) / 8.
                    df[0,5] =  (1. - y) * (1. + z) / 8.
                    df[0,6] =  (1. + y) * (1. + z) / 8.
                    df[0,7] = -(1. + y) * (1. + z) / 8.

                    df[1,0] = -(1. - x) * (1. - z) / 8.
                    df[1,1] = -(1. + x) * (1. - z) / 8.
                    df[1,2] =  (1. + x) * (1. - z) / 8.
                    df[1,3] =  (1. - x) * (1. - z) / 8.
                    df[1,4] = -(1. - x) * (1. + z) / 8.
                    df[1,5] = -(1. + x) * (1. + z) / 8.
                    df[1,6] =  (1. + x) * (1. + z) / 8.
                    df[1,7] =  (1. - x) * (1. + z) / 8.

                    df[2,0] = -(1. - x) * (1. - y) / 8.
                    df[2,1] = -(1. + x) * (1. - y) / 8.
                    df[2,2] = -(1. + x) * (1. + y) / 8.
                    df[2,3] = -(1. - x) * (1. + y) / 8.
                    df[2,4] =  (1. - x) * (1. - y) / 8.
                    df[2,5] =  (1. + x) * (1. - y) / 8.
                    df[2,6] =  (1. + x) * (1. + y) / 8.
                    df[2,7] =  (1. - x) * (1. + y) / 8.
                    return df

            # Quadratic tet
            elif num_el_node == 20:
                def evalg(xi):
                    df[:,:] = 0.
                    x, y, z = xi[:3]
                    df[0, 0] =  (-(1.-y)*(1.-z)*(-x-y-z-2.)-(1.-x)*(1.-y)*(1.-z))/8.
                    df[0, 1] =  ((1.-y)*(1.-z)*(x-y-z-2.)+(1.+x)*(1.-y)*(1.-z))/8.
                    df[0, 2] =  ((1.+y)*(1.-z)*(x+y-z-2.)+(1.+x)*(1.+y)*(1.-z))/8.
                    df[0, 3] =  (-(1.+y)*(1.-z)*(-x+y-z-2.)-(1.-x)*(1.+y)*(1.-z))/8.
                    df[0, 4] =  (-(1.-y)*(1.+z)*(-x-y+z-2.)-(1.-x)*(1.-y)*(1.+z))/8.
                    df[0, 5] =  ((1.-y)*(1.+z)*(x-y+z-2.)+(1.+x)*(1.-y)*(1.+z))/8.
                    df[0, 6] =  ((1.+y)*(1.+z)*(x+y+z-2.)+(1.+x)*(1.+y)*(1.+z))/8.
                    df[0, 7] =  (-(1.+y)*(1.+z)*(-x+y+z-2.)-(1.-x)*(1.+y)*(1.+z))/8.
                    df[0, 8] = -2.*x*(1.-y)*(1.-z)/4.
                    df[0, 9] =  (1.-y**2)*(1.-z)/4.
                    df[0,10] = -2.*x*(1.+y)*(1.-z)/4.
                    df[0,11] = -(1.-y**2)*(1.-z)/4.
                    df[0,12] = -2.*x*(1.-y)*(1.+z)/4.
                    df[0,13] =  (1.-y**2)*(1.+z)/4.
                    df[0,14] = -2.*x*(1.+y)*(1.+z)/4.
                    df[0,15] = -(1.-y**2)*(1.+z)/4.
                    df[0,16] = -(1.-y)*(1.-z**2)/4.
                    df[0,17] =  (1.-y)*(1.-z**2)/4.
                    df[0,18] =  (1.+y)*(1.-z**2)/4.
                    df[0,19] = -(1.+y)*(1.-z**2)/4.

                    df[1, 0] =  (-(1.-x)*(1.-z)*(-x-y-z-2.)-(1.-x)*(1.-y)*(1.-z))/8.
                    df[1, 1] =  (-(1.+x)*(1.-z)*(x-y-z-2.)-(1.+x)*(1.-y)*(1.-z))/8.
                    df[1, 2] =  ((1.+x)*(1.-z)*(x+y-z-2.)+(1.+x)*(1.+y)*(1.-z))/8.
                    df[1, 3] =  ((1.-x)*(1.-z)*(-x+y-z-2.)+(1.-x)*(1.+y)*(1.-z))/8.
                    df[1, 4] =  (-(1.-x)*(1.+z)*(-x-y+z-2.)-(1.-x)*(1.-y)*(1.+z))/8.
                    df[1, 5] =  (-(1.+x)*(1.+z)*(x-y+z-2.)-(1.+x)*(1.-y)*(1.+z))/8.
                    df[1, 6] =  ((1.+x)*(1.+z)*(x+y+z-2.)+(1.+x)*(1.+y)*(1.+z))/8.
                    df[1, 7] =  ((1.-x)*(1.+z)*(-x+y+z-2.)+(1.-x)*(1.+y)*(1.+z))/8.
                    df[1, 8] = -(1.-x**2)*(1.-z)/4.
                    df[1, 9] = -2.*y*(1.+x)*(1.-z)/4.
                    df[1,10] =  (1.-x**2)*(1.-z)/4.
                    df[1,11] = -2.*y*(1.-x)*(1.-z)/4.
                    df[1,12] = -(1.-x**2)*(1.+z)/4.
                    df[1,13] = -2.*y*(1.+x)*(1.+z)/4.
                    df[1,14] =  (1.-x**2)*(1.+z)/4.
                    df[1,15] = -2.*y*(1.-x)*(1.+z)/4.
                    df[1,16] = -(1.-x)*(1.-z**2)/4.
                    df[1,17] = -(1.+x)*(1.-z**2)/4.
                    df[1,18] =  (1.+x)*(1.-z**2)/4.
                    df[1,19] =  (1.-x)*(1.-z**2)/4.

                    df[2, 0] =  (-(1.-x)*(1.-y)*(-x-y-z-2.)-(1.-x)*(1.-y)*(1.-z))/8.
                    df[2, 1] =  (-(1.+x)*(1.-y)*(x-y-z-2.)-(1.+x)*(1.-y)*(1.-z))/8.
                    df[2, 2] =  (-(1.+x)*(1.+y)*(x+y-z-2.)-(1.+x)*(1.+y)*(1.-z))/8.
                    df[2, 3] =  (-(1.-x)*(1.+y)*(-x+y-z-2.)-(1.-x)*(1.+y)*(1.-z))/8.
                    df[2, 4] =  ((1.-x)*(1.-y)*(-x-y+z-2.)+(1.-x)*(1.-y)*(1.+z))/8.
                    df[2, 5] =  ((1.+x)*(1.-y)*(x-y+z-2.)+(1.+x)*(1.-y)*(1.+z))/8.
                    df[2, 6] =  ((1.+x)*(1.+y)*(x+y+z-2.)+(1.+x)*(1.+y)*(1.+z))/8.
                    df[2, 7] =  ((1.-x)*(1.+y)*(-x+y+z-2.)+(1.-x)*(1.+y)*(1.+z))/8.
                    df[2, 8] = -(1.-x**2)*(1.-y)/4.
                    df[2, 9] = -(1.-y**2)*(1.+x)/4.
                    df[2,10] = -(1.-x**2)*(1.+y)/4.
                    df[2,11] = -(1.-y**2)*(1.-x)/4.
                    df[2,12] =  (1.-x**2)*(1.-y)/4.
                    df[2,13] =  (1.-y**2)*(1.+x)/4.
                    df[2,14] =  (1.-x**2)*(1.+y)/4.
                    df[2,15] =  (1.-y**2)*(1.-x)/4.
                    df[2,16] = -z*(1.-x)*(1.-y)/2.
                    df[2,17] = -z*(1.+x)*(1.-y)/2.
                    df[2,18] = -z*(1.+x)*(1.+y)/2.
                    df[2,19] = -z*(1.-x)*(1.+y)/2.
                    return df

        return evalg

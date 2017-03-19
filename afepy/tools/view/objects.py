#!/usr/bin/env python
# -*- coding: utf-8
# vim: set fileencoding=utf-8

""" http://labs.freehackers.org/wiki/pythonmeshviewer

    Playing with math,mesh and python. You can use :

    Key binding:
        'escape' or 'q' to quit
        'c' to toggle colorization
        'left click' to change the position of the object
        'space' to toggle interactive mode

    In interactive mode:
        page up/down for zoom
        arrows for translations
        f1-f6 for rotation
"""

from math import pi, cos, sin
from modeling import *

def GetDodecahedron():
    """Created a dodecahedron, see http://en.wikipedia.org/wiki/Dodecahedron"""
    o = Object()
    o.name = "Dodecahedron"
    # golden ratio (1+sqrt(5))/2
    gr = 1.61803398874989484820
    # inverse golden ratio
    igr = 1./gr
    o.points.append( Point3D( 1, 1, 1)) #0
    o.points.append( Point3D( 1, 1,-1))
    o.points.append( Point3D( 1,-1, 1))
    o.points.append( Point3D( 1,-1,-1))
    o.points.append( Point3D(-1, 1, 1))
    o.points.append( Point3D(-1, 1,-1))
    o.points.append( Point3D(-1,-1, 1))
    o.points.append( Point3D(-1,-1,-1)) #7
 
    o.points.append( Point3D(0, gr, igr)) #8
    o.points.append( Point3D(0, gr,-igr))
    o.points.append( Point3D(0,-gr, igr))
    o.points.append( Point3D(0,-gr,-igr)) #11

    o.points.append( Point3D( gr, igr, 0)) #12
    o.points.append( Point3D( gr,-igr, 0))
    o.points.append( Point3D(-gr, igr, 0))
    o.points.append( Point3D(-gr,-igr, 0)) #15

    o.points.append( Point3D( igr, 0, gr)) #16
    o.points.append( Point3D( igr, 0,-gr))
    o.points.append( Point3D(-igr, 0, gr))
    o.points.append( Point3D(-igr, 0,-gr)) #19

    constructDodecahedronFace(o, 0,8,4,18,16)
    constructDodecahedronFace(o, 0,16,2,13,12)
    constructDodecahedronFace(o, 0,12,1,9,8)
    constructDodecahedronFace(o, 12,13,3,17,1)
    constructDodecahedronFace(o, 1,17,19,5,9)
    constructDodecahedronFace(o, 8,9,5,14,4)
    constructDodecahedronFace(o, 4,14,15,6,18)
    constructDodecahedronFace(o, 16,18,6,10,2)
    constructDodecahedronFace(o, 2,10,11,3,13)
    constructDodecahedronFace(o, 3,11,7,19,17)
    constructDodecahedronFace(o, 19,7,15,14,5)
    constructDodecahedronFace(o, 7,11,10,6,15)
    o.canonicalView()
    return o

def constructDodecahedronFace(o,a,b,c,d,e):
    """Construct a Dodecahedron face using triangles, given the object and 6
    points references IN THE RIGHT ORDER"""
    mp = o.points[a]+ o.points[b]+ o.points[c]+ o.points[d]+ o.points[e] # middle mpoint
    mp.scale(1./5.)
    o.points.append(mp)
    myidx = len(o.points)-1
    o.faces.append( Face([a,b,myidx]))
    o.faces.append( Face([b,c,myidx]))
    o.faces.append( Face([c,d,myidx]))
    o.faces.append( Face([d,e,myidx]))
    o.faces.append( Face([e,a,myidx]))

def GetIcosahedron():
    """Construct an icosahedron, see http://en.wikipedia.org/wiki/Icosahedron"""
    o = Object()
    o.name = "Icosahedron"
    # golden ratio (1+sqrt(5))/2
    gr = 1.61803398874989484820
    o.points.append( Point3D( 0, 1, gr)) #0
    o.points.append( Point3D( 0, 1,-gr))
    o.points.append( Point3D( 0,-1, gr))
    o.points.append( Point3D( 0,-1,-gr))

    o.points.append( Point3D( 1, gr, 0)) #4
    o.points.append( Point3D( 1,-gr, 0))
    o.points.append( Point3D(-1, gr, 0))
    o.points.append( Point3D(-1,-gr, 0))

    o.points.append( Point3D( gr, 0, 1)) #8
    o.points.append( Point3D(-gr, 0, 1))
    o.points.append( Point3D( gr, 0,-1))
    o.points.append( Point3D(-gr, 0,-1))

    o.faces.append( Face([0,2,8]))
    o.faces.append( Face([0,8,4]))
    o.faces.append( Face([0,4,6]))
    o.faces.append( Face([0,6,9]))
    o.faces.append( Face([0,9,2]))

    o.faces.append( Face([3,5,7]))
    o.faces.append( Face([3,7,11]))
    o.faces.append( Face([3,11,1]))
    o.faces.append( Face([3,1,10]))
    o.faces.append( Face([3,10,5]))

    o.faces.append( Face([7,5,2]))
    o.faces.append( Face([5,10,8]))
    o.faces.append( Face([10,1,4]))
    o.faces.append( Face([1,11,6]))
    o.faces.append( Face([11,7,9]))

    o.faces.append( Face([5,8,2]))
    o.faces.append( Face([10,4,8]))
    o.faces.append( Face([1,6,4]))
    o.faces.append( Face([11,9,6]))
    o.faces.append( Face([7,2,9]))

    o.canonicalView()
    return o

def GetTruncatedIcosahedron():
    """Construct a http://en.wikipedia.org/wiki/Truncated_icosahedron"""
    o = Object()
    o.name = "Truncated Icosahedron"
    # golden ratio (1+sqrt(5))/2
    gr = 1.61803398874989484820

    # orthogonal rectangles
    # (0,±1,±3φ), (±1,±3φ,0), (±3φ,0,±1) a
    o.points.append( Point3D(0, 1, 3*gr)) # 0
    o.points.append( Point3D(0,-1, 3*gr))
    o.points.append( Point3D(0, 1,-3*gr))
    o.points.append( Point3D(0,-1,-3*gr))

    o.points.append( Point3D( 1, 3*gr,0)) # 4
    o.points.append( Point3D( 1,-3*gr,0))
    o.points.append( Point3D(-1, 3*gr,0))
    o.points.append( Point3D(-1,-3*gr,0))

    o.points.append( Point3D( 3*gr, 0, 1)) # 8
    o.points.append( Point3D(-3*gr, 0, 1))
    o.points.append( Point3D( 3*gr, 0,-1))
    o.points.append( Point3D(-3*gr, 0,-1))

    # orthogonal cuboids
    # (±2,±(1+2φ),±φ), (±(1+2φ),±φ,±2), (±φ,±2,±(1+2φ))
    o.points.append( Point3D( 2, (1+2*gr), gr)) # 12
    o.points.append( Point3D(-2, (1+2*gr), gr))
    o.points.append( Point3D( 2,-(1+2*gr), gr))
    o.points.append( Point3D(-2,-(1+2*gr), gr))
    o.points.append( Point3D( 2, (1+2*gr),-gr))
    o.points.append( Point3D(-2, (1+2*gr),-gr))
    o.points.append( Point3D( 2,-(1+2*gr),-gr))
    o.points.append( Point3D(-2,-(1+2*gr),-gr))

    o.points.append( Point3D( (1+2*gr), gr, 2)) # 20
    o.points.append( Point3D(-(1+2*gr), gr, 2))
    o.points.append( Point3D( (1+2*gr),-gr, 2))
    o.points.append( Point3D(-(1+2*gr),-gr, 2))
    o.points.append( Point3D( (1+2*gr), gr,-2))
    o.points.append( Point3D(-(1+2*gr), gr,-2))
    o.points.append( Point3D( (1+2*gr),-gr,-2))
    o.points.append( Point3D(-(1+2*gr),-gr,-2))

    o.points.append( Point3D( gr, 2, (1+2*gr))) # 28
    o.points.append( Point3D(-gr, 2, (1+2*gr)))
    o.points.append( Point3D( gr,-2, (1+2*gr)))
    o.points.append( Point3D(-gr,-2, (1+2*gr)))
    o.points.append( Point3D( gr, 2,-(1+2*gr)))
    o.points.append( Point3D(-gr, 2,-(1+2*gr)))
    o.points.append( Point3D( gr,-2,-(1+2*gr)))
    o.points.append( Point3D(-gr,-2,-(1+2*gr)))

    # other orthogonal cuboids
    #(±1,±(2+φ),±2φ), (±(2+φ),±2φ,±1), (±2φ,±1,±(2+φ)), 
    o.points.append( Point3D( 1, (2+gr), 2*gr)) # 36
    o.points.append( Point3D( 1,-(2+gr), 2*gr))
    o.points.append( Point3D(-1, (2+gr), 2*gr))
    o.points.append( Point3D(-1,-(2+gr), 2*gr))
    o.points.append( Point3D( 1, (2+gr),-2*gr))
    o.points.append( Point3D( 1,-(2+gr),-2*gr))
    o.points.append( Point3D(-1, (2+gr),-2*gr))
    o.points.append( Point3D(-1,-(2+gr),-2*gr))

    o.points.append( Point3D( (2+gr), 2*gr, 1)) # 44
    o.points.append( Point3D( (2+gr),-2*gr, 1))
    o.points.append( Point3D(-(2+gr), 2*gr, 1))
    o.points.append( Point3D(-(2+gr),-2*gr, 1))
    o.points.append( Point3D( (2+gr), 2*gr,-1))
    o.points.append( Point3D( (2+gr),-2*gr,-1))
    o.points.append( Point3D(-(2+gr), 2*gr,-1))
    o.points.append( Point3D(-(2+gr),-2*gr,-1))

    o.points.append( Point3D( 2*gr, 1, (2+gr))) # 52
    o.points.append( Point3D( 2*gr,-1, (2+gr)))
    o.points.append( Point3D(-2*gr, 1, (2+gr)))
    o.points.append( Point3D(-2*gr,-1, (2+gr)))
    o.points.append( Point3D( 2*gr, 1,-(2+gr)))
    o.points.append( Point3D( 2*gr,-1,-(2+gr)))
    o.points.append( Point3D(-2*gr, 1,-(2+gr)))
    o.points.append( Point3D(-2*gr,-1,-(2+gr))) # 60

    assert(len(o.points)==60)
    # use this to get list of adjacents, this tremendously helps
    # finding indices to construct faces
    #for idx in range(60): print idx, findAdjacent(idx, o.points)

    o.faces.append( Face([1,30,37,39,31]))
    o.faces.append( Face([0,1,31,55,54,29]))
    o.faces.append( Face([0,28,52,53,30,1]))
    o.faces.append( Face([30,53,22,45,14,37]))
    o.faces.append( Face([37,14,5,7,15,39]))
    o.faces.append( Face([31,39,15,47,23,55]))
    o.faces.append( Face([21,54,55,23,9]))
    o.faces.append( Face([13,38,29,54,21,46]))
    o.faces.append( Face([38,36,28,0,29]))
    o.faces.append( Face([12,44,20,52,28,36]))
    o.faces.append( Face([20,8,22,53,52]))
    o.faces.append( Face([22,8,10,26,49,45]))
    o.faces.append( Face([45,49,18,5,14]))
    o.faces.append( Face([5,18,41,43,19,7]))
    o.faces.append( Face([7,19,51,47,15]))
    o.faces.append( Face([47,51,27,11,9,23]))
    o.faces.append( Face([51,19,43,35,59,27]))
    o.faces.append( Face([27,59,58,25,11]))
    o.faces.append( Face([11,25,50,46,21,9]))
    o.faces.append( Face([50,17,6,13,46]))
    o.faces.append( Face([4,12,36,38,13,6]))
    o.faces.append( Face([4,16,48,44,12]))
    o.faces.append( Face([8,20,44,48,24,10]))
    o.faces.append( Face([10,24,56,57,26]))
    o.faces.append( Face([18,49,26,57,34,41]))
    o.faces.append( Face([3,35,43,41,34]))
    o.faces.append( Face([2,33,58,59,35,3]))
    o.faces.append( Face([17,50,25,58,33,42]))
    o.faces.append( Face([4,6,17,42,40,16]))
    o.faces.append( Face([16,40,32,56,24,48]))
    o.faces.append( Face([2,3,34,57,56,32]))
    o.faces.append( Face([2,32,40,42,33]))

    o.canonicalView()
    return o


def findAdjacent(pointidx, points):
    adj = []
    point = points[pointidx]
    for idx in range(len(points)):
        if idx==pointidx:continue
        if (points[idx]-point).norm()<=2.001:
            adj.append(idx)
    return adj

def GetTetrahedron():
    """Construct a tetrahedron"""
    o = Object()
    o.name = "Tetrahedron"

    o.points.append( Point3D( 1, 1, 1))
    o.points.append( Point3D(-1,-1, 1))
    o.points.append( Point3D(-1, 1,-1))
    o.points.append( Point3D( 1,-1,-1))

    o.faces.append( Face([0,2,1]))
    o.faces.append( Face([0,3,2]))
    o.faces.append( Face([0,1,3]))
    o.faces.append( Face([1,2,3]))
    o.canonicalView()
#    print "after", "\n\t".join([str(p) for p in o.points])
    return o

def GetOctahedron():
    """Construct a tetrahedron"""
    o = Object()
    o.name = "Tetrahedron"

    o.points.append( Point3D( 1, 0, 0))
    o.points.append( Point3D( 0, 1, 0))
    o.points.append( Point3D( 0, 0, 1))
    o.points.append( Point3D(-1, 0, 0))
    o.points.append( Point3D( 0,-1, 0))
    o.points.append( Point3D( 0, 0,-1))

    o.faces.append( Face([2,0,1]))
    o.faces.append( Face([2,1,3]))
    o.faces.append( Face([2,3,4]))
    o.faces.append( Face([2,4,0]))
    o.faces.append( Face([0,5,1]))
    o.faces.append( Face([1,5,3]))
    o.faces.append( Face([3,5,4]))
    o.faces.append( Face([4,5,0]))
    o.canonicalView()
#    print "after", "\n\t".join([str(p) for p in o.points])
    return o

def GetCube():
    """Construct a cube centered on (0,0,0) with edges of size 2.
    This cube is only made of triangles.
    """
    o = Object()
    o.name = "Cube"
    o.points.append( Point3D(-1,-1,-1))
    o.points.append( Point3D(-1,-1, 1))
    o.points.append( Point3D(-1, 1,-1))
    o.points.append( Point3D(-1, 1, 1))
    o.points.append( Point3D( 1,-1,-1))
    o.points.append( Point3D( 1,-1, 1))
    o.points.append( Point3D( 1, 1,-1))
    o.points.append( Point3D( 1, 1, 1))
    o.faces.append( Face([0,1,2]))
    o.faces.append( Face([3,2,1]))
    o.faces.append( Face([7,2,3]))
    o.faces.append( Face([7,6,2]))
    o.faces.append( Face([5,4,7]))
    o.faces.append( Face([7,4,6]))
    o.faces.append( Face([5,1,4]))
    o.faces.append( Face([1,0,4]))
    o.faces.append( Face([1,5,3]))
    o.faces.append( Face([7,3,5]))
    o.faces.append( Face([6,2,4]))
    o.faces.append( Face([0,2,4]))
    o.canonicalView()
    return o
def GetCubeQuad():
    """Construct a cube centered on (0,0,0) with edges of size 2.
    This cube is made using 6 square faces, hence only using the "Quad"
    type of face, no triangles."""
    o = Object()
    o.name = "Cube"
    o.points.append( Point3D(-1,-1,-1))
    o.points.append( Point3D(-1,-1, 1))
    o.points.append( Point3D(-1, 1,-1))
    o.points.append( Point3D(-1, 1, 1))
    o.points.append( Point3D( 1,-1,-1))
    o.points.append( Point3D( 1,-1, 1))
    o.points.append( Point3D( 1, 1,-1))
    o.points.append( Point3D( 1, 1, 1))
    o.faces.append( Face([0,1,3,2]))
    o.faces.append( Face([7,3,1,5]))
    o.faces.append( Face([6,2,3,7]))
    o.faces.append( Face([4,6,2,0]))
    o.faces.append( Face([5,4,0,1]))
    o.faces.append( Face([5,4,6,7]))
    o.canonicalView()
    return o


# geodes-like stuff
# http://en.wikipedia.org/wiki/Geodesic_dome
def GetGeode(power=1, o=GetIcosahedron()):
    """return a Geode made starting from the polyhedron given as first
    argument, where each edge has been splitted 2^power times. The created
    points have been placed on the sphere."""
    for i in range(power):
        o = Geodise(o)
    o.name = "Geode(splits : 2^%d=%d)" % (power,2**power)
    return o

def Geodise(o):
    """
    Split each triangle by creating a new point in the middle of each edge
    and such creating 4 new triangles.
    """
    newo = Object()
    newo.points = o.points
    newpoints = {}

    # checks
    radius = o.points[0].norm()
    assert(radius>0)
    for p in o.points:
        assert( (p.norm()-radius)/radius < 1E-5)

    def testCreatePoint(p,q):
        """ return the index of the new point between points p & q, creates
        it if it doesn't exist already and cache it in dict newpoints"""
        # should be this, but the one used is enough :-) if newpoints.has_key((p,q)) or newpoints.has_key((q,p)):
        if newpoints.has_key((q,p)):
            return newpoints[(q,p)]
        r = newo.points[p] + newo.points[q]
        r.scale(radius/r.norm())
        newo.points.append(r)
        index = len(newo.points)-1
        newpoints[(p,q)] = index
        return index

    for t in o.faces:
        assert(len(t.refs)==3)
        a = t.refs[0]
        b = t.refs[1]
        c = t.refs[2]
        x = testCreatePoint(a,b)
        y = testCreatePoint(b,c)
        z = testCreatePoint(c,a)
        newo.faces.append( Face([a,x,z]))
        newo.faces.append( Face([x,b,y]))
        newo.faces.append( Face([x,y,z]))
        newo.faces.append( Face([z,y,c]))
    # even more checks
    for p in newo.points:
#        print p.norm(), radius-p.norm()
        assert( (p.norm()-radius)/radius < 1E-5)
    return newo

def sphere_point(i,j,N,M):
    teta=pi*i/N
    phi=2*pi*j/M
    c=cos(pi/2-teta)
    return Point3D( cos(phi)*c, sin(phi)*c, sin(pi/2-teta))
def GetSphere(N=10, M=10):
    """Create a sphere by creating triangles along longitude/latidue.
    The first arguement N is the number of (non-trivial = different from
    poles) latitudes, and the second argument M is the number of
    longitudes.
    """
    o = Object()
    o.points= [ Point3D(0,0,1) ]
    # north pole
    o.points.append(sphere_point(1,0,N,M))
    for j in range(1,M):
        o.points.append(sphere_point(1,j,N,M))
        o.faces.append(Face([0,j+1,j]))
    o.faces.append(Face([0,1,M]))
    # middle
    for i in range(2,N):
        o.points.append(sphere_point(i,0,N,M))
        for j in range(1,M):
            o.points.append(sphere_point(i,j,N,M))
            l = len(o.points)
            o.faces.append(Face([l-2-M,l-1-M,l-1]))
            o.faces.append(Face([l-2-M,l-1,l-2]))
        l = len(o.points)
        o.faces.append(Face([l-1-M,l-M-M,l-M]))
        o.faces.append(Face([l-1-M,l-M,l-1]))
    # south pole
    o.points.append(Point3D(0,0,-1))
    southpole = len(o.points)-1
    o.points.append(sphere_point(N-1,0,N,M))
    for j in range(1,M):
        o.points.append(sphere_point(N-1,j,N,M))
        o.faces.append(Face([southpole,southpole+j,southpole+1+j]))
    o.faces.append(Face([southpole,southpole+M,southpole+1]))
    o.canonicalView()
    return o
def torus_point(i,j,N,M,r,R):
    teta,phi=2*pi*i/N, 2*pi*j/M
    ct,st = cos(teta), sin(teta)
    myr = R+r*cos(phi)
    return Point3D( myr*ct, myr*st, r*sin(phi))
def GetTorus(N=20, M=20,r=.3,R=.6):
    """Create a Torus, see http://en.wikipedia.org/wiki/Torus"""
    # first circle
    o = Object()
    o.name = "torus"
    for j in range(0,M):
        o.points.append(torus_point(0,j,N,M,r,R))
    c = M-1 # index of last point
    # main loop
    for i in range(1,N):
        o.points.append(torus_point(i,0,N,M,r,R))
        c+=1
        for j in range(1,M):
            o.points.append(torus_point(i,j,N,M,r,R))
            c+=1
            o.faces.append(Face([c,c-1,c-M]))
            o.faces.append(Face([c-M-1,c-M,c-1]))
    # last circle
    for j in range(1,M):
        o.faces.append(Face([c,c-1,c-M]))
        o.faces.append(Face([c-M-1,c-M,c-1]))
    o.canonicalView()
    return o


#
# random stuff
#
def RandomTetra():
    t = GetTetrahedron()
    t.random_place()
    return t
def LotTetra():
    object = Object()
    for i in range(10):
        object += RandomTetra()
    return object

# vim: ai ts=4 sts=4 et sw=4

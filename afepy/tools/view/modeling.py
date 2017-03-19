#!/usr/bin/env python
# -*- coding: utf-8
# vim: set fileencoding=utf-8

from random import random
from math import pi, sqrt, cos, sin
from PyQt4 import QtGui
import numpy as np

COLORIZE_NONE = 0
COLORIZE_BW = 1
COLORIZE_COLOR = 2
COLORIZE_MODULO = 3

class Point3D:
    """Provide an elementary 3D point with associated methods for
    creation and transformation"""
    def __init__(self,a=0,b=0,c=0):
        self.x,self.y,self.z=a,b,c
    def norm(self):
        return sqrt( self.x*self.x+ self.y*self.y+ self.z*self.z)
    def __str__(self):
        return "Point3D(%f,%f,%f)" % ( self.x,self.y,self.z)
    def __neg__(self):
        return Point3D( -self.x, -self.y, -self.z)
    def __add__(self,other):
        return  Point3D( self.x+other.x, self.y+other.y, self.z+other.z)
    def __sub__(self,other):
        return  Point3D( self.x-other.x, self.y-other.y, self.z-other.z)
    def scale(self,v):
        self.x*=v; self.y*=v; self.z*=v
    def rotateX(self,angle):
        c,s=cos(angle),sin(angle)
        self.y,self.z = self.y*c-self.z*s, self.y*s+self.z*c
    def rotateY(self,angle):
        c,s=cos(angle),sin(angle)
        self.x,self.z = self.x*c-self.z*s, self.x*s+self.z*c
    def rotateZ(self,angle):
        c,s=cos(angle),sin(angle)
        self.x,self.y = self.x*c-self.y*s, self.x*s+self.y*c
    def rotate(self,teta,phi):
        self.rotateY(phi)
        self.rotateZ(teta)
    def normalize(self):
        self.scale(1/self.norm())

def printPolygon(p):
    print "Polygon with %d points" % p.count()
    for i in range(p.count()):
        print p.at(i).x(), p.at(i).y()

class Face:
    """A Face is a list of (at least three) references to vertices all
    belonging to the same plane"""
    def __init__(self, refs):
        "we do not actually check for coplanarity"
        assert(len(refs)>=3)
        self.refs = refs
    def shift(self,t):
#TODO        print "before", self.refs
        self.refs = [r+t for r in self.refs]
#        print "after", self.refs
    def dist(self,points):
        # mean distance
        dists = map(lambda r: points[r].z, self.refs)
        return sum(dists)/len(dists)
    def getPolygon(self, points):
        l = len(self.refs)
        polygon = QtGui.QPolygon(l)
        for i in range(l):
            polygon.setPoint(i, points[self.refs[i]].x, points[self.refs[i]].y)
        return polygon
    def lum_coeff(self,points,light_vector):
        """return the luminosity coefficient for this triangle, given the light_vector
        This is a float between 0 and 2.
        The light_vector is supposed normalized
        We only consider the first three points for this.
        """
        a,b,c= points[self.refs[0]], points[self.refs[1]], points[self.refs[2]]
        v1 = Point3D ( b.x-a.x, b.y-a.y, b.z-a.z)
        v2 = Point3D ( c.x-a.x, c.y-a.y, c.z-a.z)
        v = Point3D( v1.y*v2.z-v2.y*v1.z,v1.z*v2.x-v2.z*v1.x,v1.x*v2.y-v2.x*v1.y ) # vector product
        sp = (v.x*light_vector.x+v.y*light_vector.y+v.z*light_vector.z)/v.norm() # <v,light> / ||v||
        return sp+1

class Object:
    """An object is a collection of points (object:Point) and faces.
    The faces are made of indices referencing the points
    array.
    An object can be read from a file, or created by code.

    Objects can be merged using the method __add__. Exemple
    merged_object = object1 + object2

    Once created, an object can be transformed and displayed.
    """
    def __init__(self,filename=""):
        if filename=="":
            self.name="unknown"
            self.points,self.faces=[], []
        else:
            self.name="Read from "+filename
            self.read_file(filename)
    def __str__(self): return "Object %s : %d points, %d faces" % (self.name,len(self.points),len(self.faces))
    def scale(self,v):
        for p3d in self.points: p3d.scale(v)
    def translate(self,v):
        for i in range(len(self.points)): self.points[i]+=v
    def rotateX(self,angle):
        for p3d in self.points: p3d.rotateX(angle)
    def rotateY(self,angle):
        for p3d in self.points: p3d.rotateY(angle)
    def rotateZ(self,angle):
        for p3d in self.points: p3d.rotateZ(angle)
    def rotate(self,teta,phi):
        for p3d in self.points: p3d.rotate(teta,phi)
    def getMinMaxDiam(self):
        VERYMUCH = 1E30
        m,M = Point3D(VERYMUCH,VERYMUCH,VERYMUCH), Point3D(-VERYMUCH,-VERYMUCH,-VERYMUCH)
        for p3d in self.points:
            if (p3d.x<m.x):m.x = p3d.x
            if (p3d.y<m.y):m.y = p3d.y
            if (p3d.z<m.z):m.z = p3d.z
            if (p3d.x>M.x):M.x = p3d.x
            if (p3d.y>M.y):M.y = p3d.y
            if (p3d.z>M.z):M.z = p3d.z
        diam = M.x-m.x
        diam+= M.y-m.y
        diam+= M.z-m.z
        diam /= 3
        return m,M,diam
    def getCenter(self):
        m,M,d = self.getMinMaxDiam()
        m+=M
        m.scale(.5)
        return m
    def canonicalView(self):
        m,M,d = self.getMinMaxDiam()
        m+=M
        m.scale(.5) # m is the center
        self.translate(-m)
        self.scale(3000/d)
        return m
    def center(self):
        self.translate(-self.getCenter())
    def __add__(self,other):
        "Concatenate this object and 'other', returns it "
        ret = Object()
        ret.points = self.points + other.points
        l=len(self.points)
        # shift faces
        ret.faces = other.faces
        for f in ret.faces:
            f.shift(l)
        # remaining faces
        ret.faces += self.faces
        return ret
    def sort_faces(self):
        "Sort faces according to their distance from the camera, that is the z coordinate from points3d"
        self.faces.sort(key= lambda t : t.dist(self.points)) # compare the distance
    def render(self, painter, params):
        "compute the projections and display the whole object"
        self.sort_faces()
        for face in self.faces:
            polygon = face.getPolygon(self.points)
            if params.colorize==COLORIZE_COLOR:
                # computes colors for both lights
                lc1 = int(64*face.lum_coeff(self.points,params.light_vector_1))
                lc2 = int(64*face.lum_coeff(self.points,params.light_vector_2))
                # use a combination of both (two lights with != colors)
                painter.setBrush(QtGui.QBrush(QtGui.QColor(lc1*2, lc1+lc2, lc2)))
            painter.drawPolygon(polygon)

    def random_place(self):
        self.scale(random()+0.3)
        p = Point3D(random()*2-1, random()*2-1, random()*2-1)
        self.translate(p)
        self.rotate(random()*pi, random()*2*pi)

    def read_file(self, filename):
        from mesh.readers import read_file
        mesh = read_file(filename)

        if mesh.num_dim == 2:
            points = np.column_stack((mesh.coords, np.zeros(mesh.coords.shape[0])))
        else:
            points = np.array(mesh.coords)

        self.points = [Point3D(x[0], x[1], x[2]) for x in points]

        # create faces from element blocks
        self.faces=[]
        for elem_nodes in mesh.connect:
            elem_nodes = [x-1 for x in elem_nodes if x > 0]
            self.faces.append(Face(elem_nodes))

        self.rotate(pi/3,pi/4)
        self.canonicalView()

    def readFile(self,filename):
        self.points,self.faces=[], []
        print "Creating object from", filename
        f=open(filename, 'r')
        # read vertices
        line = ""
        while line != "Vertices":
            line = f.readline().strip()
        nbPoint = int(f.readline().strip())
        for i in range(nbPoint):
            line = f.readline().split()
            self.points.append(Point3D( float(line[0]), float(line[1]), float(line[2])))
        line = ""
        while line == "":
            line = f.readline().strip()
        # read faces
        if line=="Triangles":
            nbTriangles = int(f.readline().strip())
            for i in range(nbTriangles):
                line = f.readline().split()
                self.faces.append( Face([int(line[0])-1, int(line[1])-1, int(line[2])-1]))
        elif line=="Quadrilaterals":
            nbQuad = int(f.readline().strip())
            for i in range(nbQuad):
                line = f.readline().split()
                print [int(line[0])-1, int(line[1])-1, int(line[2])-1, int(line[3])-1]
                self.faces.append(Face([int(line[0])-1, int(line[1])-1, int(line[2])-1, int(line[3])-1]))
        print "readFile done : ", self
        self.rotate(pi/3,pi/4)
        self.canonicalView()

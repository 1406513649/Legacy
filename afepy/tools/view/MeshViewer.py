#!/usr/bin/env python
# -*- coding: utf-8
# vim: set fileencoding=utf-8

""" http://labs.freehackers.org/wiki/pythonmeshviewer

    Playing with math,mesh and python. You can use :

    Key binding:
        'escape' or 'q' to quit
        'c' to select colorization mode
        'left click' to change the position of the object
        'space' to toggle interactive mode

    In interactive mode:
        page up/down for zoom
        arrows for translations
        f1-f6 for rotation
"""

from random import random
from math import pi, sin
from PyQt4 import QtGui, QtCore
from mainwindow import Ui_MainWindow
from objects import *

#
# Graphical Interface (based on Qt)
#
class View(QtGui.QFrame):
    def __init__(self, object):
        QtGui.QFrame.__init__(self)
        self.zoom_factor = 0.12
        self.object = object
        self.light_vector_1 = Point3D (random(),random(),random())
        self.light_vector_1.normalize()
        self.light_vector_2 = Point3D (random(),random(),random())
        self.light_vector_2.normalize()
        self.colorize = COLORIZE_COLOR
        self.draw_edges = True

        # animation stuff:
        self.timer = QtCore.QTimer()
        QtCore.QObject.connect( self.timer, QtCore.SIGNAL('timeout()'), self.timerTimeout)
        self.teta_speed = (random()+0.3)*0.1 #      0.03<|*_speed|<0.13
        if (random()>0.5):self.teta_speed = - self.teta_speed
        self.phi_speed = (random()+0.3)*0.1
        if (random()>0.5):self.phi_speed = - self.phi_speed
        self.zoom_speed = (random()+0.3)*0.05
        self.zoom_time = 0

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.translate(self.width()/2, self.height()/2)
        painter.scale(self.zoom_factor, self.zoom_factor)
        if self.colorize==COLORIZE_BW:
            painter.setBrush(QtGui.QBrush(QtGui.QColor(255,255,255)))
        if self.draw_edges:
            painter.setPen(QtCore.Qt.black)
        else:
            painter.setPen(QtCore.Qt.transparent)
        self.object.render(painter, self)

    def timerTimeout(self):
        #print "timer out"
        self.object.rotate(self.teta_speed,self.phi_speed)
        self.zoom_time+=self.zoom_speed
        self.zoom_factor = 0.12 + sin(self.zoom_time)*.06
        # always rotate lights
        if self.colorize==COLORIZE_COLOR:
            self.light_vector_1.rotate(-0.005,-0.08)
            self.light_vector_2.rotate(+0.07,-0.003)
        # actual display
        self.repaint()

    def startAnimation(self):
        self.timer.start(150)
    def stopAnimation(self):
        self.timer.stop()

    def toggleColorization(self):
        self.colorize += 1
        self.colorize %= COLORIZE_MODULO
        if not self.timer.isActive(): self.repaint()
    def toggleEdges(self, newvalue):
        self.draw_edges = newvalue
        if not self.timer.isActive(): self.repaint()
    def toggleInteractive(self,newvalue):
        if self.timer.isActive():
            assert(newvalue)
            self.stopAnimation()
        else:
            assert(not newvalue)
            self.startAnimation()
    def zoomIn(self):
        if self.timer.isActive(): return # only available in interactive mode
        self.zoom_factor *= 1.1
        self.repaint()
    def zoomOut(self):
        if self.timer.isActive(): return # only available in interactive mode
        self.zoom_factor /= 1.1
        self.repaint()

    def translateLeft(self):
        if self.timer.isActive(): return # only available in interactive mode
        self.object.translate(Point3D(-100,0,0))
        self.repaint()
    def translateRight(self):
        if self.timer.isActive(): return # only available in interactive mode
        self.object.translate(Point3D(+100,0,0))
        self.repaint()
    def translateUp(self):
        if self.timer.isActive(): return # only available in interactive mode
        self.object.translate(Point3D(0,-100,0))
        self.repaint()
    def translateDown(self):
        if self.timer.isActive(): return # only available in interactive mode
        self.object.translate(Point3D(0,+100,0))
        self.repaint()

    def rotateX1(self):
        if self.timer.isActive(): return # only available in interactive mode
        self.object.rotateX(pi/20)
        self.repaint()
    def rotateX2(self):
        if self.timer.isActive(): return # only available in interactive mode
        self.object.rotateX(-pi/20)
        self.repaint()
    def rotateY1(self):
        if self.timer.isActive(): return # only available in interactive mode
        self.object.rotateY(pi/20)
        self.repaint()
    def rotateY2(self):
        if self.timer.isActive(): return # only available in interactive mode
        self.object.rotateY(-pi/20)
        self.repaint()
    def rotateZ1(self):
        if self.timer.isActive(): return # only available in interactive mode
        self.object.rotateZ(pi/20)
        self.repaint()
    def rotateZ2(self):
        if self.timer.isActive(): return # only available in interactive mode
        self.object.rotateZ(-pi/20)
        self.repaint()
        
class MainWindow(QtGui.QMainWindow):
    def __init__(self, object):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.setMinimumWidth(800)
        self.setMinimumHeight(650)

        self.view = View(object)
        self.setCentralWidget(self.view)
        self.ui.actionDisplay_edges.setChecked(True)

        # connect actions
        self.connect(self.ui.action_Quit, QtCore.SIGNAL("triggered()"), self.close)
        self.connect(self.ui.action_About, QtCore.SIGNAL("triggered()"), self.about)
        self.connect(self.ui.action_Sphere, QtCore.SIGNAL("triggered()"), self.loadSphere)
        self.connect(self.ui.actionFrom_Icosahedron_2, QtCore.SIGNAL("triggered()"), self.loadGeodeIcosahedron_2)
        self.connect(self.ui.actionFrom_Icosahedron_4, QtCore.SIGNAL("triggered()"), self.loadGeodeIcosahedron_4)
        self.connect(self.ui.actionFrom_Tetrahedron_2, QtCore.SIGNAL("triggered()"), self.loadGeodeTetrahedron_2)
        self.connect(self.ui.actionFrom_Tetrahedron_4, QtCore.SIGNAL("triggered()"), self.loadGeodeTetrahedron_4)
        self.connect(self.ui.actionFrom_Octahedron_2, QtCore.SIGNAL("triggered()"), self.loadGeodeOctahedron_2)
        self.connect(self.ui.actionFrom_Octahedron_4, QtCore.SIGNAL("triggered()"), self.loadGeodeOctahedron_4)
        self.connect(self.ui.action_Icosahedron, QtCore.SIGNAL("triggered()"), self.loadIcosahedron)
        self.connect(self.ui.action_Dodecahedron, QtCore.SIGNAL("triggered()"), self.loadDodecahedron)
        self.connect(self.ui.action_Tetrahedron, QtCore.SIGNAL("triggered()"), self.loadTetrahedron)
        self.connect(self.ui.action_Octahedron, QtCore.SIGNAL("triggered()"), self.loadOctahedron)
        self.connect(self.ui.action_Cube, QtCore.SIGNAL("triggered()"), self.loadCube)
        self.connect(self.ui.action_CubeQuad, QtCore.SIGNAL("triggered()"), self.loadCubeQuad)
        self.connect(self.ui.action_Lot_of_Tetras, QtCore.SIGNAL("triggered()"), self.loadTetras)
        self.connect(self.ui.action_Torus, QtCore.SIGNAL("triggered()"), self.loadTorus)
        self.connect(self.ui.action_Torus2, QtCore.SIGNAL("triggered()"), self.loadTorus2)
        self.connect(self.ui.actionTruncated_Icosahedron, QtCore.SIGNAL("triggered()"), self.loadTruncated_Icosahedron)
        self.connect(self.ui.actionDisplay_edges, QtCore.SIGNAL("toggled(bool)"), self.view.toggleEdges)
        self.connect(self.ui.action_Color_mode, QtCore.SIGNAL("triggered()"), self.view.toggleColorization)

        self.connect(self.ui.actionInteractive, QtCore.SIGNAL("toggled(bool)"), self.view.toggleInteractive)
        self.connect(self.ui.actionZoom_In, QtCore.SIGNAL("triggered()"), self.view.zoomIn)
        self.connect(self.ui.actionZoom_Out, QtCore.SIGNAL("triggered()"), self.view.zoomOut)

        self.statusBar().showMessage(self.tr("Ready"))
        self.createShortCuts()

        self.show()

    def about(self):
        QtGui.QMessageBox.about(self, self.tr("About MeshViewer"),
            self.tr("<b>MeshViewer</b> is an academic tool demonstrating how to "
            "display 3D meshes"
            "<br/>"
            "<br/>"
            "Copyright (c) 2008,2010 Thomas Capricelli"
            "<br/>"
            '<a href="http://labs.freehackers.org/projects/pythonmeshviewer/wiki">http://labs.freehackers.org/projects/pythonmeshviewer/wiki</a>'
            "<br/>"
            "<br/>"
            '<a href="http://labs.freehackers.org/projects/pythonmeshviewer/issues">Report a bug or a wish</a>'
            "<br/>"
            "Quick Help:<br/>"
            "Key binding:"
            "<ul>"
            "    <li>'escape' or 'q' to quit"
            "    <li>'c' to toggle colorization"
            "    <li>'e' to toggle edges rendering"
            "    <li>'left click' to change the position of the object"
            "    <li>'space' to toggle interactive mode"
            "</ul>"
            "In interactive mode:"
            "<ul>"
            "    <li>page up/down for zoom"
            "    <li>arrows for translations"
            "    <li>f1-f6 for rotation"
            "</ul>"
            ))

    def createShortCuts(self):
        s = QtGui.QShortcut("q", self, self.close)
        s = QtGui.QShortcut(QtCore.Qt.Key_Escape, self, self.close)

        # translations
        s = QtGui.QShortcut(QtCore.Qt.Key_Left, self.view, self.view.translateLeft)
        s = QtGui.QShortcut(QtCore.Qt.Key_Right, self.view, self.view.translateRight)
        s = QtGui.QShortcut(QtCore.Qt.Key_Up, self.view, self.view.translateUp)
        s = QtGui.QShortcut(QtCore.Qt.Key_Down, self.view, self.view.translateDown)

        # rotations
        s = QtGui.QShortcut(QtCore.Qt.Key_F1, self.view, self.view.rotateX1)
        s = QtGui.QShortcut(QtCore.Qt.Key_F2, self.view, self.view.rotateX2)
        s = QtGui.QShortcut(QtCore.Qt.Key_F3, self.view, self.view.rotateY1)
        s = QtGui.QShortcut(QtCore.Qt.Key_F4, self.view, self.view.rotateY2)
        s = QtGui.QShortcut(QtCore.Qt.Key_F5, self.view, self.view.rotateZ1)
        s = QtGui.QShortcut(QtCore.Qt.Key_F6, self.view, self.view.rotateZ2)

    def loadSphere(self):
        self.view.object = GetSphere(12,30)
        self.view.repaint()
    def loadGeodeIcosahedron_2(self):
        self.view.object = GetGeode(1)
        self.view.repaint()
    def loadGeodeIcosahedron_4(self):
        self.view.object = GetGeode(2)
        self.view.repaint()
    def loadGeodeTetrahedron_2(self):
        self.view.object = GetGeode(1, GetTetrahedron())
        self.view.repaint()
    def loadGeodeTetrahedron_4(self):
        self.view.object = GetGeode(2, GetTetrahedron())
        self.view.repaint()
    def loadGeodeOctahedron_2(self):
        self.view.object = GetGeode(1, GetOctahedron())
        self.view.repaint()
    def loadGeodeOctahedron_4(self):
        self.view.object = GetGeode(2, GetOctahedron())
        self.view.repaint()
    def loadIcosahedron(self):
        self.view.object = GetIcosahedron()
        self.view.repaint()
    def loadDodecahedron(self):
        self.view.object = GetDodecahedron()
        self.view.repaint()
    def loadTetrahedron(self):
        self.view.object = GetTetrahedron()
        self.view.repaint()
    def loadOctahedron(self):
        self.view.object = GetOctahedron()
        self.view.repaint()
    def loadCube(self):
        self.view.object = GetCube()
        self.view.repaint()
    def loadCubeQuad(self):
        self.view.object = GetCubeQuad()
        self.view.repaint()
    def loadTetras(self):
        self.view.object = LotTetra()
        self.view.repaint()
    def loadTorus(self):
        self.view.object = GetTorus()
        self.view.repaint()
    def loadTorus2(self):
        self.view.object = GetTorus(R=0.6,r=0.59)
        self.view.repaint()
    def loadTruncated_Icosahedron(self):
        self.view.object = GetTruncatedIcosahedron()
        self.view.repaint()

def main():
    from sys import argv, exit
    from random import seed
    #initialize system
    seed()

    # handle args
    nbarg = len(argv)
    if nbarg>2:
        print "Usage %s [ filename ]" % argv[0]
        exit(1)

    if nbarg==2:
        object = Object(argv[1])
    else:
        object = GetTorus()

    # Qt init
    app = QtGui.QApplication(argv)

    mainWin = MainWindow(object)
    mainWin.show()
    mainWin.view.startAnimation()

    return app.exec_()

# if python says run, then we should run
if __name__ == '__main__':
    from sys import exit
    exit(main())

# vim: ai ts=4 sts=4 et sw=4

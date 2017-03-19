#!/usr/bin/env python
"""
Convert output of time/deformation rate table to time/strain table
"""

import sys
import optparse
import os
import subprocess
import numpy
import math
try:
    import matplotlib
    import matplotlib.pyplot as plot
    can_plot = True
except:
    print 'Warning: matplotlib not found, will not make plots\n'
    can_plot = False

def main(argc,argv):
    # *************************************************************************
    # -- command line option parsing
    global inp_basename
    global lt,lcoher,ldxx,ldyy,ldzz,ldxy,ldyz,ldxz,lsxx,lsyy,lszz
    global lsxy,lsyz,lsxz,lden,lsolden,lvoidf,lvolf,lpe1,lpe2,lpe3
    global la1,la2,la3,la4,li1,lrtj2
    usage = "usage: %prog [options] <file_name>"
    parser= optparse.OptionParser(usage=usage, version="%prog 1.0")

    parser.add_option('-w','--write',
                      dest='WRITE',
                      action='store_true',
                      default=False,
                      help='Write parsed output to files [default: %default]')
    parser.add_option('-p','--plot',
                      dest='PLOT',
                      action='store_true',
                      default=False,
                      help='Plot parsed output [default: %default]')

    (opts,args) = parser.parse_args(argv)

    if len(args) < 1:
        parser.print_help()
        parser.error("Must specify file_name")
    else:
        inp = os.path.realpath(args[0])
        inp_basename, inp_ext = os.path.splitext(inp)
        if inp_ext != '.his' and not os.path.isfile('%s.his'%inp_basename):
            sys.exit('ERROR: input file must be a .his file')
        pass
    his_inp = '%s.his'%inp_basename
    work_dir = os.path.split(his_inp)[0]

    # this script relies on hisread.py to read the his file, check that it is on
    # the path
    hisread = 'hisread.py'
    path = os.getenv('PATH').split(':')
    if os.path.isfile(hisread):
        hisread = os.path.realpath(hisread)
        onpath = True
        pass
    else:
        hisread_x = os.path.split(hisread)[1]
        for p in path:
            hisread = os.path.join(p,hisread_x)
            if os.path.isfile(hisread):
                onpath = True
                break
            else:
                pass
            continue
        pass

    if not onpath:
        sys.exit('ERROR: hisread.py must be on your path')
        pass

    # get properties
    props = {'peaki1i':None,'peaki1f':None,
             'streni':None,'strenf':None,
             'fslopei':None,'fslopef':None,
             'yslopei':None,'yslopef':None}

    for line in file('%s.out'%inp_basename):
        for prop in props:
            if prop.upper() in line and not props[prop]:
                props[prop] = float(line.strip().split()[1])
                pass
            continue
        continue

    # convenience
    lt = 0;  lcoher = 1;
    ldxx=2;  ldyy=3;  ldzz=4;  ldxy=5;  ldyz=6;  ldxz=7;
    lsxx=8;  lsyy=9;  lszz=10; lsxy=11; lsyz=12; lsxz=13;
    lden=14; lsolden=15; lvoidf=16; lvolf=17;
    lpe1=18; lpe2=19; lpe3=20;
    la1=21;  la2=22;  la3=23;  la4=24;
    li1=25; lrtj2=26;

    # read data
    p=1
    cmd = [hisread,'--nolabels',
           '-g','TIME',
           '-p','%i/COHER-%i'%(p,p),
           '-p','%i/DEFORMATION-R-XX'%p,
           '-p','%i/DEFORMATION-R-YY'%p,
           '-p','%i/DEFORMATION-R-ZZ'%p,
           '-p','%i/DEFORMATION-R-XY'%p,
           '-p','%i/DEFORMATION-R-YZ'%p,
           '-p','%i/DEFORMATION-R-XZ'%p,
           '-p','%i/STRESS-%i-XX'%(p,p),
           '-p','%i/STRESS-%i-YY'%(p,p),
           '-p','%i/STRESS-%i-ZZ'%(p,p),
           '-p','%i/STRESS-%i-XY'%(p,p),
           '-p','%i/STRESS-%i-YZ'%(p,p),
           '-p','%i/STRESS-%i-XZ'%(p,p),
           '-p','%i/DENSITY-%i'%(p,p),
           '-p','%i/SOLID-DENSITY-%i'%(p,p),
           '-p','%i/VOID-FRC'%p,
           '-p','%i/VOLFRC-%i'%(p,p),
           his_inp]
    with open('%s.stdout','w') as out:
        foo = subprocess.Popen(cmd,stdout=out)
        foo.wait()
    data = []
    for line in file('%s.stdout').readlines():
        data.append(map(float,line.strip().split()))
    os.remove('%s.stdout')

    # post process the data
    E = [[0.]*6]
    for i in range(1, len(data) ):
        time_n = data[i-1][lt]
        time_p = data[i][lt]
        dt = time_p - time_n

        # convert strain rates to principal strains
        x = []
        for j in range(6):
            x.append(data[i][j+ldxx]*dt + E[-1][j])
            continue
        E.append(x)
        evals = numpy.linalg.eigvalsh(numpy.array([[x[0],x[3],x[5]],
                                                   [x[3],x[1],x[4]],
                                                   [x[5],x[4],x[2]]]))
        for eig in evals:
            data[i].append(eig)
            continue

        # get a1-a4, compute I1, RootJ2
        coher = data[i][lcoher]
        peaki1 = props['peaki1i']*coher + props['peaki1f']*(1. - coher)
        stren = props['streni']*coher + props['strenf']*(1. - coher)
        fslope = props['fslopei']*coher + props['fslopef']*(1. - coher)
        yslope = props['yslopei']*coher + props['yslopef']*(1. - coher)
        a1,a2,a3,a4 = oldFromNew(stren,peaki1,fslope,yslope)
        i1 = data[i][lsxx] + data[i][lsyy] + data[i][lszz]
        i2 = data[i][lsxx]*data[i][lsyy] \
           + data[i][lsyy]*data[i][lszz] \
           + data[i][lsxx]*data[i][lszz] \
           - data[i][lsxy]**2 - data[i][lsyz]**2 - data[i][lsxz]**2
        rtj2 = math.sqrt(1./3.*i1**2 - i2)
        for item in [a1,a2,a3,a4,i1,rtj2]:
            data[i].append(item)
            continue
        continue
    data_a = numpy.array(data[1:])

    if opts.WRITE:
        writeParsedData(data_a)
        pass

    if can_plot and opts.PLOT:
        plotParsedData(data_a)
        pass

    elif not can_plot and opts.PLOT:
        print 'WARNING: can\'t load matplotlib, no plots created\n'

def plotParsedData(data):

    ls_kmm = {'lw':1.0,'c':'orange'}
    ls_yld = {'lw':1.0,'c':'green'}

    # plot rtj2 vs i1
    # create yield surface
    i1 = data[:,li1].copy()
    i1.sort()
    one = numpy.ones(len(i1))
    l = int(len(data)/1)
    for i in range(0,len(data),l):
        gamma = 1.0
        a1 = data[i,la1]
        a2 = data[i,la2]
        a3 = data[i,la3]
        a4 = data[i,la4]
        rtj2 = (a1*one - a3*numpy.exp(a2*i1) - a4*i1)/gamma**2
        plot.plot(-i1,rtj2,label='Yield surface %s'%str(i),lw=ls_yld['lw'],c=ls_yld['c'])
        continue

    plot.figure(1)
    plot.title(r'$\sqrt{J_2}$ vs $I_1$')
    plot.xlabel(r'$I_1$ (MPa)')
    plot.ylabel(r'$\sqrt{J_2}$ (MPa)')
    x,y = -data[:,li1], data[:,lrtj2]
    plot.plot(x,y,label='Kayenta response',lw=ls_kmm['lw'],c=ls_kmm['c'])
    plot.ylim((0,1.1*max(rtj2)))
    plot.legend(loc=4)
    plot.savefig(os.path.join(os.getcwd(),'%s_rtj2_vs_i1.pdf'%inp_basename))
    plot.close()

    plot.figure(2)
    plot.title(r'principal strains vs time')
    plot.xlabel(r'time (s)')
    plot.ylabel(r'$\epsilon_{i}$')
    t = data[:,lt]
    e1 = data[:,lpe1]
    e2 = data[:,lpe2]
    e3 = data[:,lpe3]
    plot.plot(t,e1,label='$\epsilon_{1}$',lw=ls_kmm['lw'],c='blue')
    plot.plot(t,e2,label='$\epsilon_{2}$',lw=ls_kmm['lw'],c='red')
    plot.plot(t,e3,label='$\epsilon_{3}$',lw=ls_kmm['lw'],c='green')
    plot.legend(loc=2)
    plot.savefig(os.path.join(os.getcwd(),'%s_prinstrain_vs_time.pdf'%inp_basename))
    plot.close()

    plot.figure(3)
    plot.title(r'volume fraction, void fraction vs time')
    plot.xlabel(r'time (s)')
    plot.ylabel(r'void/volume fraction')
    t,voidf,volf = data[:,lt],data[:,lvoidf],2.*data[:,lvolf]
    plot.plot(t,voidf,label='void fraction',lw=ls_kmm['lw'],c='blue')
    plot.plot(t,volf,label='volume fraction',lw=ls_kmm['lw'],c='green')
    plot.legend(loc=2)
    plot.savefig(os.path.join(os.getcwd(),'%s_volfrac_vs_voidfrac.pdf'%inp_basename))
    plot.close()

    plot.figure(3)
    plot.title(r'density/solid density vs time')
    plot.xlabel(r'time (s)')
    plot.ylabel(r'density/solid density')
    t,dens,sdens = data[:,lt],2.*data[:,lden],2.*data[:,lsolden]
    plot.plot(t,dens,label='density',lw=ls_kmm['lw'],c='blue')
    plot.plot(t,sdens,label='solid density',lw=ls_kmm['lw'],c='green')
    plot.legend(loc=2)
    plot.savefig(os.path.join(os.getcwd(),'%s_density_vs_solid_density.pdf'
                              %inp_basename))
    plot.show()
    plot.close()
    return 0
def writeParsedData(data):
    '''
       write selected output to file
    '''
    out_f = '%s.prdef.out'%inp_basename
    out = open(out_f,'w')
    for row in data:
        out.write('%s %e %s %e %s %e %s %e\n'%('time = ',row[lt],
                                               'e11 = ',row[le1],
                                               'e22 = ',row[le2],
                                               'e33 = ',row[le3]))
        continue
    out.close()
    print 'Principal strains written to %s'%os.path.split(out_f)[1]

    out_f = '%s.stresspath.out'%inp_basename
    out = open(out_f,'w')
    out.write( '#   time           a1          a2           a3           a4'
               '           i1          rtj2\n')
    for row in data:
        out.write('%e %e %e %e %e %e %e\n'%(row[lt],row[la1],row[la2],row[la3],
                                            row[la4],row[li1],row[lrtj2]))
        continue
    out.close()
    print('Yield surface parameters and stress path written to %s'
          %os.path.split(out_f)[1])

    return 0

def oldFromNew(stren,peaki1,fslope,yslope):
    '''
       convert new yield surface parameters to old
    '''

    if stren == 0.:
        a1 = 0.
        a2 = 0.
        a3 = 0.
        a4 = 0.
        if fslope != 0.:
            sys.exit('fslope must be zero if stren=0')
            pass
        if yslope != 0.:
            sys.exit('yslope must be zero if stren=0')
            pass
        pass
    else:
        a1 = stren+peaki1*yslope
        a2 = (fslope-yslope)/stren
        a3 = stren*math.exp(-peaki1*(fslope-yslope)/stren)
        a4 = yslope
        pass

    dum = max(stren,peaki1)
    tiny = 1.e-10
    if a1 < tiny*dum: a1 = 0.
    if a3 < tiny*dum: a3 = 0.
    if yslope > fslope:
         sys.exit('yslope needs to be smaller than fslope')
         pass
    if fslope-yslope < tiny: a2 = 0.

    if fslope == 0. and yslope == 0. and peaki1 > 1.e50:
        a1= stren
        a2= 0.
        a3= 0.
        a4= 0.
        pass

    return a1,a2,a3,a4

if __name__ == '__main__':
    try:
        main(len(sys.argv[1:]),sys.argv[1:])
    except KeyboardInterrupt:
        sys.stderr.write('\n')
        pass







import os
import re
import sys
import logging
import numpy as np
from itertools import cycle

import pandas
from scipy.optimize import fmin, curve_fit, least_squares
from scipy import stats
import matplotlib.pyplot as plt
try: 
    import bokeh.plotting as bp
except ImportError: 
    bp = None

__all__ = ['MasterCurve', 'CurveFitter', 'mc_init_notebook',
           'to_minutes', 'cnvtime',
           'MODIFIED_POWER', 'POWER', 'PRONY', 'POLYNOMIAL',
           'MODIFIED_POWER_1']

MODIFIED_POWER = 'MODIFIED POWER'
MODIFIED_POWER_1 = 'MODIFIED POWER 1'
POWER = 'POWER'
PRONY = 'PRONY'
POLYNOMIAL = 'POLYNOMIAL'

PHONY = 123456.789
EPS = np.finfo(float).eps
BASE = 10.

TIME_UNITS = ('seconds','hours','days','weeks','months','years','hertz')

def is_time_unit(x):
    return x[:3].lower() in [xt[:3] for x in TIME_UNITS]

class Environment:
    pass
environ = Environment()
environ.notebook = 0

def _loadcsv(filename):
    """Load the csv file written out by MasterCurve.dump"""
    class CSVData:
        data = {}
        def get(self, temp):
            return self.data[temp]
        def __iter__(self):
            return iter(self.data.items())
    dtype = np.float64
    array = np.array
    cstack = np.column_stack

    assert os.path.isfile(filename)
    lines = open(filename).readlines()

    for (i, line) in enumerate(lines):
        if re.search('Version', line):
            version = float(lines[i+1])
            assert version > 1.
        if re.search('Curve Fitter', line):
            fitter = lines[i+1]
        if re.search('Fit Error', line):
            fiterr = float(lines[i+1])
        if re.search('WLF', line):
            wlf_coeffs = [float(x) for x in lines[i+1].split(',')]
            assert len(wlf_coeffs) == 2

        if re.search('Data', line):
            j = i + 1

        if re.search('Master Curve', line):
            k = i + 1

    d = CSVData()

    desc = lines[j].split(',')
    temps = array([float(x) for x in desc[2:]])
    data = array([[None if not x.split() else float(x) for x in y.split(',')]
                  for y in lines[j+1:k-1]])
    d.master = array([[float(x) for x in y.split(',')] for y in lines[k+1:]])

    d.toat = data[:,0]
    d.logtoat = data[:,1]

    d.raw_master = cstack((d.toat, d.logtoat, array(data[:,2], dtype=dtype)))
    d.ref_temp = temps[0]

    d.temps = temps[1:]
    for (i, temp) in enumerate(temps[1:]):
        td = data[:,i+3]
        idx = [j for (j,x) in enumerate(td) if x is not None]
        a = array(td[idx], dtype=dtype)
        if len(a) == 0:
            continue
        a = cstack((d.toat[idx], d.logtoat[idx], a))
        d.data[temp] = a

    return d


def _no_trans(x):
    return x


def curve_fit2(func, x, y, p0, sigma, trans_y=None, nw=None):

    # Fit the data
    def func2(p, *args):
        xp, yp, wp, yfun = args
        return wp * (yfun(yp) - func(xp, *p))

    x, y = np.asarray(x), np.asarray(y)
    if nw:
        weights = np.ones_like(y)
    elif sigma is not None:
        sigma = np.asarray(sigma)
        weights = 1. / (sigma)
    else:
        weights = np.ones_like(y)

    yfun = _no_trans if trans_y is None else trans_y
    res = least_squares(func2, p0, args=(x, y, weights, yfun))
    if not res.success:
        raise RuntimeError(res.message)

    if sigma is None:
        return res.x, None, None

    ys = func(x, *res.x)
    w1 = np.ones_like(y)
    try:
        ys_p = np.where(ys+sigma>y+sigma, ys+sigma, y+sigma)
        res_p = least_squares(func2, res.x, args=(x, ys_p, w1, yfun))
    except ValueError:
        raise
        res_p = least_squares(func2, res.x, args=(x, y+sigma, w1, yfun))

    try:
        ys_m = np.where(ys-sigma<y-sigma, ys-sigma, y-sigma)
        res_m = least_squares(func2, res.x, args=(x, ys_m, w1, yfun))
    except ValueError:
        res_m = least_squares(func2, res.x, args=(x, y-sigma, w1, yfun))

    return res.x, res_p.x, res_m.x


def log(x, base=BASE):
    e = 2.718281828459045
    if abs(base - 10.) < EPS:
        return np.log10(x)
    elif abs(base - 2.) < EPS:
        return np.log2(x)
    elif abs(base - e) < EPS:
        return np.log(x)
    else:
        return np.log(x) / np.log(BASE)

def interp1d(xy, x, findx=False, clip=False):
    """Wrapper around numpy's interp

    """
    xp = xy[:, 0]
    yp = xy[:, 1]
    if findx:
        xp, yp = yp, xp
    xd = np.diff(xp)
    if np.allclose(-1, np.sign(np.diff(xp))):
        # descending curve, reverse it
        xp, yp = xp[::-1], yp[::-1]
    if not clip:
        return np.interp(x, xp, yp)

    yval = np.interp(x, xp, yp, left=PHONY, right=PHONY)
    if abs(yval - PHONY) < 1.e-12:
        return None
    return yval

def islist(a):
    return isinstance(a, (list, tuple, np.ndarray))

def multidim(a):
    try:
        if islist(a) and islist(a[0]):
            return True
    except IndexError:
        return False

def joinn(l, sep=',', num=False, end='\n', ffmt='.6f'):
    if num:
        realfmt = lambda r: '{0:{1}}'.format(float(r), ffmt)
        l = [realfmt(x) if x is not None else '' for x in l]
    if not multidim(l):
        line = sep.join(l)
    else:
        line = '\n'.join(sep.join(s) for s in l)
    return line + end

def bounding_box(curve):
    """Determine the box that bounds curve

    Parameters
    ----------
    curve : ndarray
        curve[i, 0] is the x coordinate of the ith data point
        curve[i, 1] is the y coordinate of the ith data point

    Returns
    -------
    box : ndarray
        box[0, i] is xm[in,ax]
        box[1, i] is ym[in,ax]

    """
    if curve[0, 1] > curve[-1, 1]:
        # y values are decreasing from left to right
        xmin, ymin = curve[-1, 0], curve[-1, 1]
        xmax, ymax = curve[0, 0], curve[0, 1]
    else:
        xmin, ymin = curve[0, 0], curve[0, 1]
        xmax, ymax = curve[-1, 0], curve[-1, 1]
    return np.array([[xmin, ymin], [xmax, ymax]])

def area(x, y, yaxis=False):
    if not yaxis:
        return np.trapz(y, x)
    return np.trapz(x, y)

COLORS = ['Blue', 'Red', 'Purple', 'Green', 'Orange', 'HotPink', 'Cyan',
          'Magenta', 'Chocolate', 'Yellow', 'Black', 'DodgerBlue', 'DarkRed',
          'DarkViolet', 'DarkGreen', 'OrangeRed', 'Teal', 'DarkSlateGray',
          'RoyalBlue', 'Crimson', 'SeaGreen', 'Plum', 'DarkGoldenRod',
          'MidnightBlue', 'DarkOliveGreen', 'DarkMagenta', 'DarkOrchid',
          'DarkTurquoise', 'Lime', 'Turquoise', 'DarkCyan', 'Maroon']

def gen_colors(keys):
    colors = {}
    c = cycle(COLORS)
    for key in keys:
        colors[key] = next(c).lower()
    return colors

def aslist(item):
    if item is None:
        return []
    if not isinstance(item, (list, tuple, np.ndarray)):
        item = [skip_temps]
    return [x for x in item]

class MasterCurve(object):
    fiterr = None
    def __init__(self, txy, ref_temp=75., apply_log=False, xfac=1., yfac=1.,
                 skip_temps=None, wlf_coeffs=None,
                 xvar='Time', xunits='min', yvar='Er', yunits='psi',
                 fitter=PRONY, optcoeffs=True,
                 cnvtime=False, **kwargs):
        """Initialize the master curve object

        Parameters
        ----------
        txy : array_like (n, 3)
            txy[i] is the ith [Temp, X, Y]
        ref_temp : real
            Reference temperature
        optcoeffs : bool [True]
            Optimize the WLF parameters
        fitter : str [prony]
            Name of CurveFitter
        skip_temps : list [None]
            Temperatures to skip
        wlf_coeffs : list [None]
            Initial guesses for C1 and C2

        kwargs : dict
            keywords [optional] to pass to fitter

        """
        columns = ('Temp', 'X', 'Log[X]', 'Y')
        txy = np.asarray(txy)

        stdv = None
        if txy.shape[1] == 4:
            stdv = txy[:,3]
            txy = txy[:,:3]

        txy[:, 2] *= yfac
        if apply_log:
            txy[:, 1] *= xfac
            logx = log(txy[:, 1])
            txy = np.insert(txy, 2, logx, axis=1)
        else:
            x = (BASE ** txy[:, 1]) * xfac
            txy = np.insert(txy, 1, x, axis=1)

        xunits = xunits.lower()
        if xunits[:3] != 'min':
            txy[:,1] = to_minutes(txy[:,1], xunits[:3])
            txy[:,2] = log(txy[:,1])
            xunits = 'min'

        if stdv is not None:
            txy = np.column_stack((txy, stdv))
            columns += ('STDV',)

        self.ref_temp = ref_temp
        self.skip_temps = aslist(skip_temps)
        self.df = pandas.DataFrame(txy, columns=columns)

        self.rate = '/min' in xunits
        self.wlf_coeffs = wlf_coeffs
        self.optcoeffs = optcoeffs
        self.kwds = dict(**kwargs)
        cf = CurveFitter(fitter)
        self._cf = {0: cf(rate=self.rate, **kwargs)}

        self.xvar = xvar
        self.yvar = yvar
        self.xunits = xunits
        self.yunits = yunits

        self.temp_array = txy[:,0]
        self.x_array = txy[:,1]
        self.logx_array = txy[:,2]
        self.y_array = txy[:,3]
        self.stdv_array = None if txy.shape !=4 else txy[:,4]

        self._fit = 0

    @property
    def cf(self):
        return self._cf.get(1, self._cf[0])

    @cf.setter
    def cf(self, item):
        if item is not None:
            self._cf[1] = item

    def fit(self, wlf_coeffs=None, skip_temps=None, ref_temp=None,
            optimize_wlf=None, fitter=None, discrete_shift=None, p0=None,
            no_weight=None, **kwargs):

        skip_temps = aslist(skip_temps)
        skip_temps.extend(self.skip_temps)

        if fitter is not None:
            fitter = CurveFitter(fitter)(rate=self.rate, **kwargs)
        self.cf = fitter

        # make skip temps a list, if not already
        df = self.df.copy()
        for temp in skip_temps:
            df = df[~(np.abs(df['Temp'] - temp) < EPS)]

        ref_temp = self.ref_temp if ref_temp is None else ref_temp
        wlf_coeffs = self.wlf_coeffs if wlf_coeffs is None else wlf_coeffs

        if not any(np.abs(df['Temp'] - ref_temp) < EPS):
            raise ValueError('Reference temperature {0} not '
                             'found in data'.format(ref_temp))

        wlf_opt = None
        if discrete_shift is None:
            wlf_opt = self.find_wlf_coeffs(df, ref_temp, wlf_coeffs,
                    optimize_coeffs=optimize_wlf, no_weight=no_weight)
        else:
            if not isinstance(discrete_shift, dict):
                discrete_shift = None
            discrete_shift = self.find_discrete_wlf_shift(df, ref_temp,
                    discrete_shift, optimize_coeffs=optimize_wlf,
                    no_weight=no_weight)
        self.dfm = self.shift_data(df, ref_temp, wlf=wlf_opt,
                shift=discrete_shift)
        the_fit = self.fit_shifted_data(self.dfm, p0=p0, no_weight=no_weight)
        self.mc_fit, self.mc_std_p, self.mc_std_m = the_fit
        self.wlf_opt = wlf_opt
        self.discrete_shift = discrete_shift
        self._fit = 1

    def find_discrete_wlf_shift(self, df, ref_temp, shift,
            optimize_coeffs=None, no_weight=None):
        """Generate the optimized master curve"""

        temps = np.unique(df['Temp'])
        if len(temps) == 1:
            # only one data set
            return {temps[0], 0}

        if shift is None:
            # Shift each data set.  xs is [T, logaT]
            dg = df.groupby('Temp')
            rc = dg.get_group(ref_temp)
            shift = dict([(g, self.x_shift(rc, df1)) for (g, df1) in dg])

        if optimize_coeffs is None:
            optimize_coeffs = self.optcoeffs

        if not optimize_coeffs:
            return shift

        def func(xopt, *args):
            """Objective function returning the area between the fitted curve
            and shifted data

            """
            #if np.any(xopt < 0.):
            #    self.fiterr = 1000.
            #    return self.fiterr
            shift = dict(zip(args[0], xopt))
            df1 = self.shift_data(df.copy(), ref_temp, shift=shift)
            fit = self.fit_shifted_data(df1, no_weight=no_weight)

            # determine error between fitted curve and master curve
            xvals, yvals = [], []
            for logx in df1['Log[X/aT]']:
                xvals.append(BASE**logx)
                yvals.append(self.cf.eval(logx, fit[0]))
            yvals = np.asarray(yvals)
            e1 = np.sqrt(np.mean((yvals - df1['Y']) ** 2))
            e1 /= abs(np.mean(df1['Y']))

            error = abs(e1)

            self.fiterr = error # / area(data[:,0],data[:,1])
            return self.fiterr

        temps = sorted(shift.keys())
        x = [shift[temp] for temp in temps]
        xopt = fmin(func, x, disp=0, args=(temps,))

        return dict(zip(temps, xopt))

    def find_wlf_coeffs(self, df, ref_temp, wlf_coeffs, optimize_coeffs=None,
            no_weight=None):
        """Generate the optimized master curve"""

        temps = np.unique(df['Temp'])
        if len(temps) == 1:
            # only one data set
            return np.zeros(2)

        if wlf_coeffs is None:
            wlf_coeffs = self.get_wlf_coeffs(df, ref_temp)

        if optimize_coeffs is None:
            optimize_coeffs = self.optcoeffs

        if not optimize_coeffs:
            return wlf_coeffs

        def func(xopt, *args):
            """Objective function returning the area between the fitted curve
            and shifted data

            """
            ref_temp = self.ref_temp
            if np.any(np.abs(xopt[1] + temps - ref_temp) < EPS):
                self.fiterr = 1000.
                return self.fiterr

            df1 = self.shift_data(df.copy(), ref_temp, xopt)
            try:
                fit = self.fit_shifted_data(df1, no_weight=no_weight)
            except:
                return 100

            # determine error between fitted curve and master curve
            xvals, yvals = [], []
            for logx in df1['Log[X/aT]']:
                xvals.append(BASE**logx)
                yvals.append(self.cf.eval(logx, fit[0]))
            yvals = np.asarray(yvals)
            e1 = np.sqrt(np.mean((yvals - df1['Y']) ** 2))
            e1 /= abs(np.mean(df1['Y']))

            temp = np.unique(self.df['Temp'])
            log_at = -xopt[0] * (temp - ref_temp) / (xopt[1] + temp - ref_temp)
            m, b, r, p, std_err = stats.linregress(temp, log_at)
            e2 = 1 - r ** 2

            error = np.sqrt((fac1*e1) ** 2 + (fac2*e2) ** 2)
            self.fiterr = error # / area(data[:,0],data[:,1])

            return self.fiterr

        fac1, fac2 = .5, .5
        wlf_coeffs = fmin(func, wlf_coeffs, disp=0)
        return wlf_coeffs

    def shift_data(self, df, T0, wlf=None, shift=None):
        """Compute the master curve for data series"""
        # reference temperature curve
        if shift is None:
            if wlf is None:
                raise TypeError('one of wlf or shift must be defined')
            shift = dict([(T, -wlf[0]*(T-T0)/(wlf[1]+T-T0)) 
                          for T in df['Temp']])
        def f(x):
            temp = np.asarray(x['Temp'])[0]
            fac = 1. if '/min' in self.xunits else -1.
            x['Log[X/aT]'] = np.asarray(x['Log[X]']) + fac * shift[temp]
            return x
        df = df.groupby('Temp').apply(f)
        return df

    def fit_shifted_data(self, df, p0=None, no_weight=None):
        """Fit the master curve

        """
        sigma = None if 'STDV' not in df else df['STDV']
        t = np.asarray(df['Log[X/aT]'])
        d = np.asarray(df['Y'])
        return self.cf.fit_points(t, d, sigma=sigma, p0=p0, no_weight=no_weight)

    @staticmethod
    def x_shift(df1, df2):
        """

        Parameters
        ----------
        df1 : ndarray
            Base curve to shift to consisting of list of x,y pairs
        df2 : ndarray
            Curve to shift consisting of list of x,y pairs

         Returns
         -------
         shift : real
             A scalar shift value

        Notes
        -----
        Single curves must be monotonically increasing or decreasing. Composite
        curve can be more complex and x values should generally be increasing
        (noise is okay)

        shift value returned is such that x points should be shifted by
        subtracting the shift value

        """
        ref_curve = np.asarray(df1[['Log[X]', 'Y']])
        curve = np.asarray(df2[['Log[X]', 'Y']])

        ref_bnds = bounding_box(ref_curve)
        crv_bnds = bounding_box(curve)

        if (crv_bnds[1, 1] > ref_bnds[1, 1]):
            # y values for curve larger than ref_curve, check for overlap
            if (crv_bnds[0, 1] < ref_bnds[1, 1]):
                ypt = (ref_bnds[1, 1] + crv_bnds[0, 1]) / 2.
                x_crv = interp1d(curve, ypt, findx=True)
                x_ref = interp1d(ref_curve, ypt, findx=True)
            else:
                # no overlap
                x_ref, x_crv = ref_curve[0, 0], curve[-1, 0]
        else:
            # y values for ref_curve larger than curve, check for overlap
            if (ref_bnds[0, 1] < crv_bnds[1, 1]):
                ypt = (ref_bnds[0, 1] + crv_bnds[1, 1]) / 2.
                x_crv = interp1d(curve, ypt, findx=True)
                x_ref = interp1d(ref_curve, ypt, findx=True)
            else:
                # no overlap
                x_ref, x_crv = ref_curve[-1, 0], curve[0, 0]

        return -(x_ref - x_crv)

    def get_wlf_coeffs(self, df, T0):
        """Defines the WLF shift

        Notes
        -----
        returns a tuple containing best fits for C1 and C2:

         log(aT) = -C1(T-ref_temp)/(C2+T-ref_temp)

         The coefficients are determined by the least squares fit

              x = (A^TA)^-1 A^Tb  (T is matrix transpose)

         where A is nx2 matrix (n is number of T and logaT pairs) of rows or
         [(T-Tr) logaT] for each T,logaT pair b is a nx1 vector where each row is
         -logaT*(T-Tr) for each pair x is a 2x1 vector of C1 and C2

        """
        # shift the data to the reference curve
        dg = df.groupby('Temp')
        rc = dg.get_group(T0)

        # Shift each data set.  xs is [T, logaT]
        xs = np.array([[g, self.x_shift(rc, df1)] for (g, df1) in dg])
        if all([abs(x) < 1.e-6 for x in xs[:,1]]):
            logging.warn('No shift found, consider specifying '
                         'initial WLF coefficients')

        # Setup A Matrix
        A = np.zeros((xs.shape[0], 2))
        A[:, 0] = xs[:,0] - T0
        A[:, 1] = xs[:,1]

        # Setup b Vector
        b = -A[:, 0] * A[:, 1]

        # Calculate WLF Coefficients
        ATA = np.dot(A.T, A)
        ATb = np.dot(A.T, b)
        try:
            wlf_coeffs = np.linalg.solve(ATA, ATb)
        except np.linalg.LinAlgError:
            logging.warn('Using least squares to find wlf coefficients')
            wlf_coeffs = np.linalg.lstsq(ATA, ATb)[0]

        return wlf_coeffs

    def plot_wlf(self, *args, **kwargs):
        wlf = self.wlf_opt
        temp = np.unique(self.df['Temp'])
        ref_temp = self.ref_temp
        log_at = -wlf[0] * (temp - ref_temp) / (wlf[1] + temp - ref_temp)
        x_label = 'Temperature'
        y_label = 'Log[aT]'
        if environ.notebook == 2:
            p = bp.figure(x_axis_label=x_label, y_axis_label=y_label)
            p.scatter(temp, log_at)
            bp.show(p)
        else:
            plt.xlabel(x_label)
            plt.ylabel(y_label)
            plt.scatter(temp, log_at)
            if kwargs.get('show', 1):
                plt.show()

    def plot(self, **kwargs):
        if environ.notebook == 2:
            p = self._bp_plot(**kwargs)
            bp.show(p)
            return p
        return self._mp_plot(**kwargs)

    def _bp_plot(self, raw=False, show_fit=False):
        if bp is None:
            raise ImportError('bokeh')

        if raw:
            x_label = 'Log[{0}] ({1})'.format(self.xvar, self.xunits)
        else:
            x_label = 'Log[{0}/aT] ({1})'.format(self.xvar, self.xunits)
        yvar = self.cf.yvar or self.yvar
        y_label = '{0} ({1})'.format(self.yvar, self.yunits)
        plot = bp.figure(x_axis_label=x_label, y_axis_label=y_label)
        if raw:
            plot.title = 'Raw, unshifted data'
            dg = self.df.groupby('Temp')
            colors = gen_colors([str(temp) for temp in dg.groups.keys()])
            for (temp, df) in dg:
                plot.scatter(df['Log[X]'], df['Y'], legend='{0}'.format(temp),
                             color=colors[str(temp)])
            return plot

        if not self._fit:
            self.fit()

        dg = self.dfm.groupby('Temp')
        colors = gen_colors([str(temp) for temp in dg.groups.keys()])
        plot.title = 'Data shift: {0}'.format(self.cf.name)
        for (temp, df) in dg:
            plot.scatter(df['Log[X/aT]'], df['Y'],
                         legend='{0}'.format(temp), color=colors[str(temp)])
        if show_fit:
            xp, yp = self._mc_points()
            plot.line(xp, yp, color='black', line_width=1.5,
                      legend='Master Curve Fit')
        return plot

    def _mp_plot(self, raw=False, show_fit=False, filename=None,
                 legend_loc='lower left', legend_ncol=1, wlfbox='upper right',
                 ylim=None):
        """Plot the given data or shifted data and/or the fit """
        if plt is None:
            raise ImportError('matplotlib')
        xl, xu = self.xvar, self.xunits
        yl, yu = self.yvar, self.yunits

        fig1 = plt.figure()
        ax1 = fig1.add_subplot(111)

        if raw:
            ax1.set_xlabel(r'$\log\left(%s\right)$ (%s)' % (xl, xu))
        else:
            if not self.rate:
                ax1.set_xlabel(r'$\log\left(\frac{%s}{a_T}\right)$ (%s)' % (xl, xu))
            else:
                ax1.set_xlabel(r'$\log\left(%s \cdot a_T\right)$ (%s)' % (xl, xu))
        ylabel = r'$%s$ (%s)' % (yl, yu)
        ax1.set_ylabel(ylabel)

        if raw:
            dg = self.df.groupby('Temp')
            colors = gen_colors([str(temp) for temp in dg.groups.keys()])
            for (temp, df) in dg:
                xp, yp = df['Log[X]'], df['Y']
                ax1.scatter(xp, yp, label='{0}'.format(temp),
                            color=colors[str(temp)])
                if 'STDV' in df:
                    ax1.errorbar(xp, yp, yerr=np.array(df['STDV']),
                            label=None, ecolor=colors[str(temp)], ls='None',
                            marker='None')

        else:
            if not self._fit:
                self.fit()
            dg = self.dfm.groupby('Temp')
            colors = gen_colors([str(temp) for temp in dg.groups.keys()])
            for (temp, df) in dg:
                xp, yp = df['Log[X/aT]'], df['Y']
                ax1.scatter(xp, yp,
                            label='{0}'.format(temp), color=colors[str(temp)])
                if 'STDV' in df:
                    yerr = np.array(df['STDV'])
                    ax1.errorbar(xp, yp, yerr=yerr, marker='None', ls='None',
                            label=None, ecolor=colors[str(temp)])

            if show_fit:
                plot_label = self.cf.descriptive_plot_label(self.mc_fit)
                s = '${0}$ = {1}'.format(self.yvar, plot_label)

                if 'STDV' in df:
                    xp, yp, yp1, yp2 = self._mc_points(std=1)
                else:
                    xp, yp = self._mc_points()

                ax1.plot(xp, yp, 'k-', lw=1.5, label=s)
                #ax1.text(.6, .25, s, ha='left', transform=ax1.transAxes)

                if 'STDV' in df:
                    # get upper and lower bound fits
                    ax1.plot(xp, yp1, 'k-.', lw=1., label=None)
                    ax1.plot(xp, yp2, 'k-.', lw=1., label=None)

        if legend_loc is not None:
            kwds = {'loc': legend_loc, 'ncol': legend_ncol,
                    'scatterpoints': 1, 'fontsize':14}
            if show_fit:
                kwds['fancybox'] = True
            plt.legend(**kwds)

        if ylim is not None:
            ax1.set_ylim(ylim)

        if show_fit:
            if self.wlf_opt is not None:
                # this is an inset axes over the main axes
                wlf = self.wlf_opt
                temp = np.unique(self.df['Temp'])
                ref_temp = self.ref_temp
                log_at = -wlf[0]*(temp-ref_temp)/(wlf[1]+temp-ref_temp)
                if wlfbox == 'upper right':
                    ax2 = fig1.add_axes([.575, .57, .3, .3])
                elif wlfbox == 'upper left':
                    ax2 = fig1.add_axes([.195, .57, .3, .3])
                elif wlfbox == 'lower right':
                    ax2 = fig1.add_axes([.575, .178, .3, .3])
                ax2.set_xlabel(r'Temperature $^{\rm o}$F')
                ax2.set_ylabel(r'$\log{a_T}$')
                c1 = tolatex(-wlf[0])
                c2 = tolatex(wlf[1])
                c3 = ref_temp
                ax2.scatter(temp, log_at)
                ax2.set_title('WLF Shift')
                s = r'$\log{a_T}=\frac{%s\left(T-%g\right)}{%s+T-%g}$'%(c1,c3,c2,c3)
                ax2.text(.35, .85, s, ha='left', transform=ax2.transAxes,
                        fontsize=15)
            elif self.discrete_shift is not None:
                # this is an inset axes over the main axes
                shift = self.discrete_shift
                temp = sorted(self.discrete_shift.keys())
                log_at = [self.discrete_shift[t] for t in temp]
                if wlfbox == 'upper right':
                    ax2 = fig1.add_axes([.575, .57, .3, .3])
                elif wlfbox == 'upper left':
                    ax2 = fig1.add_axes([.195, .57, .3, .3])
                ax2.set_xlabel(r'Temperature $^{\rm o}$F')
                ax2.set_ylabel(r'$\log{a_T}$')
                ax2.scatter(temp, log_at)
                ax2.set_title('Time/Temperature Shift')
                a = max([abs(x) for x in log_at])
                ax2.set_ylim((-2*a, 2*a))

        if environ.notebook:
            plt.show()
        elif filename is None:
            plt.show()
        if filename is not None:
            plt.savefig(filename, transparent=True)

        return

    def to_csv(self, filename):
        """Dump data to a file

        Parameters
        ----------
        filename : str
            file path

        Notes
        -----
        Writes to each row of filename

        """
        if not self._fit:
            self.fit()

        fh = open(filename, 'w')
        fh.write('mcgen\nVersion\n1.2\n')
        fh.write('Curve Fitter\n{0}\n'.format(self.cf.name))
        fh.write('Curve Fitting Information\n')
        # write out the fit info
        line = self.cf.dump_info(self.mc_fit, delimiter=',')
        fh.write(line)
        try:
            fh.write('Fit Error\n{0:.6f}\n'.format(self.fiterr))
        except (ValueError, TypeError):
            pass
        fh.write(joinn(['WLF C1', 'WLF C2'], sep=','))
        fh.write(joinn([self.wlf_opt[0], self.wlf_opt[1]], sep=',', num=True))

        fh.write('Data\n')
        self.dfm.to_csv(fh, float_format='%.6f', index=False)
        fh.close()

    def to_excel(self, filename):
        if not self._fit:
            self.fit()

        def cell(i, j):
            return '{0}{1}'.format(chr(j+ord('A')), i+1)

        writer = pandas.ExcelWriter(filename)
        worksheet = writer.book.create_sheet()
        worksheet.title = 'mcgen Meta'
        worksheet[cell(0, 0)] = 'mcgen Version'
        worksheet[cell(0, 1)] = '1.2'

        worksheet[cell(1, 0)] = 'Curve Fitter'
        worksheet[cell(1, 0)] = self.cf.name

        worksheet[cell(2, 0)] = 'Curve Fitting Information'
        lines = self.cf.dump_info(self.mc_fit, delimiter=',')
        for (i, line) in enumerate(lines.split('\n')):
            for (j, item) in enumerate(line.split(',')):
                worksheet[cell(3+i, j)] = '{0}'.format(item.strip())
        n = 3+i
        try:
            worksheet[cell(n, 0)] = 'Fit Error'
            worksheet[cell(n, 1)] = '{0:.6f}\n'.format(self.fiterr)
            n += 1
        except ValueError:
            pass
        worksheet[cell(n, 0)] = 'WLF C1'
        worksheet[cell(n, 1)] = 'WLF C1'
        worksheet[cell(n+1, 0)] = '{0}'.format(self.wlf_opt[0])
        worksheet[cell(n+1, 1)] = '{0}'.format(self.wlf_opt[1])

        self.dfm.to_excel(writer, sheet_name='mcgen Data', index=False)
        writer.save()
        return

    def _mc_points(self, n=50, std=0):
        xmin = np.amin(self.dfm['Log[X/aT]'])
        xmax = np.amax(self.dfm['Log[X/aT]'])
        xvals = np.linspace(xmin, xmax, n)
        yvals = np.array([self.cf.eval(x, fit=self.mc_fit) for x in xvals])
        if not std:
            return xvals, yvals
        yp = np.array([self.cf.eval(x, fit=self.mc_std_p) for x in xvals])
        ym = np.array([self.cf.eval(x, fit=self.mc_std_m) for x in xvals])
        return xvals, yvals, yp, ym

    def eval(self, time, temp, time_units='min', disp=0):

        if not self._fit:
            self.fit()

        if self.wlf_opt is not None:
            wlf = self.wlf_opt
            ref_temp = self.ref_temp
            log_at = -wlf[0]*(temp-ref_temp)/(wlf[1]+temp-ref_temp)

        elif self.discrete_shift is not None:
            shift = self.discrete_shift
            xp = sorted(self.discrete_shift.keys())
            yp = [self.discrete_shift[t] for t in xp]
            log_at = np.interp(temp, xp, yp)

        time = to_minutes(time, time_units)

        fac = 1. if '/min' in self.xunits else -1.
        x = log(time) + fac * log_at

        if 'STDV' not in self.dfm:
            disp = 0

        y = self.cf.eval(x, fit=self.mc_fit)
        if not disp:
            return y

        yp = self.cf.eval(x, fit=self.mc_std_p)
        ym = self.cf.eval(x, fit=self.mc_std_m)

        return y, max(abs(yp-y), abs(y-ym))

    @classmethod
    def Import(cls, filename, **kwargs):
        root, ext = os.path.splitext(filename)
        if ext.lower() == '.csv':
            return ReadCSV(filename, **kwargs)
        raise TypeError('Unexpected file extension {0!r}'.format(ext))

    def Export(self, filename):
        root, ext = os.path.splitext(filename)
        if ext.lower() == '.csv':
            return self.to_csv(filename)
        elif ext.lower() == '.xlsx':
            return self.to_excel(filename)
        raise TypeError('Unexpected file extension {0!r}'.format(ext))

    @property
    def abaqus_repr(self):
        if not hasattr(self.cf, 'abaqus_repr'):
            return None
        if not self._fit:
            self.fit()
        return self.cf.abaqus_repr(self.ref_temp, self.wlf_opt, 
                self.mc_fit, self.mc_std_p, mc_std_m)

    @property
    def description(self):
        if not self._fit:
            self.fit()

        s = ''
        s += 'mcgen Version 1.2\n'
        s += 'Curve Fitter: {0}\n'.format(self.cf.name)
        s += 'Curve Fitting Information\n'

        # write out the fit info
        line = self.cf.dump_info(self.mc_fit, delimiter=',')
        s += line
        try:
            s += 'Fit Error\n{0:.6f}\n'.format(self.fiterr)
        except (ValueError, TypeError):
            pass
        if self.wlf_opt is not None:
            s += joinn(['WLF C1', 'WLF C2'], sep=',')
            s += joinn([self.wlf_opt[0], self.wlf_opt[1]], sep=',', num=True)
        elif self.discrete_shift is not None:
            temps = sorted(self.discrete_shift.keys())
            log_at = [self.discrete_shift[temp] for temp in temps]
            s += joinn(temps, sep=',', num=True)
            s += joinn(log_at, sep=',', num=True)

        return s
        #fh.write('Data\n')
        #self.dfm.to_csv(fh, float_format='%.6f', index=False)

class _CurveFitter(object):
    """CurveFitter base class"""
    name = None
    key = None
    plot_label = 'Curve fit'
    yvar = None
    def fit_points(self, *args, **kwargs):
        raise NotImplementedError
    def eval(self, *args, **kwargs):
        raise NotImplementedError
    def dump_info(self, *args, **kwargs):
        raise NotImplementedError
    def descriptive_plot_label(self, *args):
        return self.plot_label

class PronyFit(_CurveFitter):
    name = 'PRONY'
    key = PRONY
    def __init__(self, *args, **kwargs):
        rate = kwargs.get('rate')
        optprony = kwargs.pop('optprony', False)
        self.ndp = kwargs.get('num_series')
        if rate:
            self.plot_label = r'$y_{\infty}+\sum_{i=1}^{n} y_i e^{\dot{\epsilon}a_T}{\tau_i}}$'
        else:
            self.plot_label = r'$y_{\infty}+\sum_{i=1}^{n} y_i e^{\frac{t/a_T}{\tau_i}}$'

    def fit_points(self, xp, yp, sigma=None, p0=None, no_weight=None):
        """Retuns the best fits for a Prony series

        Parameters
        ----------
        xp : ndarray
            x points (log(t/aT))
        yp : ndarray
            y points

        Returns
        -------
        fit : ndarray
            (tau_i, Y_i) for Prony series fit (last point is ( ,Y_inf))

        Notes
        -----
        Fits
                       ---
                       \        -(t/aT) / tau_i
            Y = Y_0 +  /   Y_i e
                       ---

        with a least squares fit.

        xp should be given in ascending order.

        """
        n = len(xp)
        mn = np.amin(xp)
        mx = np.amax(xp)

        # number of decade points
        ndp = self.ndp or int(mx - mn + 1)

        # decades
        nn = ndp + 1
        tau = np.empty(nn)
        tau[:-1] = [BASE ** (round(mn) + i) for i in range(ndp)]

        d = np.zeros((n, nn))
        d[:, -1] = 1.
        for i in range(n):
            d[i, :ndp] = np.exp(-BASE ** xp[i] / tau[:ndp])

        if no_weight:
            weights = np.eye(yp.shape[0])
        elif sigma is not None:
            weights = np.diag(1./sigma)
        else:
            weights = np.eye(yp.shape[0])

        # Initial guess at parameters
        try:
            dtdi = np.linalg.inv(np.dot(d.T, np.dot(weights, d)))
        except np.linalg.LinAlgError:
            raise ValueError('adjust initial WLF coefficients')
        ddd = np.dot(np.dot(dtdi, d.T), weights)
        p0 = np.dot(ddd, yp)

        # finish off the optimization.
        #def func(xp, *p):
        #    return np.array([self._eval(x, tau, p) for x in xp])
        #fit = curve_fit2(func, xp, yp, p0, sigma)
        #popt, self.p_std_p, self.p_std_m = fit
        #self.popt = np.column_stack((tau, popt))
        #return self.popt, self.p_std_p, self.p_std_m

        p_opt = np.column_stack((tau, p0))
        if sigma is None:
            return p_opt, None, None

        p1 = np.dot(ddd, yp+sigma)
        p_std_p = np.column_stack((tau, p1))

        p2 = np.dot(ddd, yp-sigma)
        p_std_m = np.column_stack((tau, p2))

        return p_opt, p_std_p, p_std_m

    def _eval(self, x, ti, ci):
        ci = np.asarray(ci)
        s = np.sum(ci[:-1] * np.exp(-x / ti[:-1]))
        return ci[-1] + s

    def eval(self, x, fit=None):
        """Determine the value on the curve defined by a Prony series at x = t / aT

        Parameters
        ----------
        fit : ndarray
            Array returned by fit_points

        Returns
        -------
        val : real
            The value of the Prony series at x

        """
        if fit is None:
            fit = self.popt
        ti, ci = fit[:, 0], fit[:, 1]
        return self._eval(BASE**x, ti, ci)

    def dump_info(self, fit, ffmt='.6f', delimiter=','):
        line = []
        ti, ci = fit[:, 0], fit[:, 1]
        line.append(['tau_{0:d}'.format(i+1) for i in range(len(ti)-1)])
        line.append(['{0:{1}}'.format(r, ffmt) for r in ti[:-1]])
        line.append(['y_{0:d}'.format(i+1) for i in range(len(ci)-1)])
        line[-1].append('y_inf')
        line.append(['{0:{1}}'.format(r, ffmt) for r in ci])
        line = joinn(line, sep=delimiter)
        return line

    def abaqus_repr(self, tref, wlf, fit, stdv, ffmt='.6f'):
        def write_visco(t, c):
            fac = sum(c)
            string = '*Viscoelastic, time=PRONY\n'
            for (i, ti) in enumerate(t[:-1]):
                string += ' {0:{2}}, ,{1:{2}}\n'.format(c[i]/fac, ti, ffmt) 
            return string

        s  = ''
        if wlf is not None:
            c1, c2 = wlf
            s += '*Trs, definition=WLF\n'
            s += ' {0:{3}}, {1:{3}}, {2:{3}}\n'.format(tref, c1, c2, ffmt) 

        s += write_visco(fit[:,0], fit[:,1])
        if stdv is not None:
            raise NotImplementedError
            s += '** - STDV\n'
            c = fit[:,1] - stdv[:,1]
            s += write_visco(stdv[:,0], fit[:,1]-stdv[:,1])
            s += '** + STDV\n'
            s += write_visco(stdv[:,0], fit[:,1]+stdv[:,1])

        return s


class ModifiedPowerFit1(_CurveFitter):
    name = 'MODIFIED POWER 1'
    key = MODIFIED_POWER_1
    yvar = 'Log[Er]'
    def __init__(self, *args, **kwargs):
        self.rate = kwargs.get('rate')
        self.plot_label = r'$a_1 + a_2 e^{a_3 T_r^{a_4}}$'

    def fit_points(self, xp, yp, sigma=None, p0=None, no_weight=None):
        """Retuns the best fits for a modified power curve

        Parameters
        ----------
        xp : ndarray
            x points (log(t/aT))
        yp : ndarray
            y points

        Returns
        -------
        fit : ndarray
            The fit parameters [a1, a2, a3, a4]

        Notes
        -----
        Fits
                                       a4
                                  a3 Tr
               log[Er] = a1 + a2 e

        """
        def func(x, a1, a2, a3, a4):
            return (a1 + a2*np.exp(a3*((BASE**x)**a4)))
        if p0 is None:
            p0 = (1, 10, -1, .01)
        fit = curve_fit2(func, xp, yp, p0, sigma, trans_y=log, nw=no_weight)
        self.popt, self.p_std_p, self.p_std_m = fit
        return fit

    def eval(self, x, fit=None):
        if fit is None:
            fit = self.popt
        a1, a2, a3, a4 = fit
        return self._eval(x, a1, a2, a3, a4)

    @staticmethod
    def _eval(x, a1, a2, a3, a4):
        log_y = a1 + a2 * np.exp(a3 * (BASE**x) ** a4)
        return 10 ** log_y

    def dump_info(self, fit, ffmt='.6f', delimiter=','):
        line = []
        line.append(['a1', 'a2', 'a3', 'a4'])
        line.append(['{0:{1}}'.format(r, ffmt) for r in fit])
        line = joinn(line, sep=delimiter)
        return line

    def descriptive_plot_label(self, fit):
        a1, a2, a3, a4 = fit
        label = r'$10^{%.2f+%.2fe^{%.2f T_r^{%.2f}}}$'
        return label % (a1, a2, a3, a4)

class ModifiedPowerFit(_CurveFitter):
    name = 'MODIFIED POWER'
    key = MODIFIED_POWER
    def __init__(self, *args, **kwargs):
        self.rate = kwargs.get('rate')
        if self.rate:
            self.plot_label = r'$y_0 + y_1 \left(\frac{t}{a_T}\right) ^ a$'
        else:
            self.plot_label = r'$y_0 + y_1 \left(\dot{\epsilon}\cdot a_T\right)^a$'

    def fit_points(self, xp, yp, sigma=None, p0=None, no_weight=None):
        """Retuns the best fits for a modified power curve

        Parameters
        ----------
        xp : ndarray
            x points (log(t/aT))
        yp : ndarray
            y points

        Returns
        -------
        fit : ndarray
            The fit parameters [Ee, E1, a]

        Notes
        -----
        Fits

                                  a3
               Er = a1 + a2 (t/aT)

        """
        def func(x, a1, a2, a3):
            return self._eval(x, a1, a2, a3)
        if p0 is None:
            p0 = (2, 15, -.01)
        fit = curve_fit2(func, xp, yp, p0, sigma, nw=no_weight)
        self.popt, self.p_std_p, self.p_std_m = fit
        return fit

    def eval(self, x, fit=None):
        if fit is None:
            fit = self.popt
        Ee, E1, a = fit
        return self._eval(x, Ee, E1, a)

    @staticmethod
    def _eval(x, a1, a2, a3):
        return a1 + a2 * (BASE ** x) ** a3

    def dump_info(self, fit, ffmt='.6f', delimiter=','):
        line = []
        line.append(['Ee', 'E1', 'a'])
        line.append(['{0:{1}}'.format(r, ffmt) for r in fit])
        line = joinn(line, sep=delimiter)
        return line

    def descriptive_plot_label(self, fit):
        E1, E2, a = fit
        if self.rate:
            label = r'$%.2f+%.2f\left(\dot{\epsilon}\cdot a_T\right)^{%.2f}$'
        else:
            label = r'$%.2f+%.2f\left(\frac{{t}}{{a_T}}\right)^{%.2f}$'
        return label % (E1,E2,a)

class PowerFit(_CurveFitter):
    name = 'POWER'
    key = POWER
    plot_label = r'$y_0\left(\frac{t}{a_T}\right) ^ a$'
    def __init__(self, *args, **kwargs):
        pass
    def fit_points(self, xp, yp, sigma=None, p0=None, no_weight=None):
        """Retuns the best fits for a power curve

        Parameters
        ----------
        xp : ndarray
            x points (log(t/aT))
        yp : ndarray
            y points

        Returns
        -------
        fit : ndarray
            The fit parameters [E0, a]

        Notes
        -----
        Fits

                                  a2
               Er = a1 (t/aT)

        """
        def func(x, a1, a2):
            return self._eval(x, a1, a2)
        if p0 is None:
            p0 = (100., -1.)
        fit = curve_fit2(func, xp, yp, p0, sigma, nw=no_weight)
        self.popt, self.p_std_p, self.p_std_m = fit
        return fit

    def eval(self, x, fit=None):
        if fit is None:
            fit = self.popt
        a1, a2 = fit
        return self._eval(x, a1, a2)

    @staticmethod
    def _eval(x, a1, a2):
        return a1 * (BASE ** x) ** a2

    def dump_info(self, fit, ffmt='.6f', delimiter=','):
        line = []
        line.append(['E0', 'a'])
        line.append(['{0:{1}}'.format(r, ffmt) for r in fit])
        line = joinn(line, sep=delimiter)
        return line

class PolyFit(_CurveFitter):
    name = 'POLYNOMIAL'
    key = POLYNOMIAL
    def __init__(self, *args, **kwargs):
        self.rate = kwargs.get('rate')
        self.order = kwargs.get('order', 2)
        self.p = None
        pass
    @property
    def plot_label(self):
        if self.rate:
            f = r'\log{\left(\dot{\epsilon}\cdot a_T\right)}'
        else:
            f = r'\log{\left(\frac{t}{a_T}\right)}'
        if self.p is None:
            return r'$c_0 + c_1 %(f)s + ... + c_n %(f)s^n$' % {'f': f}
        np = self.p.shape[0]
        l = ['c_0']
        if np > 1:
            l.append('c_1 %(f)s' % {'f':f})
        if np > 2:
            l.extend([r'\cdots', r'c_%(n)d %(f)s^%(n)d' % {'f':f, 'n':np-1}])
        return r'${0}$'.format(' + '.join(l))
    def fit_points(self, xp, yp, sigma=None, p0=None, no_weight=None):
        """Retuns the best fits for a polynomial curve

        Parameters
        ----------
        xp : ndarray
            x points (log(t/aT))
        yp : ndarray
            y points

        """
        if no_weight:
            w = None
        elif sigma is not None:
            w = 1. / sigma
        else:
            w = None
        self.popt, pcov = np.polyfit(xp, yp, self.order, cov=True, w=w)
        if sigma is None:
            self.p_std_p = self.p_std_m = None
        else:
            self.p_std_p, pc = np.polyfit(xp, yp+sigma, self.order, cov=True)
            self.p_std_m, pc = np.polyfit(xp, yp-sigma, self.order, cov=True)
        return self.popt, self.p_std_p, self.p_std_m

    def eval(self, x, fit=None):
        if fit is None:
            fit = self.popt
        return np.poly1d(fit)(x)

    def dump_info(self, fit, ffmt='.6f', delimiter=','):
        line = []
        line.append(['p_{0}'.format(i) for i in range(fit.shape[0])])
        line.append(['{0:{1}}'.format(r, ffmt) for r in fit[::-1]])
        line = joinn(line, sep=delimiter)
        return line

def CurveFitter(key, rate=False):
    """Curve Fitter factory method"""
    fitters = _CurveFitter.__subclasses__()
    for f in fitters:
        if f.key == key:
            break
    else:
        raise ValueError('{0}: unrecognized fitter'.format(key))
    return f

RE = re.compile('[ \,]')
def _split(string, comments, i=0):
    return [x for x in RE.split(string.strip().split(comments,1)[i]) if x.split()]

def ReadCSV(filename, apply_log=True, ref_temp=75., columns=[0,1,2],
            xvar='Time', xunits='min', yvar='Er', yunits='psi',
            skip_temps=None, xfac=1., yfac=1., comments='#', **kwargs):
    """MasterCurve factory method

    Parameters
    ----------
    filename : str
        File in which data is found

    Returns
    -------
    mc : MasterCurve

    Notes
    -----
    Each line of filename must be formatted as

      Temperature, x, y

    """
    fown = False
    try:
        if isinstance(filename, (str,)):
            fown = True
            fh = iter(open(filename))
        else:
            fh = iter(filename)
    except (TypeError):
        message = 'filename must be a string, file handle, or generator'
        raise ValueError(message)

    data = []
    try:
        for (i, line) in enumerate(fh.readlines()):
            line = _split(line, comments)
            if not line:
                continue
            try:
                line = [float(x) for x in line]
            except ValueError:
                raise ValueError('expected floates in line{0} '
                                 'got {1}'.format(i+1, line))
            data.append(line)
    finally:
        if fown:
            fh.close()

    data = np.array(data)[:,columns]
    data = np.asarray(sorted(data, key=lambda x: (x[0], x[1])))
    return MasterCurve(data, ref_temp=ref_temp, apply_log=apply_log,
                       skip_temps=skip_temps, xfac=xfac, yfac=yfac,
                       xvar=xvar, xunits=xunits, yvar=yvar, yunits=yunits,
                       **kwargs)

def mc_init_notebook(plot_lib='bokeh', i=1):
    lib = plot_lib.lower()
    if lib == 'bokeh':
        if bp is None:
            raise ImportError('bokeh')
        if i:
            from bokeh.io import output_notebook
            output_notebook()
        environ.notebook = 2
    elif lib == 'matplotlib':
        if plt is None:
            raise ImportError('matplotlib')
        plt.rcParams['figure.figsize'] = (15, 12)
        plt.rcParams['font.family'] = 'serif'
        plt.rcParams['font.size'] = 20
        plt.rcParams['font.serif'] = 'Times New Roman'
        plt.rcParams['legend.scatterpoints'] = 1
        plt.rcParams['legend.handlelength'] = 0
        environ.notebook = 1
    else:
        raise ValueError('expected bokeh or matplotlib, got {0!r}'.format(plot_lib))

def is_stringlike(s):
    try:
        s + ''
        return True
    except (TypeError, ValueError):
        return False

def is_listlike(a):
    if is_stringlike(a):
        return False
    try:
        len(a)
        return True
    except TypeError:
        return False

def to_minutes(time, units):
    """Convert time time to minutes"""
    if is_listlike(time):
        r = range(len(time))
        if not is_listlike(units):
            units = [units] * len(time)
        return np.array([to_minutes(time[i], units[i]) for i in r])
    time = float(time)
    u = units.lower()[:3]
    if u == "sec":
        time = time / 60.
    elif u == "min":
        time = time
    elif u == "hou":
        time = time * 60.
    elif u == "day":
        time = time * 24. * 60.
    elif u == "wee":
        time = time * 7. * 24. * 60.
    elif u == "mon":
        time = time * 30. * 24. * 60.
    elif u == "yea":
        time = time * 365. * 24. * 60.
    elif u == "her":
        time = .25 / time / 60.
    return time

def cnvtime(time, units, outunits="min"):
    if is_listlike(time):
        if not is_listlike(units):
            units = [units] * len(time)
        r = range(len(time))
        return [cnvtime(time[i], units[i], outunits=outunits) for i in r]
    # convert all to minutes for now
    time = to_minutes(time, units)
    ou = outunits.lower()[:3]
    if ou == "min":
        return time
    elif ou == "sec":
        return time * 60.
    elif ou == "hou":
        return time / 60.
    elif ou == "day":
        return time / 24. / 60.
    elif ou == "wee":
        return time / 7. / 24. / 60.
    elif ou == "mon":
        return time / 30. / 24. / 60.
    elif ou == "yea":
        return time / 365. / 24. / 60.
    elif ou == "her":
        return .25 * time * 60.

def tolatex(f):
    import re
    if abs(f) < 5000:
        return '%.2f'%f

    s = '{0:.2e}'.format(f)
    x = re.split('e[+-]', s)
    return r'%s\times 10^{%s}'%(x[0], x[1])

def test_1():
    test_data = StringIO("""\
# Each line shall be as
# Temperature, Time, Value
0.0000, 0.0100, 4857.0000
0.0000, 0.0316, 3444.0000
0.0000, 0.1000, 2489.0000
0.0000, 0.3162, 1815.0000
0.0000, 1.0000, 1375.0000
0.0000, 3.1623, 1067.0000
0.0000, 10.0000, 852.0000
0.0000, 16.5959, 774.0000
20.0000, 0.0100, 3292.0000
20.0000, 0.0316, 2353.0000
20.0000, 0.1000, 1730.0000
20.0000, 0.3162, 1284.0000
20.0000, 1.0000, 970.0000
20.0000, 3.1623, 746.0000
20.0000, 10.0000, 577.0000
20.0000, 16.5959, 505.0000
40.0000, 0.0100, 2159.0000
40.0000, 0.0316, 1592.0000
40.0000, 0.1000, 1179.0000
40.0000, 0.3162, 920.0000
40.0000, 1.0000, 733.0000
40.0000, 3.1623, 585.0000
40.0000, 10.0000, 484.0000
40.0000, 16.5959, 449.0000
75.0000, 0.0100, 1287.0000
75.0000, 0.0316, 985.0000
75.0000, 0.1000, 767.0000
75.0000, 0.3162, 616.0000
75.0000, 1.0000, 498.0000
75.0000, 3.1623, 410.0000
75.0000, 10.0000, 333.0000
75.0000, 16.5959, 311.0000
100.0000, 0.0100, 1123.0000
100.0000, 0.0316, 881.0000
100.0000, 0.1000, 708.0000
100.0000, 0.3162, 573.0000
100.0000, 1.0000, 471.0000
100.0000, 3.1623, 399.0000
100.0000, 10.0000, 341.0000
100.0000, 16.5959, 316.0000
130.0000, 0.0100, 810.0000
130.0000, 0.0316, 646.0000
130.0000, 0.1000, 523.0000
130.0000, 0.3162, 432.0000
130.0000, 1.0000, 364.0000
130.0000, 3.1623, 313.0000
130.0000, 10.0000, 271.0000
130.0000, 16.5959, 254.0000""")

    # Baseline solution
    c = np.array([3.292, 181.82])
    p = np.array([[.0001, 2489],
                  [.001, 1482],
                  [.01, 803],
                  [.1, 402],
                  [1, 207],
                  [10, 124],
                  [100, 101],
                  [0, 222]], dtype=np.float64)
    mc = ReadCSV(test_data, ref_temp=75., apply_log=True,
                 fitter=PRONY, optcoeffs=False)
    s1 = 'WLF coefficients not within tolerance'
    mc.fit()
    assert np.allclose(mc.wlf_opt, c, rtol=1.e-3, atol=1.e-3), s1
    s2 = 'Prony series not within tolerance'
    assert np.allclose(mc.mc_fit[:, 1], p[:, 1], rtol=1.e-2, atol=1.e-2), s2
    mc.fit(optimize=True)
    print('Success')

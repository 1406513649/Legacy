from ..utils import *

class Interface(object):

    def __init__(self, id_interface):
        self.id_interface = id_interface
        self._interface = None

    def as_string(self):
        s = ['id_interface = {0!r}'.format(self.id_interface)]
        if self.asynchronous:
            n = self.asynchronous
            s.append('asynchronous')
            s.append('  evaluation_concurrency {0}'.format(n))

        ad = self._analysis_drivers.as_string()
        s.append(ad)
        return 'interface\n  ' + '\n  '.join(s)
        
    def Fork(self, drivers):
        f = Fork(drivers)
        self._interface = f
        return f
        

class Fork:
    def __init__(self, drivers, **kwds):
        
        self.drivers = drivers
        self.parameters_file = kwds.pop('parameters_file', 'params.in')
        self.results_file = kwds.pop('results_file', 'results.out')
        self.allow_existing_results = kwds.pop('allow_existing_results', False)
        self.verbatim = kwds.pop('verbatim', None)
        self.aprepro = kwds.get('aprepro', False)
        self.labeled = kwds.get('labeled', True)
        self.file_tag = kwds.get('file_tag', False)
        self.file_save = kwds.get('file_save', True)
        self._work_directory = None
        wd = kwds.get('work_directory', None)
        if wd is not None:
            wd = self.work_directory(**wd)

    def work_directory(self, named=None, tag=None, save=None,
            link_files=None, copy_files=None, replace=False):
        if is_stringlike(link_files):
            link_files = [link_files]
        if is_stringlike(copy_files):
            copy_files = [copy_files]

        self._work_directory = dict(named=named, tag=bool(tag), 
                save=bool(save), link_files=link_files, 
                copy_files=copy_files, replace=bool(replace))

    def as_string(self):
        s = ['fork']
        s.append('  parameters_file = {0!r}'.format(self.parameters_file))
        s.append('  results_file = {0!r}'.format(self.results_file))

        if self._work_directory is not None:
            s.append('  work_directory')

            named = self._work_directory['named']
            if named:
                s.append('    named {0!r}'.format(named))

            tag = self._work_directory['tag']
            if tag:
                s.append('    directory_tag')

            save = self._work_directory['save']
            if save:
                s.append('    directory_save')

            lf = self._work_directory['link_files']
            if lf:
                lf = ' '.join('{0!r}'.format(f) for f in lf)
                s.append('    link_files = {0}'.format(lf))

            cf = self._work_directory['copy_files']
            if cf:
                cf = ' '.join('{0!r}'.format(f) for f in cf)
                s.append('    copy_files = {0}'.format(cf))

            if self._work_directory['replace']:
                s.append('    replace')

        d = ' '.join('{0!r}'.format(d) for d in self.drivers)
        return 'analysis_drivers {0}\n    '.format(d) + '\n    '.join(s)



        self._analysis_drivers = None

        self._tags = None
        self._results_file = None
        self._parameters_file = None
        self._link_files = None
        self._asynchronous = None

    def analysis_drivers(self, driver, method='fork'):
        if is_stringlike(driver):
            driver = [driver]
        if method == 'fork':
            self._analysis_drivers = Fork(driver)
        return self._analysis_drivers

    def 

    @property
    def asynchronous(self):
        return self._asynchronous

    @asynchronous.setter
    def asynchronous(self, arg):
        self._asynchronous = int(arg)


import os
import sys
import string
import logging

from tools.misc import who_is_calling
SPLASH = ""

_LIST_ = -123
_SPLASHED_ = -124
CONSOLE = "console"
_cache = {}

def Logger(name, **kwargs):
    try:
        return _cache[name]
    except KeyError:
        pass
    _cache[name] = _Logger(name, **kwargs)
    return _cache[name]

class _Logger(object):
    _splashed = [False]
    def __init__(self, name, filename=1, verbosity=1, mode="w", splash=True):

        self.logger_id = name
        self.errors = 0

        # set the logging level
        chlev = {0: logging.CRITICAL,
                 1: logging.INFO,
                 2: logging.DEBUG}.get(abs(verbosity), logging.NOTSET)

        # basic logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(chlev)

        # console handler
        if verbosity < 0:
            # verbosity less than 0 flags a parent process, we still want to
            # log, so we send it to a 'console' file
            ch = logging.FileHandler(name + ".con", mode="w")
        else:
            ch = logging.StreamHandler()
        ch.setLevel(chlev)
        self.logger.addHandler(ch)

        # file handler.  by default, we add a file handler
        if filename == 1:
            filename = name + ".log"

        if filename:
            self.add_file_handler(filename)

        for handler in self.logger.handlers:
            # do our best to only splash to screen once
            if "stderr" in str(handler.stream) and not splash:
                continue
            elif "stderr" in str(handler.stream) and self._splashed[0]:
                continue
            handler.stream.write(SPLASH + "\n")
            self._splashed[0] = True

    def set_verbosity(self, n):
        lev = {0: logging.CRITICAL,
               1: logging.INFO,
               2: logging.DEBUG}.get(abs(n), logging.NOTSET)
        self.logger.setLevel(lev)

    def add_file_handler(self, filename):
        fhlev = logging.DEBUG
        fh = logging.FileHandler(filename, mode="w")
        fh.setLevel(fhlev)
        self.logger.addHandler(fh)

    def info(self, message, beg="", end=None, report_who=False, who=None):
        if report_who:
            who = who_is_calling()
        if who:
            beg = "{0}{1}: ".format(beg, who)
        message = message.rstrip()
        message = "{0}{1}".format(beg, message)
        if end is not None:
            message = "{0}{1}".format(message, end)
        c = True if end is not None else False
        continued = {"continued": c}
        self.logger.info(message, extra=continued)

    def warn(self, message, limit=False, warnings=[0], report_who=None, who=None):
        if report_who:
            who = who_is_calling()
        if who:
            message = "{0}: {1} ".format(who, message)
        message = "*** warning: {0}".format(message)
        if limit and warnings[0] > 10:
            return
        continued = {"continued": False}
        self.logger.warn(message, extra=continued)
        warnings[0] += 1

    def write(self, *args, **kwargs):
        if not args:
            args = ("",)
        self.info(*args, **kwargs)

    def exception(self, message, who=None):
        if who is None:
            who = who_is_calling()
        self.raise_error(message, who=who)

    def raise_error(self, message, who=None):
        if who is None:
            who = who_is_calling()
        self.error(message, who=who)
        raise Exception(message)

    def error(self, message, who=None):
        self.errors += 1
        if who is None:
            who = who_is_calling()
        message = "*** error: {0}: {1}".format(who, message)
        continued = {"continued": False}
        self.logger.error(message.rstrip(), extra=continued)

    def debug(self, message, end=None):
        if end is not None:
            message += end
        c = True if end is not None else False
        continued = {"continued": c}
        self.logger.debug(message, extra=continued)

    def finish(self):
        global logger
        logger = None

    def close(self):
        self.finish()

    def write_intro(self, solver, num_step, tol, max_iter, relax,
                    tstart, tterm, num_dof, num_elem, num_node):
        def ffmt(r):
            return "NA" if r is None else "{0:8.6f}".format(r)
        def ifmt(i):
            return "NA" if i is None else "{0:d}".format(i)

        message = """\
==============================================================================
                     Summary of simulation input

  Solver
  ------
  {0}

  Control Information
  ------- -----------
  Number of Load Steps: {1}
             Tolerance: {2}
    Maximum Increments: {3}
            Relaxation: {4}
            Start Time: {5}
      Termination Time: {6}

  Mesh Information
  ---- -----------
  Number of Dimensions: {7}
    Number of Elements: {8}
       Number of Nodes: {9}
==============================================================================
""".format(solver, ifmt(num_step), ffmt(tol), ifmt(max_iter),
           ffmt(relax), ffmt(tstart), ffmt(tterm),
           ifmt(num_dof), ifmt(num_elem), ifmt(num_node))
        self.info(message)

def emit(self, record):
    """Monkey-patch the logging StreamHandler emit function. Allows omiting
    trailing newline when not wanted"""
    msg = self.format(record)
    fs = "%s" if getattr(record, "continued", False) else "%s\n"
    self.stream.write(fs % msg)
    self.flush()

logging.StreamHandler.emit = emit
ConsoleLogger = Logger("console", filename=None, splash=False)

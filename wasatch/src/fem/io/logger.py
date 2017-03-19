import os
import sys

class Logger(object):
    loggers = {}
    def __init__(self, runid, verbosity=1):

        self.logger = self.loggers.get(runid)

        if self.logger is None:
            if verbosity == 0:
                f = None
                stream = open(os.devnull, "a")
            else:
                f = runid + ".out"
                stream = open(f, "w")

            self.logger = {"VERBOSITY": verbosity, "FILE": f, "STREAM": stream}
            self.loggers[runid] = self.logger

    def write(self, msg=None, beg="", end="\n"):
        if msg is None:
            msg = ""
        msg = "{0}{1}{2}".format(beg, msg, end)
        self.fout(msg)
        if self.logger["VERBOSITY"]:
            self.cout(msg)

    def cout(self, msg):
        sys.stdout.write(msg)
        sys.stdout.flush()

    def fout(self, msg):
        self.logger["STREAM"].write(msg)
        self.logger["STREAM"].flush()

    def close(self):
        self.logger["STREAM"].flush()
        self.logger["STREAM"].close()

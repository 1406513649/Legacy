class Options:
    pass
opts = Options()
opts.raise_e = 0

class AFEPYError(Exception):
    def __init__(self, message):
        if opts.raise_e:
            super(AFEPYError, self).__init__(message)
        else:
            raise SystemExit("AFEPYError: " + message)

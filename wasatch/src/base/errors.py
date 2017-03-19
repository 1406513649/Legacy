class UserInputError(Exception):
    def __init__(self, message):
        from __runopt__ import debug
        if debug:
            raise SyntaxError(message)
        raise SystemExit("UserInputError: {0}".format(message))

class WasatchError(Exception):
    def __init__(self, message):
        from __runopt__ import debug
        if debug:
            raise
        raise SystemExit("WasatchError: {0}".format(message))

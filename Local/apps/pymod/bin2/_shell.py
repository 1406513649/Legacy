class Shell(object):
    """Base shell class"""
    def __init__(self):
        self.environ = {}
        self.aliases = {}

    def dump_environ(self):
        raise NotImplementedError('dump_environ')

    def register_alias(self):
        raise NotImplementedError('register_alias')

    def register_env(self):
        raise NotImplementedError('register_env')

    def getenv(self, name, default=None):
        return self.environ.get(name, default)



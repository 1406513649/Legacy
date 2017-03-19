import os
import utilities as ut

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


def get_shell(shell=None):
    if shell is None:
        shell = os.path.basename(os.getenv('SHELL'))
    if shell == 'bash':
        from bash import BashShell
        return BashShell()
    ut.raise_error('Unknown shell {0!r}'.format(shell))

import re
from _shell import Shell

class BashShell(Shell):
    """Bash shell class"""
    sep = ';'
    name = 'bash'
    def __init__(self):
        super(BashShell, self).__init__()
        self.functions = {}

    def register_env(self, name, value, mode):
        if mode == 'unload':
            self.environ[name] = None
        else:
            self.environ[name] = value

    def register_alias(self, name, command, mode):
        unset = mode == 'unload'
        if re.search('(?i)\$[\@\*0-9]', command):
            # bash function
            self.functions[name] = None if unset else command 
        else:
            # alias
            self.aliases[name] = None if unset else command

    def dump_environ(self):
        # Process environment
        the_environ = self.env_repr()
        the_environ.extend(self.function_repr())
        the_environ.extend(self.alias_repr())
        return self.sep.join(the_environ) + self.sep

    def env_repr(self):
        environ = []
        for (name, value) in self.environ.items():
            if value is None:
                environ.append('unset {0}'.format(name))
            else:
                s1 = '{0}={1}'.format(name, value)
                s2 = 'export {0}'.format(name)
                environ.extend([s1, s2])
        return environ

    def alias_repr(self):
        aliases = []
        for (name, command) in self.aliases.items():
            if command is None:
                aliases.append('unalias {0}'.format(name))
            else:
                aliases.append("alias {0}='{1}'".format(name, command))
        return aliases

    def function_repr(self):
        functions = []
        for (name, command) in self.functions.items():
            if command is None:
                functions.append('unset -f {0}'.format(name))
            else:
                s1 = '{0}() {{ {1};}}'.format(name, command)
                s2 = 'export -f {0}'.format(name)
                functions.extend([s1, s2])
        return functions



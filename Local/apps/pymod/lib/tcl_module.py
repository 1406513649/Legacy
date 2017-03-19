import os
from subprocess import Popen, PIPE


def is_executable(path):
    return os.path.exists(path) and os.access(path, os.X_OK)

class EnvironmentModules:
    """Class that uses the installed environment modules to modify the internal
    environment."""

    def __init__(self, shell):

        for candidate in ('/opt/apps/modules/Modules/3.2.10',):
            if os.path.isdir(candidate):
                self.home = candidate
                break
        else:
            raise Exception('module home not found')

        self.shell = shell

        # Look for the modulecmd
        self._modulecmd = os.path.join(self.home, 'bin/modulecmd')
        if not is_executable(self._modulecmd):
            raise Exception('modulecmd must exist and be executable')

    def eval(self, subcmd, arg, environ, inplace=0):
        """Evaluate the module sub command subcmd in the environment specified by the
        dictionary environ. If the optional inplace argument is specified, the
        environ dictionary is changed in place. The updated environment is
        returned as a dictionary

        """

        def strip(item):
            item = item.strip()
            if item[0] == '"' and item[-1] == '"':
                # strip quotations
                item = item[1:-1]
            return item

        command = [self._modulecmd, 'bash', subcmd, arg]

        p = Popen(command, env=environ, stderr=PIPE, stdout=PIPE)
        p.wait()
        stdout, stderr = p.communicate()
        if stderr.split():
            # An error occurred
            raise Exception('The following error occurred while attempting '
                            'to execute {0}\n{1}'.format(' '.join(command), stderr))

        # modulecmd writes output to stdout which is then `eval`d if run by a
        # shell. We mimic the behavior by capturing stdout and putting it in to
        # a dictionary that can be used to update the caller's environment.
        updated_environ = {}
        stdout = ''.join(x for x in stdout.split('\n') if x.split())
        previous = None
        for item in stdout.split(';'):
            if not item.split():
                continue
            item = item.strip()
            if item.startswith('export '):
                key, value = previous.split('=', 1)
                updated_environ[key.strip()] = strip(value)
            previous = item
        if inplace:
            environ.update(updated_environ)
        return updated_environ

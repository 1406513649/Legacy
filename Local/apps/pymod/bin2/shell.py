import os
import sys
from os.path import realpath, expanduser, join, basename, sep, \
        isfile, isdir, exists, split


"""Monkey-patch subprocess for python 2.6 to give feature parity 
with later versions.
"""
try:
    from subprocess import check_output, Popen, PIPE
except ImportError:  # pragma: no cover
    # python 2.6 doesn't include check_output
    # monkey patch it in!
    import subprocess
    STDOUT = subprocess.STDOUT
    Popen = subprocess.Popen
    PIPE = subprocess.PIPE

    def check_output(*popenargs, **kwargs):
        if 'stdout' in kwargs:  # pragma: no cover
            raise ValueError('stdout argument not allowed, '
                             'it will be overridden.')
        process = subprocess.Popen(stdout=subprocess.PIPE,
                                   *popenargs, **kwargs)
        output, _ = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise subprocess.CalledProcessError(retcode, cmd,
                                                output=output)
        return output
    subprocess.check_output = check_output

    # overwrite CalledProcessError due to `output`
    # keyword not being available (in 2.6)
    class CalledProcessError(Exception):
        def __init__(self, returncode, cmd, output=None):
            self.returncode = returncode
            self.cmd = cmd
            self.output = output

        def __str__(self):
            return "Command '%s' returned non-zero exit status %d" % (
                self.cmd, self.returncode)
    subprocess.CalledProcessError = CalledProcessError


class GlobalOptions:
    def __init__(self):
        self.debug = False
        self.force = False
global_opts = GlobalOptions()


def to_string(text):
    if text is None:
        return ''
    try:
        text + ' '
        string = text
    except TypeError:
        string = text.decode('utf-8')
    return string.strip()


def get_pathenv(env, split=1):
    path = os.getenv(env)
    if split:
        return path_split(path)
    return path


def path_split(path, sep=os.pathsep):
    """Split the path variable"""
    if path is None:
        return []
    return [x for x in path.split(sep) if x.split()]


def path_join(path):
    """Join the path"""
    if path is None:
        return ''
    the_path = []
    for item in path:
        if item not in the_path:
            the_path.append(item)
    return os.pathsep.join(the_path)


def fixpath(path):
    if '~' in path:
        path = realpath(expanduser(path))
    return path


def get_output(command, full_output=0):
    """Get the output from a command"""

    def get_output1():
        """Get the output from a command using check_output"""
        with open(os.devnull, 'a') as fh:
            stdout = check_output(command, shell=True, stderr=fh)
        return to_string(stdout)


    def get_output2():
        """Get the output from a command using Popen"""
        p = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
        p.wait()
        stdout, stderr = p.communicate()
        output = {'returncode': p.returncode,
                  'stdout': to_string(stdout),
                  'stderr': to_string(stderr)}
        return output

    if not full_output:
        return get_output1()

    return get_output2()


def get_console_dims():
    """Return the size of the terminal"""
    out = get_output('stty size')
    rows, columns = [int(x) for x in out.split()]
    return rows, columns


def raise_error(error):
    """Write message to stderr and exit"""
    write_to_stream(sys.stderr, 'ERROR: ' + error)
    sys.exit(1)


def put_stderr(*args, **kwargs):
    """Write message to sderr"""
    write_to_stream(sys.stderr, *args, **kwargs)


def put_stdout(*args, **kwargs):
    """Write message to stdout"""
    write_to_stream(sys.stdout, *args, **kwargs)


def write_to_stream(stream, *args, **kwargs):
    """Put the message to the stream"""
    end = kwargs.get('end', '\n')
    text = ' '.join('{0}'.format(x) for x in args)
    stream.write(text + end)
    stream.flush()
    if global_opts.debug and stream != sys.stderr:
        sys.stderr.write(text+end)
        sys.stderr.flush()


def get_shell(shell):
    if shell == 'bash':
        from bash import BashShell
        return BashShell()
    raise_error('Unknown shell {0!r}'.format(shell))

import os
import sys
import getpass
import socket
from subprocess import Popen, PIPE, STDOUT

def getuser():
    """Return the user name"""
    return getpass.getuser()

def hostname():
    """Return the host name"""
    return socket.gethostname()
uname = hostname

def system():
    return sys.platform.lower()

def get_console_dims():
    """Return the size of the terminal"""
    out = check_output('stty size')
    rows, columns = [int(x) for x in out.split()]
    return rows, columns

def check_output(command):
    fh = open(os.devnull, 'a')
    p = Popen(command, shell=True, stdout=PIPE, stderr=fh)
    out, err = p.communicate()
    returncode = p.poll()
    try:
        out = out.decode('utf-8')
    except AttributeError:
        pass
    return out

def listdir(directory, key=lambda x: True):
    return [f for f in os.listdir(directory) if key(os.path.join(directory, f))]

def get_modulename(filename, n):
    return os.path.splitext(os.path.basename(filename))[0]

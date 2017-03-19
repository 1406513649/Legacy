import os
from subprocess import Popen, PIPE

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

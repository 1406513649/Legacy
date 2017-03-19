import os
import sys
try:
    from itertools import zip_longest as zip_longest
except ImportError:
    from itertools import izip_longest as zip_longest

import config
from utils import get_console_dims

class colors:
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    YELLOW = '\033[93m'
    ERROR = '\033[91m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class ModuleError(Exception):
    pass

def log_warning(filename, message):
    string = colors.WARNING + 'Warning:' + colors.ENDC
    string += ' {0}'.format(message)
    string += ' [Reported from {0!r}]'.format(filename)
    write_to_console(string)

def raise_error(message):
    raise ModuleError(message)

def log_error_and_exit(filename, message):
    string = colors.ERROR + 'Error:' + colors.ENDC
    string += ' {0}'.format(message)
    string += ' [Reported from {0!r}]'.format(filename)
    write_to_console(string)
    sys.exit(1)

def log_message(message, verbosity=None, filename=None):
    if verbosity is None:
        verbosity = config.verbosity
    if verbosity:
        string = message
        if filename is not None:
            string += ' [Reported from {0!r}]'.format(os.path.realpath(filename))
        write_to_console(message)

def write_to_console(string):
    sys.stderr.write(string + '\n')
    sys.stderr.flush()

def format_text_to_cols(array_of_str, width=None):

    if width is None:
        height, width = get_console_dims()

    text = ' '.join(array_of_str)
    space = (width - len(''.join(array_of_str))) / len(array_of_str)
    if space >= 1:
        space = ' ' * int(space)
        return space.join(array_of_str)

    N, n = len(array_of_str), 2
    while True:
        # determine number of rows to print
        chnx = [array_of_str[i:i+n] for i in range(0, N, n)]
        cw = [max(len(x) for x in chnk) for chnk in chnx]
        rows = list(zip_longest(*chnx, fillvalue=''))
        lmax, text = -1, []
        for row in rows:
            a = ['{0:{1}s}'.format(row[i], w) for (i, w) in enumerate(cw)]
            text.append(' '.join(a))
            lmax = max(lmax, len(text[-1]))

        if lmax >= width:
            n += 1
            continue

        max_row_width = max(len(row) for row in text)
        num_col = len(cw)
        dif = width - max_row_width
        extra = int(dif / num_col)
        cw = [x+extra for x in cw]
        text2 = []
        for row in text:
            row = row.split() + ['']*(num_col-len(row.split()))
            a = ['{0:{1}s}'.format(row[i], w) for (i, w) in enumerate(cw)]
            text2.append(' '.join(a))
        return '\n'.join(text2)

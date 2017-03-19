import os

shell_name = os.path.basename(os.getenv('PY_MODULE_SHELL', os.getenv('SHELL')))
if shell_name == 'bash':
    from bash import BashShell
    shell = BashShell()
else:
    from utilities import raise_error
    raise_error('Unknown shell {0!r}'.format(shell_name))

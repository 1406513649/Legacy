import re
import os
import sys
import glob

fixes = (('--', '#'),
         ('..', '+'),
         ('local cc, cxx, fc', 'cc = cxx = fc = None'),
         ('if not (fc == nil) ', 'if fc is not None'),
         ('local platform', ''),
         ('local ', ''),
         ('isDir', 'os.path.isdir'),
         (' then', ':'),
         ('pathJoin', 'os.path.join'),
         ("uname = string.lower(capture('uname -a'))", ''),
         ("darwin = uname:find('darwin')", 'darwin = system_is_darwin()'),
         ('myModuleName', 'module_name'),
         ('name:upper', 'name.upper'),
         ('myModuleVersion', 'module_version'),
         ('isFile', 'os.path.isfile'),
         ('LmodWarn', 'log_warning'),
         ('LmodError', 'log_error'),
         ('LmodMessage', 'log_message'),
         ("hostname = string.lower(capture('hostname'))", 'hostname = get_hostname()'))

for filename in glob.glob(os.path.join(sys.argv[1], '*.lua')):
    lines = open(filename).read()
    for (pat, repl) in fixes:
        lines = re.sub(re.escape(pat), repl, lines)
    lines = re.sub(r'\bend\b', '', lines)
    lines = re.sub(r'\belse\b', 'else:', lines)
    lines = re.sub(r'^  ', '    ', lines)
    pyfile = os.path.splitext(filename)[0]+'.py'
    with open(pyfile, 'w') as fh:
        fh.write(lines)

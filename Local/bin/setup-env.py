#!/usr/bin/env python
"""Set up my environment

"""
import os
import sys
import shutil
from subprocess import Popen, PIPE, STDOUT

D = os.path.dirname(os.path.realpath(__file__))
H = os.path.expanduser("~/")
ISFILE = 1
ISLINK = 2
ISDIR = 3

LOCAL_D = os.path.dirname(D)
ETC_D = os.path.join(LOCAL_D, 'etc')
VAR_D = os.path.join(LOCAL_D, 'var')
assert os.path.isdir(ETC_D)


def main():
    # bash
    source = os.path.join(ETC_D, "bash/bashrc")
    dest = os.path.join(H, ".bashrc")
    symlink(source, dest)

    source = os.path.join(ETC_D, "bash/bash_profile")
    dest = os.path.join(H, ".bash_profile")
    symlink(source, dest)

    source = os.path.join(ETC_D, "bash/iterm2_shell_integration.bash")
    dest = os.path.join(H, ".iterm2_shell_integration.bash")
    symlink(source, dest)

    # emacs
    dotemacs = os.path.join(H, ".emacs")
    if exists(dotemacs):
        move(dotemacs, unique(dotemacs))
    source = os.path.join(ETC_D, "emacs")
    if not os.path.isdir(source):
        print('Getting spacemacs')
        # get spacemacs
        command = ['git', 'clone',
                   'https://github.com/syl20bnr/spacemacs.git',
                   source]
        p = Popen(command, stdout=PIPE, stderr=STDOUT)
        p.wait()
        out, err = p.communicate()
        returncode = p.poll()
        if returncode != 0:
            raise Exception('Unable to get spacemacs, log: {0}'.format(out))
    dest = os.path.join(H, ".emacs.d")
    symlink(source, dest)

    source = os.path.join(ETC_D, "spacemacs")
    dest = os.path.join(H, ".spacemacs.d")
    symlink(source, dest)

    # conda
    source = os.path.join(ETC_D, "conda/condarc")
    dest = os.path.join(H, ".condarc")
    symlink(source, dest)

    # git
    source = os.path.join(ETC_D, "git/gitconfig")
    dest = os.path.join(H, ".gitconfig")
    symlink(source, dest)

    # ssh
    source = os.path.join(ETC_D, "ssh/config")
    dest = os.path.join(H, ".ssh/config")
    symlink(source, dest)

    # vim
    source = os.path.join(ETC_D, "vim")
    dest = os.path.join(H, ".vim")
    symlink(source, dest)

    source = os.path.join(ETC_D, "vim/vimrc")
    dest = os.path.join(H, ".vimrc")
    symlink(source, dest)

    source = os.path.join(ETC_D, "vim/gvimrc")
    dest = os.path.join(H, ".gvimrc")
    symlink(source, dest)

    # ipython
    source = os.path.join(ETC_D, "Jupyter")
    dest = os.path.join(H, ".ipython")
    symlink(source, dest, skip_if_noexist=1)

    # ipython
    if 'darwin' in sys.platform.lower():
        source = os.path.join(ETC_D, "Jupyter/nbextensions")
        dest = os.path.join(H, 'Library/Jupyter/nbextensions')
        symlink(source, dest, skip_if_noexist=1)

    # ipython
    source = os.path.join(ETC_D, "Jupyter")
    dest = os.path.join(H, ".jupyter")
    symlink(source, dest, skip_if_noexist=1)

    # My ports
    if 'darwin' in sys.platform.lower():
        source = os.path.join(VAR_D, 'ports')
        if not os.path.isdir(source):
            command = ['git', 'clone',
                       'git@github.com:tjfulle/ports',
                       source]
            p = Popen(command)
            p.wait()

    # Unison
    if 'darwin' in sys.platform.lower():
        source = os.path.join(ETC_D, "unison/default.prf")
        dest = os.path.join(H, 'Library/Unison/default.prf')
        if not os.path.isdir(os.path.dirname(dest)):
            os.makedirs(dest)
        symlink(source, dest)

    return


def exists(filepath):
    if os.path.islink(filepath):
        return ISLINK
    if os.path.isfile(filepath):
        return ISFILE
    if os.path.isdir(filepath):
        return ISDIR
    return


def move(source, dest):
    print("moving {0} to {1}".format(source, dest))
    shutil.move(source, dest)


def unique(filename):
    if not exists(filename):
        return filename
    d = os.path.dirname(filename)
    root, ext = os.path.splitext(filename)
    for i in range(100):
        f = os.path.join("{0}_{1}{2}".format(root, i, ext))
        if not exists(f):
            break
    return f


def symlink(source, link, save=0, skip_if_noexist=0):
    if exists(link):
        if save:
            move(link, unique(link))
        else:
            os.remove(link)
    if not exists(source):
        if skip_if_noexist:
            return
        raise AssertionError('{0} does not exist'.format(source))
    print("linking {0} to {1}".format(source, link))
    os.symlink(source, link)


if __name__ == "__main__":
    main()

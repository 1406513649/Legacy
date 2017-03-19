'''Pull changes from the hpc cluster to my local machine'''
import os
import sys
import argparse
import subprocess
import multiprocessing
from os.path import expanduser, isdir, realpath, dirname, sep, exists, join, basename

PUSH = 0
PULL = 1


class Logger:
    def __init__(self, filename=None):
        self.handlers = [sys.stdout]
        if filename is not None:
            self.handlers.append(open(filename, 'w'))

    def flush(self):
        for h in self.handlers:
            h.flush()

    def write(self, string):
        for h in self.handlers:
            h.write(string)

    def info(self, message, pre='info: ', end='\n'):
        '''Log a message to the console handler'''
        message = '{0}{1}{2}'.format(pre, message, end)
        self.write(message)
        self.flush()

    def warn(self, message):
        '''Log a warning to the console handler'''
        message = '*** warning: {0}\n'.format(message)
        self.write(message)
        self.flush()

    def error(self, message):
        message = '*** error: {0}\n'.format(message)
        self.write(message)
        self.flush()
logger = Logger()


def make_remote_dir(remote, d, dryrun=False):
    cmd = ['ssh', remote, 'mkdir -p {0}'.format(d)]
    stat = call(cmd, dryrun=dryrun)
    if stat != 0:
        logger.warn('failed to create {0} on {1}'.format(d, remote))
    return stat

def call(cmd, dryrun=False):
    if dryrun:
        cmd = ' '.join(cmd)
        logger.info(cmd)
        return 0
    proc = subprocess.Popen(cmd)
    proc.wait()
    return proc.returncode

class Syncer(object):
    def __init__(self, remote, action, sources,
            delete=False, nproc=2, dryrun=False, skip=None):
        self.dryrun = bool(dryrun)

        self.D = delete
        self.R = remote
        self.nproc = min(len(sources), nproc)
        self.X = skip or []

        # format sources
        self.ax = {'pull': PULL, 'push': PUSH}[action.lower()]
        self.src_dst_pairs = []
        for source in sources:
            s = realpath(expanduser(source))
            if self.ax == PUSH:
                # source better exist
                assert exists(s), '{0} no such file or directory'.format(source)
                if isdir(s):
                    d = source
                    if not source.endswith(sep):
                        source += sep
                else:
                    d = dirname(source)
                d = d.replace('/Users', '/home')
                f = basename(source)
                stat = make_remote_dir(remote, d, dryrun=self.dryrun)
                assert stat == 0, 'failed to make remote directory'
                dest = join(d, f)

            else:
                if isdir(s) or source.endswith(sep):
                    # source on remote is a directory - as best we can tell
                    dest = source
                    d = source
                    if not source.endswith(sep):
                        source += sep
                else:
                    dest = '.'
                    d = dirname(source)

                try:
                    os.makedirs(d)
                except OSError:
                    pass
                source = source.replace('/Users', '/home')

            self.src_dst_pairs.append((source, dest))

    def sync(self):
        '''Perform the sync'''
        args = [(s, d, self.R, self.D, self.X, self.dryrun) 
                for (s, d) in self.src_dst_pairs]
        action = {PULL: pull_from_remote, PUSH: send_to_remote}[self.ax]
        if self.nproc == 1:
            action(args[0])
        else:
            pool = multiprocessing.Pool(self.nproc)
            pool.map(action, args)
            pool.close()


def pull_from_remote(args):
    source, dest, remote, delete, exts_to_skip, dryrun = args
    dest = expanduser(dest)
    excludes = ' '.join('--exclude {0}'.format(ext) for ext in exts_to_skip)
    opts  = '-arvzPt --update '
    opts += '--exclude tmp/* --exclude *.bak {0} -e ssh'.format(excludes)
    if delete: opts += ' --delete'
    cmd = 'rsync {0} {1}:{2} {3}'.format(opts, remote, source, dest)
    return call(cmd.split(), dryrun=dryrun)


def send_to_remote(args):
    source, dest, remote, delete, exts_to_skip, dryrun = args
    source = expanduser(source)
    excludes = ' '.join('--exclude {0}'.format(ext) for ext in exts_to_skip)
    opts  = '-arvzPt --update '
    opts += '--exclude tmp/* --exclude *.bak {0} -e ssh'.format(excludes)
    if delete: opts += ' --delete'
    cmd = 'rsync {0} {1} {2}:{3}'.format(opts, source, remote, dest)
    return call(cmd.split(), dryrun=dryrun)

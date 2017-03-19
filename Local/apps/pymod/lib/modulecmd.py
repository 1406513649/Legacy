#!/usr/bin/env python
import sys

from argparse import ArgumentParser
import config
from shell import Shell
from module_loader import module_loader
from module_purge import module_purge


def main(argv=None):
    """The main module interface"""

    if argv is None:
        argv = sys.argv[1:]

    p = ArgumentParser(prog='module')
    p.add_argument('shell', choices=('bash',))
    p.add_argument('--debug', action='store_true', default=False)
    p.add_argument('-v', default=config.verbosity, type=int,
            help='Level of verbosity [default: %(default)s]')

    sub_p = p.add_subparsers(dest='subparser',
                             title='subcommands',
                             description='valid subcommands',
                             help='sub-command help')

    p_avail = sub_p.add_parser('avail', help='Display available modules')
    p_avail.add_argument('-t', default=False, action='store_true',
            help='Display available modules in terse format [default: False]')

    p_list = sub_p.add_parser('list', help='Display loaded modules')
    p_list.add_argument('-t', default=False, action='store_true',
            help='Display available modules in terse format [default: False]')

    p_load = sub_p.add_parser('load', help='Load module[s]')
    p_load.add_argument('modulename', nargs='+', help='Valid modulename[s]')
    p_load.add_argument('-f', '--force', action='store_true', default=False,
            help='Force load missing prerequisites [default: False]')

    p_uload = sub_p.add_parser('unload', help='Unload module[s]')
    p_uload.add_argument('modulename', nargs='+', help='Valid modulename[s]')
    p_uload.add_argument('-f', '--force', action='store_true', default=False,
            help='Remove loaded prerequisites [default: False]')

    p_purge = sub_p.add_parser('purge', help='Unload all modules')

    p_swap = sub_p.add_parser('swap', help='Swap modules')
    p_swap.add_argument('modulename', nargs=2, help='Valid modulenames')

    p_help = sub_p.add_parser('help', help='Display help for module[s]')
    p_help.add_argument('modulename', nargs='+', help='Valid modulename[s]')

    p_what = sub_p.add_parser('whatis', help='Display short help for module[s]')
    p_what.add_argument('modulename', nargs='*', help='Valid modulename[s]')

    args = p.parse_args(argv)

    shell = Shell(args.shell)
    if args.subparser == 'avail':
        return shell.display_modules('available', terse=args.t)

    if args.subparser == 'list':
        return shell.display_modules('loaded', terse=args.t)

    if args.subparser == 'load':
        for modulename in args.modulename:
            shell.load_module_by_name('load', modulename)
        sys.stdout.write(shell.dump())
        return 0

    if args.subparser == 'unload':
        for modulename in args.modulename:
            shell.load_module_by_name('unload', modulename)
        sys.stdout.write(shell.dump())
        return 0

    if args.subparser == 'purge':
        module_purge(shell)
        sys.stdout.write(shell.dump())
        return 0


if __name__ == '__main__':
    sys.exit(main())

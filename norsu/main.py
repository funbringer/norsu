import argparse
import sys

import norsu.commands as commands

from norsu import __version__
from norsu.exceptions import LogicError, ProcessError
from norsu.terminal import Style

from norsu.args import (
    ShlexSplitAction,
    split_args_extra,
)

from norsu.utils import (
    eprint,
    limit_lines,
)


def main():
    # split args using '--'
    args, extra = split_args_extra(sys.argv)

    app = args[0]
    examples = f"""
examples:
    {app} install  9.6.5  10  master
    {app} pgxs     9.6   9.5  --  install -j4
    {app} pull     REL_10_STABLE
    {app} remove   9.5
    {app} status
    """

    # Hint for all TARGET args
    known_targets = commands.known_targets()

    parser = argparse.ArgumentParser(
        description=f'PostgreSQL builds manager v{__version__}',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples)

    parser.set_defaults(func=None)

    subparsers = parser.add_subparsers(title='commands', dest='command')

    # norsu install
    p_install = subparsers.add_parser(
        'install', description='build & install a list of versions')
    p_install.add_argument('target', nargs='*')
    p_install.add_argument('--configure',
                           action=ShlexSplitAction,
                           help='options for ./configure')
    p_install.add_argument('--extensions',
                           nargs='*',
                           help='also install listed exceptions')
    p_install.add_argument('-E',
                           '--no-update',
                           action='store_true',
                           help='do not pull and install updates')
    p_install.set_defaults(func=commands.cmd_install)

    # norsu remove
    p_remove = subparsers.add_parser('remove',
                                     description='remove specified builds')
    p_remove.add_argument('target', nargs='*')
    p_remove.add_argument('--force',
                          action='store_true',
                          help='force remove, even if no target')
    p_remove.set_defaults(func=commands.cmd_instance)

    # norsu status
    p_status = subparsers.add_parser(
        'status', description='show some info for each build installed')
    p_status.add_argument('target', nargs='*')
    p_status.set_defaults(func=commands.cmd_instance)

    # norsu pull
    p_pull = subparsers.add_parser(
        'pull', description='pull latest changes from git repos')
    p_pull.add_argument('target', nargs='*')
    p_pull.set_defaults(func=commands.cmd_instance)

    # norsu search
    p_search = subparsers.add_parser(
        'search', description='find matching branches in git repos')
    p_search.add_argument('target', nargs='*')
    p_search.set_defaults(func=commands.cmd_search)

    # norsu purge
    p_purge = subparsers.add_parser(
        'purge', description='remove orphaned cloned git repos')
    p_purge.add_argument('target', nargs='*')
    p_purge.set_defaults(func=commands.cmd_purge)

    # norsu pgxs
    p_pgxs = subparsers.add_parser(
        'pgxs', description='run "make USE_PGXS=1 ..." in current dir')
    p_pgxs.add_argument('target', nargs='*')
    p_pgxs.add_argument('-R',
                        '--run-pg',
                        action='store_true',
                        help='run temp instance')
    p_pgxs.add_argument('--run-pg-port',
                        type=int,
                        help='port to be used for temp instance')
    p_pgxs.set_defaults(func=commands.cmd_pgxs)

    # norsu run
    p_run = subparsers.add_parser(
        'run', description='run a temp instance of PostgreSQL')
    p_run.add_argument('target', choices=known_targets)
    p_run.add_argument('--config',
                       nargs='*',
                       help='additional config files for PostgreSQL')
    p_run.add_argument('--psql',
                       action='store_true',
                       help='[DEPRECATED] run PSQL after PG has started')
    p_run.add_argument('-i',
                       '--interactive',
                       action='store',
                       const='psql',
                       metavar='CLI',
                       nargs='?',
                       help='start an interactive CLI connected to a DB')
    p_run.add_argument('--pgxs',
                       action='store_true',
                       help='grab PGXS config as well')
    p_run.add_argument('--dbname',
                       default='postgres',
                       help='database name for PSQL')
    p_run.add_argument('--port',
                       type=int,
                       help='port to be used for this instance')
    p_run.add_argument('--dump',
                       metavar='FILENAME',
                       type=str,
                       help='dump a DB to a file before shutdown')
    p_run.add_argument('--restore',
                       metavar='FILENAME',
                       type=str,
                       help='restore a DB from a file')
    p_run.set_defaults(func=commands.cmd_run)

    # norsu path
    p_path = subparsers.add_parser(
        'path', description='show paths to a specific build')
    p_path.add_argument('target', nargs='*')
    p_path.set_defaults(func=commands.cmd_path)

    try:
        parsed_args = parser.parse_args(args[1:])
        command = parsed_args.func

        if command:
            # execute a suitable command
            command(parsed_args, extra)
        else:
            parser.print_help()

    except KeyboardInterrupt:
        pass

    except LogicError as e:
        eprint(Style.red(str(e)))
        sys.exit(1)

    except ProcessError as e:
        eprint(Style.red(str(e)))
        if e.stderr:
            eprint('LOG:\n\n<... skipped lines ...>')
            eprint(limit_lines(e.stderr, 8))
        sys.exit(1)

    # XXX: We deliberately don't catch Exception,
    # since it might point to application's bugs
    except Exception:
        raise

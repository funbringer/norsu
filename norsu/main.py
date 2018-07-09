import argparse
import os
import sys
import subprocess

from shutil import rmtree
from time import sleep

from . import __version__
from .argparse_actions import ShlexSplitAction
from .config import NORSU_DIR, WORK_DIR, CONFIG
from .exceptions import Error
from .extension import Extension
from .git import find_relevant_refs
from .terminal import Style
from .utils import partition, give_terminal_to

from .instance import \
    Instance, \
    InstanceName, \
    sort_refs, \
    run_temp


def preprocess_targets(raw_targets, dir=NORSU_DIR):
    entries_pos, entries_neg = partition(lambda x: x.startswith('^'), raw_targets)

    entries_neg = set((e[1:] for e in entries_neg))  # remove '^'
    entries_pos = set(entries_pos)

    if not entries_pos or entries_neg:
        entries_pos = set([
            e for e in os.listdir(dir)
            if not e.startswith('.')
        ])

    entries = []
    for e in sorted(entries_pos - entries_neg):
        name, _, query = e.partition(':')
        entries.append(InstanceName(name=name, query=query))

    return entries


def split_make_args(args):
    entries, options = partition(lambda x: x.startswith('-'), args)

    entries = list(entries)
    options = list(options)

    return (entries, options)


def split_args_extra(args):
    """
    Separate main args from auxiliary ones.
    """

    try:
        i = args.index('--')
        return (args[:i], args[i + 1:])
    except ValueError:
        return (args, [])


def cmd_install(args, _):
    for target in preprocess_targets(args.target):
        print('Selected instance:', Style.bold(target))

        Instance(target).install(configure=args.configure,
                                 extensions=args.extensions)

        print()  # splitter


def cmd_instance(args, _):
    cmd = args.command

    # safety pin (see config)
    if not args.target and cmd == 'remove' and \
       CONFIG['commands']['remove']['require_args']:
        raise Error('By default, this command requires arguments')

    for target in preprocess_targets(args.target):
        print('Selected instance:', Style.bold(target))

        instance = Instance(target)

        cmds = {
            'remove': lambda: instance.remove(),
            'status': lambda: instance.status(),
            'pull': lambda: instance.pull(),
        }

        # execute command
        cmds[cmd]()

        print()  # splitter


def cmd_run(args, _):
    instance = Instance(args.target)
    port = args.port
    dbname = args.dbname

    with run_temp(instance, grab_pgxs=args.pgxs, port=port) as node:
        print('dir:', node.base_dir)
        print('port:', node.port)

        if args.psql:
            print('dbname:', dbname)
            print()

            args = [
                instance.get_bin_path('psql'),
                '-p', str(node.port),
                '-d', dbname,
            ]
            p = subprocess.Popen(args, preexec_fn=os.setpgrp)
            give_terminal_to(p.pid)  # give PTS control to psql
            p.wait()                 # wait for psql to finish
        else:
            print()
            print('Press Ctrl+C to exit')
            while True:
                sleep(1)


def cmd_search(args, _):
    for target in preprocess_targets(args.target):
        print('Search query:', Style.bold(target.query),
              '({})'.format(target.type.name))

        patterns = target.to_patterns()
        refs = find_relevant_refs(CONFIG['repos']['urls'], patterns)

        for ref in sort_refs(refs, target):
            print('\t', ref.name)

        print()  # splitter


def cmd_purge(args, _):
    for target in preprocess_targets(args.target, WORK_DIR):
        instance = Instance(target)
        if not os.path.exists(instance.main_dir):
            rmtree(path=instance.work_dir, ignore_errors=True)


def cmd_pgxs(main_args, make_args):
    make_targets, make_opts = split_make_args(make_args)
    work_dir = os.getcwd()

    for pg in preprocess_targets(main_args.target):
        instance = Instance(pg)
        pg_config = instance.get_bin_path('pg_config')
        extension = Extension(work_dir=work_dir, pg_config=pg_config)

        if os.path.exists(pg_config):
            print('Executing against instance', Style.bold(pg), '\n')
        else:
            print(Style.yellow('Cannot find instance {}\n'.format(pg)))
            continue

        # should we start PostgreSQL?
        if main_args.run_pg:
            mk_var = 'EXTRA_REGRESS_OPTS'
            port = main_args.run_pg_port

            # run commands under a running PostgreSQL instance
            with run_temp(instance, grab_pgxs=True, port=port) as node:
                # make pg_regress aware of non-default port
                make_opts.append('{}+=--port={}'.format(mk_var, node.port))
                extension.make(targets=make_targets, options=make_opts)
        else:
            extension.make(targets=make_targets, options=make_opts)

        print()  # splitter


def cmd_path(args, _):
    for target in preprocess_targets(args.target):
        print(Instance(target).main_dir)


def main():
    # split args using '--'
    args, extra = split_args_extra(sys.argv)

    examples = """
examples:
    {0} install  9.6.5  10  master
    {0} pgxs     9.6   9.5  --  install -j4
    {0} pull     REL_10_STABLE
    {0} remove   9.5
    {0} status
    """.format(os.path.basename(args[0]))

    parser = argparse.ArgumentParser(
        description='PostgreSQL builds manager v{}'.format(__version__),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples)

    parser.set_defaults(func=None)

    subparsers = parser.add_subparsers(title='commands', dest='command')

    p_install = subparsers.add_parser('install', help='build & install a list of versions')
    p_install.add_argument('target', nargs='*')
    p_install.add_argument('--configure', action=ShlexSplitAction)
    p_install.add_argument('--extensions', nargs='*')
    p_install.set_defaults(func=cmd_install)

    p_remove = subparsers.add_parser('remove', help='remove specified builds')
    p_remove.add_argument('target', nargs='*')
    p_remove.set_defaults(func=cmd_instance)

    p_status = subparsers.add_parser('status', help='show some info for each build installed')
    p_status.add_argument('target', nargs='*')
    p_status.set_defaults(func=cmd_instance)

    p_pull = subparsers.add_parser('pull', help='pull latest changes from git repos')
    p_pull.add_argument('target', nargs='*')
    p_pull.set_defaults(func=cmd_instance)

    p_search = subparsers.add_parser('search', help='find matching branches in git repos')
    p_search.add_argument('target', nargs='*')
    p_search.set_defaults(func=cmd_search)

    p_purge = subparsers.add_parser('purge')
    p_purge.add_argument('target', nargs='*', help='remove orphaned cloned repos')
    p_purge.set_defaults(func=cmd_purge)

    p_pgxs = subparsers.add_parser('pgxs', help='run "make USE_PGXS=1 ..." in current dir')
    p_pgxs.add_argument('target', nargs='*')
    p_pgxs.add_argument('-R', '--run-pg', action='store_true', help='run temp instance')
    p_pgxs.add_argument('--run-pg-port', type=int, help='port to be used for temp instance')
    p_pgxs.set_defaults(func=cmd_pgxs)

    p_run = subparsers.add_parser('run', help='run a temp instance of PostgreSQL')
    p_run.add_argument('target')
    p_run.add_argument('--psql', action='store_true', help='run PSQL after PG has started')
    p_run.add_argument('--pgxs', action='store_true', help='grab PGXS config as well')
    p_run.add_argument('--dbname', default='postgres', help='database name for PSQL')
    p_run.add_argument('--port', type=int, help='port to be used for this instance')
    p_run.set_defaults(func=cmd_run)

    p_path = subparsers.add_parser('path', help='show paths to the specified builds')
    p_path.add_argument('target', nargs='*')
    p_path.set_defaults(func=cmd_path)

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
    except Error as e:
        print(Style.red(str(e)))
        exit(1)

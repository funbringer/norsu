import argparse
import os
import sys
import subprocess

from shutil import rmtree

from . import __version__
from .argparse_actions import ShlexSplitAction
from .config import NORSU_DIR, WORK_DIR, CONFIG
from .exceptions import Error
from .extension import Extension
from .git import find_relevant_refs
from .terminal import Style

from .instance import (
    Instance,
    InstanceName,
    sort_refs,
    run_temp,
)

from .utils import (
    eprint,
    give_terminal_to,
    limit_lines,
    partition,
    str_args_to_dict,
)


def known_targets(directory=NORSU_DIR):
    return {
        e for e in os.listdir(directory)
        if not e.startswith('.')
    }


def preprocess_targets(raw_targets, directory=NORSU_DIR):
    entries_pos, entries_neg = partition(lambda x: x.startswith('^'), raw_targets)

    entries_neg = set((e[1:] for e in entries_neg))  # remove '^'
    entries_pos = set(entries_pos)

    if not entries_pos or entries_neg:
        entries_pos = known_targets(directory=directory)

    entries = []
    for e in sorted(entries_pos - entries_neg):
        name, _, query = e.partition(':')
        entries.append(InstanceName(name=name, query=query))

    return entries


def split_make_args(args):
    entries, options = partition(lambda x: x.startswith('-'), args)

    entries = list(entries)
    options = list(options)

    return entries, options


def split_args_extra(args):
    """
    Separate main args from auxiliary ones.
    """

    try:
        i = args.index('--')
        return args[:i], args[i + 1:]
    except ValueError:
        return args, []


def cmd_install(args, _):
    for target in preprocess_targets(args.target):
        print('Selected instance:', Style.bold(target))

        Instance(target).install(configure=args.configure,
                                 extensions=args.extensions,
                                 update=not args.no_update)

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


def cmd_run(main_args, psql_args):
    instance = Instance(main_args.target)
    dbname = main_args.dbname
    port = main_args.port

    dump_file = main_args.dump
    restore_file = main_args.restore

    work_dir = os.getcwd()
    pg_config = instance.get_bin_path('pg_config')

    config_files = []

    # Grab extra extension options
    if main_args.pgxs:
        extension = Extension(work_dir=work_dir, pg_config=pg_config)

        mk_var = 'EXTRA_REGRESS_OPTS'
        regress_opts = str_args_to_dict(extension.makefile_var(mk_var))
        config_files.append(regress_opts.get('--temp-config'))

    # Grab extra PG config files
    if main_args.config:
        config_files.extend(main_args.config)

    with run_temp(instance, config_files=config_files, port=port) as node:
        if restore_file:
            node.restore(restore_file, dbname=dbname)
            print('Restored from', Style.bold(restore_file))

        if main_args.psql:
            cmd = [
                instance.get_bin_path('psql'),
                '-p', str(node.port),
                '-d', dbname,
                *psql_args
            ]

        else:
            print('Press Ctrl+C to exit', file=sys.stderr)
            cmd = [
                'sleep',
                'infinity'
            ]

        # XXX: to avoid undesirable PG shutdown (signal),
        # run cmd within its own process group
        p = subprocess.Popen(cmd, preexec_fn=os.setpgrp)

        # give PTS control to cmd and wait for it to finish
        give_terminal_to(p.pid)
        p.wait()

        if dump_file:
            filename = node.dump(filename=dump_file, dbname=dbname)
            print('Dump has been saved to', Style.bold(filename))

        sys.exit(p.returncode)


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
            port = main_args.run_pg_port

            mk_var = 'EXTRA_REGRESS_OPTS'
            regress_opts = str_args_to_dict(extension.makefile_var(mk_var))
            config_files = [regress_opts.get('--temp-config')]

            # run commands under a running PostgreSQL instance
            with run_temp(instance, config_files=config_files, port=port) as node:
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

    p_install = subparsers.add_parser('install', description='build & install a list of versions')
    p_install.add_argument('target', nargs='*')
    p_install.add_argument('--configure', action=ShlexSplitAction, help='options for ./configure')
    p_install.add_argument('--extensions', nargs='*', help='also install listed exceptions')
    p_install.add_argument('--no-update', '-E', action='store_true', help='do not pull and install updates')
    p_install.set_defaults(func=cmd_install)

    p_remove = subparsers.add_parser('remove', description='remove specified builds')
    p_remove.add_argument('target', nargs='*')
    p_remove.set_defaults(func=cmd_instance)

    p_status = subparsers.add_parser('status', description='show some info for each build installed')
    p_status.add_argument('target', nargs='*')
    p_status.set_defaults(func=cmd_instance)

    p_pull = subparsers.add_parser('pull', description='pull latest changes from git repos')
    p_pull.add_argument('target', nargs='*')
    p_pull.set_defaults(func=cmd_instance)

    p_search = subparsers.add_parser('search', description='find matching branches in git repos')
    p_search.add_argument('target', nargs='*')
    p_search.set_defaults(func=cmd_search)

    p_purge = subparsers.add_parser('purge', description='remove orphaned cloned repos')
    p_purge.add_argument('target', nargs='*')
    p_purge.set_defaults(func=cmd_purge)

    p_pgxs = subparsers.add_parser('pgxs', description='run "make USE_PGXS=1 ..." in current dir')
    p_pgxs.add_argument('target', nargs='*')
    p_pgxs.add_argument('-R', '--run-pg', action='store_true', help='run temp instance')
    p_pgxs.add_argument('--run-pg-port', type=int, help='port to be used for temp instance')
    p_pgxs.set_defaults(func=cmd_pgxs)

    p_run = subparsers.add_parser('run', description='run a temp instance of PostgreSQL')
    p_run.add_argument('target', choices=known_targets())
    p_run.add_argument('--config', nargs='*', help='additional config files for PostgreSQL')
    p_run.add_argument('--psql', action='store_true', help='run PSQL after PG has started')
    p_run.add_argument('--pgxs', action='store_true', help='grab PGXS config as well')
    p_run.add_argument('--dbname', default='postgres', help='database name for PSQL')
    p_run.add_argument('--port', type=int, help='port to be used for this instance')
    p_run.add_argument('--dump', metavar='FILENAME', type=str, help='save dump to file before shutdown')
    p_run.add_argument('--restore', metavar='FILENAME', type=str, help='restore from dump file')
    p_run.set_defaults(func=cmd_run)

    p_path = subparsers.add_parser('path', description='show paths to the specified builds')
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
        eprint(Style.red(str(e)))
        if e.stderr:
            eprint('LOG:\n\n<... skipped lines ...>')
            eprint(limit_lines(e.stderr, 8))
        sys.exit(1)

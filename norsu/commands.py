import os
import subprocess
import sys

from shutil import rmtree

from norsu.extension import Extension
from norsu.git import find_relevant_refs

from norsu.config import (
    NORSU_DIR,
    WORK_DIR,
    CONFIG,
)

from norsu.instance import (
    Instance,
    InstanceName,
    sort_refs,
    run_temp,
)

from norsu.terminal import (
    Style,
    give_terminal_to,
)

from norsu.utils import (
    partition,
    str_args_to_dict,
)


def known_targets(directory=NORSU_DIR):
    return {e for e in os.listdir(directory) if not e.startswith('.')}


def preprocess_targets(raw_targets, directory=NORSU_DIR):
    entries_pos, entries_neg = partition(lambda x: x.startswith('^'),
                                         raw_targets)

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


def cmd_install(args, _):
    for target in preprocess_targets(args.target):
        print('Selected instance:', Style.bold(target))

        Instance(target).install(configure=args.configure,
                                 extensions=args.extensions,
                                 update=not args.no_update)

        print()  # splitter


def cmd_instance(args, _):
    cmd = args.command

    for target in preprocess_targets(args.target):
        print('Selected instance:', Style.bold(target))

        instance = Instance(target)

        cmds = {
            'pull': lambda: instance.pull(),
            'remove': lambda: instance.remove(),
            'status': lambda: instance.status(),
        }

        # execute command
        cmds[cmd]()

        print()  # splitter


def cmd_run(main_args, cli_args):
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

        cli = (main_args.psql and 'psql') or main_args.interactive
        if cli:
            cmd = [
                instance.get_bin_path(cli),
                f'postgres://localhost:{node.port}/{dbname}',
                *cli_args,
            ]
            print(' '.join(cmd))

        else:
            print('Press Ctrl+C to exit', file=sys.stderr)
            cmd = ['sleep', 'infinity']

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
              f'({target.type.name})')

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
            print(Style.yellow(f'Cannot find instance {pg}\n'))
            continue

        # should we start PostgreSQL?
        if main_args.run_pg:
            port = main_args.run_pg_port

            mk_var = 'EXTRA_REGRESS_OPTS'
            regress_opts = str_args_to_dict(extension.makefile_var(mk_var))
            config_files = [regress_opts.get('--temp-config')]

            # run commands under a running PostgreSQL instance
            with run_temp(instance, config_files=config_files,
                          port=port) as node:
                # make pg_regress aware of non-default port
                make_opts.append(f'{mk_var}+=--port={node.port}')
                extension.make(*make_targets, options=make_opts)
        else:
            extension.make(*make_targets, options=make_opts)

        print()  # splitter


def cmd_path(args, _):
    for target in preprocess_targets(args.target):
        print(Instance(target).main_dir)

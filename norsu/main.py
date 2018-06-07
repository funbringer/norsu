import os
import sys

from shutil import rmtree
from testgres import get_new_node

from .config import NORSU_DIR, WORK_DIR, CONFIG
from .exceptions import Error
from .extension import Extension
from .git import find_relevant_refs
from .instance import Instance, InstanceName, sort_refs
from .terminal import Style
from .utils import partition, try_read_file


def extract_instances(args, dir):
    entries, options = extract_entries(args)

    entries_pos, entries_neg = partition(lambda x: x.startswith('^'), entries)

    entries_pos = list(entries_pos)
    entries_neg = [e[1:] for e in entries_neg]  # remove caps

    if not entries_pos:
        entries_pos = sorted([
            e for e in os.listdir(dir)
            if not e.startswith('.')
        ])

    entries = [e for e in entries_pos if e not in entries_neg]

    return (entries, options)


def extract_entries(args):
    entries, options = partition(lambda x: x.startswith('-'), args)

    entries = list(entries)
    options = list(options)

    return (entries, options)


def split_args(args):
    """
    Separate main args from auxiliary ones.
    """

    try:
        i = args.index('--')
        return (args[:i], args[i + 1:])
    except ValueError:
        return (args, [])


def cmd_instance(cmd, args):
    entries, _ = extract_instances(split_args(args)[0], NORSU_DIR)

    # safety pin (see config)
    if not args and cmd == 'remove' and \
       CONFIG['commands']['remove']['require_args']:
        raise Error('By default, this command requires arguments')

    for entry in entries:
        print('Selected instance:', Style.bold(entry))

        instance = Instance(entry)

        cmds = {
            'install': lambda: instance.install(),
            'remove': lambda: instance.remove(),
            'status': lambda: instance.status(),
            'pull': lambda: instance.pull(),
        }

        # execute command
        cmds[cmd]()

        print()


def cmd_search(_, args):
    entries, _ = extract_instances(split_args(args)[0], NORSU_DIR)

    for entry in entries:
        name = InstanceName(entry)
        patterns = name.to_patterns()

        print('Search query:', Style.bold(entry))

        refs = find_relevant_refs(CONFIG['repos']['urls'], patterns)

        for ref in sort_refs(refs, name):
            print('\t', ref.name)

        print()


def cmd_purge(_, args):
    entries, _ = extract_instances(split_args(args)[0], WORK_DIR)

    for entry in entries:
        instance = Instance(entry)

        if not os.path.exists(instance.main_dir):
            rmtree(path=instance.work_dir, ignore_errors=True)


def cmd_pgxs(_, args):
    main_args, make_args = split_args(args)

    pgs, cmd_opts = extract_instances(main_args, NORSU_DIR)
    targets, make_opts = extract_entries(make_args)
    work_dir = os.getcwd()

    # extension we're going to build
    extension = Extension(work_dir=work_dir)

    for pg in pgs:
        instance = Instance(pg)
        pg_config = instance.get_bin_path('pg_config')

        if instance.installed_commit_hash:
            print('Executing against instance', Style.bold(pg), '\n')
        else:
            print(Style.yellow('Cannot find instance {}\n'.format(pg)))
            continue

        # should we start PostgreSQL?
        if any(k in cmd_opts for k in ['-R', '--run-pg']):
            regress_opts = extension.extra_regress_opts(pg_config)
            temp_conf_file = regress_opts.get('--temp-config')
            temp_conf = ''

            # read additional config
            if temp_conf_file:
                path = os.path.join(work_dir, temp_conf_file)
                temp_conf = try_read_file(path)
                print('Found custom config:', os.path.basename(path))

            # run commands under a running PostgreSQL instance
            with get_new_node(port=5432) as node:
                print('Starting temporary PostgreSQL instance...\n')
                os.environ['PG_CONFIG'] = pg_config
                node.cleanup_on_bad_exit = True
                node.init().append_conf(line=temp_conf).start()

                extension.make(pg_config, targets, make_opts)
        else:
            extension.make(pg_config, targets, make_opts)

        print()  # splitter


def cmd_path(_, args):
    entries, _ = extract_instances(split_args(args)[0], NORSU_DIR)

    for entry in entries:
        print(Instance(entry).main_dir)


def cmd_help(*_):
    name = os.path.basename(sys.argv[0])
    print('{} -- PostgreSQL builds manager'.format(Style.blue(name)))
    print()
    print('Usage:')
    print('\t{} <command> [options]'.format(name))
    print()
    print('Commands:')

    for method in METHODS.keys():
        print('\t{}'.format(method))

    print()
    print('Examples:')
    print('\t{} install 9.6.5 10 master'.format(name))
    print('\t{} pgxs 9.6 9.5 -- install'.format(name))
    print('\t{} pull REL_10_STABLE'.format(name))
    print('\t{} remove 9.5'.format(name))
    print('\t{} status'.format(name))


def main():
    args = sys.argv[1:]
    if len(args) == 0:
        args = ['install']

    command = args[0]
    method = METHODS.get(command)

    try:
        if method is None:
            raise Error('Unknown command {}'.format(command))
        method(command, args[1:])
    except KeyboardInterrupt:
        pass
    except Error as e:
        print(Style.red(str(e)))
        exit(1)


METHODS = {
    'install': cmd_instance,
    'remove': cmd_instance,
    'status': cmd_instance,
    'search': cmd_search,
    'pull': cmd_instance,
    'purge': cmd_purge,
    'pgxs': cmd_pgxs,
    'path': cmd_path,
    'help': cmd_help,
}

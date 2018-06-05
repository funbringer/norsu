import os
import sys

from shutil import rmtree
from subprocess import check_call

from .config import NORSU_DIR, WORK_DIR, CONFIG
from .exceptions import Error
from .git import find_relevant_refs
from .instance import Instance, InstanceName, sort_refs
from .terminal import Style
from .utils import partition


def extract_entries(args, dir=None):
    entries, options = partition(lambda x: x.startswith('-'), args)

    entries = list(entries)
    options = list(options)

    if not entries and dir:
        entries = sorted([
            e for e in os.listdir(dir)
            if not e.startswith('.')
        ])

    return (entries, options)


def split_args(args):
    """
    Separate main args from auxiliary ones.
    """

    try:
        i = args.index('--')
        return (args[:i], args[i + 1:])
    except ValueError:
        return (args, None)


def cmd_instance(cmd, args):
    entries, _ = extract_entries(split_args(args)[0], NORSU_DIR)

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
    entries, _ = extract_entries(split_args(args)[0], NORSU_DIR)

    for entry in entries:
        name = InstanceName(entry)
        patterns = name.to_patterns()

        print('Search query:', Style.bold(entry))

        refs = find_relevant_refs(CONFIG['repos']['urls'], patterns)

        for ref in sort_refs(refs, name):
            print('\t', ref.name)

        print()


def cmd_purge(_, args):
    entries, _ = extract_entries(split_args(args)[0], WORK_DIR)

    for entry in entries:
        instance = os.path.join(NORSU_DIR, entry)

        if not os.path.exists(instance):
            path = os.path.join(WORK_DIR, entry)
            rmtree(path=path, ignore_errors=True)


def cmd_pgxs(_, args):
    main_args, make_args = split_args(args)

    pgs, _ = extract_entries(main_args, NORSU_DIR)
    targets, opts = extract_entries(make_args)

    if not targets:
        targets = ['clean', 'install']

    for pg in pgs:
        instance = Instance(pg)

        if instance.installed_commit_hash:
            print('Executing against instance', Style.bold(pg), '\n')
        else:
            print(Style.yellow('Cannot find instance {}\n'.format(pg)))
            continue

        pg_config = os.path.join(instance.main_dir, 'bin', 'pg_config')

        for target in targets:
            print(Style.green('$ make {} {}').format(target, ' '.join(opts)))

            args = [
                'make',
                'USE_PGXS=1',
                'PG_CONFIG={}'.format(pg_config),
                target,
            ] + opts

            # execute make
            check_call(args)
            print()

        print()


def cmd_path(_, args):
    entries, _ = extract_entries(split_args(args)[0], NORSU_DIR)

    for entry in entries:
        print(os.path.join(NORSU_DIR, entry))


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

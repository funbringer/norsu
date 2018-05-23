import os
import sys

from shutil import rmtree

from .config import NORSU_DIR, WORK_DIR, CONFIG
from .exceptions import Error
from .instance import Instance, InstanceName, sort_refs
from .refs import find_relevant_refs
from .terminal import Style


def parse_args(args, dir=NORSU_DIR):
    entries = args

    if not entries:
        entries = (
            e for e in os.listdir(dir)
            if not e.startswith('.')
        )

    # TODO: also return options
    return (sorted(entries), None)


def cmd_instance(cmd, args):
    entries, _ = parse_args(args)

    # safety pin (see config)
    if not args and cmd == 'remove' and \
       CONFIG.commands.remove.require_args:
        raise Error('By default, this command requires arguments')

    for entry in entries:
        print('Selected instance:', Style.bold(entry))

        instance = Instance(entry)

        cmds = {
            'install': lambda: instance.install(),
            'remove': lambda: instance.remove(),
            'status': lambda: instance.status(),
        }

        # execute command
        cmds[cmd]()

        print()


def cmd_search(_, args):
    entries, _ = parse_args(args)

    for entry in entries:
        name = InstanceName(entry)
        patterns = name.to_patterns()

        print('Search query:', Style.bold(entry))

        refs = find_relevant_refs(CONFIG.repos.urls, patterns)

        for ref in sort_refs(refs, name):
            print('\t', ref)

        print()


def cmd_purge(_, args):
    entries, _ = parse_args(args, WORK_DIR)

    for entry in entries:
        instance = os.path.join(NORSU_DIR, entry)

        if not os.path.exists(instance):
            path = os.path.join(WORK_DIR, entry)
            rmtree(path=path, ignore_errors=True)


def cmd_path(_, args):
    entries, _ = parse_args(args, NORSU_DIR)

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
    print('\t{} remove'.format(name))


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
    'purge': cmd_purge,
    'path': cmd_path,
    'help': cmd_help,
}

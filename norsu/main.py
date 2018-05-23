import os
import sys

from shutil import rmtree

from .config import NORSU_DIR, WORK_DIR
from .exceptions import Error
from .instance import Instance
from .terminal import Style


def cmd_instance(cmd, entries):
    if not entries:
        entries = (
            e for e in os.listdir(NORSU_DIR)
            if not e.startswith('.')
        )

    for entry in sorted(entries):
        print('Selected instance:', Style.bold(entry))

        instance = Instance(entry)

        cmds = {
            'install': lambda: instance.install(),
            'remove': lambda: instance.remove(),
        }

        # execute command
        cmds[cmd]()

        print()


def cmd_purge(_, entries):
    if not entries:
        entries = (
            e for e in os.listdir(WORK_DIR)
            if not e.startswith('.')
        )

    for entry in sorted(entries):
        instance = os.path.join(NORSU_DIR, entry)

        if not os.path.exists(instance):
            path = os.path.join(WORK_DIR, entry)
            rmtree(path=path, ignore_errors=True)


def cmd_path(_, entries):
    if not entries:
        entries = (
            e for e in os.listdir(NORSU_DIR)
            if not e.startswith('.')
        )

    for entry in sorted(entries):
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
    'purge': cmd_purge,
    'path': cmd_path,
    'help': cmd_help,
}

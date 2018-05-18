import os
import sys


# select default dir
HOME = os.environ['HOME']
NORSU_DIR = os.environ.get('NORSU_PATH') or os.path.join(HOME, 'pg')
WORK_DIR = os.path.join(NORSU_DIR, '.norsu')


def cmd_install(entries):
    print("hi")


def cmd_remove(entries):
    pass


def cmd_purge(entries):
    pass


def cmd_help(_):
    pass


def main():
    commands = {
        'install': cmd_install,
        'remove': cmd_remove,
        'purge': cmd_purge,
        'help': cmd_help,
    }

    # extract main command
    args = sys.argv[1:]
    if len(args) == 0:
        args = ['install']

    # pass remaining args to command handler
    commands[args[0]](args[1:])


if __name__ == '__main__':
    main()

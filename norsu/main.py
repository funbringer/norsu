import os
import sys


# select default dir
HOME = os.environ['HOME']
NORSU_DIR = os.environ.get('NORSU_PATH') or os.path.join(HOME, 'pg')
WORK_DIR = os.path.join(NORSU_DIR, '.norsu')

GIT_REPOS = [
    'git://git.postgresql.org/git/postgresql.git',
]


class Style:
    def style(color, text):
        return '\033[{}m{}\033[0m'.format(color, text)

    def bold(text): return Style.style(1, text)

    def red(text): return Style.style(31, text)

    def green(text): return Style.style(32, text)

    def yellow(text): return Style.style(33, text)


def step(*args):
    print(Style.green('\t=>'), *args)


class Instance:
    def __init__(self, name):
        self.name = name
        self.main_dir = os.path.join(NORSU_DIR, name)
        self.work_dir = os.path.join(WORK_DIR, name)

    @property
    def ignored(self):
        ignore_file = os.path.join(self.main_dir, '.norsu_ignore')
        return os.path.exists(ignore_file)

    def install(self):
        if not self.ignored:
            self._prepare_work_dir()
            self._configure_project()
            self._make_install()
        else:
            step(Style.yellow('Ignored due to .norsu_ignore'))

    def _prepare_work_dir(self):
        if not os.path.exists(self.work_dir):
            step('No work dir, choosing the branch')

            for repo in GIT_REPOS:
                pass

    def _configure_project(self):
        pass

    def _make_install(self):
        pass


def cmd_install(entries):
    if not entries:
        entries = (
            e for e in os.listdir(NORSU_DIR)
            if not e.startswith('.')
        )

    for entry in entries:
        print('Installing instance of PostgreSQL', Style.bold(entry))

        instance = Instance(entry)
        instance.install()

        print()


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

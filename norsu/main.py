import os
import sys
import subprocess

from enum import Enum
from functools import total_ordering
from shutil import rmtree


# select default dir
HOME = os.environ['HOME']
NORSU_DIR = os.environ.get('NORSU_PATH') or os.path.join(HOME, 'pg')
WORK_DIR = os.path.join(NORSU_DIR, '.norsu')

GIT_REPOS = [
    'git://git.postgresql.org/git/postgresql.git',
]


def step(*args):
    print(Style.green('\t=>'), *args)


class Error(Exception):
    pass


class Style:
    def style(color, text):
        return '\033[{}m{}\033[0m'.format(color, text)

    def bold(text): return Style.style(1, text)

    def red(text): return Style.style(31, text)

    def green(text): return Style.style(32, text)

    def blue(text): return Style.style(94, text)

    def yellow(text): return Style.style(33, text)


@total_ordering
class GitRefVer:
    def __init__(self, ref):
        ref_original = ref

        # use lowercase for substr search
        ref = ref_original.lower()

        # extract numbers from ref
        ver = ''.join((c for c in ref if c.isdigit() or c == '_'))
        ver = (n for n in ver.split('_') if n)
        ver = list(map(lambda n: int(n), ver))

        types = [
            ('stable', float('+inf')),
            ('rc', -1),
            ('beta', -2),
            ('alpha', -3),
        ]

        for t, num in types:
            if t in ref:
                # example:
                #  REL_10_RC1 => (10, -1, 1)
                #  REL_9_6_STABLE => (9, 6, 'inf')
                _, _, s = ref.rpartition(t)
                if s.isdigit():
                    ver.pop()  # see ver extraction
                    ver.append(num)
                    ver.append(int(s))
                else:
                    ver.append(num)

        self.ref = ref_original
        self.ver = ver

    def __eq__(self, other):
        return self.ver == other.ver

    def __lt__(self, other):
        return self.ver < other.ver

    def __str__(self):
        return self.ref


class InstanceNameType(Enum):
    Version = 1
    Branch = 2


class InstanceName:
    def __init__(self, name):
        self.name = name

        if name.replace('.', '').replace('_', '').isdigit():
            self.type = InstanceNameType.Version
        else:
            self.type = InstanceNameType.Branch

    def to_patterns(self):
        fmt = '*{0}*'
        pattern = self.name

        if self.type == InstanceNameType.Version:
            pattern = pattern.replace('.', '_')

        return [fmt.format(pattern)]

    def __str__(self):
        return self.name


class Instance:
    def __init__(self, name):
        self.name = InstanceName(name)
        self.main_dir = os.path.join(NORSU_DIR, name)
        self.work_dir = os.path.join(WORK_DIR, name)

    @property
    def ignore(self):
        ignore_file = os.path.join(self.main_dir, '.norsu_ignore')
        return os.path.exists(ignore_file)

    def install(self):
        if not self.ignore:
            try:
                self._prepare_work_dir()
                self._configure_project()
                self._make_install()
                step('Done')
            except Error as e:
                step(Style.red(str(e)))
        else:
            step(Style.yellow('Ignored due to .norsu_ignore'))

    def remove(self):
        rmtree(path=self.main_dir, ignore_errors=True)
        rmtree(path=self.work_dir, ignore_errors=True)
        step('Removed all relevant directories')

    def _prepare_work_dir(self):
        if not os.path.exists(self.work_dir):
            def to_key(x):
                return GitRefVer(x)

            step('No work dir, choosing the branch')

            patterns = self.name.to_patterns()

            for repo in GIT_REPOS:
                args = ['git', 'ls-remote', '--heads', '--tags', repo]
                args += patterns  # search patterns

                p = subprocess.Popen(args,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL)

                out, _ = p.communicate()

                if p.returncode != 0:
                    raise Error('git ls-remote failed')

                # list of matching branches and tags
                refs = [
                    os.path.basename(r.split()[-1])
                    for r in out.decode('utf8').splitlines()
                ]

                if not refs:
                    continue

                # select the most relevant branch
                ref = sorted(refs, reverse=True, key=to_key)[0]
                step('Selected branch {}'.format(Style.bold(ref)))

                args = [
                    'git',
                    'clone',
                    '--branch', str(ref),
                    '--depth', str(1),
                    repo,
                    self.work_dir,
                ]

                p = subprocess.Popen(args,
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.STDOUT)
                p.wait()

                if p.returncode != 0:
                    raise Error('git clone failed')

                step('Cloned git repo to work dir')

                # success
                return

            # no suitable branch found
            raise Error('No branch found for {}'.format(self.name))

    def _configure_project(self):
        makefile = os.path.join(self.work_dir, 'GNUmakefile')
        if not os.path.exists(makefile):
            args = [
                './configure',
                'CFLAGS=-g3',
                '--enable-cassert',
                '--prefix={}'.format(self.main_dir)
            ]

            p = subprocess.Popen(args,
                                 cwd=self.work_dir,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.STDOUT)
            p.wait()

            if p.returncode != 0:
                raise Error('configure failed')

            step('Configured sources')

    def _make_install(self):
        postgres = os.path.join(self.main_dir, 'bin', 'postgres')
        if not os.path.exists(postgres):
            for args in [['make', '-j4'], ['make', 'install']]:
                p = subprocess.Popen(args,
                                     cwd=self.work_dir,
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.STDOUT)
                p.wait()

                if p.returncode != 0:
                    raise Error('{} failed'.format(' '.join(args)))

            step('Built and installed to', Style.blue(self.main_dir))


def cmd_instance(cmd, entries):
    if not entries:
        entries = (
            e for e in os.listdir(NORSU_DIR)
            if not e.startswith('.')
        )

    for entry in entries:
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

    for entry in entries:
        instance = os.path.join(NORSU_DIR, entry)

        if not os.path.exists(instance):
            path = os.path.join(WORK_DIR, entry)
            rmtree(path=path, ignore_errors=True)


def cmd_help(*_):
    name = os.path.basename(sys.argv[0])
    print('{} -- PostgreSQL builds manager'.format(Style.blue(name)))
    print()
    print('Usage:')
    print('\t{} <command> [options]'.format(name))
    print()
    print('Commands:')
    print()

    for method in METHODS.keys():
        print('\t{}'.format(method))

    print()
    print('Examples:')
    print('\t{} install 9.6 10'.format(name))
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
    'help': cmd_help,
}


if __name__ == '__main__':
    main()

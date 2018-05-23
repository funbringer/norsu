import os
import re
import subprocess
import shlex

from enum import Enum
from shutil import rmtree

from .config import NORSU_DIR, WORK_DIR, CONFIG
from .exceptions import Error
from .refs import SortRefByVersion, find_relevant_refs
from .terminal import Style


def step(*args):
    print(Style.green('\t=>'), *args)


class InstanceNameType(Enum):
    Version = 1
    Branch = 2


class InstanceName:
    rx_is_ver = re.compile(r'\d+([._]\d+)*')
    rx_sep = re.compile(r'(\.|_)')

    def __init__(self, name):
        self.name = name

        if self.rx_is_ver.match(name):
            self.type = InstanceNameType.Version
        else:
            self.type = InstanceNameType.Branch

    def to_patterns(self):
        pattern = self.name

        if self.type == InstanceNameType.Version:
            pattern = self.rx_sep.sub(lambda m: '[._]', pattern)

        return ['*{0}*'.format(pattern)]

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

    def _configure_options(self):
        pg_config = os.path.join(self.main_dir, 'bin', 'pg_config')
        norsu_file = os.path.join(self.main_dir, '.norsu_configure')

        if os.path.exists(norsu_file):
            with open(norsu_file, 'r') as f:
                return shlex.split(f.read())

        elif os.path.exists(pg_config):
            args = [pg_config, '--configure']

            p = subprocess.Popen(args,
                                 stdout=subprocess.STDOUT,
                                 stderr=subprocess.DEVNULL)

            out, _ = p.communicate()

            return shlex.split(out.decode('utf8'))

        else:
            return ['CFLAGS=-g3', '--enable-cassert']

    def _prepare_work_dir(self):
        git_repo = os.path.join(self.work_dir, '.git')

        if not os.path.exists(git_repo):
            def to_key(x):
                return SortRefByVersion(x)

            step('No work dir, choosing repo & branch')

            patterns = self.name.to_patterns()
            refs = find_relevant_refs(CONFIG.repos.urls, patterns)

            if not refs:
                raise Error('No branch found for {}'.format(self.name))

            # select the most relevant branch
            ref = sorted(refs, reverse=True, key=to_key)[0]
            step('Selected repo', Style.bold(ref.repo))
            step('Selected branch', Style.bold(ref.name))

            args = [
                'git',
                'clone',
                '--branch', ref.name,
                '--depth', str(1),
                ref.repo,
                self.work_dir,
            ]

            p = subprocess.Popen(args,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.STDOUT)
            p.wait()

            if p.returncode != 0:
                raise Error('git clone failed')

            step('Cloned git repo to work dir')

    def _configure_project(self):
        makefile = os.path.join(self.work_dir, 'GNUmakefile')
        if not os.path.exists(makefile):
            args = [
                './configure',
                '--prefix={}'.format(self.main_dir)
            ] + self._configure_options()

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

import os
import re
import subprocess
import shlex

from enum import Enum
from shutil import rmtree

from .config import NORSU_DIR, WORK_DIR, CONFIG
from .exceptions import Error
from .terminal import Style

from .refs import \
    SortRefByVersion, \
    SortRefBySimilarity, \
    find_relevant_refs


def step(*args):
    print(Style.green('\t=>'), *args)


def line(name, value=None):
    print('\t', name, '\t{}'.format(value) if value else '')


def sort_refs(refs, name):
    # key function for sort
    def to_key(x):
        if name.type == InstanceNameType.Version:
            return SortRefByVersion(x)
        else:
            # pre-calculated for better performance
            name_ngram = SortRefBySimilarity.ngram(name.value)
            return SortRefBySimilarity(x, name_ngram)

    return sorted(refs, reverse=True, key=to_key)


class InstanceNameType(Enum):
    Version = 1
    Branch = 2


class InstanceName:
    rx_is_ver = re.compile(r'\d+([._]\d+)*')
    rx_sep = re.compile(r'(\.|_)')

    def __init__(self, name):
        for s in ['/']:
            if s in name:
                raise Error('Wrong name {}'.format(name))

        self.value = name

        if self.rx_is_ver.match(name):
            self.type = InstanceNameType.Version
        else:
            self.type = InstanceNameType.Branch

    def to_patterns(self):
        pattern = self.value
        result = [pattern]

        if self.type == InstanceNameType.Version:
            # replace version separators with a pattern
            pattern = self.rx_sep.sub(lambda m: '[._]', pattern)

            for fmt in ['REL_{}*', 'REL{}*']:
                result.append(fmt.format(pattern))
        else:
            result.append('*{}*'.format(pattern))

        return result

    def __str__(self):
        return self.value


class Instance:
    def __init__(self, name):
        self.name = InstanceName(name)
        self.main_dir = os.path.join(NORSU_DIR, name)
        self.work_dir = os.path.join(WORK_DIR, name)

    @property
    def ignore(self):
        ignore_file = os.path.join(self.main_dir, '.norsu_ignore')
        return os.path.exists(ignore_file)

    @property
    def branch(self):
        args = ['git', 'symbolic-ref', '--short', 'HEAD']

        if os.path.exists(self.work_dir):
            p = subprocess.Popen(args,
                                 cwd=self.work_dir,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL)

            out, _ = p.communicate()

            if p.returncode == 0:
                return out.decode('utf8').strip()

    def pg_config(self, params=None):
        pg_config = os.path.join(self.main_dir, 'bin', 'pg_config')

        if os.path.exists(pg_config):
            args = [pg_config] + params

            p = subprocess.Popen(args,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL)

            out, _ = p.communicate()

            return out.decode('utf-8')

    def status(self):
        postgres = os.path.join(self.main_dir, 'bin', 'postgres')

        if os.path.exists(postgres):
            status = Style.green('Installed')
        else:
            status = Style.red('Not installed')

        line('Status:', status)

        if os.path.exists(self.main_dir):
            line('Main dir:', self.main_dir)
        else:
            line('Main dir:', 'none')

        if os.path.exists(self.work_dir):
            line('Work dir:', self.work_dir)
            branch = self.branch
            if branch:
                line('Branch:', branch)
        else:
            line('Work dir:', 'none')

        pg_config_out = self.pg_config(['--version'])
        if pg_config_out:
            line('Version:', pg_config_out.strip())

        configure = self._configure_options()
        line('CONFIGURE:', configure)

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
        if os.path.exists(self.main_dir):
            rmtree(path=self.main_dir, ignore_errors=True)
            step('Removed main dir')

        if os.path.exists(self.work_dir):
            rmtree(path=self.work_dir, ignore_errors=True)
            step('Removed work dir')

    def _configure_options(self):
        norsu_file = os.path.join(self.main_dir, '.norsu_configure')

        if os.path.exists(norsu_file):
            with open(norsu_file, 'r') as f:
                return shlex.split(f.read())

        pg_config_out = self.pg_config(['--configure'])
        if pg_config_out:
            options = shlex.split(pg_config_out)
            return [x for x in options if not x.startswith('--prefix')]

        return ['CFLAGS=-g3', '--enable-cassert']

    def _prepare_work_dir(self):
        git_repo = os.path.join(self.work_dir, '.git')

        if not os.path.exists(git_repo):
            step('No work dir, choosing repo & branch')

            patterns = self.name.to_patterns()
            refs = find_relevant_refs(CONFIG.repos.urls, patterns)

            if not refs:
                raise Error('No branch found for {}'.format(self.name))

            # select the most relevant branch
            ref = sort_refs(refs, self.name)[0]
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

import os
import re
import shlex

from enum import Enum
from shutil import rmtree

from .config import NORSU_DIR, WORK_DIR, CONFIG, TOOL_MAKE
from .exceptions import Error
from .terminal import Style
from .utils import execute, ExecOutput

from .git import \
    GitRepo, \
    SortRefByVersion, \
    SortRefBySimilarity, \
    find_relevant_refs


def step(*args):
    print(Style.green('\t=>'), *args)


def line(name, value=None):
    print('\t', name, '\t{}'.format(value) if value is not None else '')


def read_commit_file(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return f.read().strip()


def write_commit_file(path, value):
    with open(path, 'w') as f:
        f.write(value)


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
        self.git = GitRepo(work_dir=self.work_dir)

        # various utility files
        self.configure_file = os.path.join(self.main_dir, '.norsu_configure')
        self.ignore_file = os.path.join(self.main_dir, '.norsu_ignore')

        # store commit hashes (build + install)
        self.installed_commit_file = os.path.join(self.main_dir, '.norsu_build')
        self.built_commit_file = os.path.join(self.work_dir, '.norsu_build')

    @property
    def ignore(self):
        return os.path.exists(self.ignore_file)

    @property
    def actual_commit_hash(self):
        if os.path.exists(self.work_dir):
            return self.git.hash

    @property
    def installed_commit_hash(self):
        return read_commit_file(self.installed_commit_file)

    @installed_commit_hash.setter
    def installed_commit_hash(self, value):
        write_commit_file(self.installed_commit_file, value)

    @property
    def built_commit_hash(self):
        return read_commit_file(self.built_commit_file)

    @built_commit_hash.setter
    def built_commit_hash(self, value):
        write_commit_file(self.built_commit_file, value)

    @property
    def requires_reinstall(self):
        # NOTE: remember that re-build != re-install!
        # We might already have a fresh build in work dir
        return self.installed_commit_hash != self.actual_commit_hash

    @property
    def requires_rebuild(self):
        return self.built_commit_hash != self.actual_commit_hash

    def get_bin_path(self, name):
        return os.path.join(self.main_dir, 'bin', name)

    def pg_config(self, params=None):
        pg_config = self.get_bin_path('pg_config')
        if os.path.exists(pg_config):
            return execute([pg_config] + params)

    def status(self):
        postgres = os.path.join(self.main_dir, 'bin', 'postgres')

        if os.path.exists(postgres):
            if self.requires_reinstall:
                status = Style.yellow('Installed (out of date)')
            else:
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
            branch = self.git.branch or self.git.tag
            if branch:
                line('Branch:', branch)
        else:
            line('Work dir:', 'none')

        pg_config_out = self.pg_config(['--version'])
        if pg_config_out:
            line('Version:', pg_config_out.strip())

        commit = self.installed_commit_hash
        if commit:
            line('Commit:', commit)

        configure = self._configure_options()
        line('CONFIGURE:', configure)

    def pull(self):
        self._prepare_work_dir()

    def install(self):
        if not self.ignore:
            try:
                self._prepare_work_dir()
                self._make_distclean()
                self._configure_project()
                self._make_install()
            except Error as e:
                step(Style.red(str(e)))
        else:
            step(Style.yellow('Ignored due to .norsu_ignore'))

    def remove(self):
        for path, name in [(self.main_dir, 'main'), (self.work_dir, 'work')]:
            if os.path.exists(path):
                rmtree(path=path, ignore_errors=True)
                step('Removed {} dir'.format(name))

    def _configure_options(self):
        if os.path.exists(self.configure_file):
            with open(self.configure_file, 'r') as f:
                return shlex.split(f.read())

        pg_config_out = self.pg_config(['--configure'])
        if pg_config_out:
            options = shlex.split(pg_config_out)
            return [x for x in options if not x.startswith('--prefix')]

        return CONFIG['build']['configure_options']

    def _prepare_work_dir(self):
        git_repo = os.path.join(self.work_dir, '.git')

        if os.path.exists(git_repo):
            branch = self.git.branch

            # pull latest changes
            if branch:
                self.git.pull()

            # should we reinstall PG?
            if self.requires_reinstall:
                fresh_commits = ''

                # show distance between installed and fresh commits
                installed_commit = self.installed_commit_hash
                if installed_commit:
                    commits = self.git.distance(installed_commit, branch)
                    fresh_commits = ' ({} commits)'.format(commits)

                step('Current branch:', Style.bold(branch))
                step('Installed build is out of date{}'.format(fresh_commits))
        else:
            step('No work dir, choosing repo & branch')

            patterns = self.name.to_patterns()
            refs = find_relevant_refs(CONFIG['repos']['urls'], patterns)

            if not refs:
                raise Error('No branch found for {}'.format(self.name))

            # select the most relevant branch
            ref = sort_refs(refs, self.name)[0]
            step('Selected repo', Style.bold(ref.repo))
            step('Selected branch', Style.bold(ref.name))

            # finally, clone repo
            self.git.clone(url=ref.repo, branch=ref.name)
            step('Cloned git repo to work dir')

        # add .norsu* to git excludes
        excludes = os.path.join(self.work_dir, '.git', 'info', 'exclude')
        with open(excludes, 'r+') as f:
            lines = f.readlines()
            if not any('.norsu*' in s for s in lines):
                f.seek(0, os.SEEK_END)
                f.write('.norsu*')

    def _configure_project(self):
        makefile = os.path.join(self.work_dir, 'GNUmakefile')
        if not os.path.exists(makefile):
            args = [
                './configure',
                '--prefix={}'.format(self.main_dir)
            ] + self._configure_options()

            execute(args, cwd=self.work_dir, output=ExecOutput.Devnull)
            step('Configured sources')

    def _make_install(self):
        if self.requires_reinstall:
            # update built commit hash
            self.built_commit_hash = self.actual_commit_hash

            jobs = int(CONFIG['build']['jobs'])
            for arg in ['-j{}'.format(jobs), 'install']:
                args = [TOOL_MAKE, arg]
                execute(args, cwd=self.work_dir, output=ExecOutput.Devnull)

            # update installed commit hash
            self.installed_commit_hash = self.actual_commit_hash

            step('Built and installed')

    def _make_distclean(self):
        makefile = os.path.join(self.work_dir, 'GNUmakefile')
        if os.path.exists(makefile) and self.requires_rebuild:
            args = [TOOL_MAKE, 'distclean']
            execute(args, cwd=self.work_dir, error=False,
                    output=ExecOutput.Devnull)

            step('Prepared work dir for a new build')

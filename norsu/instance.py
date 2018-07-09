import os
import re
import shlex

from contextlib import contextmanager
from enum import Enum
from shutil import rmtree
from testgres import get_new_node, configure_testgres

from .config import NORSU_DIR, WORK_DIR, CONFIG, TOOL_MAKE
from .exceptions import Error
from .extension import Extension
from .terminal import Style

from .git import \
    GitRepo, \
    SortRefByVersion, \
    SortRefBySimilarity, \
    find_relevant_refs

from .utils import \
    execute, \
    ExecOutput, \
    path_exists, \
    try_read_file, \
    str_args_to_dict


def step(*args):
    print(Style.green('\t=>'), *args)


def line(name, value=None):
    print('\t', name, '\t{}'.format(value))


def read_commit_file(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return f.read().strip()


def write_commit_file(path, value):
    with open(path, 'w') as f:
        f.write(value or '')


def sort_refs(refs, name):
    # key function for sort
    def to_key(x):
        if name.type == InstanceNameType.Version:
            return SortRefByVersion(x)
        else:
            # pre-calculated for better performance
            name_ngram = SortRefBySimilarity.ngram(name.query)
            return SortRefBySimilarity(x, name_ngram)

    return sorted(refs, reverse=True, key=to_key)


class InstanceNameType(Enum):
    Version = 1
    Branch = 2


class InstanceName:
    rx_is_ver = re.compile(r'\d+([._]\d+)*')
    rx_sep = re.compile(r'(\.|_)')

    @staticmethod
    def _check_str(s):
        pred1 = len(s.strip()) > 0
        pred2 = any(c.isalnum() for c in s)

        if not (pred1 and pred2):
            raise Error('Wrong identifier: {}'.format(s))

        return s

    def __init__(self, name, query=None):
        self.value = self._check_str(name)
        self.query = self._check_str(query or name)

        if self.rx_is_ver.match(self.query):
            self.type = InstanceNameType.Version
        else:
            self.type = InstanceNameType.Branch

    def to_patterns(self):
        pattern = self.query
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
        if isinstance(name, InstanceName):
            self.name = name
        else:
            self.name = InstanceName(name)

        self.main_dir = os.path.join(NORSU_DIR, str(name))
        self.work_dir = os.path.join(WORK_DIR, str(name))
        self.git = GitRepo(work_dir=self.work_dir)

        # various utility files
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
        ic = self.installed_commit_hash
        ac = self.actual_commit_hash

        return ic != ac or not ic or not ac

    @property
    def requires_rebuild(self):
        bc = self.built_commit_hash
        ac = self.actual_commit_hash

        return bc != ac or not bc or not ac

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
        line('Main dir:', path_exists(self.main_dir))
        line('Work dir:', path_exists(self.work_dir))

        if os.path.exists(self.work_dir):
            branch = self.git.branch or self.git.tag
            if branch:
                line('Branch:', branch)

        pg_config_out = self.pg_config(['--version'])
        if pg_config_out:
            line('Version:', pg_config_out.strip())

        commit = self.installed_commit_hash
        if commit:
            line('Commit:', commit)

        pg_config_manual = os.path.join(self.main_dir,
                                        'include', 'pg_config_manual.h')
        if os.path.exists(pg_config_manual):
            with open(pg_config_manual, 'r') as f:
                for l in f:
                    if l.startswith('#define MEMORY_CONTEXT_CHECKING'):
                        break  # too late
                    if l.startswith('#define USE_VALGRIND'):
                        line('Valgrind:', 'Enabled')
                        break  # OK

        configure = self._configure_options()
        line('CONFIGURE:', configure)

    def pull(self):
        self._maybe_git_clone_or_pull()

    def install(self, configure=None, extensions=None):
        if not self.ignore:
            try:
                self._maybe_git_clone_or_pull()
                self._maybe_make_distclean(configure)
                self._maybe_configure_project(configure)
                self._maybe_make_install(configure)
                self._maybe_make_extensions(extensions)
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
        pg_config_out = self.pg_config(['--configure'])
        if pg_config_out:
            options = shlex.split(pg_config_out)
            return [x for x in options if not x.startswith('--prefix')]

        return CONFIG['build']['configure_options']

    def _configure_options_are_new(self, opts):
        # operation's required if new non-trivial configure flags
        return opts is not None and opts != self._configure_options()

    def _maybe_git_clone_or_pull(self):
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
        self.git.add_excludes('.norsu*')

    def _maybe_configure_project(self, configure=None):
        makefile = os.path.join(self.work_dir, 'GNUmakefile')
        if not os.path.exists(makefile):
            args = [
                './configure',
                '--prefix={}'.format(self.main_dir)
            ]

            # NOTE: [] is a valid choice
            if configure is None:
                configure = self._configure_options()

            if configure:
                args.extend(configure)

            execute(args, cwd=self.work_dir, output=ExecOutput.Devnull)
            step('Configured sources with', configure)

    def _maybe_make_distclean(self, configure=None):
        makefile = os.path.join(self.work_dir, 'GNUmakefile')
        new_conf_opts = self._configure_options_are_new(configure)

        if os.path.exists(makefile) and \
           (new_conf_opts or self.requires_rebuild):

            # reset built commit hash
            self.built_commit_hash = None

            args = [TOOL_MAKE, 'distclean']
            execute(args, cwd=self.work_dir, error=False,
                    output=ExecOutput.Devnull)

            step('Prepared work dir for a new build')

    def _maybe_make_install(self, configure=None):
        new_conf_opts = self._configure_options_are_new(configure)

        if new_conf_opts or self.requires_reinstall:
            # update built commit hash
            self.built_commit_hash = self.actual_commit_hash

            jobs = int(CONFIG['build']['jobs'])
            for arg in ['-j{}'.format(jobs), 'install']:
                args = [TOOL_MAKE, arg]
                execute(args, cwd=self.work_dir, output=ExecOutput.Devnull)

            # update installed commit hash
            self.installed_commit_hash = self.actual_commit_hash

            step('Built and installed')

    def _maybe_make_extensions(self, extensions=None):
        if extensions is None:
            return

        # provide defaults
        if not extensions:
            path = os.path.join(self.work_dir, 'contrib')
            extensions = sorted((
                e for e in os.listdir(path)
                if os.path.isdir(os.path.join(path, e))
            ))

        failed = []
        missing = []

        for extension in extensions:
            # is it a contrib?
            path = os.path.join(self.work_dir, 'contrib', extension)
            if os.path.exists(path):
                try:
                    args = [TOOL_MAKE, 'install']
                    execute(args, cwd=path, output=ExecOutput.Devnull)
                    step('Installed contrib', Style.bold(extension))
                except Error:
                    failed.append(extension)
            else:
                missing.append(extension)

        if failed:
            raise Error('Failed to install: {}'.format(' '.join(failed)))

        if missing:
            raise Error('Failed to find: {}'.format(' '.join(missing)))


@contextmanager
def run_temp(instance, cwd=None, grab_pgxs=False, **kwargs):
    work_dir = cwd or os.getcwd()
    pg_config = instance.get_bin_path('pg_config')
    temp_conf = ''

    if not os.path.exists(pg_config):
        raise Error('Failed to find pg_config at {}'.format(pg_config))

    # HACK: help testgres find our instance
    os.environ['PG_CONFIG'] = pg_config

    # disable instance caching
    configure_testgres(cache_initdb=False)

    # Grab extra extension options
    if grab_pgxs:
        extension = Extension(work_dir=work_dir, pg_config=pg_config)

        mk_var = 'EXTRA_REGRESS_OPTS'
        regress_opts = str_args_to_dict(extension.makefile_var(mk_var))
        temp_conf_file = regress_opts.get('--temp-config')

        # read additional config
        if temp_conf_file:
            path = os.path.join(work_dir, temp_conf_file)
            temp_conf = try_read_file(path)
            print('Found custom config:', os.path.basename(path))

    with get_new_node(**kwargs) as node:
        print('Starting temporary PostgreSQL instance...\n')

        # prepare and start a new node
        node.cleanup_on_bad_exit = True
        node.init().append_conf(line=temp_conf).start()

        yield node

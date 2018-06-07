import os
import shlex

from pkg_resources import resource_filename

from .config import CONFIG, TOOL_MAKE
from .terminal import Style
from .utils import execute, ExecOutput


class Extension:
    def __init__(self, work_dir):
        self.work_dir = work_dir

    def make(self, pg_config, targets=None, options=None):

        if not targets:
            targets = CONFIG['pgxs']['default_targets']

        if not options:
            options = CONFIG['pgxs']['default_options']

        # copy options
        opts = [x for x in options]

        # append compiler options, if needed (e.g. for scan_build)
        for env in ['CC', 'CXX']:
            if env in os.environ:
                opts.append('{}={}'.format(env, os.environ.get(env)))

        for target in targets:
            print(Style.green('$ {} {} {}').format(TOOL_MAKE,
                                                   target,
                                                   ' '.join(opts)))

            args = [
                TOOL_MAKE,
                'USE_PGXS=1',
                'PG_CONFIG={}'.format(pg_config),
                target,
            ] + opts

            # execute make (writes to stdout)
            execute(args,
                    cwd=self.work_dir,
                    env=os.environ,
                    output=ExecOutput.Stdout)
            print()

    def makefile_print_var(self, pg_config, name):
        makefile = os.path.join(self.work_dir, 'Makefile')
        print_mk = resource_filename('norsu', 'data/print.mk')

        args = [
            TOOL_MAKE,
            'USE_PGXS=1',
            'PG_CONFIG={}'.format(pg_config),
            '-f', makefile,
            '-f', print_mk,
            'print-{}'.format(name)
        ]

        key, _, value = execute(args).partition('=')
        return value

    def extra_regress_opts(self, pg_config):
        name = 'EXTRA_REGRESS_OPTS'
        ret = self.makefile_print_var(pg_config, name)

        result = {}
        for s in shlex.split(ret):
            key, _, value = s.partition('=')
            result[key] = value

        return result

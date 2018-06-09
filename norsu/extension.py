import os
import shlex

from pkg_resources import resource_filename

from .config import CONFIG, TOOL_MAKE
from .terminal import Style
from .utils import execute, ExecOutput


class Extension:
    def __init__(self, work_dir, pg_config):
        self.work_dir = work_dir
        self.pg_config = pg_config

    def make(self, targets=None, options=None):

        if not targets:
            targets = CONFIG['pgxs']['default_targets']

        if not options:
            options = CONFIG['pgxs']['default_options']

        # copy options
        opts = options[:]

        # append compiler options, if needed (e.g. for scan_build)
        mk_vars = []
        for env in ['CC', 'CXX']:
            if env in os.environ:
                mk_vars.append('{}={}'.format(env, os.environ.get(env)))

        for target in targets:
            # print simplified command
            quoted_vars = ' '.join([shlex.quote(x) for x in mk_vars])
            quoted_opts = ' '.join([shlex.quote(x) for x in opts])
            s = '$ make {} {} {}'.format(quoted_vars, quoted_opts, target)
            print(Style.green(s))

            args = [
                TOOL_MAKE,
                'USE_PGXS=1',
                'PG_CONFIG={}'.format(self.pg_config),
            ]

            args.extend(mk_vars)
            args.extend(opts)
            args.append(target)

            # execute make (writes to stdout)
            execute(args,
                    cwd=self.work_dir,
                    env=os.environ,
                    output=ExecOutput.Stdout)
            print()

    def makefile_var(self, name):
        makefile = os.path.join(self.work_dir, 'Makefile')
        print_mk = resource_filename('norsu', 'data/print.mk')

        args = [
            TOOL_MAKE,
            'USE_PGXS=1',
            'PG_CONFIG={}'.format(self.pg_config),
            '-f', makefile,
            '-f', print_mk,
            'print-{}'.format(name)
        ]

        # return var's value
        return execute(args).partition('=')[2]

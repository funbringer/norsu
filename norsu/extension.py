import os
import shlex
import importlib

from norsu.config import CONFIG, TOOL_MAKE
from norsu.exceptions import LogicError, ProcessError
from norsu.execute import ExecOutput, execute
from norsu.terminal import Style


class Extension:
    def __init__(self, work_dir, pg_config=None):
        self.work_dir = work_dir
        self.pg_config = pg_config

    def __pgxs_args(self):
        if self.pg_config:
            return ['USE_PGXS=1', f'PG_CONFIG={self.pg_config}']
        return []

    def make(self, *targets, options=None):
        if not targets:
            targets = CONFIG['pgxs']['default_targets']

        if not options:
            options = CONFIG['pgxs']['default_options']

        # copy options
        opts = options[:]

        # append compiler options, if needed (e.g. for scan_build)
        for env in ['CC', 'CXX']:
            if env in os.environ:
                opts.append(f'{env}={os.environ.get(env)}')

        for target in targets:
            # print simplified command
            quoted_opts = ' '.join([shlex.quote(x) for x in opts])
            s = f'$ make {quoted_opts} {target}'
            print(Style.green(s))

            args = [
                TOOL_MAKE,
                *self.__pgxs_args(),
                *opts,
                target,
            ]

            # execute make (writes to stdout)
            execute(args,
                    cwd=self.work_dir,
                    env=os.environ,
                    output=ExecOutput.Stdout)
            print()

    def makefile_var(self, name):
        makefile = os.path.join(self.work_dir, 'Makefile')
        print_mk = importlib.resources.path('norsu', 'data/print.mk')

        args = [
            TOOL_MAKE,
            *self.__pgxs_args(),
            '-f',
            makefile,
            '-f',
            print_mk,
            f'print-{name}',
        ]

        try:
            # return var's value
            return execute(args).partition('=')[2]
        except ProcessError as e:
            raise LogicError(
                f'Failed to get variable {name} from Makefile') from e

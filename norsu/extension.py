import os
import shlex
import shutil

from pkg_resources import resource_filename

from .config import CONFIG, TOOL_MAKE
from .exceptions import Error
from .terminal import Style
from .utils import execute, ExecOutput, str_args_to_dict


class Extension:
    def __init__(self, work_dir, pg_config):
        self.work_dir = work_dir
        self.pg_config = pg_config

        self.specs = None
        specs_dir = os.path.join(work_dir, 'specs')
        if os.path.exists(specs_dir):
            self.specs = [os.path.splitext(spec)[0] for spec in os.listdir(specs_dir)]

        self._regress_opts = None

    def get_temp_config(self):
        mk_var = 'EXTRA_REGRESS_OPTS'
        if self._regress_opts is None:
            self._regress_opts = str_args_to_dict(self.makefile_var(mk_var))

        return self._regress_opts.get('--temp-config')

    def make(self, targets=None, options=None, instance=None):

        if not targets:
            targets = CONFIG['pgxs']['default_targets']

        if not options:
            options = CONFIG['pgxs']['default_options']

        # copy options
        opts = options[:]

        # append compiler options, if needed (e.g. for scan_build)
        for env in ['CC', 'CXX']:
            if env in os.environ:
                opts.append('{}={}'.format(env, os.environ.get(env)))

        for target in targets:
            # print simplified command
            quoted_opts = ' '.join([shlex.quote(x) for x in opts])
            s = '$ make {} {}'.format(quoted_opts, target)
            print(Style.green(s))

            args = [
                TOOL_MAKE,
                'USE_PGXS=1',
                'PG_CONFIG={}'.format(self.pg_config),
            ]

            args.extend(opts)
            args.append(target)

            # execute make (writes to stdout)
            execute(args,
                    cwd=self.work_dir,
                    env=os.environ,
                    output=ExecOutput.Stdout)

            if target in ('check', 'installcheck') and self.specs:
                print(Style.green('\n$ make isolationcheck'))

                tmpdir = os.path.join(self.work_dir, "tmp_check_iso")
                if os.path.exists(tmpdir):
                    shutil.rmtree(tmpdir)

                isolation_args = [
                    os.path.join(instance.work_dir,
                        "src/test/isolation/pg_isolation_regress"),
                    "--temp-instance=%s" % tmpdir,
                    "--inputdir=.",
                    "--outputdir=output_iso",
                    "--bindir=%s" % instance.get_bin_path(""),
                ]

                temp_config = self.get_temp_config()
                if temp_config:
                    isolation_args.append("--temp-config=%s" % temp_config)

                for spec in self.specs:
                    isolation_args.append(spec)

                try:
                    execute(isolation_args,
                            cwd=self.work_dir,
                            env=os.environ,
                            output=ExecOutput.Stdout)
                except:
                    raise
                finally:
                    if os.path.exists(tmpdir):
                        shutil.rmtree(tmpdir)

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

        try:
            # return var's value
            return execute(args).partition('=')[2]
        except Error:
            raise Error('Failed to get variable {} from Makefile'.format(name))

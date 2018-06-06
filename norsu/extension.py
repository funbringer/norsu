import os
import subprocess

from .terminal import Style


class Extension:
    def __init__(self, work_dir):
        self.work_dir = work_dir

    def make(self, pg_config, targets=None, options=None):
        # copy options
        opts = [x for x in options]

        # provide default targets
        if not targets:
            targets = ['clean', 'install']

        # append compiler options, if needed (e.g. for scan_build)
        for env in ['CC', 'CXX']:
            if env in os.environ:
                opts.append('{}={}'.format(env, os.environ.get(env)))

        for target in targets:
            print(Style.green('$ make {} {}').format(target, ' '.join(opts)))

            args = [
                'make',
                'USE_PGXS=1',
                'PG_CONFIG={}'.format(pg_config),
                target,
            ] + opts

            # execute make (writes to stdout)
            subprocess.Popen(args, cwd=self.work_dir, env=os.environ).wait()
            print()

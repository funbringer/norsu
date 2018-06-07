import os
import subprocess

from .exceptions import Error
from itertools import tee, filterfalse


def execute(args, cwd=None, output=True, error=True):
    stdout = subprocess.PIPE if output else subprocess.DEVNULL

    p = subprocess.Popen(args, cwd=cwd,
                         stdout=stdout,
                         stderr=subprocess.STDOUT)

    if output:
        out, _ = p.communicate()
        out = out.decode('utf8')
    else:
        p.wait()
        out = None

    if p.returncode != 0:
        if error:
            raise Error('Failed to execute {}'.format(' '.join(args)))
    else:
        return out


def partition(pred, iterable):
    t1, t2 = tee(iterable)
    return filterfalse(pred, t1), filter(pred, t2)


def try_read_file(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return f.read()

    return ''

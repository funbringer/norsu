import os
import shlex
import signal
import subprocess

from enum import Enum

from .exceptions import Error
from itertools import tee, filterfalse


class ExecOutput(Enum):
    Stdout = None
    Pipe = subprocess.PIPE
    Devnull = subprocess.DEVNULL


def execute(args, error=True, output=ExecOutput.Pipe, **kwargs):
    p = subprocess.Popen(args,
                         stdout=output.value,
                         stderr=subprocess.STDOUT,
                         **kwargs)

    if output == ExecOutput.Pipe:
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


def str_args_to_dict(a):
    result = {}
    for arg in shlex.split(a):
        k, _, v = arg.partition('=')
        result[k] = v
    return result


def give_terminal_to(pgid):
    signals = {
        signal.SIGTTOU,
        signal.SIGTTIN,
        signal.SIGTSTP,
        signal.SIGCHLD,
    }

    old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, signals)
    try:
        os.tcsetpgrp(2, pgid)
        return True
    except ProcessLookupError:
        return False
    except OSError:
        return False
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)


def path_exists(path):
    if os.path.exists(path):
        return path

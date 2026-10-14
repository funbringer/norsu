import os
import shlex
import sys
from itertools import filterfalse, tee


def partition(pred, iterable):
    t1, t2 = tee(iterable)
    return filterfalse(pred, t1), filter(pred, t2)


def str_args_to_dict(a: str) -> dict[str, str]:
    result = {}
    for arg in shlex.split(a):
        k, _, v = arg.partition('=')
        result[k] = v
    return result


def path_exists(path: str) -> str | None:
    if os.path.exists(path):
        return path
    return None


def eprint(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


def limit_lines(string: str, n: int) -> str:
    return '\n'.join(string.splitlines()[-n:])

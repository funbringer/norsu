import argparse
import shlex


class ShlexSplitAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs):
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, shlex.split(values))


def split_args_extra(args: list[str]):
    """
    Separate main args from auxiliary ones.
    """

    try:
        i = args.index('--')
        return args[:i], args[i + 1 :]
    except ValueError:
        return args, []

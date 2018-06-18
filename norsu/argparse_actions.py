import argparse
import shlex


class ShlexSplitAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        super(ShlexSplitAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, shlex.split(values))

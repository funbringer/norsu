import subprocess

from enum import Enum

from norsu.exceptions import ProcessError


class ExecOutput(Enum):
    """
    Possible outputs of a spawned subprocess.
    """

    Stdout = None
    Pipe = subprocess.PIPE
    Devnull = subprocess.DEVNULL


def execute(args,
            error: bool = True,
            output: ExecOutput = ExecOutput.Pipe,
            **kwargs):
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
            raise ProcessError('Failed to execute {}'.format(' '.join(args)),
                               stderr=out)  # attach output if possible

    return out

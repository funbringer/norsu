import os
import signal

from norsu.config import CONFIG


class Style:
    @staticmethod
    def style(color, text):
        if os.isatty(1) and os.isatty(2) and CONFIG['misc']['colors']:
            return f'\033[{color}m{text}\033[0m'
        return text

    @staticmethod
    def bold(text):
        return Style.style(1, text)

    @staticmethod
    def red(text):
        return Style.style(31, text)

    @staticmethod
    def green(text):
        return Style.style(32, text)

    @staticmethod
    def blue(text):
        return Style.style(94, text)

    @staticmethod
    def yellow(text):
        return Style.style(33, text)


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

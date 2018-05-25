import os

from .config import CONFIG


class Style:
    def style(color, text):
        if os.isatty(1) and os.isatty(2) and CONFIG['misc']['colors']:
            return '\033[{}m{}\033[0m'.format(color, text)
        return text

    def bold(text):
        return Style.style(1, text)

    def red(text):
        return Style.style(31, text)

    def green(text):
        return Style.style(32, text)

    def blue(text):
        return Style.style(94, text)

    def yellow(text):
        return Style.style(33, text)

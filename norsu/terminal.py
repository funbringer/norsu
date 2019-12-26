import os

from .config import CONFIG


class Style:
    @staticmethod
    def style(color, text):
        if os.isatty(1) and os.isatty(2) and CONFIG['misc']['colors']:
            return '\033[{}m{}\033[0m'.format(color, text)
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

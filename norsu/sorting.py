from functools import total_ordering


@total_ordering
class GitRefVer:
    def __init__(self, ref):
        ref_original = ref

        # use lowercase for substr search
        ref = ref_original.lower()

        # extract numbers from ref
        ver = ''.join((c for c in ref if c.isdigit() or c == '_'))
        ver = (n for n in ver.split('_') if n)
        ver = list(map(lambda n: int(n), ver))

        types = [
            ('stable', float('+inf')),
            ('rc', -1),
            ('beta', -2),
            ('alpha', -3),
        ]

        for t, num in types:
            if t in ref:
                # example:
                #  REL_10_RC1 => (10, -1, 1)
                #  REL_9_6_STABLE => (9, 6, 'inf')
                _, _, s = ref.rpartition(t)
                if s.isdigit():
                    ver.pop()  # see ver extraction
                    ver.append(num)
                    ver.append(int(s))
                else:
                    ver.append(num)

        self.ref = ref_original
        self.ver = ver

    def __eq__(self, other):
        return self.ver == other.ver

    def __lt__(self, other):
        return self.ver < other.ver

    def __str__(self):
        return self.ref

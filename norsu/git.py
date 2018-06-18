import os

from functools import total_ordering

from .config import CONFIG
from .utils import execute, ExecOutput


@total_ordering
class SortRefByVersion:
    def __init__(self, ref):
        # use lowercase for substr search
        name = ref.name.lower()

        # extract version numbers
        ver = ''.join((c for c in name if c.isdigit() or c == '_'))
        ver = (n for n in ver.split('_') if n)
        ver = list(map(lambda n: int(n), ver))

        types = [
            ('stable', float('+inf')),
            ('rc', -1),
            ('beta', -2),
            ('alpha', -3),
        ]

        for t, num in types:
            if t in name:
                # example:
                #  REL_10_RC1 => (10, -1, 1)
                #  REL_9_6_STABLE => (9, 6, 'inf')
                _, _, s = name.rpartition(t)
                if s.isdigit():
                    ver.pop()  # see ver extraction
                    ver.append(num)
                    ver.append(int(s))
                else:
                    ver.append(num)

        self.ref = ref
        self.ver = ver

    def __eq__(self, other):
        return self.ver == other.ver

    def __lt__(self, other):
        return self.ver < other.ver

    def __str__(self):
        return self.ref


@total_ordering
class SortRefBySimilarity:
    @staticmethod
    def ngram(text, N=3):
        ngrams = (text[i:i + N] for i in range(0, len(text) - N + 1))
        return set(ngrams)

    @staticmethod
    def similarity(ng1, ng2):
        return len(ng1 & ng2) / float(len(ng1 | ng2))

    def __init__(self, ref, name_ngram):
        ng1 = self.ngram(ref.name)
        ng2 = name_ngram

        self.similarity = self.similarity(ng1, ng2)
        self.ref = ref

    def __eq__(self, other):
        return self.similarity == other.similarity

    def __lt__(self, other):
        return self.similarity < other.similarity


class GitRef:
    def __init__(self, repo, name):
        self.repo = repo
        self.name = name


class GitRepo:
    def __init__(self, work_dir, url=None):
        self.work_dir = work_dir
        self.url = url

    @property
    def branch(self):
        args = ['git', 'symbolic-ref', '--short', 'HEAD']
        out = execute(args, cwd=self.work_dir, error=False)
        if out:
            return out.strip()

    @property
    def tag(self):
        args = ['git', 'tag', '--points-at', 'HEAD']
        out = execute(args, cwd=self.work_dir, error=False)
        if out:
            return out.strip()

    @property
    def hash(self):
        args = ['git', 'rev-parse', 'HEAD']
        return execute(args, cwd=self.work_dir).strip()

    def clone(self, url=None, branch='master', depth=1):
        args = [
            'git',
            'clone',
            '--branch', branch,
            '--depth', str(depth),
            url or self.url,
            self.work_dir,
        ]
        execute(args, output=ExecOutput.Devnull)

    def pull(self, remote='origin', branch=None):
        args = ['git', 'pull', remote, branch or self.branch]
        execute(args, cwd=self.work_dir, output=ExecOutput.Devnull)

    def distance(self, commit1, commit2):
        args = [
            'git',
            'rev-list',
            '{}..{}'.format(commit1, commit2),
            '--count',
        ]

        try:
            # mute possible cast errors
            return int(execute(args, cwd=self.work_dir).strip())
        except ValueError:
            pass

    def add_excludes(self, pattern):
        excludes = os.path.join(self.work_dir, '.git', 'info', 'exclude')
        with open(excludes, 'r+') as f:
            lines = f.readlines()
            if not any(pattern in s for s in lines):
                f.seek(0, os.SEEK_END)
                f.write(pattern)


def find_relevant_refs(repos, patterns):
    refs = []

    for repo in repos:
        args = ['git', 'ls-remote', '--heads', '--tags', repo]
        args += patterns  # search patterns

        out = execute(args)

        # list of matching branches and tags
        refs += [
            GitRef(repo, os.path.basename(r.split()[-1]))
            for r in out.splitlines()
        ]

        # should we stop after 1st match?
        if refs and CONFIG['repos']['first_match']:
            break

    return refs

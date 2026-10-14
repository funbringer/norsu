import os
import tomllib
from typing import Any

import tomli_w


def merge_config(current, new):
    if isinstance(current, dict):
        for k, v in new.items():
            if k not in current:
                raise Exception(f'Config: unknown option: {k}')

            if not merge_config(current[k], new[k]):
                if type(current[k]) is not type(v):
                    raise Exception(f'Config: bad option type: {k}')
                current[k] = v

        return True

    return False


# select default dir
HOME = os.environ['HOME']
NORSU_DIR = os.environ.get('NORSU_PATH') or os.path.join(HOME, 'pg')
WORK_DIR = os.path.join(NORSU_DIR, '.norsu')

if not os.path.exists(WORK_DIR):
    os.makedirs(WORK_DIR)

CONFIG: dict[str, Any] = {
    'repos': {
        'urls': [
            'https://git.postgresql.org/git/postgresql.git',
        ],
        'first_match': True,
    },
    'commands': {},
    'build': {
        'configure_options': ['CFLAGS=-g3', '--enable-cassert'],
        'jobs': 0,
    },
    'pgxs': {
        'default_targets': ['clean', 'install'],
        'default_options': [],
    },
    'tools': {
        'make': 'make',
    },
    'misc': {
        'colors': True,
    },
}

cfg = os.path.join(NORSU_DIR, '.norsu.toml')

if not os.path.exists(cfg):
    with open(cfg, 'wb') as fw:
        tomli_w.dump(CONFIG, fw)
else:
    with open(cfg, 'rb') as fr:
        merge_config(CONFIG, tomllib.load(fr))

TOOL_MAKE = CONFIG['tools']['make']

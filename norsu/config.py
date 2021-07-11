import os
import toml


def merge_config(current, new):
    if isinstance(current, dict):
        for k, v in new.items():
            if k not in current:
                raise Exception(f'Config: unknown option: {k}')

            if not merge_config(current[k], new[k]):
                if type(current[k]) != type(v):
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

CONFIG = {
    'repos': {
        'urls': [
            'git://git.postgresql.org/git/postgresql.git',
        ],
        'first_match': True,
    },
    'commands': {},
    'build': {
        'configure_options': ['CFLAGS=-g3', '--enable-cassert'],
        'jobs': 1,
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
    }
}

cfg = os.path.join(NORSU_DIR, '.norsu.toml')

if not os.path.exists(cfg):
    with open(cfg, 'w') as f:
        f.write(toml.dumps(CONFIG))
else:
    with open(cfg, 'r') as f:
        merge_config(CONFIG, toml.loads(f.read()))

TOOL_MAKE = CONFIG['tools']['make']

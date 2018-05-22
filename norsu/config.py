import os
import toml


# select default dir
HOME = os.environ['HOME']
NORSU_DIR = os.environ.get('NORSU_PATH') or os.path.join(HOME, 'pg')
WORK_DIR = os.path.join(NORSU_DIR, '.norsu')

if not os.path.exists(WORK_DIR):
    os.makedirs(WORK_DIR)


def read_config():
    cfg = os.path.join(NORSU_DIR, '.norsu.toml')

    if not os.path.exists(cfg):
        config = {
            'repos': [
                'git://git.postgresql.org/git/postgresql.git',
            ]
        }

        with open(cfg, 'w') as f:
            f.write(toml.dumps(config))

    with open(cfg, 'r') as f:
        config = toml.loads(f.read())
        return config


CONFIG = read_config()

import os
import toml


# select default dir
HOME = os.environ['HOME']
NORSU_DIR = os.environ.get('NORSU_PATH') or os.path.join(HOME, 'pg')
WORK_DIR = os.path.join(NORSU_DIR, '.norsu')

if not os.path.exists(WORK_DIR):
    os.makedirs(WORK_DIR)


class Config:
    def __init__(self, items):
        self.items = items

    def __getattr__(self, name):
        if isinstance(self.items, dict):
            if name in self.items:
                return Config(self.items[name])
            else:
                raise KeyError('No such item: {}'.format(name))
        else:
            raise TypeError('Not a dict')

    def __iter__(self):
        return self.items.__iter__()


def read_config():
    cfg = os.path.join(NORSU_DIR, '.norsu.toml')

    if not os.path.exists(cfg):
        config = {
            'repos': {
                'urls': [
                    'git://git.postgresql.org/git/postgresql.git',
                ],
                'first_match': True,
            }
        }

        with open(cfg, 'w') as f:
            f.write(toml.dumps(config))

    with open(cfg, 'r') as f:
        return Config(toml.loads(f.read()))


CONFIG = read_config()

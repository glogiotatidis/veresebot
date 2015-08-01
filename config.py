db_filename = 'db.fs'
port = '8899'

try:
    from local_config import *  # noqa
except ImportError:
    pass

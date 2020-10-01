from . import config
from .transform import Transform
from . import util
from .sql_loader import SqlLoader

class SQLTransform(Transform):
    """
    SQL transform runs in the destination, it needs a local source (same db as destination)
    """
    def __init__(_, mode, source, destination, directory=None, filename=None):
        super().__init__(mode, source, destination)
        assert source.local == True

        if directory:
            _.scripts = SqlLoader.from_directory(directory, mode, source, destination)
        elif filename:
            _.scripts = [SqlLoader(filename, mode, source, destination)]
        else:
            raise config.ConfigError("SQL transform must be given directory or file attribute")

    def get_scripts(_):
        return _.scripts

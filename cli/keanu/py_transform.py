from . import config
from .transform import Transform
from . import util
from .py_loader import PyLoader


class PyTransform(Transform):
    """
    """
    def __init__(_, mode, source, destination, directory=None, filename=None):
        super().__init__(mode, source, destination)

        if directory:
            _.scripts = PyLoader.from_directory(directory, mode, source, destination)
        elif filename:
            _.scripts = [PyLoader(filename, mode, source, destination)]
        else:
            raise config.ConfigError("SQL transform must be given directory or file attribute")

    def get_scripts(_):
        return _.scripts

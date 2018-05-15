# encoding: utf-8
"""Adapted from IPython :mod:`traitlets.config/loader`."""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.


from ruamel import yaml  # @UnresolvedImport

from .._vendor.traitlets import config as trc


class YAMLFileConfigLoader(trc.loader.FileConfigLoader):
    """A YAML file loader for config

    Can also act as a context manager that rewrite the configuration file to disk on exit.

    Example::

        with YAMLFileConfigLoader('myapp.json','/home/jupyter/configurations/') as c:
            c.MyNewConfigurable.new_value = 'Updated'

    """
    yaml = None

    def __init__(self, *args, **kw):
        if not self.yaml:
            YAMLFileConfigLoader.yaml = yaml.YAML(typ='safe')  # round-trip
        super().__init__(*args, **kw)

    def load_config(self):
        """Load the config from a file and return it as a Config object."""
        self.clear()
        try:
            self._find_file()
        except OSError as e:
            raise trc.ConfigFileNotFound(str(e))
        dct = self._read_file_as_dict()
        self.config = self._convert_to_config(dct)
        return self.config

    def _read_file_as_dict(self):
        with open(self.full_filename) as f:
            return self.yaml.load(f)

    def _convert_to_config(self, dictionary):
        if 'version' in dictionary:
            version = dictionary.pop('version')
        else:
            version = 1

        if version == 1:
            return trc.Config(dictionary)
        else:
            raise ValueError('Unknown version of YAML config file: {version}'
                             .format(version=version))

    def __enter__(self):
        self.load_config()
        return self.config

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exit the context manager but do not handle any errors.

        In case of any error, we do not want to write the potentially broken
        configuration to disk.
        """
        self.config.version = 1
        yaml_config = self.yaml.dumps(self.config, indent=2)
        with open(self.full_filename, 'w') as f:
            f.write(yaml_config)

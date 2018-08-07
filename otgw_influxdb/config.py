import yaml
from yaml.parser import ParserError
from yaml.scanner import ScannerError


class ConfigError(NotImplementedError):
    pass


class Settings(object):
    REQUIRED_FIELDS = (
        "otmonitor_url",
        "otmonitor_websocket_url"

        "poller_wait_time"
        "status_keys"

        "influx_hostname"
        "influx_port"

        "influx_database"
        "influx_username"
        "influx_password"

        "influx_measurement"
        "influx_retention_policy"
        "influx_tags"

        "max_modulation"
        "min_modulation"
    )

    def __init__(self, filename):
        self.filename = filename
        self.config = self._read(filename)
        self._parse()
        self._verify()

    @staticmethod
    def _read(filename):
        try:
            with open(filename) as fh:
                return yaml.safe_load(fh.read())
        except (IOError, ParserError, ScannerError) as e:
            raise ConfigError(e)

    def _parse(self):
        self.items = []
        for key, value in self.config.items():
            if not hasattr(self, key):
                self.items.append(key)
                if isinstance(value, str):
                    value = value.format(**self.config)
                setattr(self, key, value)

    def _verify(self):
        for key in self.REQUIRED_FIELDS:
            if key not in self.config.keys():
                raise ConfigError('{} not found in {}'.format(key, self.filename))

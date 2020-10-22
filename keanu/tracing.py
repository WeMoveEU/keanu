from atexit import register
from getpass import getuser
from time import sleep

from jaeger_client import Config

config = Config(
    {
        "sampler": {
            "type": "const",
            "param": 1,
        },
        "logging": True,
        "tags": {"user": getuser()},
    },
    service_name="keanu",
    validate=True,
)

tracer = config.initialize_tracer()


def close_tracer(*a):
    try:
        tracer.close()
    except RuntimeError:
        pass
    # this is unfortunately needed as silly jaeger does not let to sync flush spans :(
    sleep(1)


register(close_tracer)


class Tags:
    def __init__(self):
        self._tracing_tags = {}

    # pylint: disable=no-member
    @property
    def tracing_tags(self):
        t = {
            "incremental": self.options["incremental"] == True,
        }
        if self.source:
            t["source_name"] = self.source.name
        if self.destination:
            t["destination_name"] = self.destination.name
        t.update(self._tracing_tags)
        return t

    @tracing_tags.setter
    def tracing_tags(self, tags):
        self._tracing_tags = tags

from jaeger_client import Config
from getpass import getuser
from atexit import register
from time import sleep

config = Config(
    {
        'sampler': {
            'type': 'const',
            'param': 1,
        },
        'logging': True,
        'tags': {
            'user': getuser()
        }
    },
    service_name='keanu',
    validate=True
)

tracer = config.initialize_tracer()

def close_tracer(*a):
    try:
        tracer.close()
    except RuntimeError:
        pass
    sleep(1) # this is unfortunately needed as silly jaeger does not let to sync flush spans :(


register(close_tracer)


class Tags:
    def __init__(_):
        _._tracing_tags = {}

    @property
    def tracing_tags(_):
        t = {
            'incremental': _.options['incremental'] == True,
            }
        if _.source:
            t['source_name'] = _.source.name
        if _.destination:
            t['destination_name'] = _.destination.name
        t.update(_._tracing_tags)
        return t

    @tracing_tags.setter
    def tracing_tags(_, tags):
        _._tracing_tags = tags

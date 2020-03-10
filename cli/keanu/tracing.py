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
    # sleep(1)
    try:
        tracer.close()
    except RuntimeError:
        sleep(1)

register(close_tracer)

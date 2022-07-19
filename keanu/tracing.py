from atexit import register
from getpass import getuser
from time import sleep
from os import environ, path

from contextlib import contextmanager
import sentry_sdk

if 'SENTRY_DSN' in environ:
    sentry_sdk.init(environ['SENTRY_DSN'], traces_sample_rate=1.0, _experiments={"max_spans": 10000})


class Tags:
    """
    Loader mixin that adds self.tracing_tags property.

    """
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

@contextmanager
def transaction(description, tags={}):
    with sentry_sdk.start_transaction() as t:
        t.name = description
        for k,v in tags.items():
            t.set_tag(k, v)
        yield t

@contextmanager
def span(description, tags={}):
    with sentry_sdk.start_span() as s:
        s.description = description
        
        for k,v in tags.items():
            s.set_tag(k,v) 
        yield s


@contextmanager
def batch(batch):
    with sentry_sdk.start_transaction(name=batch.name, op="batch") as t:
        tags = batch.tracing_tags
        for k,v in tags.items():
            t.set_tag(k,v)

        # pass this in thread local storage of Sentry too
        if 'SENTRY_DSN' in environ:
            sentry_sdk.hub.Hub.current._parent_tx = t

        yield t

@contextmanager
def loader(loader, batch_tx=None):
    if batch_tx is None and 'SENTRY_DSN' in environ:
        batch_tx = sentry_sdk.hub.Hub.current._parent_tx

    if loader.options['rewind']:
        name_prefix='delete'
    else:
        name_prefix='load'

    # dry run are called dry_run_delete dry_run_load
    if loader.options['dry_run']:
        name_prefix = 'dry_run_' + name_prefix

    name = "{}.{}".format(name_prefix, path.relpath(loader.filename).replace('../', '').replace("/", "."))

    # loader description - filename, but make it relative, and if the file is in
    # another directory, remove the ../ from name (case for helpers)
    with sentry_sdk.start_span(description=loader.filename) as s:
        with sentry_sdk.start_transaction(
                name=name, op='loader', trace_id=batch_tx.trace_id,
                parent_span_id=s.span_id, containing_transaction=batch_tx) as t:

            tags = {}
            tags.update(batch_tx._tags)
            tags.update(loader.tracing_tags)

            for k,v in tags.items():
                t.set_tag(k,v)

            yield t

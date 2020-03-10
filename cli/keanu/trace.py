from .tracing import tracer

class Trace:
    def __init__(_):
        _.script_tracer_tags = {}

    @property
    def tracer_tags(_):
        t = {
            'incremental': _.options['incremental'] == True,
            }
        if _.source:
            t['source_name'] = _.source.name
        if _.destination:
            t['destination_name'] = _.destination.name
        t.update(_.script_tracer_tags)
        return t

    @staticmethod
    def trace(label_or_func):
        def wrap(f):
            def with_tracing(self, *args, **kwargs):
                if isinstance(label_or_func, str):
                    event = label_or_func
                else:
                    event = label_or_func(self)

                with tracer.start_active_span(event, tags=self.tracer_tags):
                    for x in f(self, *args, **kwargs):
                        yield x
            return with_tracing
        return wrap

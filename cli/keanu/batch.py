import operator
import click
from time import sleep
from . import util
from .tracing import tracer

from signal import signal, SIGUSR1

sighup_received = False
def sighup(_a, _b):
    click.echo("\r🛬 Received SIGUSR1, stopping as soon as possible...")
    global sighup_received
    sighup_received = True

signal(SIGUSR1, sighup)

class RetryScript(Exception):
    pass

RETRY_COUNT = 3
RETRY_SLEEP = 10


class Batch:
    def __init__(_, mode):
        """
        mode - running mode of this batch. Map containing:
        = {
          incremental - boolean - whether to avoid updating data that did not change (optimization)
          order - string - order specification, limiting scripts to run
          dry_run - boolean - if set, don't execute statements for real
          display - boolean - display more information
          warn - boolean - display warnings (supressed by default)
          rewind - boolean - run in rewind mode
          threads - int - number of threads for parallel processing
          }
        """
        _.mode = {
            'incremental': False,
            'display': False,
            'warn': False,
            'dry_run': False,
            'rewind': False,
            'threads': 1
        }

        _.mode.update(mode)
        _.sources = []
        _.destination = None
        _.scripts = []

    @property
    def is_dry_run(_):
        return _.mode['dry_run']

    def add_source(_, source):
        source.batch = _
        _.sources.append(source)

    def add_destination(_, destination):
        destination.batch = _
        _.destination = destination

    def add_transform(_, transform):
        """
        Gets all scripts from this transform and stores them in sorted order
        """
        _.scripts += transform.get_scripts()
        if 'order' in _.mode:
            _.scripts = util.filter_scripts_by_order(_.scripts, _.mode['order'])
        _.scripts = _.sort(_.scripts)
        if _.mode['rewind']:
            _.scripts.reverse()

    def execute(_):
        with tracer.start_active_span('batch', tags=_.tracer_tags):
            for scr in _.scripts:
                for tries in range(RETRY_COUNT):
                    try:
                        if _.mode['rewind'] == False:
                            for e,d in scr.execute():
                                yield e, d
                        else:
                            for e,d in scr.delete():
                                yield e, d

                        if sighup_received:
                            raise click.Abort("Stopped gracefully due to USR1 signal")

                        break # from retry loop
                    except RetryScript as rse:
                        if tries + 1 == RETRY_COUNT:
                            raise click.Abort("Too many retries, aborting") from rse
                        else:
                            click.echo("Encountered error that can be retried: {}.\n😴  Sleeping 10 seconds....".format(rse.__cause__))
                            sleep(RETRY_SLEEP)
                            click.echo("Retrying....")

    def find_source(_, criteria):
        for s in reversed(_.sources):
            if criteria(s):
                return s
        return None

    def find_source_by_name(_, name):
        return _.find_source(lambda s: s.name == name)

    @staticmethod
    def sort(scripts):
        scripts.sort(key=operator.attrgetter('order'))
        return scripts

    @property
    def tracer_tags(_):
        return {
            'mode': 'delete' if _.mode['rewind'] else 'load',
            'incremental': _.mode['incremental'] == True
        }

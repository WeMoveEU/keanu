import operator
import traceback
from signal import signal, SIGUSR1
from time import sleep

import click

from . import util
from . import tracing
from .helpers import run_history


sighup_received = False


def sighup(_a, _b):
    util.clear_line()
    click.echo("🛬 Received SIGUSR1, stopping as soon as possible...")
    global sighup_received
    sighup_received = True


signal(SIGUSR1, sighup)


class RetryScript(Exception):
    pass


RETRY_COUNT = 3
RETRY_SLEEP = 10


class Batch:
    def __init__(self, mode, name='batch'):
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
        self.mode = {
            "incremental": False,
            "display": False,
            "warn": False,
            "dry_run": False,
            "rewind": False,
            "threads": 1,
        }

        self.mode.update(mode)
        self.sources = []
        self.destination = None
        self.scripts = []
        self.name = name

    @property
    def is_dry_run(self):
        return self.mode["dry_run"]

    def add_source(self, source):
        source.batch = self
        self.sources.append(source)

    def add_destination(self, destination):
        destination.batch = self
        self.destination = destination

    def add_transform(self, transform):
        """
        Gets all scripts from this transform and stores them in sorted order
        """
        self.scripts += transform.get_scripts()
        if "order" in self.mode:
            self.scripts = util.filter_scripts_by_order(
                self.scripts, self.mode["order"]
            )
        self.scripts = self.sort(self.scripts)
        if self.mode["rewind"]:
            self.scripts.reverse()

    def execute(self):
        # Dry-run and destination-less batches skip history tracking — they don't
        # represent real loader cycles and shouldn't pollute the stats.
        track_history = (
            not self.mode["dry_run"] and self.destination is not None
        )

        conn = self.destination.connection() if track_history else None
        cycle_id = None
        cycle_status = 'success'

        if track_history:
            run_history.prune(conn)
            cycle_id = run_history.start_cycle(conn, self.name)

        try:
            with tracing.batch(self):
                for scr in self.scripts:
                    for tries in range(RETRY_COUNT):
                        run_id = None
                        if track_history:
                            run_id = run_history.start_run(
                                conn, cycle_id, scr.filename, scr.order
                            )
                        try:
                            if self.mode["rewind"] == False:
                                for e, d in scr.execute():
                                    yield e, d
                            else:
                                for e, d in scr.delete():
                                    yield e, d

                            if sighup_received:
                                raise click.Abort("Stopped gracefully due to USR1 signal")

                            if track_history:
                                run_history.end_run(conn, run_id, 'success')
                            break  # from retry loop
                        except RetryScript as rse:
                            if track_history:
                                run_history.end_run(
                                    conn, run_id, 'failure', traceback.format_exc()
                                )
                            if tries + 1 == RETRY_COUNT:
                                raise click.Abort("Too many retries, aborting") from rse
                            else:
                                click.echo(
                                    "Encountered error that can be retried: {}.\n😴  Sleeping 10 seconds....".format(
                                        rse.__cause__
                                    )
                                )
                                sleep(RETRY_SLEEP)
                                click.echo("Retrying....")
                        except Exception:
                            if track_history:
                                run_history.end_run(
                                    conn, run_id, 'failure', traceback.format_exc()
                                )
                            raise
        except Exception:
            cycle_status = 'failure'
            raise
        finally:
            if track_history and cycle_id is not None:
                run_history.end_cycle(conn, cycle_id, cycle_status)

    def find_source(self, criteria):
        for s in reversed(self.sources):
            if criteria(s):
                return s
        return None

    def find_source_by_name(self, name):
        return self.find_source(lambda s: s.name == name)

    @staticmethod
    def sort(scripts):
        scripts.sort(key=operator.attrgetter("order"))
        return scripts

    @property
    def tracing_tags(self):
        if self.mode['dry_run']:
            mode = 'dry_run'
        else:
            if self.mode['rewind']:
                mode = 'delete'
            else:
                mode = 'load'

        return {
            "mode": mode,
            "incremental": self.mode["incremental"] == True,
        }

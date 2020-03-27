import os
import sys
from pathlib import Path
from glob import glob
from importlib import import_module
from . import tracing, db
from time import time
import click
from pymysql.err import MySQLError
from sqlalchemy.exc import IntegrityError, InternalError, ProgrammingError, DataError
from threading import Thread, Lock
from collections import namedtuple
import itertools

ThreadInfo = namedtuple('ThreadInfo', ['index', 'count'])

class PyLoader(tracing.Tags):
    """
    Class that runs load modules, that is Python modules that load some data in keanu database.
    """
    def __init__(_, filename, mode, source, destination):
        super().__init__()
        _.filename = filename
        
        _.module = PyLoader.import_module(filename)
        _.lock = Lock()

        _.options = {
            'incremental': False,
            'display': False,
            'warn': False,
            'dry_run': False,
            'threads': 1
        }
        _.options.update(mode)

        _.source = source
        _.destination = destination

        if _.defines('TAGS'):
            if isinstance(_.module.TAGS, dict):
                _.tracing_tags = _.module.TAGS
            else:
                raise click.ClickException("TAGS in {} should be a dict".format(_.filename))
        else:
            _.tracing_tags = {}

        if _.defines('ORDER'):
            if isinstance(_.module.ORDER, int):
                _.order = _.module.ORDER
            else:
                raise click.ClickException("ORDER in {} should be a number".format(_.filename))
        else:
            _.order = 100

        if _.defines('IGNORE'):
            _.ignore = _.module.IGNORE
        else:
            _.ignore = not _.defines('execute')

        _.checkpoint = None

    @staticmethod
    def import_module(filename):
        if filename.endswith(".py"):
            mod_name = os.path.splitext(os.path.basename(filename))[0]
            dir = os.path.dirname(os.path.abspath(filename))
            sys.path.insert(0, dir)
            mod = import_module(mod_name)
            sys.path.pop(0)
            return mod
        else:
            raise click.ClickException("Cannot load non-py file {}".format(filename))

    @staticmethod
    def from_directory(sqldir, mode, source, destination):
        files = glob(os.path.join(sqldir, '**/*.py'), recursive=True)
        if len(files) == 0:
            raise click.BadParameter('No py files found in {}'.format(sqldir), param_hint='config_or_dir')
        # skip __init__.py
        files = filter(lambda x: os.path.basename(x) != "__init__.py", files)
        scripts = list(map(lambda fn: PyLoader(fn, mode, source, destination), files))
        return scripts

    def __str__(_):
        return '{} ({})'.format(_.filename, _.order)


    def delete(_):
        if _.ignore or not _.defines('delete'):
            return
        try:
            yield 'py.script.start.delete', { 'script': _ }
            start_time = time()

            if _.options['dry_run']:
                return
            with tracing.tracer.start_active_span(
                    'delete.{}'.format(_.filename.replace('/', '.')),
                    tags=_.tracing_tags
                    ):
                _.module.delete(_)
            yield 'py.script.end.delete', { 'script': _, 'time': time() - start_time }

        except KeyboardInterrupt as ctrlc:
            raise ctrlc


    def execute(_):
        if _.ignore:
            return

        try:
            yield 'py.script.start', { 'script': _ }
            start_time = time()

            if _.options['dry_run']:
                return

            with tracing.tracer.start_active_span(
                    'script.{}'.format(_.filename.replace('/', '.')),
                    tags=_.tracing_tags
                    ):

                result = _.module.execute(_)

            yield 'py.script.end', {
                'script': _,
                'time': time() - start_time,
                'result': result
            }
        except KeyboardInterrupt as ctrlc:
            raise click.Abort("aborted.")
        except (ProgrammingError, IntegrityError, MySQLError, InternalError, DataError) as e:
            msg = str(e.args[0])
            msg = msg.replace('\\n', "\n")
            click.echo(message=msg, err=True)
            raise click.Abort(msg)

    @staticmethod
    def slice_for_thread(iterable, thread):
        for i, v in enumerate(iterable):
            if i % thread.count == thread.index:
                yield v

    @staticmethod
    def thread_info(thread_index, thread_count):
        return ThreadInfo(thread_index, thread_count)

    def defines(_, varname):
        return varname in dir(_.module)

    @staticmethod
    def path_to_module(path):
        p = Path(path)

        def strip_py(x):
            if x.endswith('.py'):
                return x[0:-3]
            else:
                return x

        m = '.'.join(map(lambda a: strip_py(a), p.parts))

        return m

    def threaded(_, function):
        if _.options['threads'] > 1:
            def execute_then_close_connections(thr):
                try:
                    r = function(thr)
                    return ("ok", r)
                except Exception as exc:
                    click.echo(exc)
                    return ("error", exc.__class__.__name__, exc.args)
                finally:
                    db.close_connections()

            thr_ct  = _.options['threads']
            threads = [Thread(target=execute_then_close_connections, args=(ThreadInfo(i, thr_ct),))
                       for i in range(thr_ct)]

            [t.start() for t in threads]

            [t.join() for t in threads]
            # Python multi-threading is very lame.
            # Can't get return value with oh-so-basic threading.Thread :-<
            #  concurrent.futures.ThreadPoolExecutor crashes with SIGSEGV (even official docs examples)
            # TODO: test: from multiprocessing.pool import ThreadPool
            # failures = list(itertools.filterfalse(lambda a: a[0] == 'ok', results))
            # if len(failures) > 0:
            #     f = failures[0]
            #     raise click.Abort("Exception (in thread): {ex} with {args}".format(
            #         ex=f[1], args=f[2]))
            # else:
            #     return list(map(lambda a: a[1], results))

        else:
            return function(ThreadInfo(0,1))


    def get_checkpoint(_, checkpoint):
        """
Used to synchronize the checkpoint, which will be max processed id of imput data, between all processing threads. Because input data can grow realtime, we would run into problems if some threads would use a different input boundary.
        This is the value that should also be saved to last_sync tables.
        """
        try:
            _.lock.acquire()
            if _.checkpoint is None:
                _.checkpoint = checkpoint
            return _.checkpoint
        finally:
            _.lock.release()

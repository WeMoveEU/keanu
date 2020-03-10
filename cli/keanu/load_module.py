from pathlib import Path
from importlib import import_module
from .trace import Trace
import click

class LoadModule(Trace):
    """
    Class that runs load modules, that is Python modules that load some data in keanu database.
    """
    def __init(_, filename, mode, source, destionation):
        Trace.__init__(_)
        _.filename = filename
        mod_path = to_module(filename)
        _.module = import_module(mod_path)

        _.options = {
            'incremental': False,
            'display': False,
            'warn': False
        }
        _.options.update(mode)

        _.source = source
        _.destination = destination

        if defines('TAGS'):
            if isinstance(_.module.TAGS, dict):
                _.script_tracer_tags = _.module.TAGS
            else:
                raise click.ClickException("TAGS in {} should be a dict".format(_.filename))
        else:
            _.script_tracer_tags = {}

        if defines('ORDER'):
            if isinstance(_.module.ORDER, int):
                _.order = _.module.ORDER
            else:
                raise click.ClickException("ORDER in {} should be a number".format(_.filename))
        else:
            _.order = 100

    @Trace.trace(lambda _: 'delete.{}'.format(_.filename.replace('/', '.')))
    def delete(_):
        if not defines('delete'):
            return

        connection = _.destination.connection()
        with connection.begin() as transaction:
            yield 'sql.script.start.delete', { 'script': _ }
            try:
                if _.defines("delete"):
                    _.module.delete()
            except KeyboardInterrupt as ctrlc:
                transaction.rollback()
                raise ctrlc
            yield 'sql.script.end.delete', { 'script': _ }

    @Trace.trace(lambda _: 'script.{}'.format(_.filename.replace('/', '.')))
    def execute(_):
        if len(_.statements) == 0:
            return

        connection = _.destination.connection()
        with connection.begin() as transaction:
            try:
                yield 'sql.script.start', { 'script': _ }
                _.module.execute()
                yield 'sql.script.end', { 'script': _ }
            except KeyboardInterrupt as ctrlc:
                transaction.rollback()
                raise click.Abort("aborted.")
            except (ProgrammingError, IntegrityError, MySQLError, InternalError, DataError) as e:
                transaction.rollback()
                msg = str(e.args[0])
                msg = msg.replace('\\n', "\n")
                click.echo(message=msg, err=True)
                raise click.Abort(msg)

    def defines(varname):
        return varname in dir(_.module)

    @staticmethod
    def to_module(path):
        p = Path(path)

        def strip_py(x):
            if x.endswith('.py'):
                return x[0:-3]
            else:
                return x

        m = '.'.join(map(p.parts, lambda a: stripy_py(a)[0]))

        return m

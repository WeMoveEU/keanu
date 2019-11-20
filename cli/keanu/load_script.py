import operator
import re
from sqlalchemy import text
import click
from .run_statement import RunStatement
from .util import highlight_sql
import os

class LoadScript(RunStatement):
    """
    Class that runs load scripts, that is SQL that loads some data in keanu database.
    It can read extra metadata from the script comments.

    Pass path to file of SQL script.

    options can be:
    incremental - run incremental variant of the script (no by default)
    display - displays full SQL while executing (no by default)
    warn - do show warnings from mysql driver (no by default)
    """
    def __init__(_, filename, **options):
        # filename and class options
        _.filename = filename
        _.options = {
            'incremental': False,
            'display': False,
            'warn': False
        }
        _.options.update(options)

        # defaults
        _.deleteSql = []
        _.order = 100

        # parse SQL
        _.lines = _.parse(open(filename, 'r').readlines())
        _.statements = _.split_statements(_.lines)

    """
    Parse script lines and load metadata. Returns list of lines after parsing (will be modified).
    Has effects of setting fields on object.
    """
    def parse(_, lines):
        out = []
        contexts = []
        comment_line = lambda x: '-- ' + x

        lines = map(_.interpolate_environ, lines)

        for l in lines:
            m = re.match(r" *-- *ORDER: (\d+)", l)
            if m:
                _.order = int(m.group(1))
                continue

            m = re.match(r" *-- *((DELETE|TRUNCATE) .*)$", l)
            if m:
                _.deleteSql.append(m.group(1))
                continue


            m = re.match(r" *-- *BEGIN (\w+)", l)
            if m:
                contexts.append(m.group(1).upper())
                continue

            m = re.match(r" *-- *END (\w+)", l)
            if m:
                contexts.remove(m.group(1).upper())
                continue

            m = re.match(r" *-- *IGNORE", l)
            if m:
                break

            if 'INCREMENTAL' in contexts and not _.options['incremental']:
                l = comment_line(l)

            out.insert(0, l)

        out.reverse()
        return out

    """
    Performs interpolation on string, replacing ${FOO} with FOO environment variable.
    """
    @staticmethod
    def interpolate_environ(line):
        def get_var(m):
            return os.environ[m.group(1)]
        return re.subn(r"[$]{([A-Za-z1-9_]+)}", get_var, line)[0]

    """
    Predicate - is this line just a comment line?
    """
    @staticmethod
    def noop_line(line):
        return re.match(r" *--", line) or re.match(r"^[\s;]*$", line)


    """
    Will split the lines of script into SQL statements (separated by semicolon)
    """
    def split_statements(_, lines):
        out = []
        c = []
        for l in lines:
            c.append(l)
            if re.search(r";[\s]*($|--.*$)", l):
                out.append(c)
                c = []

        if len(c) > 0 and any(map(lambda a: not _.noop_line(a), c)):
            out.append(c)

        return list(map(lambda a: ''.join(a), out))

    def statement_abbrev(_, statement):
        if _.options['display']:
            return statement

        trim_to = max(50, int(os.get_terminal_size().columns / 2))
        lines = statement.split("\n")
        lines = filter(lambda x: not re.match(r" *--", x) and not re.match(r"\s*$", x), lines)
        try:
            first = next(lines)
            if len(first) > trim_to:
                first =  first[0:trim_to] + '...'
            return first
        except StopIteration:
            return ''
        

    def delete(_, connection):
        result = None
        if len(_.deleteSql) > 0:
            for event, data in super().execute(connection, _.deleteSql, warn=_.options['warn']):
                if event == 'start':
                    click.echo("🔥 {0}".format(highlight_sql(_.statement_abbrev(data['sql']))))
        return result


    def execute(_, connection):
        # ses = connection.begin()
        res = None
        row_counts = []
        for event, data in super().execute(connection, _.statements, warn=_.options['warn']):
            if event == 'start':
                click.echo("📦 {0}...".format(
                    highlight_sql(
                        _.statement_abbrev(data['sql']))),
                           nl=False)
            elif event == 'end':
                click.echo("\r✅️ {} rows in {:0.2f}s {:}".format(
                    data['result'].rowcount,
                    data['time'],
                    highlight_sql(_.statement_abbrev(data['sql']))
                ))
                res = data['result']
        return res


    @staticmethod
    def sort(scripts):
        return scripts.sort(key=operator.attrgetter('order'))

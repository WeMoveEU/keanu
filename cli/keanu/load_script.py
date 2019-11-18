import operator
import re
from sqlalchemy import text
import click
from .run_statement import RunStatement

class LoadScript(RunStatement):
    def __init__(_, filename, **options):
        # filename and class options
        _.filename = filename
        _.options = {
            'incremental': False,
            'display': False
        }
        _.options.update(options)

        # defaults
        _.deleteSql = []
        _.order = 100

        # parse SQL
        _.lines = _.parse(open(filename, 'r').readlines())
        _.statements = _.split_statements(_.lines)

    def parse(_, lines):
        out = []
        contexts = []
        comment_line = lambda x: '-- ' + x

        for l in lines:
            m = re.match(r" *-- *ORDER: (\d+)", l)
            if m:
                _.order = int(m[1])
                continue

            m = re.match(r" *-- *((DELETE|TRUNCATE) .*)$", l)
            if m:
                _.deleteSql.append(m[1])
                continue


            m = re.match(r" *-- *BEGIN (\w+)", l)
            if m:
                contexts.append(m[1].upper())
                continue

            m = re.match(r" *-- *END (\w+)", l)
            if m:
                contexts.remove(m[1].upper())
                continue

            m = re.match(r" *-- *IGNORE", l)
            if m:
                break

            if 'INCREMENTAL' in contexts and not _.options['incremental']:
                l = comment_line(l)

            out.insert(0, l)

        out.reverse()
        return out

    @staticmethod
    def noop_line(line):
        return re.match(r" *--", line) or re.match(r"^[\s;]*$", line)

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

    @staticmethod
    def statement_abbrev(statement):
        trim_to = 50
        lines = statement.split("\n")
        lines = filter(lambda x: not re.match(r" *--", x) and not re.match(r"\s*$", x), lines)
        first = next(lines)
        if len(first) > trim_to:
            first =  first[0:trim_to] + '...'
        return first

    def delete(_, connection):
        result = None
        if len(_.deleteSql) > 0:
            for event, data in super().execute(connection, _.deleteSql):
                if event == 'start':
                    click.echo("🎰 {0}".format(_.statement_abbrev(data['sql'])))
        return result


    def execute(_, connection):
        # ses = connection.begin()
        res = None
        row_counts = []
        for event, data in super().execute(connection, _.statements):
            if event == 'start':
                click.echo("🎰 {0}...".format(_.statement_abbrev(data['sql'])), nl=False)
            elif event == 'end':
                click.echo("\r☑️ in {:0.2f}s {:}".format(data['time'], _.statement_abbrev(data['sql'])))
                res = data['result']
        return res


    @staticmethod
    def sort(scripts):
        return scripts.sort(key=operator.attrgetter('order'))

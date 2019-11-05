import operator
import re
from sqlalchemy import text
import click

class LoadScript:
    def __init__(_, filename, **options):
        _.filename = filename
        _.options = {
            'incremental': False,
            'display': False
        }
        _.options.update(options)

        _.order = 100
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



    def execute(_, connection):
        # ses = connection.begin()
        res = None
        row_counts = []
        for sql in _.statements:
            if _.options['display']:
                click.echo(sql)
            res = connection.execute(text(sql))
            #ses.commit()
        return res


    @staticmethod
    def sort(scripts):
        return scripts.sort(key=operator.attrgetter('order'))

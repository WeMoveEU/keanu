import pygments
import pygments.formatters
import pygments.lexers

terminal = pygments.formatters.get_formatter_by_name('console256')
mysql = pygments.lexers.get_lexer_by_name('mysql') 

def highlight_sql(code):
    ends_with_nl = code.endswith("\n")
    c = pygments.highlight(code, mysql, terminal)
    if not ends_with_nl:
        c = c.rstrip()
    return c

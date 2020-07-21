import yaml
from os import path, makedirs, listdir, unlink
from slug import slug
from shutil import rmtree


class sql_code(str):
    """
Wrap SQL code in sql_code() to have it dumped as multi-line string.
    """
    pass

def sql_code_representer(dumper, data):
    """
Registers sql_code as scalar representer of block style (|)
    """
    return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='|')

yaml.add_representer(sql_code, sql_code_representer)

class Splitter:
    """
    Maps between export json file and directory/file structure, wich is easier to maintain in a source repository (to see diffs, merge, etc)

    Requirements:
    - yaml format (more diff friendly, because it's line based)
    - multiline values in block scalar format
    - all the map keys are sorted
    """
    def __init__(_, directory):
        _.directory = directory

    def store(_, json):
        _.clean_directory()
        _.store_mappings(json)
        _.store_datamodel(json)
        _.store_items(json['items'])

    def store_mappings(_, node):
        mappings = node['mappings']

        _.store_to(mappings, 'mappings')

    def store_datamodel(_, node):
        dbs = node['datamodel']['databases']

        for db_spec in dbs.values():
            db_file = slug(db_spec['name'])
            _.store_to(db_spec, 'databases/{}'.format(db_file))

    def store_items(_, items, prefix=[]):
        for idx, i in enumerate(items):
            if i['model'] == 'card' or i['model'] == 'dashboard':
                if i['model'] == 'card':
                    _.format_query_as_block(i)

                file_name = slug(i['name'])
                loc = path.join('items', *prefix, file_name)

                _.store_to(i, loc)

            elif i['model'] == 'collection':
                dir_name = slug(i['name'])
                loc = path.join('items', *prefix, dir_name, '__meta__')

                col_items = i['items']
                del i['items']
                _.store_to(i, loc)
                _.store_items(col_items, prefix + [dir_name])

    def format_query_as_block(_, card):
        if 'dataset_query' in card and 'native' in card['dataset_query']:
            card['dataset_query']['native']['query'] = sql_code(card['dataset_query']['native']['query'])

    def store_to(_, node, loc):
        floc = path.join(_.directory, loc) + '.yaml'
        fdir = path.dirname(floc)
        makedirs(fdir, 0o755, True)

        # Avoid overwriting files if two have the same slug (like card and dashboard)
        floc1 = floc
        idx = 1
        while path.exists(floc1):
            floc1 = "{}-{}".format(floc, idx)
            idx + 1

        with open(floc, 'w') as out:
            yaml.dump(node, stream=out)


    def clean_directory(_):
        if not path.exists(_.directory):
            makedirs(_.directory, 0o755, True)
            return

        for f in listdir(_.directory):
            if f.startswith("."):
                continue
            try:
                unlink(path.join(_.directory, f))
            except IsADirectoryError:
                rmtree(path.join(_.directory, f))

    
    def load(_):
        data = {}

        data['items'] = _.load_items()
        data['datamodel'] = _.load_datamodel()
        data['mappings'] = _.load_from('mappings.yaml')

        return data

    def load_datamodel(_):
        databases = {}
        for f in listdir(path.join(_.directory, 'databases')):
            db = _.load_from(path.join('databases', f))
            databases[str(db['id'])] = db
        return { 'databases': databases }

    def load_items(_, prefix=[]):
        items = []
        ls = listdir(path.join(_.directory, 'items', *prefix))
        ls.sort()
        for f in ls:
            if f == '__meta__.yaml':
                continue

            if path.isdir(path.join(_.directory, 'items', *prefix, f)):
                col = _.load_from(path.join('items', *prefix, f, '__meta__.yaml'))

                col['items'] = _.load_items(prefix + [f])
                items.append(col)
            else:
                item = _.load_from(path.join('items', *prefix, f))
                items.append(item)
        return items


    def load_from(_, loc):
        floc = path.join(_.directory, loc)
        # fdir = path.dirname(floc)
        return yaml.load(open(floc))

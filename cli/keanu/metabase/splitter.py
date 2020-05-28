import yaml
from os import path, makedirs
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
        rmtree(_.directory)
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
        for i in items:
            if i['model'] == 'card' or i['model'] == 'dashboard':
                if i['model'] == 'card':
                    _.format_query_as_block(i)

                file_name = slug(i['name'])
                loc = path.join('items', *prefix, file_name)

                _.store_to(i, loc)

            elif i['model'] == 'collection':
                dir_name = slug(i['name'])
                loc = path.join('items', *prefix, dir_name, '__meta__')

                _.store_to(i, loc)
                _.store_items(i['items'], prefix + [dir_name])

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

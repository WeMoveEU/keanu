#!/usr/bin/env python
import click
from dotenv import load_dotenv
load_dotenv()
import json
from keanu import metabase
from pprint import pprint

@click.group()
def cli():
    pass

@cli.command()
@click.option('-c', '--collection', help="Name of the collection to export")
def export(collection):
    client = metabase.Client()
    source = client.get_by_name('collection', collection)
    result = {
        'items': metabase.get_items(client, source['id']),
    }
    result['mappings'] = metabase.source_mappings(client, result['items'])
    print(json.dumps(result, indent=2))

@cli.command('import')
@click.option('-c', '--collection', help="Name of the collection to import into")
@click.option('-j', '--json-file', help="path to JSON file to import")
def import_json(collection, json_file):
    client = metabase.Client()
    destination = client.get_by_name('collection', collection)
    if len(client.collection_items(destination['id'])) > 0:
        raise Exception("The destination collection is not empty")
    
    with open(json_file, 'r') as f:
        source = json.loads(f.read())

    mappings = metabase.dest_mappings(client, source['mappings'])
    metabase.add_items(client, source['items'], destination['id'], mappings)

if __name__ == '__main__':
    cli()

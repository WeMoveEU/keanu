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
    source = client.collection_by_name(collection)
    result = {
        'items': metabase.get_items(client, source['id']),
    }
    result['mappings'] = metabase.mappings(client, result['items'])
    print(json.dumps(result, indent=2))

@cli.command('import')
@click.option('-c', '--collection', help="Name of the collection to import into")
@click.option('-j', '--json-file', help="path to JSON file to import")
def import_json(collection, json_file):
    client = metabase.Client()
    destination = client.collection_by_name(collection)
    if len(client.collection_items(destination['id'])) > 0:
        raise Exception("The destination collection is not empty")
    
    with open(json_file, 'r') as f:
        source = json.loads(f.read())

    metabase.add_items(client, source['items'], destination)

if __name__ == '__main__':
    cli()

#!/usr/bin/env python
import click
from dotenv import load_dotenv
load_dotenv()
import json
from metabase import Metabase
from pprint import pprint

def collection_by_name(client, collection):
    status, collections = client.get('/collection/')
    if not status:
      raise Exception("Error while retrieving collections")

    collections = list(filter(lambda c: c['name'] == collection, collections))
    if len(collections) == 0:
        raise Exception("No such collection: {}".format(collection))

    return collections[0]

def collection_items(client, collection_id, recurse=True, retrieve=True):
    result = []
    status, items = client.get('/collection/{}/items'.format(collection_id))
    if not status:
      raise Exception("Error while retrieving collection items for collection {}".format(collection_id))

    for i in items:
        if retrieve:
            status, item = client.get('/{}/{}'.format(i['model'], i['id']))
            item['model'] = i['model']
        else:
            item = i
        if recurse and item['model'] == 'collection':
            item['items'] = collection_items(client, item['id'])
        if 'collection_id' not in item:
            item['collection_id'] = collection_id
        result.append(item)

    return result

def load_items(client, items, destination):
    result = []
    for item in items:
        if item['model'] == 'collection':
            result.append(load_collection(client, item, destination))
        elif item['model'] == 'card':
            result.append(load_card(client, item, destination))
            break
    return result

def load_card(client, card, destination):
    params = {k: card[k] for k in card.keys() & ['name', 'description', 'visualization_settings', 'collection_position', 'result_metadata', 'metadata_checksum', 'dataset_query', 'display']}
    pprint(params)
    return {}

def load_collection(client, collection, destination):
    params = {k: collection[k] for k in ['name', 'description', 'color']}
    params['parent_id'] = destination['id']
    status, result = client.post('/collection/', json=params)
    if not status:
        raise Exception("Could not create collection {}".format(params['name']))
    result['items'] = load_items(client, collection['items'], result)
    return result

@click.group()
def cli():
    pass

@cli.command()
@click.option('-c', '--collection', help="Name of the collection to export")
def export(collection):
    client = Metabase()
    result = collection_by_name(collection)
    result['items'] = collection_items(client, collections[0]['id'])
    print(json.dumps(result, indent=2))

@cli.command('import')
@click.option('-c', '--collection', help="Name of the collection to import into")
@click.option('-j', '--json-file', help="path to JSON file to import")
def import_json(collection, json_file):
    client = Metabase()
    destination = collection_by_name(client, collection)
    if len(collection_items(client, destination['id'], False, False)) > 0:
        raise Exception("The destination collection is not empty")
    
    with open(json_file, 'r') as f:
        source = json.loads(f.read())

    load_items(client, source['items'], destination)

if __name__ == '__main__':
    cli()

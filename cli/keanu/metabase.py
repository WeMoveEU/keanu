from metabase import Metabase

class Client:
  def __init__(self):
    self.client = Metabase()

  def get(self, model, model_id):
    status, item = self.client.get('/{}/{}'.format(model, model_id))
    if not status:
      raise Exception("Error while retrieving {} {}".format(model, model_id))
    return item

  def collection_items(self, cid):
    status, items = self.client.get('/collection/{}/items'.format(cid))
    if not status:
      raise Exception("Error while retrieving collection items for collection {}".format(cid))
    return items

  def collection_by_name(self, collection):
    status, collections = self.client.get('/collection/')
    if not status:
      raise Exception("Error while retrieving collections")

    collections = list(filter(lambda c: c['name'] == collection, collections))
    if len(collections) == 0:
      raise Exception("No such collection: {}".format(collection))

    return collections[0]

  def add_card(self, card, collection_id):
    params = {k: card[k] for k in card.keys() & ['name', 'description', 'visualization_settings', 'collection_position', 'result_metadata', 'metadata_checksum', 'dataset_query', 'display']}
    params['collection_id'] = collection_id
    status, result = self.client.post('/card/', json=params)
    if not status:
      raise Exception("Could not create card {}".format(params['name']))
    return result

  def add_collection(self, collection, parent_id):
    params = {k: collection[k] for k in ['name', 'description', 'color']}
    params['parent_id'] = parent_id
    status, result = self.client.post('/collection/', json=params)
    if not status:
      raise Exception("Could not create collection {}".format(params['name']))
    result['items'] = add_items(self, collection['items'], result)
    return result

def get_items(client, collection_id):
    result = []
    items = client.collection_items(collection_id)

    for i in items:
      item = client.get(i['model'], i['id'])
      item['model'] = i['model']
      if item['model'] == 'collection':
        item['items'] = get_items(client, item['id'])
      if 'collection_id' not in item:
        item['collection_id'] = collection_id
      result.append(item)

    return result

def add_items(client, items, destination):
    result = []
    for item in items:
      if item['model'] == 'collection':
        result.append(client.add_collection(item, destination['id']))
      elif item['model'] == 'card':
        result.append(client.add_card(item, destination['id']))
        break
    return result

def add_card_mappings(client, card, mappings):
  if 'dataset_query' in card:
    query = card['dataset_query']
    if 'database' in query:
      dbid = query['database']
      mappings['databases'][dbid] = client.get('database', dbid)['name']

def mappings(client, items, result = None):
    if result is None:
      result = {'databases': {}}
    for item in items:
      if item['model'] == 'collection':
        result = mappings(client, item['items'], result)
      elif item['model'] == 'card':
        add_card_mappings(client, item, result)
    return result


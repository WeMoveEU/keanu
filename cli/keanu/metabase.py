from metabase import Metabase

class Client:
  def __init__(self):
    self.client = Metabase()

  def get(self, model, model_id, subquery = None):
    if subquery is None:
      query = '/{}/{}'.format(model, model_id)
    else:
      query = '/{}/{}/{}'.format(model, model_id, subquery)
    status, item = self.client.get(query)
    if not status:
      if subquery is None:
        msg = "Error while retrieving {} {}".format(model, model_id)
      else:
        msg = "Error while retrieving {} for {} {}".format(subquery, model, model_id)
      raise Exception(msg)
    return item

  def get_by_name(self, model, name):
    status, models = self.client.get('/{}/'.format(model))
    if not status:
      raise Exception("Error while retrieving {}s".format(model))

    models = list(filter(lambda m: m['name'] == name, models))
    if len(models) == 0:
      raise Exception("No such {}: {}".format(model, name))

    return models[0]

  def collection_items(self, cid):
    status, items = self.client.get('/collection/{}/items'.format(cid))
    if not status:
      raise Exception("Error while retrieving collection items for collection {}".format(cid))
    return items

  def add_card(self, card, collection_id):
    card['collection_id'] = collection_id
    status, result = self.client.post('/card/', json=card)
    if not status:
      raise Exception("Could not create card {}".format(card['name']))
    return result

  def add_collection(self, collection, parent_id):
    params = {k: collection[k] for k in ['name', 'description', 'color']}
    params['parent_id'] = parent_id
    status, result = self.client.post('/collection/', json=params)
    if not status:
      raise Exception("Could not create collection {}".format(params['name']))
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


def add_items(client, items, collection_id, mappings):
    result = []
    for item in items:
      if item['model'] == 'collection':
        c = client.add_collection(item, collection_id)
        c['items'] = add_items(client, item['items'], c['id'], mappings)
        result.append(c)
      elif item['model'] == 'card':
        card = deref_card(item, mappings)
        result.append(client.add_card(item, collection_id))
    return result

def add_card_mappings(client, card, mappings):
  if 'dataset_query' in card:
    dquery = card['dataset_query']
    if 'database' in dquery:
      db_id = dquery['database']
      if db_id not in mappings['databases']:
        mappings['databases'][db_id] = {
          'name': client.get('database', db_id)['name'],
          'tables': {}
        }

      if 'query' in dquery:
        query = dquery['query']
        if 'source-table' in query:
          table_id = query['source-table']
          if table_id not in mappings['databases'][db_id]['tables']:
            mappings['databases'][db_id]['tables'][table_id] = {
              'name': client.get('table', table_id)['name'],
              'fields': {}
            }
          if 'expressions' in query:
            for exp in query['expressions'].values():
              for factor in exp:
                if isinstance(factor, list) and factor[0] == 'field-id':
                  mappings['databases'][db_id]['tables'][table_id]['fields'][factor[1]] = client.get('field', factor[1])['name']

def deref_card(card, mappings):
  card = {k: card[k] for k in card.keys() & ['name', 'description', 'visualization_settings', 'collection_position', 'result_metadata', 'metadata_checksum', 'dataset_query', 'display']}

  if 'dataset_query' in card:
    dquery = card['dataset_query']
    if 'database' in dquery:
      db_id = dquery['database']
      dquery['database'] = mappings['databases'][db_id]

      if 'query' in dquery:
        query = dquery['query']
        if 'source-table' in query:
          table_id = query['source-table']
          query['source-table'] = mappings['tables'][table_id]

          if 'expressions' in query:
            for exp in query['expressions'].values():
              for factor in exp:
                if isinstance(factor, list) and factor[0] == 'field-id':
                  factor[1] = mappings['fields'][factor[1]]
  return card

def source_mappings(client, items, result = None):
  if result is None:
    result = {'databases': {}}
  for item in items:
    if item['model'] == 'collection':
      result = mappings(client, item['items'], result)
    elif item['model'] == 'card':
      add_card_mappings(client, item, result)
  return result

def dest_mappings(client, source_map):
  result = {'databases': {}, 'tables': {}, 'fields': {}}
  for db_id, db in source_map['databases'].items():
    dest_db = client.get_by_name('database', db['name'])
    result['databases'][int(db_id)] = dest_db['id']

    db_data = client.get('database', dest_db['id'], 'metadata')
    for table_id, table in db['tables'].items():
      dest_table = list(filter(lambda t: t['name'] == table['name'], db_data['tables']))
      if len(dest_table) == 0:
        raise Exception("Table {} could not be mapped".format(table['name']))
      dest_table = dest_table[0]
      result['tables'][int(table_id)] = dest_table['id']

      for field_id, field_name in table['fields'].items():
        dest_field = list(filter(lambda f: f['name'] == field_name, dest_table['fields']))
        if len(dest_field) == 0:
          raise Exception("Field {} could not be mapped".format(field_name))
        result['fields'][int(field_id)] = dest_field[0]['id']

  return result


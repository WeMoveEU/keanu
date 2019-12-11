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
    return self.get('collection', cid, 'items')

  def add_card(self, card, collection_id):
    card['collection_id'] = collection_id
    status, result = self.client.post('/card/', json=card)
    if not status:
      raise Exception("Could not create card {}".format(card['name']))
    return result

  def add_dashboard(self, dashboard, collection_id):
    dashboard['collection_id'] = collection_id
    status, result = self.client.post('/dashboard/', json=dashboard)
    if not status:
      raise Exception("Could not create dashboard {}".format(dashboard['name']))
    return result

  def add_dashboard_card(self, card, dashboard_id):
    status, result = self.client.post('/dashboard/{}/cards'.format(dashboard_id), json=card)
    if not status:
      raise Exception("Could not add card {} to dashboard {}".format(card['cardId'], dashboard_id))
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
        created_card = client.add_card(card, collection_id)
        if item['id'] in mappings['cards']:
          mappings['cards'][item['id']] = created_card['id']
        result.append(created_card)
      elif item['model'] == 'dashboard':
        dashboard = deref_dashboard(item, mappings)
        d = client.add_dashboard(item, collection_id)
        d = add_dashboard_cards(client, dashboard['ordered_cards'], d)
        result.append(d)
    return result

def add_dashboard_cards(client, cards, dashboard):
  dashboard['ordered_cards'] = []
  for card in cards:
    c = client.add_dashboard_card(card, dashboard['id'])
    dashboard['ordered_cards'].append(c)
  return dashboard

def deref(obj, prop, mapping):
  obj[prop] = mapping[obj[prop]]

def add_table_mapping(client, db_id, table_id, mappings):
  if table_id not in mappings['databases'][db_id]['tables']:
    table = client.get('table', table_id)
    mappings['databases'][db_id]['tables'][table_id] = {
      'name': table['name'],
      'fields': {}
    }

def add_fields_mapping(client, expression, mappings):
  for factor in expression:
    if isinstance(factor, list):
      if factor[0] == 'field-id':
        field_id = factor[1]
        field = client.get('field', field_id)
        db_id = field['table']['db_id']
        table_id = field['table_id']
        if db_id not in mappings['databases']:
          mappings['databases'][db_id] = { 'name': field['table']['db']['name'], 'tables': {} }
        if table_id not in mappings['databases'][db_id]['tables']:
          mappings['databases'][db_id]['tables'][table_id] = { 'name': field['table']['name'], 'fields': {} }
        mappings['databases'][db_id]['tables'][table_id]['fields'][field_id] = field['name']
      else:
        add_fields_mapping(client, factor, mappings)

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
          add_table_mapping(client, db_id, table_id, mappings)

        for exp in query.get('expressions', {}).values():
          add_fields_mapping(client, exp, mappings)

        for join in query.get('joins', []):
          table_id = join['source-table']
          add_table_mapping(client, db_id, table_id, mappings)
          add_fields_mapping(client, join['condition'], mappings)

        add_fields_mapping(client, query.get('filter', []), mappings)
        add_fields_mapping(client, query.get('order-by', []), mappings)

def deref_fields(expression, mappings):
  for factor in expression:
    if isinstance(factor, list):
      if factor[0] == 'field-id':
        factor[1] = mappings['fields'][factor[1]]
      else:
        deref_fields(factor, mappings)

def deref_card(card, mappings):
# skipping 'result_metadata', 
  card = {k: card[k] for k in card.keys() & ['name', 'description', 'visualization_settings', 'collection_position', 'metadata_checksum', 'dataset_query', 'display']}

  if 'dataset_query' in card:
    dquery = card['dataset_query']
    if 'database' in dquery:
      dquery['database'] = mappings['databases'][dquery['database']]

      if 'query' in dquery:
        query = dquery['query']
        if 'source-table' in query:
          query['source-table'] = mappings['tables'][query['source-table']]

          for exp in query.get('expressions', {}).values():
            deref_fields(exp, mappings)

        for join in query.get('joins', []):
          join['source-table'] = mappings['tables'][join['source-table']]
          deref_fields(join['condition'], mappings)

        deref_fields(query.get('filter', []), mappings)
        deref_fields(query.get('order-by', []), mappings)
            
  return card

def add_dashboard_mappings(client, dashboard, mappings):
  for card in dashboard['ordered_cards']:
    if card['card_id'] not in mappings['cards']:
      mappings['cards'][card['card_id']] = 'to_be_created'

    for pm in card['parameter_mappings']:
      pm['card_id'] = card['card_id']
      for target_spec in pm['target']:
        if isinstance(target_spec, list):
          add_fields_mapping(client, target_spec, mappings)

def deref_dashboard(dashboard, mappings):
  dashboard = {k: dashboard[k] for k in dashboard.keys() & ['name', 'description', 'parameters', 'collection_position', 'ordered_cards']}
  for c, card in enumerate(dashboard['ordered_cards']):
    card = {k: card[k] for k in card.keys() & ['card_id', 'parameter_mappings', 'series', 'row', 'col', 'sizeX', 'sizeY']}
    card['card_id'] = mappings['cards'][card['card_id']]
    card['cardId'] = card['card_id']  # Inconsistency in dashboard API

    for pm in card['parameter_mappings']:
      pm['card_id'] = card['card_id']
      for target_spec in pm['target']:
        if isinstance(target_spec, list):
          deref_fields(target_spec, mappings)

    dashboard['ordered_cards'][c] = card
  return dashboard

def source_mappings(client, items, result = None):
  if result is None:
    result = {'databases': {}, 'cards': {}}
  for item in items:
    if item['model'] == 'collection':
      source_mappings(client, item['items'], result)
    elif item['model'] == 'card':
      add_card_mappings(client, item, result)
    elif item['model'] == 'dashboard':
      add_dashboard_mappings(client, item, result)
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

  result['cards'] = { int(k): v for k, v in source_map['cards'].items() }

  return result


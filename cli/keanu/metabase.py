from metabase import Metabase

class Client:
  """
    Wrapper around Metabase client for not having to deal with response status
    and to provide shorcut methods
  """

  def __init__(self):
    self.client = Metabase()

  def get(self, model, model_id, subquery = None):
    """
      Generic get method to retrieve a specific object or sub-objects
    """
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
    """
      Retrieve an object by name.
      Search done on the client side, so watch out if there are many objects of that model
    """
    status, models = self.client.get('/{}/'.format(model))
    if not status:
      raise Exception("Error while retrieving {}s".format(model))

    models = list(filter(lambda m: m['name'] == name, models))
    if len(models) == 0:
      raise Exception("No such {}: {}".format(model, name))

    return models[0]

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

  def add_dimension(self, dimension, field_id):
    status, result = self.client.post('/field/{}/dimension'.format(field_id), json=dimension)
    if not status:
      raise Exception("Could not add dimension to field {}".format(field_id))
    return result

  def update_field(self, field_id, params):
    status = self.client.put('/field/{}'.format(field_id), json=params)
    if not status:
      raise Exception("Could not update field {}".format(field_id))


class MetabaseIO:
  """
    This class holds the logic to export and import metabase objects to/from a JSON file
  """
  def __init__(self, client):
    self.client = client

  def export_json(self, collection):
    """
      Generate dictionary representation of JSON export file for all the items of the given collection name
    """
    source = self.client.get_by_name('collection', collection)
    result = {
        'items': self.get_items(source['id']),
    }
    result['datamodel'] = self.get_datamodel(result['items'])
    mapper = Mapper(self.client)
    result['mappings'] = mapper.add_cards(result['items'])
    return result

  def import_json(self, source, collection, with_metadata=False):
    """
      Create in the given collection name all the items of the source data (dictionary representation of JSON export).
      If `with_metadata` is True, the extra metadata about the model is also imported
    """
    has_items = len(source['items']) > 0
    if has_items:
      destination = self.client.get_by_name('collection', collection)
      if len(self.client.get('collection', destination['id'], 'items')) > 0:
          raise Exception("The destination collection is not empty")

    if has_items or with_metadata:
      mapper = Mapper(self.client)
      mappings = mapper.resolved_mappings(source['mappings'], source['datamodel'])
      if with_metadata:
        self.import_metadata(source['datamodel'], mappings)
      if has_items:
        self.add_items(source['items'], destination['id'], mappings)
    
  def get_items(self, collection_id):
    """
      Recursively retrieve the items of a collection and return the nested list of items.
      Make sure each item has a model and collection_id properties
    """
    result = []
    items = self.client.get('collection', collection_id, 'items')

    for i in items:
      item = self.client.get(i['model'], i['id'])
      item['model'] = i['model']
      if item['model'] == 'collection':
        item['items'] = self.get_items(item['id'])
      if 'collection_id' not in item:
        item['collection_id'] = collection_id
      result.append(item)

    return result

  def import_metadata(self, datamodel, mappings):
    for db in datamodel['databases'].values():
      for table in db['tables'].values():
        for field in table['fields'].values():
          dest_field_id = mappings['fields'][field['id']]

          field_values = field.get('has_field_values', 'none')
          if field_values != 'none':
            self.client.update_field(dest_field_id, { 'has_field_values': field_values })

          if 'dimensions' in field:
            dest_field = self.client.get('field', dest_field_id)
            if 'dimensions' not in dest_field:
              self.client.add_dimension(field['dimensions'], dest_field_id)

  def add_items(self, items, collection_id, mappings, only_model='all', result=[]):
    """
      Create the given items into the given collection.
      Collections are created recursively.
      The `mappings` parameter holds the information to translate db, table, field and card ids
      in the context of current Metabase instance. The object may be modified with ids of card created during the process.
      Return the nested list of created items.
    """
    if only_model == 'all':
      self.add_items(items, collection_id, mappings, 'collection', result)
      self.add_items(items, collection_id, mappings, 'card', result)
      self.add_items(items, collection_id, mappings, 'dashboard', result)
    else:
      for item in items:
        if item['model'] == 'collection':
          if only_model == 'collection':
            c = self.client.add_collection(item, collection_id)
            mappings['collections'][item['id']] = c['id']
            c['items'] = []
            result.append(c)
          else:
            c = next(filter(lambda r: r['id'] == mappings['collections'][item['id']], result))
          self.add_items(item['items'], c['id'], mappings, only_model, c['items'])

        elif item['model'] == 'card' and only_model == 'card':
          card = deref_card(item, mappings)
          created_card = self.client.add_card(card, collection_id)
          mappings['cards'][item['id']] = created_card['id']
          result.append(created_card)

        elif item['model'] == 'dashboard' and only_model == 'dashboard':
          dashboard = deref_dashboard(item, mappings)
          d = self.client.add_dashboard(item, collection_id)
          d = self.add_dashboard_cards(dashboard['ordered_cards'], d)
          result.append(d)

    return result

  def add_dashboard_cards(self, cards, dashboard):
    dashboard['ordered_cards'] = []
    for card in cards:
      c = self.client.add_dashboard_card(card, dashboard['id'])
      dashboard['ordered_cards'].append(c)
    return dashboard

  def get_datamodel(self, items):
    db_ids = self.get_database_ids(items)
    result = { 'databases': {} }
    for db_id in db_ids:
      result['databases'][db_id] = self.db_data(self.client.get('database', db_id, 'metadata'))
    return result

  def get_database_ids(self, items, result = None):
    if result is None:
      result = set()

    for item in items:
      if item['model'] == 'collection':
        self.get_database_ids(item['items'], result)
      elif item['model'] == 'card':
        result.add(item['database_id'])

    return result

  def db_data(self, db):
    f_db = { k: db[k] for k in ['id', 'name'] }
    f_db['tables'] = {}

    for table in db['tables']:
      f_table = { k: table[k] for k in ['id', 'name'] }
      f_table['fields'] = {}
      f_db['tables'][table['id']] = f_table

      for field in table['fields']:
        if field['special_type'] == 'type/FK':
          # If the field may have dimensions, retrieve the fields to get them
          field = self.client.get('field', field['id'])

        f_field = { k: field[k] for k in ['id', 'name', 'has_field_values'] }
        if 'dimensions' in field and len(field['dimensions']) > 0:
          f_field['dimensions'] = { k: field['dimensions'][k] for k in ['type', 'name', 'human_readable_field_id'] }

        f_table['fields'][field['id']] = f_field

    return f_db

class Mapper:
  """
    Functions to record and translate all the ids of an export file
  """
  def __init__(self, client):
    self.client = client

  def add_cards(self, items, result = None):
    """
      Browse recursively a nested list of items and record into `result` the ids
      that will need to be translated during import.
      If `result` is not given, a new dictionary is created.
      Return the updated result.
    """
    if result is None:
      result = {'cards': {}}

    for item in items:
      if item['model'] == 'collection':
        self.add_cards(item['items'], result)
      elif item['model'] == 'dashboard':
        for card in item['ordered_cards']:
          if 'card_id' not in card or card['card_id'] is None:
            card['card_id'] = card['id']
          if card['card_id'] not in result['cards']:
            result['cards'][card['card_id']] = 'source_card_' + str(card['card_id'])

    return result

  def add_table(self, db_id, table_id, mappings):
    if str(table_id).startswith('card__'):
      # The table is actually a saved question
      card_id = int(table_id[6:])
      if card_id not in mappings['cards']:
        mappings['cards'][card_id] = 'source_card_' + str(card_id)
    elif table_id not in mappings['databases'][db_id]['tables']:
      table = self.client.get('table', table_id)
      mappings['databases'][db_id]['tables'][table_id] = {
        'name': table['name'],
        'fields': {}
      }

  def add_fields(self, expression, mappings):
    if isinstance(expression, list):
      if len(expression) == 2 and expression[0] == 'field-id':
        field_id = expression[1]
        field = self.client.get('field', field_id)
        db_id = field['table']['db_id']
        table_id = field['table_id']
        if db_id not in mappings['databases']:
          mappings['databases'][db_id] = { 'name': field['table']['db']['name'], 'tables': {} }
        if table_id not in mappings['databases'][db_id]['tables']:
          mappings['databases'][db_id]['tables'][table_id] = { 'name': field['table']['name'], 'fields': {} }
        mappings['databases'][db_id]['tables'][table_id]['fields'][field_id] = field['name']
      else:
        for factor in expression:
          self.add_fields(factor, mappings)

  def add_card(self, card, mappings):
    if 'dataset_query' in card:
      dquery = card['dataset_query']
      if 'database' in dquery:
        db_id = dquery['database']
        if db_id not in mappings['databases']:
          mappings['databases'][db_id] = {
            'name': self.client.get('database', db_id)['name'],
            'tables': {}
          }

        if 'query' in dquery:
          query = dquery['query']
          if 'source-table' in query:
            table_id = query['source-table']
            self.add_table(db_id, table_id, mappings)

          for exp in query.get('expressions', {}).values():
            self.add_fields(exp, mappings)

          for join in query.get('joins', []):
            table_id = join['source-table']
            self.add_table(db_id, table_id, mappings)
            self.add_fields(join['condition'], mappings)

          self.add_fields(query.get('fields', []), mappings)
          self.add_fields(query.get('filter', []), mappings)
          self.add_fields(query.get('breakout', []), mappings)
          self.add_fields(query.get('order-by', []), mappings)
          
        if 'native' in dquery and 'template-tags' in dquery['native']:
          for tag in dquery['native']['template-tags'].values():
            self.add_fields(tag['dimension'], mappings)

  def add_dashboard(self, dashboard, mappings):
    for card in dashboard['ordered_cards']:
      if 'card_id' not in card or card['card_id'] is None:
        card['card_id'] = card['id']
      if card['card_id'] not in mappings['cards']:
        mappings['cards'][card['card_id']] = 'source_card_' + str(card['card_id'])

      for pm in card['parameter_mappings']:
        pm['card_id'] = card['card_id']
        for target_spec in pm['target']:
          if isinstance(target_spec, list):
            self.add_fields(target_spec, mappings)

          
  def resolved_mappings(self, source_map, datamodel):
    """
      Translates all the ids found in source_map into corresponding ids for the current Metabase instance
      Return a dictionary { model => { source_id => translated_id } }
      Cards are not resolved because they can only be resolved while creating them
    """
    result = {'databases': {}, 'tables': {}, 'fields': {}}

    for db_id, db in datamodel['databases'].items():
      dest_db = self.client.get_by_name('database', db['name'])
      result['databases'][int(db_id)] = dest_db['id']

      db_data = self.client.get('database', dest_db['id'], 'metadata')
      for table_id, table in db['tables'].items():
        dest_table = list(filter(lambda t: t['name'] == table['name'], db_data['tables']))
        if len(dest_table) == 0:
          raise Exception("Table {} could not be mapped".format(table['name']))
        dest_table = dest_table[0]
        result['tables'][int(table_id)] = dest_table['id']

        for field_id, field in table['fields'].items():
          dest_field = list(filter(lambda f: f['name'] == field['name'], dest_table['fields']))
          if len(dest_field) == 0:
            raise Exception("Field {} could not be mapped".format(field['name']))
          result['fields'][int(field_id)] = dest_field[0]['id']

    result['cards'] = { int(k): v for k, v in source_map['cards'].items() }
    result['collections'] = {}

    return result

def deref(obj, prop, mapping):
  obj[prop] = mapping[obj[prop]]

def deref_table(table_id, mappings):
  if str(table_id).startswith('card__'):
    return mappings['cards'][int(table_id[6:])]
  else:
    return mappings['tables'][table_id]

def deref_fields(expression, mappings):
  if isinstance(expression, list):
    if len(expression) == 2 and expression[0] == 'field-id':
      expression[1] = mappings['fields'][expression[1]]
    else:
      for factor in expression:
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
          query['source-table'] = deref_table(query['source-table'], mappings)

          for exp in query.get('expressions', {}).values():
            deref_fields(exp, mappings)

        for join in query.get('joins', []):
          join['source-table'] = deref_table(join['source-table'], mappings)
          deref_fields(join['condition'], mappings)

        deref_fields(query.get('fields', []), mappings)
        deref_fields(query.get('filter', []), mappings)
        deref_fields(query.get('breakout', []), mappings)
        deref_fields(query.get('order-by', []), mappings)

      if 'native' in dquery and 'template-tags' in dquery['native']:
        for tag in dquery['native']['template-tags'].values():
          deref_fields(tag['dimension'], mappings)
            
  return card

def deref_dashboard(dashboard, mappings):
  dashboard = {k: dashboard[k] for k in dashboard.keys() & ['name', 'description', 'parameters', 'collection_position', 'ordered_cards']}
  for c, card in enumerate(dashboard['ordered_cards']):
    card = {k: card[k] for k in card.keys() & ['card_id', 'parameter_mappings', 'series', 'row', 'col', 'sizeX', 'sizeY', 'visualization_settings']}
    card['card_id'] = mappings['cards'][card['card_id']]
    if not is_virtual_card(card):
      card['cardId'] = card['card_id']  # Inconsistency in dashboard API

    if 'series' in card:
      for s, serie in enumerate(card['series']):
        card_id = mappings['cards'][serie['id']]
        serie = deref_card(serie, mappings)
        serie['id'] = card_id
        card['series'][s] = serie

    for pm in card['parameter_mappings']:
      pm['card_id'] = card['card_id']
      for target_spec in pm['target']:
        if isinstance(target_spec, list):
          deref_fields(target_spec, mappings)

    dashboard['ordered_cards'][c] = card
  return dashboard

def is_virtual_card(card):
  """
    Tell whether the given card object represents a virtual dashboard card (text cards)
  """
  return 'visualization_settings' in card and 'virtual_card' in card['visualization_settings']


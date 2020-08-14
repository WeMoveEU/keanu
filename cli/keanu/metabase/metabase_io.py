import copy
import json
import logging
import re

from .helpers import *

metabase_io_log = logging.getLogger('metabase.io')

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

  def import_json(self, source, collection, with_metadata=False, overwrite=False, db_map=[]):
    """
      Create in the given collection name all the items of the source data (dictionary representation of JSON export).
      If `with_metadata` is True, the extra metadata about the model is also imported
    """
    has_items = len(source['items']) > 0
    if has_items:
      destination = self.client.get_by_name('collection', collection)
      if not overwrite and len(self.client.get('collection', destination['id'], 'items')) > 0:
          raise Exception("The destination collection is not empty")

    if has_items or with_metadata:
      mapper = Mapper(self.client)
      mappings = mapper.resolved_mappings(source['mappings'], source['datamodel'], overwrite, destination['id'], db_map)
      if has_items:
        self.add_items(source['items'], destination['id'], mappings, mapper)
      if with_metadata:
        self.import_metadata(source['datamodel'], mappings, mapper)
    
  def get_items(self, collection_id):
    """
      Recursively retrieve the items of a collection and return the nested list of items.
      Make sure each item has a model and collection_id properties
    """
    result = []
    items = self.client.get('collection', collection_id, 'items')

    for i in items:
      metabase_io_log.info("⬇️ {} {}: {}".format(i['model'], i['id'], i.get('name', '')))
      item = self.client.get(i['model'], i['id'])
      item['model'] = i['model']
      item = Trimmer.trim_data(item)

      if item['model'] == 'collection':
        item['items'] = self.get_items(item['id'])
      if 'collection_id' not in item:
        item['collection_id'] = collection_id
      result.append(item)

    return result

  def import_metadata(self, datamodel, mappings, mapper):
    for db in datamodel['databases'].values():
      for table in db['tables'].values():
        for field in table['fields'].values():
          dest_field_id = mappings['fields'][field['id']]

          update_attrs = {}
          field_values = field.get('has_field_values', 'none')
          if field_values != 'none':
            update_attrs['has_field_values'] = field_values

          special_type = field.get('special_type', None)
          if special_type is not None:
            update_attrs['special_type'] = special_type

          fk_target_field_id = field.get('fk_target_field_id', None)
          if fk_target_field_id is not None:
            update_attrs['fk_target_field_id'] = mappings['fields'][fk_target_field_id]

          if 'settings' in field:
            update_attrs['settings'] = field['settings']
          
          if update_attrs:
            metabase_io_log.info("🏷️ setting custom field values for {}.{}: {}".format(table['name'], field['name'], update_attrs))
            self.client.update_field(dest_field_id, update_attrs)

          if 'dimensions' in field:
            dest_field = self.client.get('field', dest_field_id)

            dimensions = field['dimensions'].copy()
            if 'human_readable_field_id' in dimensions:
              mapper.deref(dimensions, 'human_readable_field_id', mappings['fields'])

            metabase_io_log.info("🏷️ setting custom dimensions for {}.{}: {}".format(table['name'], field['name'], dimensions))
            # XXX should we not always update this ?  what if dimensions change ?
            # if 'dimensions' not in dest_field:
            self.client.add_dimension(dimensions, dest_field_id)

  def add_items(self, items, collection_id, mappings, mapper, only_model='all', result=[]):
    """
      Create the given items into the given collection.
      Collections are created recursively.
      The `mappings` parameter holds the information to translate db, table, field and card ids
      in the context of current Metabase instance. The object may be modified with ids of card created during the process.
      Return the nested list of created items.
    """
    if only_model == 'all':
      self.add_items(items, collection_id, mappings, mapper, 'collection', result)
      self.add_items(items, collection_id, mappings, mapper, 'card', result)
      self.add_items(items, collection_id, mappings, mapper, 'dashboard', result)
      if len(mapper.missing_mapping_cards) > 0:
        # Some cards refer to dashboards that were imported after the card, update them now
        for card in mapper.missing_mapping_cards:
          c = next(filter(lambda r: r['id'] == mappings['collections'][card['collection_id']], result))
          self.add_items([card], c['id'], mappings, mapper, 'card', c['items'])

    else:
      for item in items:
        if item['model'] == 'collection':
          # Inserting collection
          # 
          # Please note:
          #      ,- ITEMS -                             ,- RESULT -
          #      |  coll  ----> INSERT or UPDATE ---->  |  coll (shallow copy)
          #      |  card  ----> new id is given  ---->  |  card (same dict!)
          #      |  dash  ----> or from mapping  ---->  |  dash (same dict!)
          # items hold dicts with source ids, whereas result holds items with destination ids
          # For collection, we need to have a copy of the item because the source collections
          # are used when inserting cards and dashboards.
          # When we overwrite, we do an explicit shallow copy, when we create a new collection,
          # we will get a new dict back.
          # For cards and dashboards this is not so important because we use them only once,
          # but this code will modify cards and dashboards also in items (in source data).
          # This can lead to errors if caution is not taken. Immutable data structures would be
          # useful here.
          if only_model == 'collection':
            # Is this an only-collection phase? If so, get or create the collection
            metabase_io_log.info("⬆️ {} {}: {}".format(item['model'], item['id'], item['name']))
            if item['id'] in mappings['collections']:
              dst_item = item.copy() # shallow copy is fine
              mapper.deref(dst_item, 'id', mappings['collections'])
              c = self.client.update_collection(dst_item, collection_id)
            else:
              c = self.client.add_collection(item, collection_id)
              mappings['collections'][item['id']] = c['id']
            c['items'] = []
            result.append(c)
          else:
            # Is this non-collection insert phase? Get the collection id that was created
            c = next(filter(lambda r: r['id'] == mappings['collections'][item['id']], result))

          # Whether its collection or non-collection phase, add all items with
          # destination collection as parent
          self.add_items(item['items'], c['id'], mappings, mapper, only_model, c['items'])

        elif item['model'] == 'card' and only_model == 'card':
          metabase_io_log.info("⬆️ {} {}: {}".format(item['model'], item['id'], item['name']))
          card = mapper.deref_card(item, mappings)

          if item['id'] in mappings['cards']:
            card['id'] = mappings['cards'][item['id']]
            upserted_card = self.client.update_card(card, collection_id)
          else:
            upserted_card = self.client.add_card(card, collection_id)
          mappings['cards'][item['id']] = upserted_card['id']
          result.append(upserted_card)

        elif item['model'] == 'dashboard' and only_model == 'dashboard':
          metabase_io_log.info("⬆️ {} {}: {}".format(item['model'], item['id'], item['name']))
          exists = item['id'] in mappings['dashboards']

          mapper.deref_dashboard(item, mappings)
          if exists:
            mapper.deref(item, 'id', mappings['dashboards'])
            d = self.client.update_dashboard(item, collection_id)
            self.client.clear_dashboard(d)
          else:
            d = self.client.add_dashboard(item, collection_id)
            mappings['dashboards'][item['id']] = d['id']
          d = self.add_dashboard_cards(item['ordered_cards'], d)
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
    """
    Search items for cards (questions), recursively scanning collections, and
    return a set of database_id's the cards are using.
    """
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
      f_table = { k: table[k] for k in ['id', 'name', 'description', 'display_name'] }
      f_table['fields'] = {}
      f_db['tables'][table['id']] = f_table

      for field in table['fields']:
        if field['special_type'] == 'type/FK':
          # If the field may have dimensions, retrieve the fields to get them
          field = self.client.get('field', field['id'])

        f_field = { k: field[k] for k in ['id', 'name', 'has_field_values', 'description', 'display_name', 'settings', 'special_type', 'fk_target_field_id'] }
        if 'dimensions' in field and len(field['dimensions']) > 0:
          f_field['dimensions'] = { k: field['dimensions'][k] for k in ['type', 'name', 'human_readable_field_id'] }

        # see https://github.com/metabase/metabase/blob/master/src/metabase/api/field.clj#L221
        if f_field['has_field_values'] == 'list' or f_field['has_field_values'] == 'type/Boolean':
          f_field['values'] = self.client.get('field', field['id'], 'values')['values']

        f_table['fields'][field['id']] = f_field

    return f_db

class Mapper:
  """
    Functions to record and translate all the ids of an export file
  """
  def __init__(self, client):
    self.client = client
    self.missing_mapping_cards = []

  def add_cards(self, items, result = None):
    """
      Browse recursively a nested list of items and record into `result` the ids
      that will need to be translated during import.
      If `result` is not given, a new dictionary is created.
      Return the updated result.
    """
    if result is None:
      result = {'cards': {}, 'collections': {}, 'dashboards': {}, 'databases': {}}

    for item in items:
      if item['model'] == 'collection':
        result['collections'][item['id']] = { 'name': item['name'] }
        self.add_cards(item['items'], result)
      elif item['model'] == 'dashboard':
        result['dashboards'][item['id']] = { 'name': item['name'] }
      elif item['model'] == 'card':
        result['cards'][item['id']] = { 'name': item['name'] }
        self.add_card(item, result)

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
        next    # text card, wholly embedded, no mapping is needed
      #   card['card_id'] = card['id']  
      if card['card_id'] not in mappings['cards']:
        mappings['cards'][card['card_id']] = 'source_card_' + str(card['card_id'])

      for pm in card['parameter_mappings']:
        pm['card_id'] = card['card_id']
        for target_spec in pm['target']:
          if isinstance(target_spec, list):
            self.add_fields(target_spec, mappings)

  def resolved_mappings(self, source_map, datamodel, overwrite, collection_id, db_map):
    """Translates all the ids found in source_map into corresponding ids for the
    current Metabase instance Return a dictionary { model => { source_id =>
    translated_id } }

      When overwrite is True, cards, collections and dashboards are found by
      name under collection_id in destination MB.

      When overwrite is False, these are not resolved because their id will be
      known after creating them. They will be added to mapping on the go.

    """
    result = {'databases': {}, 'tables': {}, 'fields': {},
              'cards': {}, 'collections': {}, 'dashboards': {}}

    for db_id, db in datamodel['databases'].items():
      dest_db = self.client.get_by_name('database', db_map.get(db['name'], db['name']))
      result['databases'][int(db_id)] = dest_db['id']

      db_data = self.client.get('database', dest_db['id'], 'metadata')
      for table_id, table in db['tables'].items():
        dest_table = list(filter(lambda t: t['name'] == table['name'], db_data['tables']))
        if len(dest_table) == 0:
          raise Exception("Table {}.{} could not be mapped".format(db['name'], table['name']))
        dest_table = dest_table[0]
        result['tables'][int(table_id)] = dest_table['id']

        for field_id, field in table['fields'].items():
          dest_field = list(filter(lambda f: f['name'] == field['name'], dest_table['fields']))
          if len(dest_field) == 0:
            raise Exception("Field {}.{}.{} could not be mapped".format(db['name'], table['name'], field['name']))
          result['fields'][int(field_id)] = dest_field[0]['id']

    if overwrite:
      def col_location(cid):
        return '/' if cid == 'root' else "/{}/".format(cid)

      # map name->id in destination, for collections, cards, and dashboards
      # only for items that are under destination collection
      collection_names_to_id = {
        col['name']: col['id']
        for col in self.client.get('collection')
        if col_location(collection_id) in col.get('location', '')
      }

      collection_ids = set(collection_names_to_id.values())
      # The collection ids are going to be compared to ids returned by the API, so they need to be api_collection_id'ed
      # But this affects only the root collection, and we know that root collection cannot be listed in the imported one
      # so only `collection_id` needs this treatment
      collection_ids.add(api_collection_id(collection_id))

      card_names_to_id = {
        card['name']: card['id']
        for card in self.client.get('card')
        if card["collection_id"] in collection_ids
      }

      dashboard_names_to_id = {
        dash['name']: dash['id']
        for dash in self.client.get('dashboard')
        if dash["collection_id"] in collection_ids
      }

      # now iterate throught source items and build src id->dest id using names
      result['cards'] = {
        int(k): card_names_to_id[v['name']]
        for k, v in source_map['cards'].items()
        if v['name'] in card_names_to_id
      }

      result['collections'] = {
        int(k): collection_names_to_id[v['name']]
        for k, v in source_map['collections'].items()
        if v['name'] in collection_names_to_id
      }

      result['dashboards'] = {
        int(k): dashboard_names_to_id[v['name']]
        for k, v in source_map['dashboards'].items()
        if v['name'] in dashboard_names_to_id
      }

    return result

  def deref(self, obj, prop, mapping):
    obj[prop] = mapping[obj[prop]]

  def deref_table(self, table_id, mappings):
    if str(table_id).startswith('card__'):
      return mappings['cards'][int(table_id[6:])]
    else:
      return mappings['tables'][table_id]

  def deref_fields(self, expression, mappings):
    if isinstance(expression, list):
      if len(expression) == 2 and expression[0] == 'field-id':
        expression[1] = mappings['fields'][expression[1]]
      else:
        for factor in expression:
          self.deref_fields(factor, mappings)
    elif isinstance(expression, dict):
      for factor in expression.values():
        self.deref_fields(factor, mappings)

  def deref_column_setting_key(self, cs, mappings):
    if cs.startswith('["ref",["field-id",'):
      csobj = json.loads(cs)
      try:
        csobj = ["ref", ["field-id", mappings['fields'][csobj[1][1]]]]
      except KeyError:
        # There could be stale column_settings that have orphan field-id
        # e.g. referring to archived card
        return cs
      return json.dumps(csobj)
    else:
      return cs

  def deref_column_settings(self, col_settings, mappings, for_card):
    '''Check if custom link contains a dashboard URL, and replace its id with the mapped one.
    As column settings may refer to a dashboard and as dashboards are imported after cards,
    the mapping for the referenced dashboard may not be available yet. In such a case,
    the column setting is not deref'ed and the card id (for_card) is queued, to fix the reference after
    dashboards are imported.
    '''
    if col_settings is not None and 'link_url' in col_settings:
      col_settings = col_settings.copy()
      url = col_settings['link_url']
      m = re.search('/dashboard/(\d+)', url)
      if m is not None:
        ref_id = int(m.group(1))
        if ref_id in mappings['dashboards']:
          url = url.replace(m.group(1), str(mappings['dashboards'][ref_id]))
          col_settings['link_url'] = url
        elif for_card['id'] not in map(lambda c: c['id'], self.missing_mapping_cards):
          self.missing_mapping_cards.append(for_card)

    return col_settings

  def deref_card(self, card, mappings):
    original_card = card
    card = copy.deepcopy(original_card)

    if 'dataset_query' in card:
      dquery = card['dataset_query']
      if 'database' in dquery:
        dquery['database'] = mappings['databases'][dquery['database']]

        if 'query' in dquery:
          query = dquery['query']
          if 'source-table' in query:
            query['source-table'] = self.deref_table(query['source-table'], mappings)

            for exp in query.get('expressions', {}).values():
              self.deref_fields(exp, mappings)

          for join in query.get('joins', []):
            join['source-table'] = self.deref_table(join['source-table'], mappings)
            self.deref_fields(join['condition'], mappings)
            self.deref_fields(join.get('fields', []), mappings)

          self.deref_fields(query.get('fields', []), mappings)
          self.deref_fields(query.get('filter', []), mappings)
          self.deref_fields(query.get('breakout', []), mappings)
          self.deref_fields(query.get('order-by', []), mappings)
          self.deref_fields(query.get('aggregation', []), mappings)

        if 'native' in dquery and 'template-tags' in dquery['native']:
          for tag in dquery['native']['template-tags'].values():
            self.deref_fields(tag['dimension'], mappings)

    if 'visualization_settings' in card:
      vs = card['visualization_settings']
      if 'column_settings' in vs:
        vs['column_settings'] = {
          self.deref_column_setting_key(k, mappings): self.deref_column_settings(v, mappings, original_card)
          for k,v in vs['column_settings'].items()
        }

      if 'table.columns' in vs:
        self.deref_fields(vs['table.columns'], mappings)

    return card

  def deref_dashboard(self, dashboard, mappings):
    dashboard = {k: dashboard[k] for k in dashboard.keys() & ['name', 'description', 'parameters', 'collection_position', 'ordered_cards']}
    for c, card in enumerate(dashboard['ordered_cards']):
      card = {k: card[k] for k in card.keys() & ['card_id', 'parameter_mappings', 'series', 'row', 'col', 'sizeX', 'sizeY', 'visualization_settings']}

      if not is_virtual_card(card):
        card['card_id'] = mappings['cards'][card['card_id']]
        card['cardId'] = card['card_id']  # Inconsistency in dashboard API

      if 'series' in card:
        for s, serie in enumerate(card['series']):
          card_id = mappings['cards'][serie['id']]
          serie = self.deref_card(serie, mappings)
          serie['id'] = card_id
          card['series'][s] = serie

      for pm in card['parameter_mappings']:
        pm['card_id'] = card['card_id']
        for target_spec in pm['target']:
          if isinstance(target_spec, list):
            self.deref_fields(target_spec, mappings)

      dashboard['ordered_cards'][c] = card
    return dashboard

def broken_cards(items, datamodel, broken=set()):
  def check_field(card, fld_id, db_id):
    if not datamodel_has_field(datamodel, db_id, fld_id):
      broken.add((card['id'], card['name']))
        
  def check_query(card, values, db_id):
    for v in values:
      if isinstance(v, dict):
        check_query(card, v.values(), db_id)
      elif isinstance(v, list):
        if v[0] == 'field-id':
          check_field(card, v[1], db_id)
        else:
          check_query(card, v, db_id)

  for item in items:
    if item['model'] == 'collection':
      broken_cards(item['items'], datamodel, broken)
    elif item['model'] == 'card':
      if item['query_type'] == 'query':
        dq = item['dataset_query']
        db_id = dq['database']
        dqq = dq['query']
        check_query(item, dqq.values(), db_id)

  return broken

def broken_dashboards(items, broken=set()):
  def find_card(items, card_id):
    for item in items:
      if item['model'] == 'card' and item['id'] == card_id:
        return item
      elif item['model'] == 'collection':
        cf = find_card(item['items'], card_id)
        if cf:
          return cf
    return None

  for dash in filter(lambda i: i["model"] == "dashboard", items):
    for card in dash['ordered_cards']:
      if is_virtual_card(card):
        continue
      if find_card(items, card['card_id']) is None:
        broken.add((dash["id"], dash["name"], card['card_id']))
        
  for col in filter(lambda i: i["model"] == "collection", items):
    broken_dashboards(col["items"], broken)

  return broken

def broken_datamodel(datamodel, broken=set()):
  all_field_ids = set()
  for database in datamodel['databases'].values():
    for table in database["tables"].values():
      for fid in table['fields'].keys():
        all_field_ids.add(int(fid))

  for database in datamodel['databases'].values():
    for table in database["tables"].values():
      for field in table['fields'].values():
        if 'dimentions' in field and 'human_readable_field_id' in field['dimentions']:
          if field['dimentions']['human_readable_field_id'] not in all_field_ids:
            broken.add((field["id"],
                        "{}.{}".format(table['name'], field['name']),
                        "dimension set to nonexistent field id {}".format(field['dimentions']['human_readable_field_id'])))

        if 'fk_target_field_id' in field and field['fk_target_field_id'] is not None:
          if field['fk_target_field_id'] not in all_field_ids:
            broken.add((field["id"], "{}.{}".format(table['name'], field['name']),
                        "FK target does not exist (id {})".format(field['fk_target_field_id'])))
    return broken



def datamodel_has_field(datamodel, db_id, fld_id):
  db = datamodel['databases'][str(db_id)]
  for table in db['tables'].values():
    if str(fld_id) in table['fields']:
      return True
  return False

          


def is_virtual_card(card):
  """
    Tell whether the given card object represents a virtual dashboard card (text cards)
  """
  return 'visualization_settings' in card and 'virtual_card' in card['visualization_settings']

class Trimmer:
  keep_card_keys = [
    'id',
    'model',
    'visualization_settings',
    'description',
    'collection_position',
    'metadata_checksum',
    'collection_id',
    'name',
    'dataset_query',
    'display',
    'query_type',
    'database_id'
  ]

  keep_dashboard_keys = [
    'id',
    'model',
    'name',
    'description',
    'parameters',
    'collection_id',
    'collection_position',
    'dashboard',
    'ordered_cards'
  ]

  keep_collection_keys = [
    'id',
    'model',
    'name',
    'color',
    'description',
    'parent_id'
  ]

  keep_dashboard_card_keys = [
    'card_id',
    'parameter_mappings',
    'series',
    'row',
    'col',
    'sizeX',
    'sizeY',
    'visualization_settings'
  ]

  @staticmethod
  def trim_data(item, keep_keys=None):
    if keep_keys is None:
      if item['model'] == 'card':
        keep_keys = Trimmer.keep_card_keys
      elif item['model'] == 'collection':
        keep_keys = Trimmer.keep_collection_keys
      elif item['model'] == 'dashboard':
        keep_keys = Trimmer.keep_dashboard_keys
      else:
        raise Exception('Do not know how to trim_data on hash with no known model key')

    trimmed = { k:  item[k] for k in item if k in keep_keys }

    if 'ordered_cards' in trimmed:
      trimmed['ordered_cards'] = filter(lambda c: c.get('card', {}).get('archived', False) == False, trimmed['ordered_cards'])
      trimmed['ordered_cards'] = list(map(lambda c: Trimmer.trim_data(c, Trimmer.keep_dashboard_card_keys), trimmed['ordered_cards']))

    return trimmed


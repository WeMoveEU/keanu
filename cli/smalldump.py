#!/usr/bin/env python

import argparse
import pymysql
import os

user = os.environ['USER']
parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('source_db', help="The CiviCRM database to dump and reduce")
parser.add_argument('-u', '--user', default=user, help="DB user to query the information schema")
parser.add_argument('-p', '--password', help="DB password to query the information schema")
opts = parser.parse_args()

def get_references(cursor, source_db, limit_table, column, table_pattern):
  cursor.execute("""SELECT {} FROM key_column_usage
    WHERE referenced_table_schema=%s AND referenced_table_name=%s AND referenced_column_name='id'
    AND table_schema=%s AND table_name LIKE %s""".format(column), 
    [source_db, limit_table, source_db, table_pattern])
  return single_col_values(cursor)

def get_mailing_senders(cursor, source_db):
  cursor.execute("SELECT DISTINCT scheduled_id FROM {}.civicrm_mailing WHERE scheduled_id IS NOT NULL".format(source_db))
  return single_col_values(cursor)

def single_col_values(result, col=0):
  return list(map(lambda r: r[col], result))

def column_condition(column, required_contacts, limit_factor):
  params = {
    'c': column,
    'cids': ','.join(map(str, required_contacts)),
    'modulo': limit_factor
  }
  return '{c} < 100 OR {c} IN ({cids}) OR {c} % {modulo} = 0'.format(**params)

def where(columns, required_contacts, limit_factor):
  conditions = map(lambda c: column_condition(c, required_contacts, limit_factor), columns)
  where = ') AND ('.join(conditions)
  if len(where) > 0:
    return '--where "({})"'.format(where)
  else:
    return ''


source_db = opts.source_db
table_pattern = 'civicrm%'
limit_table = 'civicrm_contact'
limit_factor = 11
indirect_tables = {
  'civicrm_activity': 'civicrm_activity_contact', 
  'civicrm_mailing_event_delivered': 'civicrm_mailing_event_queue',
  'civicrm_mailing_event_opened': 'civicrm_mailing_event_queue',
  'civicrm_mailing_event_trackable_url_open': 'civicrm_mailing_event_queue',
  'civicrm_mailing_event_unsubscribe': 'civicrm_mailing_event_queue',
  'civicrm_mailing_event_bounce': 'civicrm_mailing_event_queue'
}

connection = pymysql.connect(host='localhost', user=opts.user, password=opts.password, db='information_schema', unix_socket='/var/run/mysqld/mysqld.sock')
with connection:
  cursor = connection.cursor()
  contact_tables = get_references(cursor, source_db, limit_table, 'table_name', table_pattern)
  wemove_contacts = get_mailing_senders(cursor, source_db)

  cursor.execute("SELECT table_name FROM tables WHERE table_schema=%s AND table_name LIKE %s", [source_db, table_pattern])
  for table in single_col_values(cursor):
    if table in indirect_tables.keys():
      link_table = indirect_tables[table]
      if link_table == 'civicrm_activity_contact':
        where_option = '--where "id IN (SELECT activity_id FROM civicrm_activity_contact WHERE {})"'.format(column_condition('contact_id', wemove_contacts, limit_factor))
      elif link_table == 'civicrm_mailing_event_queue':
        where_option = '--where "event_queue_id IN (SELECT id FROM civicrm_mailing_event_queue WHERE {})"'.format(column_condition('contact_id', wemove_contacts, limit_factor))

    else:
      if table in contact_tables:
        columns = get_references(cursor, source_db, limit_table, 'column_name', table)
        if table == limit_table:
          columns = ['id'] + columns
      else:
        columns = []
      where_option = where(columns, wemove_contacts, limit_factor)

    print("mysqldump --single-transaction {} {} {} >> smalldump.sql".format(where_option, source_db, table))

print('echo "--- DONE: dumpfile available in smalldump.sql"')

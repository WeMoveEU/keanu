import os
from urllib.parse import urlparse
from sqlalchemy import create_engine


database_url = os.getenv('DATABASE_URL')
schema_name = urlparse(database_url).path[1:]

def engine(url = database_url):
  return create_engine(url)

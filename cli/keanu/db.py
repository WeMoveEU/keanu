import os
from urllib.parse import urlparse
from sqlalchemy import create_engine


database_url = os.getenv('DATABASE_URL')
engine = create_engine(database_url)
schema_name = urlparse(database_url).path[1:]

FROM python:3.5

# -- Install dependencies: --
# - pipenv to create python environment
# - dumb-init as docker init process
RUN pip3 install pipenv
RUN apt-get update && apt-get install -y \
  dumb-init \
 && rm -rf /var/lib/apt/lists/*

# -- Create directories for app and loaders --
RUN set -ex && mkdir /app && mkdir -p /queries/civicrm && mkdir -p /queries/currency && mkdir -p /metabase
WORKDIR /app

# -- Add app to container, and install deps --
ADD cli /app
RUN set -ex && pipenv install --deploy --system

# -- Set up docker runtime --
ADD docker-entrypoint.sh /app
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# -- Add loader files --
ADD erd/keanu-schema.sql /queries/
ADD erd/currency-schema.sql /queries/
ADD loaders/civicrm_currency /queries/currency
ADD loaders/civicrm /queries/civicrm

# -- Add metabase file --
ADD metabase/datapoc.json /metabase/keanu-mb.json

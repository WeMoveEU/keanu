FROM python:3.5

RUN pip3 install pipenv
RUN apt-get update && apt-get install -y \
  dumb-init \
 && rm -rf /var/lib/apt/lists/*


RUN set -ex && mkdir /app && mkdir -p /queries/civicrm && mkdir -p /queries/currency

ADD docker-entrypoint.sh /app

ADD cli /app

WORKDIR /app
ENTRYPOINT ["/app/docker-entrypoint.sh"]

RUN set -ex && pipenv install --deploy --system

ADD erd/keanu-schema.sql /queries/
ADD currency_sql /queries/currency
ADD sql /queries/civicrm

ADD keanu.yaml /app
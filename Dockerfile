FROM python:3.5

RUN pip3 install pipenv

RUN set -ex && mkdir /app && mkdir -p /queries/civicrm && mkdir -p /queries/currency

ADD cli /app

WORKDIR /app

RUN set -ex && pipenv install --deploy --system

ADD erd/keanu-schema.sql /queries/
ADD currency_sql /queries/currency
ADD sql /queries/civicrm


# Project Keanu

Welcome to Project Keanu!

![](https://media.giphy.com/media/MC6eSuC3yypCU/source.gif)

Project Keanu consists of:
- ETL tool to run the queries
- Metabase setup tool (mainly import/export of questions, dashboards) 

## Metabase import/export tool

Keanu CLI app contains subcommand `keanu metabase` that allows to export and import collections of Metabase questions and dashboards.


# Keanu CLI

Keanu command lives in `cli` directory. It is a multitool consisting of following subcommands:

- `schema` - create tables from keanu schema in a database, or drop tables from a database.
- `load` - runs loaders to load data into destination db from source(s). It can run in full or incremental mode. Can run loaders all at once or in steps.
- `delete` - deletes data loaded by particular loader. Lets you "rewind" the work done by a particular loader (only full mode). This way you can "step back" in loading data.
- `metabase` - export, import collections from/to Metabase, query the REST GET api of Metabase. 

![](doc/img/keanu-load.png)

## Setup

1. Install Pipenv command in your system: `sudo apt install pipenv`
2. Install dependencies in `cli` directory: `pipenv install`

## Configuration

Depending on subcommand, you configure keanu cli with:
1. environment variables (mostly for credentials eg API keys, or access urls, eg. url to database with user, pass, hostname, db name)
2. configuration YAML file (when more structured configuration is needed eg. to specify sources and destination for loaders, as well as which loaders are used)
3. command line switches and arguments

### Environment variables reference

1. API keys and Database access urls

Keanu uses metabase API in its metabase subcommand. Define Metabase url, username and password with these variables:

- `METABASE_ENDPOINT` - url of Metabase instance with scheme, eg: https://data.awesome.com
- `METABASE_AUTH_EMAIL` - email for login
- `METABASE_AUTH_PASSWORD` - password for login

Keanu uses Database credentials in form of database url in format suitable for SQLalchemy. Because keanu can have many sources and another destination, the urls are provided using a yaml configuration. 

### Configuration file

The configuration file must have `.yaml` extension and contain alist of elements that define sources of data, destination of data, and transforms, which run a series of loaders.
You provide the configuration file as a positional argument to `load` or `delete` subcommands.

#### Source

The source should have a name, and db specification can either be url or schema. In case that source is the same db as destination, we say it is _local_ to that destination, and we can provide just schema name using `schema` key. You can use `${VARIABLE}` syntax to insert env variables (so, for instance, you do not store database credentials in configuration file).

Example: source with database url, named _foobarcrm_
```
- source:
    name: foobarcrm
    db:
      url: ${DATABASE_URL}
```

Example: source in the same DB as destination, but in `exchange_rates` database
```
- source:
    name: currency_data
    db:
    schema: exchange_rates
```

#### Destination

There can be only one destination in the config file (so there is no need to give it a name). The SQL transforms are run
In the destination DB (they are SQL statements run on the DB server). This means
sources must be local to the destination for SQL loaders. Keanu cannot yet
stream data from one DB and insert it to another DB, but this is a feature we
would like to develop in the feature (in this case the transform should run in
the source and return a dataset that can be directly inserted to the
destination).

The python loaders run inside the keanu cli process, and download/upload data. They can use different db servers for sources and destination.

Example:
```
- destination:
    db:
      url: ${DATABASE_URL}
```

#### Transform

The transform points to directory with loaders and specifies their type. Transform is applied to one source and one destination. Because there can be many sources, transform should specify name of the sources under `source` key. Transform can point to `directory` or just one `file`.

Example: transform will execute all SQL files found under `some/directory`. It will use `foobarcrm` as source.
```
- transform:
    source: foobarcrm
    sql:
      directory: some/directory
```

Example: a transform using just one python loader file.
```
- transform:
    source: foobarcrm
    py:
      file: python_scripts/conversions.py
```

1. You can  Copy the `cli/.env.sample` file to `.env` and change it to taste. 
### Default setting

However, keanu can also run with minamal default configuration.
Running `keanu load sql_files` is equal to `keanu load config1.yaml` with `config1.yaml`:


```
- source:
    db:
      schema: ${SOURCE}
- destination:
    db:
      url: ${DATABASE_URL}
- transform:
    sql:
       directory: ${ARGV[1]}
```

- `DATABASE_URL` - must use schema understood by SQLAlchemy library, required for load and delete subcommands
- `SOURCE` - is a name of CiviCRM database (also called schema), required only for SQL loaders

## Usage

Keanu commands has a set of subcommands, similar to git or heroku.

## Running from source

Install dependencies using `pipenv insall` and open shell with needed requirements with `pipenv shell`.

## Package building

To build the package use `python setup.py bdist_wheel`.

To upload it to PyPI:

1. Create a `~/.pypirc` file:
```
[distutils] 
index-servers=pypi
[pypi] 
repository = https://upload.pypi.org/legacy/ 
username = pypi-username
```

To install the package locally:

```pip install --upgrade dist/keanu-0.1-py3-none-any.whl```

2. Use `python -m twine upload dist/*`.

### SQL commands

These are the commands related to creating and filling in the Keanu schema (from CiviCRM DB).

#### schema: manipulating database schema

- `keanu.py schema -L FILENAME` - loads SQL schema file.
- `keanu.py schema -D` - drops all tables from the database.

#### load: loading data

`keanu.py load CONFIGFILE` loads data from source to destination db in ordered steps. The queries to run are specified in the configuration file.
Currently we support two kinds of loaders:

- SQL loader - consists of SQL file, containing special metadata in comments. It is run in the destination database server, and the source data must be available on the same server (in another database/schema).
- Python loader - consists of Python file, and is run on the local machine. Keanu bundles sqlalchemy and pandas libraries in case you need them. 

Loaders are run in order specified in each loader's metadata (`ORDER` key), unless they are ingored (`IGNORE` key). See other metadata keys in sql and py loader reference.

Options:

- `-o 10:` - _order_, start from SQL file with order 10 (also see order spec)
- `-n` - _dry run_, do not execute the SQL. Usefull to see the order of scripts
- `-i` - _incremental_, also run the incremental parts of the SQL, normally deleted (they are marked by `-- BEGIN INCREMENTAL` and `-- END INCREMENTAL` comments)
- `-d` - _display_ a whole SQL statement instead of abbreviation of first line

#### delete: deleting data

`keanu.py delete SQLDIR` will go through the SQL scripts in _reverse order_ and execute the commented `DELETE` and `TRUNCATE` statements in the scripts. 

Options:

- `-n` - _dry run_, do not execute the SQL. Usefull to see the order of scripts
- `-o 10:` - delete data until the SQL file _order_ (inclusive) and stop
- `-d` - _display_ a whole SQL statement instead of abbreviation of first line

#### Order spec

You can provide just a number to order (`-o`) option, but you can also provide:
- a list of numbers such as `10,11,50` and scripts with respective order will be run
- a range in python format such as `10:16` equal to `10,11,12,13,14,15` (excluding 16)
- a mix of them: `10:13,31,50:52`


#### SQL file reference:

We add metadata to SQL files in SQL comments. This is usefull because you can still work with the SQL files using tools like MySQL Workbench, or mysql command - the commands will be ignored.

Supported commands are:

`-- ORDER: arg` - arg should be a 3 digit number. It specifies the order this script will be run.
`-- DELETE FROM .. ` - a DELETE statement will be saved to revert this script, so to remove all the data it has added. Must start with all caps DELETE.
`-- TRUNCATE` - similar to above. Please note: TRUNCATE will fail if any other table has reference to this table, even when it's empty.
`-- IGNORE` - the rest of the file will be ignored.

Blocks are also supported. They are marked by a pair of lines: 

```sql
-- BEGIN keyword
 .. some SQL code here..
-- END keyword
```

They should be properly nested.

Supported blocks are:
- `BEGIN INCREMENTAL` / `END INCREMENTAL` - marks part of the SQL that will normally be removed, and will be only used if `-i` (incremental flag) is used while loading. You can have many INCREMENTAL blocks. Example use:

```sql
-- this scripts inserts into cookie jar
-- ORDER: 10
-- DELETE FROM jar

INSERT INTO jar (colour, size, external_id)
SELECT
  cd.name, 
  c.size,
  c.id
FROM cookie c
JOIN colour_dictionary cd ON c.colour_id = cd.id

-- when we do incremental, we exclude external_id's we already have:
-- BEGIN INCREMENTAL
WHERE c.id NOT IN (SELECT external_id FROM jar)
-- END INCREMENTAL

```

- `BEGIN INITIAL` / `END INITIAL` - marks part of the SQL that will be removed in incremental `-i` mode.

Enviroment variable interpolation. Similar to shell, simple variable interpolation is supported. `${FOO}` will be interpolated into value of FOO environment variable. This is currently used to insert the source schema name with `${SOURCE}`.

### Metabase commands

These are the commands to export / import Metabase questions and dashboards that are related to the Keanu schema

#### Export

`keanu.py metabase export` generates a JSON dump of all the data required to import the collections / dashboards / questions given in options.

The generated JSON is printed on standard output. It contains a property `items` with the list of objects that got exported, as well as a property `mappings` with information to translate ids that make sense only in the context of a Metabase instance (table ids, card ids, etc).

Options:
 - `-c "Some collection"` - Exports all the questions and dashboards contained in the named collection and its child collections. You should ensure that the dashboards refer only to questions contained within that collection, unless you plan to import the data within the same Metabase instance. The collection must exist.

#### Import

`keanu.py metabase import` reads a JSON dump generated by the export command and import the object into a Metabase instance.

Options:
 - `-c "Some collection"` - The name of the collection into which the objects should be imported. The collection must exist and be empty (no support for overwrite / merge at the moment).
 - `-j /path/to/file.json` - The JSON file to import.

### Contributing

TODO

#### Code Linting and Formatting

A pylint configuration is in pylintrc - configure your editor to run it automatically. Use black for formatting.

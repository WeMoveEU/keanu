# Project Keanu

Welcome to Project Keanu!

![](https://media.giphy.com/media/MC6eSuC3yypCU/source.gif)

Project Keanu constist of:
- Handbook for analytic terms, metrics and their definitions,
- Common data model for campaign evaluation,
- Set of queries to load data from sources (Currently CiviCRM, Identity in the future) to common data model
- ETL tool to run the queries
- Set of queries to visualize metrics and key indicators in Metabase
- Metabase setup tool (mainly import/export of questions, dashboards) 


## Handbook

The handbook is not part of this repository. It is developed within WeMove wiki. The release data is unknown.

## Common data model

We have developed a common, standard model based on our experience in online
campaigning. It should allow to accommodate most if not all of analytical data
used to display key indicators to your campaign team. If something is missing
for you - you can easily extend it.

![](doc/img/keanu-erd.svg)

The model is defined as _MySQL Workbench_ project in `erd/keanu-erd.mwb`, and
exported to MySQL SQL dile in `erd/keanu-schema.sql`. We realize the limitation
of MySQL only workfiles, yet we were unable to find portable ERD IDE that would
fit our needs. The schema can be transformed to PostgreSQL using analyze
database tool in an IDE that supports PostgreSQL. Ideally, we should develop
further in some portable format.

A basic documentation for tables and columns is embedded in the schema, in table
and column comment metadata.

## Loader queries

Under `queries` directory, you will find subdirectories with loaders for
different data sources. At the time of writing, we are using CiviCRCM and both
sources are using it as a source.

Loaders are meant to be single-concern files which transform source data into
destination database (keanu database). One loader can populate the contacts
table, or actions table from particular source. A loader has one destination db
(usually with Keanu schema), and one source.

Currently we support two kinds of loaders:

- SQL loader - consists of SQL file, containing special metadata in comments. It is run in the destination database server, and the source data must be available on the same server (in another database/schema).
- Python loader - consists of Python file, and is run on the local machine. Keanu bundles sqlalchemy and pands libraries in case you need them. Right now keanu does not contain sqlalchemy definitions of keanu schema, so you will need to use sqlalchemy.core instead of the ORM.

Loaders are run in order specified in each loader's metadata (`ORDER` key), unless they are ingored (`IGNORE` key). See other metadata keys in sql and py loader reference.

## ETL tool to run queries

The `cli` directory contains command line python app, publishd in PyPI as `keanu-etl`, which lets you run loaders agains source and destination database in two modes - full load and incremental load (meant to just load new data from source to destination), load keanu schema, and delete it. See Keanu CLI.

## Set of queries to visualize metrics and key indicators in Metabase

Under `metabase` you can find an export of questions and dashboard collections used to visualize data from a Keanu database. 

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

### Environment reference

1. You can  Copy the `cli/.env.sample` file to `.env` and change it to taste. 

- `DATABASE_URL` - must use schema understood by SQLAlchemy library, required for load and delete subcommands
- `SOURCE` - is a name of CiviCRM database (also called schema), required only for SQL related commands
- `METABASE_ENDPOINT`, `METABASE_AUTH_EMAIL`, `METABASE_AUTH_PASSWORD` - Metabase credentials, required only metabase commands

## Usage

Keanu commands has a set of subcommands, similar to git or heroku.
You need to enable the Pipenv, by running `pipenv shell`.

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

`keanu.py load SQLDIR` loads data from CiviCRM to keanu db in ordered steps. Every SQL file in `SQLDIR` directory has `-- ORDER: 12` comment which specifies an order. The default order is 100.

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

## Product vision

Right now during initial development, we run keanu command from the source
directory `cli`, and the SQL scripts are kept in `sql`. The vision for the
future product is the following:

Keanu will be a command installed gloablly into the system, with `pip install
keanu`. It will work like git or heroku, a multi-tool to do everything
conntected to common DB model, ETL, running AI logic, installing dashboards in
Metabase (this last function fits this command least, but let's see).

It will download a repository of SQL files, properly divided between general
use, CiviCRM users, Identity users, etc, and be able to configure itself with
`keanu setup` - saving information about source and target DBs. It will be able
also to upload SQL files that were changed and verion manage them somehow, to
help in collaboration (this could be done using git).

Similarly, it will enable import and export of Metabase questions (called
_cards_) and dashboards. Not only their SQL, but also their JSON configuration
(using [python Metabase API client
library](https://github.com/stunitas/metabase-py)).


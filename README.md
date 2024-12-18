# Offer Database Repository

This file explains about basics regarding databases of [Offer][1] project. List of this file contents can be seen here:

* [Running database containers locally](#run-locally)
* [Deploying databases to server](#deployment-manual)
* [Updating databases schema](#updating-schema)

## Run Locally

...

## Deployment Manual

...

## Updating Schema

In order to update schema of existing database run following 
commands in python interactive console:

```python
>>> from db import *
>>> Base.metadata.drop_all(pg_engine)
#   ^ this drops all database contents, so don't use it in production
>>> Base.metadata.create_all(pg_engine)
```

As already mentioned, in order for this to work, database must not contain any tables, that's why we drop all of them there. This happens because SQLAlchemy doesn't support migrations as of now. If you want to save data that already exists in database, you should:

1. Store old data in another database.
2. Update schema of required database.
3. Manually migrate old data to new database. 


[1]: https://github.com/PyotrAndreev/best-opportunity-provider

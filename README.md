# Funding Backend Flask

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Installing

A step by step series of examples that tell you how to get a development env running

initialize virtual environment

```
python -m venv venv
```

activiate virtual environment

```
source venv/bin/activate
```

install requirements

```
pip install -r requirements.txt
```
initialize database connection

```
python manage.py db init
```

any time there are updates to the database schema


```
python manage.py db migrate —message ‘migration’

python manage.py db upgrade

```
run project

```
python run.py

```
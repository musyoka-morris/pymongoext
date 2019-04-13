Quick Start
************

Pymongoext is an ORM-like Pymongo extension that adds json schema validation,
index management and intermediate data manipulators.
Pymongoext simplifies working with MongoDB, while maintaining a syntax very identical to Pymongo.

``pymongoext.Model`` is simply a wrapper around ``pymongo.Collection``.
As such, all of the pymongo.Collection API is exposed through pymongoext.Model.
If you don't find what you want in the pymongoext.Model API,
please take a look at pymongo's Collection documentation.

Features
=========

- schema validation (which uses MongoDB JSON Schema validation)
- schema-less feature
- nested and complex schema declaration
- untyped field support
- required fields validation
- default values
- custom validators
- operator for validation (OneOf, AllOf, AnyOf, Not)
- indexes management
- data manipulators (transform documents before saving and after retrieval)
- Easy to create custom data manipulators
- object-like results instead of dict-like. (i.e. foo.bar instead of foo['bar'])
- No custom-query language or API to learn (If you know how to use pymongo, you already know how to use pymongoext)

Examples
=========
Some simple examples of what pymongoext code looks like:

.. highlight:: python
.. code-block:: python

    from datetime import datetime
    from pymongo import MongoClient, IndexModel
    from pymongoext import *


    class User(Model):
        @classmethod
        def db(cls):
            return MongoClient()['my_database_name']

        __schema__ = DictField(dict(
            email=StringField(required=True),
            name=StringField(required=True),
            yob=IntField(minimum=1900, maximum=2019)
        ))

        __indexes__ = [IndexModel('email', unique=True), 'name']

        class AgeManipulator(Manipulator):
            def transform_outgoing(self, doc, model):
                doc['age'] = datetime.now().year - doc['yob']
                return doc


    # Create a user
    >>> User.insert_one({'email': 'jane@gmail.com', 'name': 'Jane Doe', 'yob': 1990})

    # Fetch one user
    >>> user = User.find_one()

    # Print the users age
    >>> print(user.age)


Contents
=========

.. toctree::
   :maxdepth: 2

   self
   guides
   install
   api_reference


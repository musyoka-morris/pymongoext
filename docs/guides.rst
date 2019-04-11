Guides
**********

.. currentmodule:: pymongoext

Getting Started
==================

Before we start, make sure that a copy of `MongoDB <https://www.mongodb.com/downloads>`_
is running in an accessible location.
If you haven’t installed pymongoext, simply use pip to install it like so::

   $ pip install pymongoext

Every Model subclass need implement the :meth:`pymongoext.model.Model.db` method which returns a
valid pymongo database instance.
To achieve this, we advice creating a base model class that implements the ``db()`` method.

.. highlight:: python
.. code-block:: python

   from pymongo import MongoClient
   from pymongoext import Model

   class BaseModel(Model):
       @classmethod
       def db(cls):
           return MongoClient()['my_database_name']

Now all concrete models would extend this class.


Defining our documents
=========================

MongoDB is `schemaless`, which means that no schema is enforced by the database —
we may add and remove fields however we want and MongoDB won’t complain.
This makes life a lot easier in many regards, especially when there is a change to the data model.
However, defining schemas for our documents can help to iron out bugs involving incorrect types
or missing fields, and also allow us to define utility methods on our documents in the same way
that traditional ORMs do.

Users Model
~~~~~~~~~~~
Just as if we were using a relational database with an ORM,
we need to define which fields a User may have (**schema**), and what types of data they might store.

.. highlight:: python
.. code-block:: python

   from pymongoext import DictField, StringField, IntField

   class User(BaseModel):
      __schema__ = DictField(dict(
         email=StringField(required=True),
         first_name=StringField(required=True),
         last_name=StringField(required=True),
         yob=IntField(minimum=1900, maximum=2019)
      ))

Indexes
===========
MongoDB supports `secondary indexes <https://docs.mongodb.com/manual/indexes/>`_.
With pymongoext, we define these indexes as a list within our Model on the ``__indexes__`` variable.
Both Single Field and compound indexes are supported.

.. highlight:: python
.. code-block:: python

   from pymongo import IndexModel

   class User(BaseModel):
      .....
      __indexes__ = [IndexModel('email', unique=True), 'first_name']

This example creates a **unique** index on ``email`` and an index on ``first_name``.

Single Field descending index
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Suppose we wanted the index on ``first_name`` to be sorted in a descending manner.
That could be achieved as follows

   >>> ('first_name', pymongo.DESCENDING)

Alternatively, we could also create a descending index by prefixing the field name with a ``-`` sign

   >>> '-first_name'

Compound indexes
~~~~~~~~~~~~~~~~~~
A compound index is simply a list of single field indexes.
Therefore, to create a compound index on ``first_name`` and ``last_name`` sorted in opposite directions


.. highlight:: python
.. code-block:: python

   from pymongo import IndexModel

   class User(BaseModel):
      .....
      __indexes__ = [
         IndexModel('email', unique=True),
         ['-first_name', '+last_name'] # compound index
      ]

Note the ``-`` and ``+`` signs which specify the index on first_name and last_name should be sorted in
descending and ascending order respectively.

Manipulators
================

Manipulators are useful for manipulating (adding, removing, modifying) document properties
before being persisted to MongoDB and after retrieval.
A manipulator has two methods ``transform_incoming`` and ``transform_outgoing``.

Suppose you want to print out the person's full name. You could do it yourself:


.. highlight:: python
.. code-block:: python

   user = User.find_one()
   print("{} {}".format(user['first_name'], user['last_name']))

But concatenating the first and last name every time can get cumbersome.
And what if you want to do some extra processing on the name, like removing diacritics?
A Manipulator lets you define a virtual property ``full_name`` that won't get persisted to MongoDB.


.. highlight:: python
.. code-block:: python

   from pymongoext.manipulators import Manipulator

   class User(BaseModel):
      .....
      class FullNameManipulator(Manipulator):
         def transform_outgoing(self, doc, model):
            doc['full_name'] = "{} {}".format(user['first_name'], user['last_name'])
            return doc

         def transform_incoming(self, doc, model, action):
            if 'full_name' in doc:
               del doc['full_name']  # Don't persist full name
            return doc

Now, every document you retrieve will have a full_name property.

.. highlight:: python
.. code-block:: python

   user = User.find_one()
   print(user['full_name'])

Parametrized Manipulator
~~~~~~~~~~~~~~~~~~~~~~~~~
A manipulator is bind to a Model as either a manipulator class or object.
The later is necessary when using manipulators that are initialized with parameters.

Suppose you had a manipulator that adds a dynamic value to a dynamic field:

.. highlight:: python
.. code-block:: python

   class AddManipulator(Manipulator):
      def __init__(self, field, value):
         self.field = field
         self.value = value

      def transform_outgoing(self, doc, model):
         doc[self.field] = doc[self.field] + self.value
         return doc

Then we would bind this manipulator to the model as an object

.. highlight:: python
.. code-block:: python

   class User(BaseModel):
      .....
      addOneToFamilySize = AddManipulator('family_size', 1)

   class Book(BaseModel):
      ......
      subtractFirstAndLastPages = AddManipulator('page_count', -2)

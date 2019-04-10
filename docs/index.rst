.. pymongoext documentation master file, created by
   sphinx-quickstart on Sat Mar 30 16:56:31 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

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
------------------------

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

Suppose we wanted to add a **unique** index on ``email`` as well as an index on ``first_name``.
This would be achieved as follows:

.. highlight:: python
.. code-block:: python

   from pymongo import IndexModel

   class User(BaseModel):

      # .....

      __indexes__ = [IndexModel('email', unique=True), 'first_name']


Manipulators
*************

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

      # .....

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


.. toctree::
   :maxdepth: 2

   self
   install
   api_reference




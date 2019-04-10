Pymongoext
===========

Pymongoext is an ORM-like Pymongo extension that adds json schema validation,
index management and intermediate data manipulators.
Pymongoext simplifies working with MongoDB, while maintaining a syntax very identical to Pymongo.

Documentation is available at https://pymongoext.readthedocs.io

The code is hosted on Github https://github.com/musyoka-morris/pymongoext

Supported MongoDB & Python Versions
====================================
Pymongoext uses JSON Schema for validation and thus we only support
MongoDB v3.6+.

Pymongoext supports python v3+. Support for python v2.7 is currently under consideration.


Installation
=============
We recommend the use of `virtualenv <https://virtualenv.pypa.io>`_ and of
`pip <https://pip.pypa.io>`_. You can then use ``pip install -U pymongoext``.

You may also have `setuptools <http://peak.telecommunity.com/DevCenter/setuptools>`_
and thus you can use ``easy_install -U pymongoext``. Another option is
`pipenv <https://docs.pipenv.org>`_. You can then use ``pipenv install pymongoext``
to both create the virtual environment and install the package.

Alternatively, you can download the source from `GitHub <https://github.com/musyoka-morris/pymongoext>`_ and
run ``python setup.py install``.

Examples
=========
Some simple examples of what pymongoext code looks like:

.. code :: python

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
    >>> print(user['age'])

Contributing
=============
We welcome contributions!
See the `Contribution guidelines <https://github.com/musyoka-morris/pymongoext/blob/master/CONTRIBUTING.rst>`_
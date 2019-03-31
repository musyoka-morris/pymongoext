from pymongo import IndexModel
from pymongo.errors import OperationFailure
from pymongo.collection import Collection
import inflection
from pymongoext.binder import _BindCollectionMethods
from pymongoext.exceptions import NoDocumentFound, MultipleDocumentsFound
from pymongoext.fields import DictField
from pymongoext.manipulators import Manipulator, IdWithoutUnderscoreManipulator, ParseManipulator


_BM = Manipulator()


def _manipulator_method_overwritten(instance, method):
    """Test if this method has been overridden."""
    return getattr(instance, method).__func__ != getattr(_BM, method).__func__


class Model(metaclass=_BindCollectionMethods):
    """The base class used for defining the structure and properties of collections of documents stored in MongoDB.
    You should not use the :class:`Model` class directly.
    Instead Inherit from this class to define a document’s structure.

    In pymongoext, the term "Model" refers to subclasses of the :class:`~Model` class.
    A Model is your primary tool for interacting with MongoDB collections.

    Note:

        All concrete classes must implement the :meth:`~db` which should return a valid mongo database instance.

    Examples:

        Create a Users model

        .. highlight:: python
        .. code-block:: python

            from pymongo import MongoClient, IndexModel
            from pymongoext import Model, DictField, StringField, IntField

            class User(Model):

                @classmethod
                def db(cls):
                    return MongoClient()['the_test_db']

                __schema__ = DictField(dict(
                    email=StringField(required=True),
                    name=StringField(required=True),
                    password=StringField(required=True),
                    age=IntField(minimum=0)
                ))

                __indexes__ = [IndexModel('email', unique=True), 'name']

        All `pymongo.collection.Collection
        <https://api.mongodb.com/python/current/api/pymongo/collection.html#pymongo.collection.Collection>`_
        methods and attributes can be accessed through the Model as shown below

        Create a new user

        .. highlight:: python
        .. code-block:: python

            result = User.insert_one({
                "email": "john.doe@dummy.com",
                "name": "John Doe",
                "password": "secret",
                "age": 35
            })
            user_id = result.inserted_id

        Find a single document by id.
        See :meth:`~get` for an alternative to :meth:`find_one`

        .. highlight:: python
        .. code-block:: python

            user = User.find_one(user_id)

        Check if a document exists

        .. highlight:: python
        .. code-block:: python

            user_exists = User.exists({"_id": user_id})
    """

    __collection_name__ = None
    """
    Pymongoext by default produces a collection name by taking the under_score_case of the model.
    See `inflection.underscore <https://inflection.readthedocs.io/en/latest/#inflection.underscore>`_ for more info.
    
    Set this if you need a different name for your collection.
    """

    __auto_update__ = True
    """
    By default, pymongoext ensures the indexes and schema defined on the model are in sync with mongodb.
    It achieves this by creating & dropping indexes and 
    pushing updates to the the JsonSchema defined in mongodb collection. 
    This is done when your code runs for the first time or the server is restarted.
    
    If you want to disable this functionality and manage the updates yourself, 
    you can set ``__auto_update__`` to False.
    
    But then remember to call :meth:`~._update` yourself to update the schema.
    """

    __indexes__ = []
    """List of Indexes to create on this collection
    
    Todo:
        
        Support Index direction specification by prefixing the field names with a ``+`` or ``-`` sign.
    
    An index is defined as either 
        1. a single key or 
        2. a list of (key, direction) pairs or
        3. an instance of ``pymongo.IndexModel``
        
    See the `create_index 
    <https://api.mongodb.com/python/current/api/pymongo/collection.html#pymongo.collection.Collection.create_index>`_ 
    and `create_indexes 
    <https://api.mongodb.com/python/current/api/pymongo/collection.html#pymongo.collection.Collection.create_indexes>`_ 
    methods of pymongo Collection for more info.
    """

    __schema__ = None
    """:class:`pymongoext.fields.DictField`: Specifies model schema"""

    __manipulators__ = [IdWithoutUnderscoreManipulator(), ParseManipulator()]
    """A list of manipulators to be applied to incoming and outgoing documents.
    Manipulators are applied sequentially in the order given.
    
    A manipulator operates on a single document before it is saved to mongodb and after it is retrieved.
    
    See :class:`pymongoext.manipulators.Manipulator` on how to implement your own manipulators.
    """

    @classmethod
    def db(cls):
        """Get the mongo database instance associated with this collection

        All concrete classes must implement this method. A sample implementation is shown below


        .. highlight:: python
        .. code-block:: python

            from pymongo import MongoClient
            from pymongoext import Model

            class User(Model):
                @classmethod
                def db(cls):
                    return MongoClient()['test_db']

        Returns:
            :class:`pymongo.database.Database`
        """
        raise NotImplementedError

    @classmethod
    def name(cls):
        """Returns the collection name.

        See :attr:`~__collection_name__` for more info on how the collection name is determined
        """
        if cls.__collection_name__ is None:
            return inflection.underscore(cls.__name__)
        return cls.__collection_name__

    @classmethod
    def c(cls):
        """Get the collection associated with this model.
        This method ensures that the model indexes and schema validators are up to date.

        Returns:
            :class:`pymongo.collection.Collection`
        """
        if cls._should_update():
            cls._update()
        return cls.db()[cls.name()]

    @classmethod
    def apply_incoming_manipulators(cls, doc, action):
        """Apply manipulators to an incoming document before it gets stored.

        Args:
            doc (dict): the document to be inserted into the database
            action (str): the incoming action being performed

        Returns:
            dict: the transformed document
        """
        for manipulator in cls.__manipulators__:
            if _manipulator_method_overwritten(manipulator, 'transform_incoming'):
                doc = manipulator.transform_incoming(doc, cls, action)
        return doc

    @classmethod
    def apply_outgoing_manipulators(cls, doc):
        """Apply manipulators to an outgoing document.

        Args:
            doc (dict): the document being retrieved from the database

        Returns:
            dict: the transformed document
        """
        if doc is not None:
            for manipulator in cls.__manipulators__:
                if _manipulator_method_overwritten(manipulator, 'transform_outgoing'):
                    doc = manipulator.transform_outgoing(doc, cls)
        return doc

    @classmethod
    def _validator(cls):
        """Convert the schema to a valid JsonSchema object"""
        if cls.__schema__ is None:
            return {}
        return {"$jsonSchema": cls.__schema__.schema()}

    @classmethod
    def _indexes(cls):
        """Maps all indexes to a list of :class:`pymongo.IndexModel`

        All indexes are created in the background
        """
        def _model(index):
            if not isinstance(index, IndexModel):
                index = IndexModel(index)
            index.document['background'] = True
            return index

        return [_model(i) for i in cls.__indexes__]

    _UPTO_DATE = []
    """Cache for collections that are upto date"""

    @classmethod
    def _on_update(cls):
        """Method called on successful update"""
        Model._UPTO_DATE.append(cls.name())

    @classmethod
    def _should_update(cls):
        """Checks if we should update the collection meta"""
        return cls.__auto_update__ and cls.name() not in Model._UPTO_DATE

    @classmethod
    def _update(cls):
        """Runs validator & index update commands on database"""
        db = cls.db()
        name = cls.name()
        validator = cls._validator()
        indexes = cls._indexes()
        collection = db[name]

        # Create or update validator
        try:
            collection = Collection(db, name, validator=validator)
        except OperationFailure:
            db.command({
                "collMod": name,
                "validator": validator
            })

        # Update Indexes
        i_names = [model.document['name'] for model in indexes]
        existing = list(collection.index_information().keys())

        for name in existing:
            if name != '_id_' and name not in i_names:
                collection.drop_index(name)

        to_create = [model for model in indexes if model.document['name'] not in existing]
        if len(to_create) > 0:
            collection.create_indexes(indexes)

        # Set as updated
        cls._on_update()

    @classmethod
    def _limited_cursor(cls, filter_, limit, *args, **kwargs):
        """Helper method to create cursor.

        See :meth:`~exists` and :meth:`~get` on how it is used
        """
        if filter_ is not None and not isinstance(filter_, dict):
            filter_ = {"_id": filter_}

        return cls.find(filter_, *args, **kwargs).limit(limit)

    @classmethod
    def exists(cls, filter_=None, *args, **kwargs):
        """Check if a document exists in the database

        All arguments to :meth:`find` are also valid arguments for
        :meth:`~exists`, although any `limit` argument will be
        ignored. Returns ``True`` if a matching document is found,
        otherwise ``False`` .

        Args:

          filter_ (optional): a dictionary specifying
            the query to be performed OR any other type to be used as
            the value for a query for ``"_id"``.

          *args (optional): any additional positional arguments
            are the same as the arguments to :meth:`find`.

          **kwargs (optional): any additional keyword arguments
            are the same as the arguments to :meth:`find`.
        """
        return cls._limited_cursor(filter_, 1, *args, **kwargs).count() > 0

    @classmethod
    def get(cls, filter_=None, *args, **kwargs):
        """Retrieve the the matching object raising
        :class:`pymongoext.exceptions.MultipleDocumentsFound` exception if multiple results
        and :class:`pymongoext.exceptions.NoDocumentFound` if no results are found.

        All arguments to :meth:`find` are also valid arguments for
        :meth:`~get`, although any `limit` argument will be
        ignored. Returns the matching document

        Args:

          filter_ (optional): a dictionary specifying
            the query to be performed OR any other type to be used as
            the value for a query for ``"_id"``.

          *args (optional): any additional positional arguments
            are the same as the arguments to :meth:`find`.

          **kwargs (optional): any additional keyword arguments
            are the same as the arguments to :meth:`find`.
        """
        cursor = cls._limited_cursor(filter_, 2, *args, **kwargs)
        count = cursor.count()
        if count < 1:
            raise NoDocumentFound()
        if count > 1:
            raise MultipleDocumentsFound()
        return cursor.next()

    @classmethod
    def parse(cls, data, with_defaults=False):
        """Prepare the data to be stored in the db

        For example, given a simple user model

        .. highlight:: python
        .. code-block:: python

            class User(Model):

                @classmethod
                def db(cls):
                    return MongoClient()['the_test_db']

                __schema__ = DictField(dict(
                    name=StringField(required=True),
                    age=IntField(minimum=0, required=True, default=18)
                ))

        .. highlight:: python
        .. code-block:: python

            User.parse({'name': 'John Doe'}, with_defaults=True)
            >>> {'name': 'John Doe', 'age': 18}

        Args:
            data (dict): Data to be stored
            with_defaults (bool): If ``True``, None and missing values are set to the field default

        Returns:
            dict
        """
        if isinstance(cls.__schema__, DictField):
            return cls.__schema__.parse(data, with_defaults, is_schema=True)
        return data
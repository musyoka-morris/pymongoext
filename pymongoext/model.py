from pymongo import IndexModel
from pymongo.errors import OperationFailure
from pymongo.collection import Collection
import inflection
from pymongoext.binder import _BindCollectionMethods
from pymongoext.exceptions import NoDocumentFound, MultipleDocumentsFound


class Model(metaclass=_BindCollectionMethods):
    """You should not use the :class:`Model` class directly.
    Instead create subclasses of :class:`Model` as shown below.

    .. highlight:: python
    .. code-block:: python

        from pymongo import MongoClient
        from pymongoext import Model, DictField, StringField, IntField

        class UserModel(Model):

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

    The example above creates a user model which enforces the defined schema and ensures indexes are in sync.
    All `pymongo.collection.Collection` methods and attributes can be accessed through the Model as shown below


    .. highlight:: python
    .. code-block:: python

        # Insert document example
        user_id = UserModel.insert_one({
            "email": "john.doe@dummy.com",
            "name": "John Doe",
            "password": "secret",
            "age": 35
        })

        # Find a single document by id
        john = UserModel.find_one(user_id)

        # Check if a document exists
        john_exists = UserModel.exists({"_id": user_id})
    """

    __collection_name__ = None

    __auto_update__ = True
    """"""

    __indexes__ = []
    """Indexes to create"""

    __schema__ = None
    """:type: Field Specifies model schema"""

    @classmethod
    def db(cls):
        """Get the mongo database instance associated with this collection

        Returns:
            pymongo.database.Database
        """
        raise NotImplementedError

    @classmethod
    def name(cls):
        if cls.__collection_name__ is None:
            return inflection.underscore(cls.__name__)
        return cls.__collection_name__

    @classmethod
    def c(cls):
        if cls._should_update():
            cls._update()
        return cls.db()[cls.name()]

    @classmethod
    def _validator(cls):
        if cls.__schema__ is None:
            return {}
        return {"$jsonSchema": cls.__schema__.schema()}

    @classmethod
    def _indexes(cls):
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
        Model._UPTO_DATE.append(cls.name())

    @classmethod
    def _should_update(cls):
        return cls.__auto_update__ and cls.name() not in Model._UPTO_DATE

    @classmethod
    def _update(cls):
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
    def _find_cursor(cls, filter_, limit, *args, **kwargs):
        if filter_ is not None and not isinstance(filter_, dict):
            filter_ = {"_id": filter_}
        return cls.find(filter_, *args, **kwargs).limit(limit)

    @classmethod
    def exists(cls, filter_=None, *args, **kwargs):
        """Check if a document exists in the database

        All arguments to :meth:`find` are also valid arguments for
        :meth:`exists`, although any `limit` argument will be
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
        return cls._find_cursor(filter_, 1, *args, **kwargs).count() > 0

    @classmethod
    def get(cls, filter_=None, *args, **kwargs):
        """Retrieve the the matching object raising
        :class:`pymongoext.exceptions.MultipleDocumentsFound` exception if multiple results
        and :class:`pymongoext.exceptions.NoDocumentFound` if no results are found.

        All arguments to :meth:`find` are also valid arguments for
        :meth:`get`, although any `limit` argument will be
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
        cursor = cls._find_cursor(filter_, 2, *args, **kwargs)
        count = cursor.count()
        if count < 1:
            raise NoDocumentFound()
        if count > 1:
            raise MultipleDocumentsFound()
        return cursor.next()

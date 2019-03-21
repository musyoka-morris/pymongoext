from pymongo import IndexModel
from pymongo.errors import OperationFailure
from pymongo.collection import Collection
import inflection
from pymongoext.binder import _BindCollectionMethods


class Document(metaclass=_BindCollectionMethods):
    __TOUCHED = []
    """Cache for collections that are upto date"""

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
        return inflection.underscore(cls.__name__)

    @classmethod
    def c(cls):
        db = cls.db()
        name = cls.name()
        collection = db[name]

        if name not in Document.__TOUCHED:
            # Validator
            validator = cls._validator()
            try:
                collection = Collection(db, name, validator=validator)
            except OperationFailure:
                db.command({
                    "collMod": name,
                    "validator": validator
                })

            # Indexes
            indexes = cls._indexes()
            i_names = [model.document['name'] for model in indexes]
            existing = list(collection.index_information().keys())

            for name in existing:
                if name != '_id_' and name not in i_names:
                    collection.drop_index(name)

            to_create = [model for model in indexes if model.document['name'] not in existing]
            if len(to_create) > 0:
                collection.create_indexes(indexes)

            # Set as touched
            Document.__TOUCHED.append(name)

        return collection

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
        if filter_ is not None and not isinstance(filter_, dict):
            filter_ = {"_id": filter_}

        return cls.find(filter_, *args, **kwargs).limit(1).count() > 0

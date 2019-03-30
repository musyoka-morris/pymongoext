from pymongoext.cursor import WrappedCursor
from pymongoext.manipulators import IncomingAction
from bson.py3compat import abc


def _wrap_outgoing(method):
	"""Helper method to wrap methods that return a single SON document"""
	def _wrapper(model, *args, **kwargs):
		"""Retrieves document and passes it through outgoing manipulators

		Args:
			model (pymongoext.model.Model): The associated model
			*args: Args to pass to the pymongo.Collection method
			**kwargs: Kwargs to pass to the pymongo.Collection method

		Returns:
			dict
		"""
		doc = getattr(model.c(), method)(*args, **kwargs)
		return model.apply_outgoing_manipulators(doc)
	return _wrapper


def _wrap_update(one_or_many):
	"""Helper method to wrap update_one and update_many methods

	Args:
		one_or_many (str): must be one of `one|many`
	"""
	method = "update_{}".format(one_or_many)

	def _w_update_one_or_many(cls, filter, update, *args, **kwargs):
		"""Wrap update_one method

		Args:
			cls (pymongoext.model.Model)
		"""
		update = cls.apply_incoming_manipulators(update, IncomingAction.UPDATE)
		return getattr(cls.c(), method)(filter, update, *args, **kwargs)

	return _w_update_one_or_many


class _BindCollectionMethods(type):
	"""Metaclass to bind class method calls to mongo collection instance"""
	def __getattr__(self, item):
		wrapper = '_w_{}'.format(item)
		if wrapper in _W_ATTRIBUTES:
			return getattr(self, wrapper)

		return self.c().__getattribute__(item)

	def _w_find(cls, *args, **kwargs):
		"""Wrap find method

		Args:
			cls (pymongoext.model.Model)
		"""
		cursor = cls.c().find(*args, **kwargs)
		return WrappedCursor(cursor, cls)

	_w_find_one = _wrap_outgoing('find_one')
	_w_find_one_and_delete = _wrap_outgoing('find_one_and_delete')

	def _w_find_one_and_replace(cls, filter, replacement, *args, **kwargs):
		"""Wrap find_one_and_replace method

		Args:
			cls (pymongoext.model.Model)
		"""
		replacement = cls.apply_incoming_manipulators(replacement, IncomingAction.REPLACE)
		return _wrap_outgoing('find_one_and_replace')(cls, filter, replacement, *args, **kwargs)

	def _w_replace_one(cls, filter, replacement, *args, **kwargs):
		"""Wrap replace_one method

		Args:
			cls (pymongoext.model.Model)
		"""
		replacement = cls.apply_incoming_manipulators(replacement, IncomingAction.REPLACE)
		return cls.c().replace_one(filter, replacement, *args, **kwargs)

	def _w_find_one_and_update(cls, filter, update, *args, **kwargs):
		"""Wrap find_one_and_update method

		Args:
			cls (pymongoext.model.Model)
		"""
		update = cls.apply_incoming_manipulators(update, IncomingAction.UPDATE)
		return _wrap_outgoing('find_one_and_update')(cls, filter, update, *args, **kwargs)

	_w_update_one = _wrap_update('one')
	_w_update_many = _wrap_update('many')

	def _w_insert_one(cls, document, *args, **kwargs):
		"""Wrap insert_one method

		Args:
			cls (pymongoext.model.Model)
		"""
		document = cls.apply_incoming_manipulators(document, IncomingAction.CREATE)
		return cls.c().insert_one(document, *args, **kwargs)

	def _w_insert_many(cls, documents, *args, **kwargs):
		"""Wrap insert_many method

		Args:
			cls (pymongoext.model.Model)
		"""
		if documents and isinstance(documents, abc.Iterable):
			documents = [cls.apply_incoming_manipulators(d, IncomingAction.CREATE) for d in documents]
		return cls.c().insert_many(documents, *args, **kwargs)


_W_ATTRIBUTES = [x for x in _BindCollectionMethods.__dict__.keys() if x.startswith('_w_')]

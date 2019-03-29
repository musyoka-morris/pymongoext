from pymongo.cursor import Cursor


def _idify(d):
	"""Add id field to a SON document

	Args:
		d (dict): The document to manipulate
	"""
	if isinstance(d, dict) and '_id' in d and 'id' not in d:
		d['id'] = d['_id']
	return d


class _WrappedCursor:
	def __init__(self, cursor):
		"""Wraps pymongo cursor

		Args:
			cursor (Cursor): The underlying pymongo cursor
		"""
		self.cursor = cursor

	def __getattr__(self, item):
		return getattr(self.cursor, item)

	def __getitem__(self, index):
		"""Apply manipulators"""
		res = self.cursor.__getitem__(index)

		if not isinstance(res, Cursor):
			return _idify(res)

		return [_idify(d) for d in res]


def _w(method):
	"""Helper method to wrap methods that return a single SON document"""
	def _wrapper(self, *args, **kwargs):
		return _idify(getattr(self.c(), method)(*args, **kwargs))
	return _wrapper


class _BindCollectionMethods(type):
	"""Metaclass to bind class method calls to mongo collection instance"""
	def __getattr__(self, item):
		wrapper = '_w_{}'.format(item)
		if wrapper in _W_ATTRIBUTES:
			return getattr(self, wrapper)

		return self.c().__getattribute__(item)

	def _w_find(self, *args, **kwargs):
		cursor = self.c().find(*args, **kwargs)
		return _WrappedCursor(cursor)

	_w_find_one = _w('find_one')
	_w_find_one_and_update = _w('find_one_and_update')
	_w_find_one_and_replace = _w('find_one_and_replace')
	_w_find_one_and_delete = _w('find_one_and_delete')


_W_ATTRIBUTES = [x for x in _BindCollectionMethods.__dict__.keys() if x.startswith('_w_')]

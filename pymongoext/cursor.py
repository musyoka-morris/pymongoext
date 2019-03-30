from pymongo.cursor import Cursor


class WrappedCursor:
	def __init__(self, cursor, model):
		"""Wraps pymongo cursor

		Args:
			cursor (Cursor): The underlying pymongo cursor
			model (pymongoext.model.Model): The associated model
		"""
		self.cursor = cursor
		self.model = model

	def __getattr__(self, item):
		def _wrap(method):
			def _wrapper(*args, **kwargs):
				res = method(*args, **kwargs)
				if isinstance(res, Cursor):
					return WrappedCursor(res, model)
				return res
			return _wrapper

		model = self.model
		attr = getattr(self.cursor, item)
		return _wrap(attr) if callable(attr) else attr

	def next(self):
		doc = self.cursor.next()
		return self.model.apply_outgoing_manipulators(doc)

	def __getitem__(self, index):
		res = self.cursor.__getitem__(index)

		if isinstance(res, Cursor):
			return WrappedCursor(res, self.model)

		return self.model.apply_outgoing_manipulators(res)

	def __iter__(self):
		return self

	__next__ = next

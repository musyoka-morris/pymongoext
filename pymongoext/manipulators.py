from munch import Munch

__all__ = [
	'IncomingAction',
	'Manipulator',
	'MunchManipulator',
	'IdWithoutUnderscoreManipulator',
	'ParseInputsManipulator'
]


class IncomingAction:
	"""Enum for Incoming action types"""
	CREATE = 'CREATE'
	REPLACE = 'REPLACE'
	UPDATE = 'UPDATE'


class Manipulator:
	"""A base document manipulator.

	This manipulator just saves and restores documents without changing them.
	"""

	priority = 5
	"""Determines the order in which the manipulators will be applied.
	Manipulators with a lower priority will be applied first	
	"""

	def transform_incoming(self, doc, model, action):
		"""Manipulate an incoming document.

		Args:
			doc (dict): the SON object to be inserted into the database
			model (Type[pymongoext.model.Model]): the model the object is associated with
			action (str): One of CREATE|REPLACE|UPDATE. Signifies the action being performed
		"""
		return doc

	def transform_outgoing(self, doc, model):
		"""Manipulate an outgoing document.

		Args:
			doc (dict): the SON object being retrieved from the database
			model (Type[pymongoext.model.Model]): the model associated with this document
		"""
		return doc


class MunchManipulator(Manipulator):
	"""Transforms documents to Munch objects.
	A Munch is a Python dictionary that provides attribute-style access

	See https://github.com/Infinidat/munch
	"""
	priority = -1

	def transform_incoming(self, doc, model, action):
		return Munch(doc)

	def transform_outgoing(self, doc, model):
		return Munch(doc)


class IdWithoutUnderscoreManipulator(Manipulator):
	"""A document manipulator that manages a virtual id field."""

	priority = 0

	def transform_incoming(self, doc, model, action):
		"""Remove id field if given and set _id to that value if missing"""
		if "id" in doc:
			if "_id" not in doc:
				doc["_id"] = doc['id']
			del doc["id"]
		return doc

	def transform_outgoing(self, doc, model):
		"""Add an id field if it is missing."""
		if "id" not in doc:
			doc["id"] = doc["_id"]
		return doc


class ParseInputsManipulator(Manipulator):
	"""Parses incoming documents to ensure data is in the valid format"""
	priority = 7

	def transform_incoming(self, doc, model, action):
		if action in [IncomingAction.CREATE, IncomingAction.REPLACE]:
			return model.parse(doc, with_defaults=True)

		if action == IncomingAction.UPDATE and '$set' in doc:
			data = doc['$set']
			# todo: Handle array elements and embedded documents. eg user.name, products.0.name
			#   1. Expand the data to eliminate .s (dots)
			#   2. Parse the data
			#   3. Deflate the data to bring back the dots
			doc['$set'] = model.parse(data, with_defaults=False)

		return doc

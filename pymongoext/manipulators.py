__all__ = [
	'IncomingAction',
	'Manipulator',
	'IdWithoutUnderscoreManipulator',
	'ParseManipulator'
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


class IdWithoutUnderscoreManipulator(Manipulator):
	"""A document manipulator that manages a virtual id field."""

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


class ParseManipulator(Manipulator):
	"""Parses incoming documents to ensure data is in the valid format"""
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

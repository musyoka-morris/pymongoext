class MultipleDocumentsFound(Exception):
	"""Raised by :meth:`pymongoext.model.Model.get`
	when multiple documents matching the search criteria are found"""


class NoDocumentFound(Exception):
	"""Raised by :meth:`pymongoext.model.Model.get`
	when no documents matching the search criteria are found"""

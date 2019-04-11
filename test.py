from pymongoext import Manipulator, Model, DictField, StringField, DateTimeField
from pymongo import MongoClient
import datetime


class AB(Model):
	__collection_name__ = 'ab_test'

	@classmethod
	def db(cls):
		return MongoClient()['the_test_db']

	__schema__ = DictField(dict(
		name=StringField(required=True),
		createdAt=DateTimeField(default=datetime.datetime.utcnow, required=True)
	))

	__indexes__ = ["name", "-createdAt"]

	class DummyManipulator(Manipulator):
		priority = 10

		def transform_outgoing(self, doc, model):
			doc['is_dummy'] = True
			return doc


res = AB.insert_many([{'name': 'Jane'}, {'name': 'John'}])
print(list(AB.find({})))

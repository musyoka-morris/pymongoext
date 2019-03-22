from pymongoext import Model, DictField, StringField
from pymongo import MongoClient


class AB(Model):
	__collection_name__ = 'ab_test'

	@classmethod
	def db(cls):
		return MongoClient()['the_test_db']

	__schema__ = DictField(dict(
		name=StringField(required=True),
	))

	__indexes__ = ["name"]


# AB.insert_one({'name': 'abc'})
# print(AB.find_one({'name': 'abc'}))

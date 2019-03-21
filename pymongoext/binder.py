class _BindCollectionMethods(type):
	"""Metaclass to bind class method calls to mongo collection instance"""
	def __getattr__(self, item):
		return self.c().__getattribute__(item)

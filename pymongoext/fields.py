import inflection
import copy
from datetime import datetime
from dateutil import parser
import bson
from fastnumbers import fast_float

__all__ = [
    "Field",
    "NullField",
    "StringField",

    "NumberField",
    "IntField",
    "FloatField",

    "BooleanField",
    "DateTimeField",
    "TimeStampField",
    "ObjectIDField",

    "ListField",
    "DictField",
    "MapField",

    "OneOf",
    "AllOf",
    "AnyOf",

    "Not"
]

_ID = '_id'


def _float(x):
    """Convert to a float"""
    if x == "" or x is None:
        return None
    return fast_float(x, raise_on_invalid=True, nan=None)


def _v(value, validator, error):
    if value is None or validator(value):
        return
    raise ValueError(error.format(value))


def _is_positive_int(x):
    return x >= 0 and x % 1 == 0


class Field:
    """Base class for all fields

    Args:
        required (bool): Specifies if a value is required for this field. defaults to ``False``
        enum (list): Enumerates all possible values of the field
        title (str): A descriptive title string with no effect
        description (str): A string that describes the schema and has no effect
        **kwargs: Additional parameters
    """

    __type__ = None
    """Specifies the bsonType"""

    def __init__(self, default=None, required=False, enum=None, title=None, description=None, **kwargs):
        self.default = default
        self.required = required
        self.attributes = dict(
            enum=enum if enum is None else list(set(enum)),
            title=title,
            description=description,
            **kwargs
        )

    def _bson_type(self):
        """Defer computation of bson_type as it depends on the required attribute"""
        if self.__type__ is None or self.__type__ == 'null' or self.required:
            return self.__type__
        return [self.__type__, "null"]

    def _deferred_attributes(self):
        """Defer computation of dynamic attributes"""
        return {}

    def schema(self):
        """Creates a valid JsonSchema object

        Returns:
            dict
        """
        attributes = dict(
            **self.attributes,
            **self._deferred_attributes(),
            bson_type=self._bson_type()
        )

        return {
            inflection.camelize(k, uppercase_first_letter=False): v
            for k, v in attributes.items() if v is not None
        }

    def _parse_non_null_value(self, value):
        return value

    def parse(self, value, with_default):
        if value is not None:
            return self._parse_non_null_value(value)

        if not with_default or self.default is None:
            return value

        if callable(self.default):
            return self.default()

        return copy.deepcopy(self.default)

    def __str__(self):
        return str(self.schema())


class NullField(Field):
    """Null field"""
    __type__ = 'null'

    def __init__(self):
        super().__init__()


class StringField(Field):
    """String field

    Args:
        max_length (int): The maximum length of the field
        min_length (int): The minimum length of the field
        pattern (str): Field must match the regular expression
        **kwargs: any additional keyword arguments are the same as the arguments to the :class:`~Field` class
    """
    __type__ = 'string'

    def __init__(self, max_length=None, min_length=None, pattern=None, **kwargs):
        _v(max_length, _is_positive_int, '{} is not a valid value for max_length')
        _v(min_length, _is_positive_int, '{} is not a valid value for min_length')

        super().__init__(
            **kwargs,
            max_length=max_length,
            min_length=min_length,
            pattern=pattern
        )

    def _parse_non_null_value(self, value):
        return str(value)


class NumberField(Field):
    """Numeric field

    Args:
        maximum (int|long): The inclusive maximum value of the field
        minimum (int|long): The inclusive minimum value of the field
        exclusive_maximum (int|long): The exclusive maximum value of the field.
            values are valid if they are strictly less than (not equal to) the given value.
        exclusive_minimum (int|long): The exclusive minimum value of the field.
            values are valid if they are strictly greater than (not equal to) the given value.
        multiple_of (int|long): Field must be a multiple of this value
        **kwargs: any additional keyword arguments are the same as the arguments to the :class:`~Field` class
    """
    __type__ = 'number'

    def __init__(self,
                 maximum=None,
                 minimum=None,
                 exclusive_maximum=None,
                 exclusive_minimum=None,
                 multiple_of=None,
                 **kwargs):
        limits = dict(
            maximum=maximum,
            minimum=minimum
        )

        if exclusive_maximum is not None:
            limits['maximum'] = exclusive_maximum
            limits['exclusive_maximum'] = True

        if exclusive_minimum is not None:
            limits['minimum'] = exclusive_minimum
            limits['exclusive_minimum'] = True

        super().__init__(
            **kwargs,
            **limits,
            multiple_of=multiple_of
        )

    def _parse_non_null_value(self, value):
        return _float(value)


class IntField(NumberField):
    """Integer field"""
    __type__ = 'int'

    def _parse_non_null_value(self, value):
        value = _float(value)
        return None if value is None else int(value)


class FloatField(NumberField):
    """Float field"""
    __type__ = 'long'


class BooleanField(Field):
    """Boolean field"""
    __type__ = 'bool'


class ListField(Field):
    """List field

    Args:
        field (Field): A field to validate each type against
        max_items (int): The maximum length of array
        min_items (int): The minimum length of array
        unique_items (bool): 	If true, each item in the array must be unique.
            Otherwise, no uniqueness constraint is enforced.
        **kwargs: any additional keyword arguments are the same as the arguments to the :class:`~Field` class
    """

    __type__ = 'array'

    def __init__(self, field=None, max_items=None, min_items=None, unique_items=None, **kwargs):
        _v(max_items, _is_positive_int, '{} is not a valid value for max_items')
        _v(min_items, _is_positive_int, '{} is not a valid value for min_items')

        self.field = field

        super().__init__(
            **kwargs,
            max_items=max_items,
            min_items=min_items,
            unique_items=unique_items
        )

    def _deferred_attributes(self):
        return dict(
            items=None if self.field is None else self.field.schema()
        )

    def _parse_non_null_value(self, value):
        return list(value)


class DictField(Field):
    """Dict Field

    Args:
        props (dict of str: Field): A map of known properties
        max_props (int): The maximum number of properties allowed
        min_props (int): The minimum number of properties allowed
        additional_props (Field | bool): If ``True``, additional fields are allowed.
            If ``False``, only properties specified in ``props`` are allowed.
            If an instance of :class:`~Field` is specified, additional fields must validate against that field.
        required_props (list of str): Property names that must be included
        **kwargs: any additional keyword arguments are the same as the arguments to the :class:`~Field` class
    """

    __type__ = 'object'

    def __init__(self,
                 props=None,
                 max_props=None,
                 min_props=None,
                 additional_props=True,
                 required_props=None,
                 **kwargs):
        _v(max_props, _is_positive_int, '{} is not a valid value for max_props')
        _v(min_props, _is_positive_int, '{} is not a valid value for min_props')

        self.additional_props = additional_props
        self.props = props
        self.required_props = required_props

        super().__init__(
            **kwargs,
            max_properties=max_props,
            min_properties=min_props
        )

    def _deferred_attributes(self):
        ap = self.additional_props
        props = self.props
        required_props = self.required_props

        required_props = [] if required_props is None else list(copy.deepcopy(required_props))
        if props is not None:
            for name, field in props.items():
                if field.required:
                    required_props.append(name)

        required_props = list(set(required_props))

        return dict(
            properties=props if props is None else {k: v.schema() for k, v in props.items()},
            additional_properties=ap.schema() if isinstance(ap, Field) else ap,
            required=required_props if len(required_props) > 0 else None
        )

    def schema(self):
        schema = super().schema()
        return schema

    def parse(self, value, with_defaults, is_schema=False):
        if value is None and not with_defaults:
            return value

        # Handle Nones
        data = copy.deepcopy({} if value is None else value)
        props = {} if self.props is None else self.props

        # _id field defaults to ObjectID
        if is_schema and _ID not in props:
            props['_id'] = ObjectIDField()

        # Parse given keys
        for key, value in data.items():
            if key in props:
                data[key] = props[key].parse(value, with_defaults)

        # Fill in missing keys
        if with_defaults:
            missing = set(props.keys()) - set(data.keys())
            for key in missing:
                default = props[key].parse(None, True)
                if default is not None:
                    data[key] = default

        # Additional props
        additional = set(data.keys()) - set(props.keys())

        if not self.additional_props:
            for key in additional:
                del data[key]

        elif isinstance(self.additional_props, Field):
            for key in additional:
                data[key] = self.additional_props.parse(data[key], with_defaults)

        return data


class MapField(DictField):
    def __init__(self, field, **kwargs):
        super().__init__(**kwargs, additional_props=field)


class _WithListFieldsInput(Field):
    """Base class for fields that take as input multiple :class:`~Field` parameters

    Args:
        *fields (Field): Allowed fields
        **kwargs: any additional keyword arguments are the same as the arguments to the :class:`~Field` class
    """

    __add_null__ = True
    """Specifies if a null field should be added to the fields list if required=```False``"""

    def __init__(self, *fields, **kwargs):
        if len(fields) == 0:
            raise ValueError('At least one field must be provided')

        self._fields = list(fields)

        super().__init__(**kwargs)

    def _deferred_attributes(self):
        fields = list(copy.deepcopy(self._fields))
        for field in fields:
            field.required = True

        if self.__add_null__ and not self.required:
            fields.append(NullField())

        key = inflection.underscore(self.__class__.__name__)
        return {key: [field.schema() for field in fields]}


class OneOf(_WithListFieldsInput):
    """value must match exactly one of the specified fields

    Example:

        >>> OneOf(StringField(), IntField(minimum=10), required=True)
    """


class AllOf(_WithListFieldsInput):
    """value must match all specified fields"""
    __add_null__ = False


class AnyOf(_WithListFieldsInput):
    """value must match at least one of the specified fields"""


class Not(Field):
    """Allow anything that does not match the given field

    Args:
        field (Field): value must not match this field
        **kwargs: any additional keyword arguments are the same as the arguments to the :class:`~Field` class
    """
    def __init__(self, field, **kwargs):
        self._field = field
        super().__init__(**kwargs)

    def _deferred_attributes(self):
        field = copy.deepcopy(self._field)
        field.required = not self.required  # Negate field's required state
        return {'not': field.schema()}


class DateTimeField(Field):
    """Datetime field"""
    __type__ = 'date'

    def _parse_non_null_value(self, value):
        if isinstance(value, datetime):
            return value

        return parser.parse(value)


class TimeStampField(Field):
    """Timestamp field"""
    __type__ = 'timestamp'


class ObjectIDField(Field):
    """ObjectID field"""
    __type__ = 'objectId'

    def _parse_non_null_value(self, value):
        return bson.ObjectId(value)

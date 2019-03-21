import inflection
import copy


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

    def __init__(self, required=False, enum=None, title=None, description=None, **kwargs):
        self.required = required
        self.attributes = dict(
            bson_type=self.__type__,
            enum=enum if enum is None else list(set(enum)),
            title=title,
            description=description,
            **kwargs
        )

    def schema(self):
        """Creates a valid JsonSchema object

        Returns:
            dict
        """
        return {
            inflection.camelize(k, uppercase_first_letter=False): v
            for k, v in self.attributes.items() if v is not None
        }

    def __str__(self):
        return str(self.schema())


class StringField(Field):
    """String field

    Args:
        max_length (int): The maximum length of the field
        min_length (int): The minimum length of the field
        pattern (str): Field must match the regular expression
        **kwargs: Additional kwargs to be passed to BaseField
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
        **kwargs: Additional kwargs to be passed to BaseField
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


class IntField(NumberField):
    """Integer field"""
    __type__ = 'int'


class FloatField(NumberField):
    """Float field"""
    __type__ = 'long'


class BooleanField(Field):
    """Boolean field"""
    __type__ = 'boolean'


class ListField(Field):
    """List field

    Args:
        field (Field): A field to validate each type against
        max_items (int): The maximum length of array
        min_items (int): The minimum length of array
        unique_items (bool): 	If true, each item in the array must be unique.
            Otherwise, no uniqueness constraint is enforced.
        **kwargs:
    """

    __type__ = 'array'

    def __init__(self, field=None, max_items=None, min_items=None, unique_items=None, **kwargs):
        _v(max_items, _is_positive_int, '{} is not a valid value for max_items')
        _v(min_items, _is_positive_int, '{} is not a valid value for min_items')

        super().__init__(
            **kwargs,
            max_items=max_items,
            min_items=min_items,
            unique_items=unique_items,
            items=None if field is None else field.schema()
        )


class DictField(Field):
    """Dict Field

    Args:
        props (dict): A name => Field map of known properties
        max_props (int): The maximum number of properties allowed
        min_props (int): The minimum number of properties allowed
        additional_props (Field | bool): If ``true``, additional fields are allowed.
            If ``false``, only properties specified in ``props`` are allowed.
            If an instance of ``Field`` is specified, additional fields must validate against that field.
        required_props (list of str): Property names that must be included
        **kwargs:
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

        ap = additional_props  # just a shorter name

        super().__init__(
            **kwargs,
            max_properties=max_props,
            min_properties=min_props,
            properties=props if props is None else {k: v.schema() for k, v in props.items()},
            additional_properties=ap.schema() if isinstance(ap, Field) else ap
        )

        required_props = [] if required_props is None else list(copy.deepcopy(required_props))
        if props is not None:
            for name, field in props.items():
                if field.required:
                    required_props.append(name)

        self.required_props = list(set(required_props))

    def schema(self):
        schema = super().schema()
        if len(self.required_props) > 0:
            schema['required'] = self.required_props
        return schema


class MapField(DictField):
    def __init__(self, field, **kwargs):
        super().__init__(**kwargs, additional_props=field)


class _WithListFieldsInput(Field):
    """Base class for fields that take as input multiple ``Field`` parameters

    Args:
        *fields (Field): Allowed fields
        **kwargs:
    """
    def __init__(self, *fields, **kwargs):
        if len(fields) == 0:
            raise ValueError('At least one field must be provided')

        key = inflection.underscore(self.__class__.__name__)
        kwargs[key] = [field.schema() for field in fields]
        super().__init__(**kwargs)


class OneOf(_WithListFieldsInput):
    """value must match exactly one of the specified fields"""


class AllOf(_WithListFieldsInput):
    """value must match all specified fields"""


class AnyOf(_WithListFieldsInput):
    """value must match at least one of the specified fields"""


class Not(Field):
    """Allow anything that does not match the given field

    Args:
        field (Field): value must not match this field
        **kwargs:
    """
    def __init__(self, field, **kwargs):
        kwargs['not'] = field.schema()
        super().__init__(**kwargs)


class DateTimeField(Field):
    """Datetime field"""
    __type__ = 'date'


class TimeStamp(Field):
    """Timestamp field"""
    __type__ = 'timestamp'


class ObjectIDField(Field):
    """ObjectID field"""
    __type__ = 'objectId'

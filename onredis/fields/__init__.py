import typing

from .basic import (
    AbstractField,
    GenericField,
    BytesField,
    StrField,
    IntField,
    FloatField,
    BooleanField,
)
from .dictionary_field import DictionaryField


def get_field(field_type, default_value, allow_generic=True):
    field_class_args = tuple()

    # create an instance of AbstractField or use the one provided as a default value
    if isinstance(default_value, AbstractField):
        # use the default
        return default_value

    # create a new instance of AbstractField
    if isinstance(field_type, typing._GenericAlias):
        if field_type.__origin__ == typing.Union:
            # Union

            args = field_type.__args__
            if len(args) == 2 and args[1] is type(None):
                field_type = args[0]
            else:
                field_type = typing.Any
        else:
            # Not Union

            if not allow_generic:
                raise ValueError("Generic can't be nested")
            # this is a generic alias like Dict[int, str] or List[str]
            # create Field for each arguments
            field_class_args = [
                get_field(t, None, allow_generic=False) for t in field_type.__args__
            ]
            # look into FIELD_CLASSES using the origin type (typing.Dict -> dict)
            field_type = field_type.__origin__

    field_class = FIELD_CLASSES.get(field_type, GenericField)
    return field_class(*field_class_args, default_value=default_value)


FIELD_CLASSES = {
    bytes: BytesField,
    str: StrField,
    int: IntField,
    float: FloatField,
    bool: BooleanField,
    dict: DictionaryField,
    typing.Dict: DictionaryField,
    typing.Mapping: DictionaryField,
}

from enum import Enum
from inspect import isclass
from typing import Dict, Type

from graphql import GraphQLEnumValue, GraphQLSchema, assert_enum_type, is_enum_type

EnumTypeMap = Dict[str, Type[Enum]]

enum_type_map: EnumTypeMap = {}


def enum_type(_cls):
    # if _cls is a class, use _cls name.
    if isclass(_cls):
        enum_type_map[_cls.__name__] = _cls
        return _cls

    # if not, _cls is type name.
    def wrap(cls):
        if isinstance(cls, Enum):
            raise Exception('enum_resolver must resolve a Enum class.')
        enum_type_map[_cls] = cls
        return cls

    return wrap


def register_enums(schema: GraphQLSchema):
    for type_name, type_ in schema.type_map.items():
        if not is_enum_type(type_) or type_name.startswith('__'):
            continue

        type_ = assert_enum_type(type_)
        _enum_type = enum_type_map.get(type_name)
        if not _enum_type:
            type_.values = {value: GraphQLEnumValue(value) for value in type_.values}
        else:
            type_.values = {value.name: GraphQLEnumValue(value.value) for value in _enum_type}

import json
from datetime import datetime, timezone
from inspect import isclass
from numbers import Number
from typing import Any, Dict

from graphql import (
    INVALID,
    GraphQLSchema,
    IntValueNode,
    StringValueNode,
    assert_scalar_type,
    is_scalar_type,
)
from graphql.pyutils import inspect, is_integer

ScalarTypeMap = Dict[str, Any]

scalar_type_map: ScalarTypeMap = {}


def scalar_type(_cls):
    # if _cls is a class, use _cls name.
    if isclass(_cls):
        scalar_type_map[_cls.__name__] = _cls
        return _cls

    # if not, _cls is type name.
    def wrap(cls):
        scalar_type_map[_cls] = cls
        return cls

    return wrap


def register_scalars(schema: GraphQLSchema):
    for type_name, _scalar_type in scalar_type_map.items():
        type_ = schema.get_type(type_name)
        if not type_:
            continue
        if not is_scalar_type(type_):
            raise Exception(f'{type_name} is not a scalar type.')
        type_ = assert_scalar_type(type_)
        serialize = getattr(_scalar_type, 'serialize', None)
        if serialize:
            type_.serialize = serialize
        parse_value = getattr(_scalar_type, 'parse_value', None)
        if parse_value:
            type_.parse_value = parse_value
        parse_literal = getattr(_scalar_type, 'parse_literal', None)
        if parse_literal:
            type_.parse_literal = parse_literal


@scalar_type
class Upload:
    description = """The `Upload` type represents a type implement graphql multipart request spec
    (https://github.com/jaydenseric/graphql-multipart-request-spec)."""

    @staticmethod
    def serialize(value: Any) -> Any:
        return value

    @staticmethod
    def parse_value(value: Any) -> Any:
        return value

    @staticmethod
    def parse_literal(ast, _variables=None):
        return ast


@scalar_type
class Timestamp:
    description = "The `Timestamp` represents a millisecond unix timestamp with time zone."

    @staticmethod
    def serialize(value: Any) -> int:
        if isinstance(value, Number):
            return int(value)
        if isinstance(value, str) and value.isdigit():
            return int(value)

        if not isinstance(value, datetime):
            raise TypeError(f'Timestamp cannot represent non datetime value: {inspect(value)}')
        return int(value.timestamp() * 1000)

    @staticmethod
    def parse_value(value: Any) -> datetime:
        if not is_integer(value):
            raise TypeError(f'Timestamp cannot represent non datetime value: {inspect(value)}')
        return datetime.utcfromtimestamp(int(value) / 1000).replace(tzinfo=timezone.utc)

    @staticmethod
    def parse_literal(ast, _variables=None):
        if isinstance(ast, IntValueNode):
            return datetime.utcfromtimestamp(int(ast.value) / 1000).replace(tzinfo=timezone.utc)

        return INVALID


@scalar_type
class JSONString:
    description = "The `JSONString` represents a json string."

    @staticmethod
    def serialize(value: Any) -> str:
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value)

        if isinstance(value, str):
            return value
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    @staticmethod
    def parse_value(value: Any) -> dict:
        if not isinstance(value, str):
            raise TypeError(f'JSONString cannot represent non string value: {inspect(value)}')
        return json.loads(value)

    @staticmethod
    def parse_literal(ast, _variables=None):
        if isinstance(ast, StringValueNode):
            return json.loads(ast.value)

        return INVALID

import json
from typing import NewType, Any

import graphql
from graphql.pyutils import inspect, is_integer

ID = NewType('ID', str)
Upload = NewType('Upload', object)
JSONString = NewType('JSONString', object)


def serialize_upload(value: Any) -> Any:
    return value


def coerce_upload(value: Any) -> Any:
    return value


def parse_upload_literal(ast, _variables=None):
    return ast


GraphQLUpload = graphql.GraphQLScalarType(
    name='Upload',
    description="The `Upload` type represents a type implement graphql multipart request spec"
    "(https://github.com/jaydenseric/graphql-multipart-request-spec).",
    serialize=serialize_upload,
    parse_value=coerce_upload,
    parse_literal=parse_upload_literal,
)


def serialize_json(value: dict) -> str:
    return json.dumps(value)


def coerce_json(value: str) -> dict:
    if not isinstance(value, str):
        raise TypeError(f"JSON cannot represent a non string value: {inspect(value)}")
    return json.loads(value)


def parse_json_literal(ast, _variables=None):
    if isinstance(ast, graphql.StringValueNode):
        return json.loads(ast.value)

    return graphql.INVALID


GraphQLJSONString = graphql.GraphQLScalarType(
    name='JSONString',
    description="The `JSONString` type represents a json string.",
    serialize=serialize_json,
    parse_value=coerce_json,
    parse_literal=parse_json_literal,
)

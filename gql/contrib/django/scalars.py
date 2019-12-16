from datetime import datetime, timezone
from typing import Any

import graphql
from graphql.pyutils import inspect, is_integer

from .settings import api_settings


def serialize_timestamp(value: Any) -> int:
    if not isinstance(value, datetime):
        raise TypeError(f'Timestamp cannot represent non datetime value: {inspect(value)}')
    return int(value.timestamp() * 1000)


def coerce_timestamp(value: Any) -> datetime:
    if not is_integer(value):
        raise TypeError(f'Timestamp cannot represent non datetime value: {inspect(value)}')
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)


def parse_timestamp_literal(ast, _variables=None):
    if isinstance(ast, graphql.IntValueNode):
        return datetime.fromtimestamp(int(ast.value) / 1000, tz=timezone.utc)

    return graphql.INVALID


GraphQLTimestamp = graphql.GraphQLScalarType(
    name='Timestamp',
    description="The `Timestamp` represents a millisecond unix timestamp.",
    serialize=serialize_timestamp,
    parse_value=coerce_timestamp,
    parse_literal=parse_timestamp_literal,
)


def update_scalars():
    if api_settings.DATETIME_CONVERT_TIMESTAMP:
        from gql.type_converter import REGISTRY

        REGISTRY[datetime] = GraphQLTimestamp

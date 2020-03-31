from typing import Union

import graphql

from .resolver import register_resolvers


def build_schema(
    source: Union[str, graphql.Source],
    assume_valid=False,
    assume_valid_sdl=False,
    no_location=False,
    experimental_fragment_variables=False,
):
    schema = graphql.build_schema(
        source, assume_valid, assume_valid_sdl, no_location, experimental_fragment_variables
    )
    register_resolvers(schema)
    return schema


def build_schema_from_file(file: str) -> graphql.GraphQLSchema:
    with open(file, 'r') as f:
        schema = build_schema(f.read())
        return schema

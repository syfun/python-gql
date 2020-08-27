from typing import List, Union, cast

from graphql import (
    GraphQLObjectType,
    GraphQLSchema,
    GraphQLUnionType,
    build_schema,
    extend_schema,
    parse,
)

from .enum import register_enums
from .federation import (
    federation_entity_type_defs,
    federation_service_type_defs,
    get_entity_types,
    purge_schema_directives,
    remove_subscription,
    resolve_entities,
)
from .resolver import register_resolvers
from .scalar import register_scalars
from .utils import join_type_defs


def make_schema(
    type_defs: Union[str, List[str]],
    assume_valid: bool = False,
    assume_valid_sdl: bool = False,
    no_location: bool = False,
    experimental_fragment_variables: bool = False,
    federation: bool = False,
) -> GraphQLSchema:
    if isinstance(type_defs, list):
        type_defs = join_type_defs(type_defs)

    if not federation:
        schema = build_schema(
            type_defs, assume_valid, assume_valid_sdl, no_location, experimental_fragment_variables
        )
    else:
        schema = make_federation_schema(type_defs)

    register_resolvers(schema)
    register_enums(schema)
    register_scalars(schema)
    return schema


def make_schema_from_file(
    file: str,
    assume_valid: bool = False,
    assume_valid_sdl: bool = False,
    no_location: bool = False,
    experimental_fragment_variables: bool = False,
    federation: bool = False,
) -> GraphQLSchema:
    with open(file, 'r') as f:
        schema = make_schema(
            f.read(),
            assume_valid,
            assume_valid_sdl,
            no_location,
            experimental_fragment_variables,
            federation,
        )
        return schema


def make_federation_schema(
    type_defs: str,
    assume_valid: bool = False,
    assume_valid_sdl: bool = False,
    no_location: bool = False,
    experimental_fragment_variables: bool = False,
):
    # Remove custom schema directives (to avoid apollo-gateway crashes).
    sdl = purge_schema_directives(type_defs)

    # remove subscription because Apollo Federation not support subscription yet.
    sdl = remove_subscription(type_defs)

    type_defs = join_type_defs([type_defs, federation_service_type_defs])
    schema = build_schema(
        type_defs, assume_valid, assume_valid_sdl, no_location, experimental_fragment_variables
    )
    entity_types = get_entity_types(schema)
    if entity_types:
        schema = extend_schema(schema, parse(federation_entity_type_defs))

        # Add _entities query.
        entity_type = schema.get_type("_Entity")
        if entity_type:
            entity_type = cast(GraphQLUnionType, entity_type)
            entity_type.types = entity_types

        query_type = schema.get_type("Query")
        if query_type:
            query_type = cast(GraphQLObjectType, query_type)
            query_type.fields["_entities"].resolve = resolve_entities

    # Add _service query.
    query_type = schema.get_type("Query")
    if query_type:
        query_type = cast(GraphQLObjectType, query_type)
        query_type.fields["_service"].resolve = lambda _service, info: {"sdl": sdl}

    return schema

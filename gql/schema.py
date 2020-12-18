from pathlib import Path
from typing import Dict, List, Type, Union, cast

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
from .schema_visitor import SchemaDirectiveVisitor
from .utils import join_type_defs


def make_schema(
    type_defs: Union[str, List[str]],
    assume_valid: bool = False,
    assume_valid_sdl: bool = False,
    no_location: bool = False,
    experimental_fragment_variables: bool = False,
    federation: bool = False,
    directives: Dict[str, Type[SchemaDirectiveVisitor]] = None,
) -> GraphQLSchema:
    if isinstance(type_defs, list):
        type_defs = join_type_defs(type_defs)

    if federation:
        # Remove custom schema directives (to avoid apollo-gateway crashes).
        sdl = purge_schema_directives(type_defs)

        # remove subscription because Apollo Federation not support subscription yet.
        # type_defs = remove_subscription(type_defs)

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
    else:
        schema = build_schema(
            type_defs, assume_valid, assume_valid_sdl, no_location, experimental_fragment_variables
        )

    register_resolvers(schema)
    register_enums(schema)
    register_scalars(schema)

    if directives:
        SchemaDirectiveVisitor.visit_schema_directives(schema, directives)
    return schema


def make_schema_from_file(
    file: str,
    assume_valid: bool = False,
    assume_valid_sdl: bool = False,
    no_location: bool = False,
    experimental_fragment_variables: bool = False,
    federation: bool = False,
    directives: Dict[str, Type[SchemaDirectiveVisitor]] = None,
) -> GraphQLSchema:
    with open(file, 'r') as f:
        schema = make_schema(
            f.read(),
            assume_valid,
            assume_valid_sdl,
            no_location,
            experimental_fragment_variables,
            federation,
            directives,
        )
        return schema


def parse_from_file(file: Path):
    with file.open('r') as f:
        type_defs = f.read()
        parse(type_defs)
        return type_defs


base_type_defs = """
type Query
type Mutation
"""


def make_schema_from_path(
    path: str,
    assume_valid: bool = False,
    assume_valid_sdl: bool = False,
    no_location: bool = False,
    experimental_fragment_variables: bool = False,
    federation: bool = False,
    directives: Dict[str, Type[SchemaDirectiveVisitor]] = None,
):
    p = Path(path)
    if p.is_file():
        type_defs = parse_from_file(p)
    elif p.is_dir():
        type_defs = [base_type_defs]
        for file in p.glob('*.graphql'):
            type_defs.extend([parse_from_file(file)])
    else:
        raise RuntimeError('path: expect a file or directory!')

    return make_schema(
        type_defs,
        assume_valid,
        assume_valid_sdl,
        no_location,
        experimental_fragment_variables,
        federation,
        directives,
    )
import re
from inspect import isawaitable
from typing import Any, List

from graphql import (
    DirectiveNode,
    GraphQLInputObjectType,
    GraphQLNamedType,
    GraphQLObjectType,
    GraphQLResolveInfo,
    GraphQLSchema,
)

federation_service_type_defs = """
    scalar _Any

    type _Service {
      sdl: String
    }

    extend type Query {
      _service: _Service!
    }

    directive @external on FIELD_DEFINITION
    directive @requires(fields: String) on FIELD_DEFINITION
    directive @provides(fields: String) on FIELD_DEFINITION
    directive @key(fields: String) on OBJECT | INTERFACE

    # this is an optional directive discussed below
    directive @extends on OBJECT | INTERFACE
"""

federation_entity_type_defs = """
    # a union of all types that use the @key directive
    union _Entity

    extend type Query {
        _entities(representations: [_Any!]!): [_Entity]!
    }
"""

_i_token_delimiter = r"(?:^|[\s\r\n]+|$)"
_i_token_name = "[_A-Za-z][_0-9A-Za-z]*"
_i_token_arguments = r"\([^)]*\)"
_i_token_location = "[_A-Za-z][_0-9A-Za-z]*"

_r_directive_definition = re.compile(
    "("
    f"{_i_token_delimiter}directive"
    f"(?:{_i_token_delimiter})?@({_i_token_name})"
    f"(?:(?:{_i_token_delimiter})?{_i_token_arguments})?"
    f"{_i_token_delimiter}on"
    f"{_i_token_delimiter}(?:[|]{_i_token_delimiter})?{_i_token_location}"
    f"(?:{_i_token_delimiter}[|]{_i_token_delimiter}{_i_token_location})*"
    ")"
    f"(?={_i_token_delimiter})",
)

_r_directive = re.compile(
    "("
    f"(?:{_i_token_delimiter})?@({_i_token_name})"
    f"(?:(?:{_i_token_delimiter})?{_i_token_arguments})?"
    ")"
    f"(?={_i_token_delimiter})",
)

_allowed_directives = [
    "skip",  # Default directive as per specs.
    "include",  # Default directive as per specs.
    "deprecated",  # Default directive as per specs.
    "external",  # Federation directive.
    "requires",  # Federation directive.
    "provides",  # Federation directive.
    "key",  # Federation directive.
    "extends",  # Federation directive.
]


def purge_schema_directives(joined_type_defs: str) -> str:
    """Remove custom schema directives from federation."""
    joined_type_defs = _r_directive_definition.sub("", joined_type_defs)
    joined_type_defs = _r_directive.sub(
        lambda m: m.group(1) if m.group(2) in _allowed_directives else "", joined_type_defs,
    )
    return joined_type_defs


def gather_directives(type_object: GraphQLNamedType,) -> List[DirectiveNode]:
    """Get all directive attached to a type."""
    directives: List[DirectiveNode] = []

    if hasattr(type_object, "extension_ast_nodes"):
        if type_object.extension_ast_nodes:
            for ast_node in type_object.extension_ast_nodes:
                if ast_node.directives:
                    directives.extend(ast_node.directives)

    if hasattr(type_object, "ast_node"):
        if type_object.ast_node and type_object.ast_node.directives:
            directives.extend(type_object.ast_node.directives)

    return directives


def includes_directive(type_object: GraphQLNamedType, directive_name: str,) -> bool:
    """Check if specified type includes a directive."""
    if isinstance(type_object, GraphQLInputObjectType):
        return False

    directives = gather_directives(type_object)
    return any([d.name.value == directive_name for d in directives])


def get_entity_types(schema: GraphQLSchema) -> List[GraphQLNamedType]:
    """Get all types that include the @key directive."""
    schema_types = schema.type_map.values()

    def check_type(t):
        return isinstance(t, GraphQLObjectType) and includes_directive(t, "key")

    return [t for t in schema_types if check_type(t)]


def resolve_entities(_: Any, info: GraphQLResolveInfo, **kwargs) -> Any:
    representations = list(kwargs.get("representations", list()))

    result = []
    for reference in representations:
        __typename = reference["__typename"]
        type_object = info.schema.get_type(__typename)

        if not type_object or not isinstance(type_object, GraphQLObjectType):
            raise Exception(
                f"The `_entities` resolver tried to load an entity for"
                f' type "{__typename}", but no object type of that name'
                f" was found in the schema",
            )

        resolve_reference = getattr(
            type_object, "__resolve_reference__", lambda o, i, r: reference,
        )

        representation = resolve_reference(type_object, info, reference)

        if isawaitable(representation):
            result.append(add_typename_to_async_return(representation, __typename))
        else:
            result.append(add_typename_to_possible_return(representation, __typename))

    return result


def add_typename_to_possible_return(obj: Any, typename: str) -> Any:
    if obj is not None:
        if isinstance(obj, dict):
            obj["__typename"] = typename
        else:
            setattr(obj, f"_{obj.__class__.__name__}__typename", typename)
        return obj
    return {"__typename": typename}


async def add_typename_to_async_return(obj: Any, typename: str) -> Any:
    return add_typename_to_possible_return(await obj, typename)

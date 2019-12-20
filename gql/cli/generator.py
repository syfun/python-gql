from typing import cast, List

from graphql import (
    GraphQLType,
    is_non_null_type,
    is_list_type,
    is_interface_type,
    GraphQLWrappingType,
    is_wrapping_type,
    get_named_type,
    is_leaf_type,
    TypeDefinitionNode,
    GraphQLNamedType,
    GraphQLField,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLInputField,
)
from graphql.language.parser import SourceType, parse
from graphql.type.schema import TypeMap
from graphql.utilities.build_ast_schema import ASTDefinitionBuilder
from graphql.validation.validate import assert_valid_sdl

from gql.utils.str_converters import to_snake_case

SCALAR_MAP = {
    'String': 'typing.Text',
    'Int': 'int',
    'Float': 'float',
    'Boolean': 'bool'
}


def get_type_literal(type_: GraphQLType) -> str:
    """
    String! => typing.Text
    String => typing.Optional[typing.Text]
    [Character!]! => ['Character']
    [Character!] => typing.Optional['Character']
    [Character] => typing.Optional[typing.List[typing.Optional['Character']]]
    """
    is_null = False
    if is_non_null_type(type_):
        type_ = cast(GraphQLWrappingType, type_).of_type
    else:
        is_null = True

    if is_wrapping_type(type_):
        type_ = cast(GraphQLWrappingType, type_)
        value = get_type_literal(type_.of_type)
        if is_list_type(type_):
            value = f'typing.List[{value}]'
    else:
        type_ = get_named_type(type_)
        value = SCALAR_MAP.get(type_.name) or type_.name
        value = value if is_leaf_type(type_) or is_interface_type(type_) else f"'{value}'"

    if is_null:
        value = f'typing.Optional[{value}]'

    return value


def get_field_def(name: str, field: GraphQLField):
    return_type = get_type_literal(field.type)
    args_value = ': '
    if field.args:
        args = [f'{to_snake_case(arg_name)}: {get_type_literal(arg.type)}' for arg_name, arg in field.args.items()]
        args_value = '(parent, info, ' + ', '.join(args) + ') -> '

    return f'{to_snake_case(name)}{args_value}{return_type}'


def get_input_field_def(name: str, field: GraphQLInputField):
    return_type = get_type_literal(field.type)
    return f'{to_snake_case(name)}: {return_type}'


def get_type_map(source: SourceType) -> TypeMap:
    document_ast = parse(source)
    assert_valid_sdl(document_ast)
    type_defs: List[TypeDefinitionNode] = []
    for def_ in document_ast.definitions:
        if isinstance(def_, TypeDefinitionNode):
            type_defs.append(def_)

    def resolve_type(type_name: str) -> GraphQLNamedType:
        type_ = type_map.get(type_name)
        if not type_:
            raise TypeError(f"Type '{type_name}' not found in document.")
        return type_

    ast_builder = ASTDefinitionBuilder(resolve_type=resolve_type)
    type_map = {node.name.value: ast_builder.build_type(node) for node in type_defs}
    return type_map


def get_interface_def(type_: GraphQLInterfaceType):
    def_ = f'\nclass {type_.name}:\n'
    for name, field in type_.fields.items():
        def_ += f'    {get_field_def(name, field)}\n'
    return def_


def get_object_def(type_: GraphQLObjectType):
    def_ = f'\nclass {type_.name}'
    if type_.interfaces:
        interfaces = ', '.join([i.name for i in type_.interfaces])
        def_ += f'({interfaces})'
    def_ += ':\n'
    for name, field in type_.fields.items():
        def_ += f'    {get_field_def(name, field)}\n'
    return def_


def get_input_def(type_: GraphQLInputObjectType):
    def_ = f'\nclass {type_.name}:\n'
    for name, field in type_.fields.items():
        def_ += f'    {get_input_field_def(name, field)}\n'
    return def_


def get_enum_def(type_: GraphQLEnumType):
    def_ = f'\nclass {type_.name}(Enum):\n'
    i = 1
    for key in type_.values.keys():
        def_ += f'   {key} = {i}\n'
        i += 1
    return def_

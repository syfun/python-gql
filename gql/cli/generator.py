from typing import Dict, List, Union, cast

from graphql import (
    GraphQLEnumType,
    GraphQLField,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLNamedType,
    GraphQLObjectType,
    GraphQLType,
    GraphQLWrappingType,
    Source,
    TypeDefinitionNode,
    get_named_type,
    is_leaf_type,
    is_list_type,
    is_non_null_type,
    is_wrapping_type,
    parse,
)
from graphql.utilities.build_ast_schema import ASTDefinitionBuilder
from graphql.validation.validate import assert_valid_sdl

from gql.utils import to_snake_case

TypeMap = Dict[str, GraphQLNamedType]
SourceType = Union[Source, str]

SCALAR_MAP = {'String': 'Text', 'Int': 'int', 'Float': 'float', 'Boolean': 'bool'}


def get_type_literal(type_: GraphQLType) -> str:
    """
    String! => Text
    String => Optional[Text]
    [Character!]! => ['Character']
    [Character!] => Optional['Character']
    [Character] => Optional[List[Optional['Character']]]
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
            value = f'List[{value}]'
    else:
        type_ = get_named_type(type_)
        value = SCALAR_MAP.get(type_.name) or type_.name
        value = value if is_leaf_type(type_) else f"'{value}'"
        # value = value if is_leaf_type(type_) or is_interface_type(type_) else f"'{value}'"

    if is_null:
        value = f'Optional[{value}]'

    return value


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
            raise TypeError(f"""Type '{type_name}' not found in document.""")
        return type_

    ast_builder = ASTDefinitionBuilder(resolve_type=resolve_type)
    type_map = {node.name.value: ast_builder.build_type(node) for node in type_defs}
    return type_map


class FieldGenerator:
    @staticmethod
    def output_field(name: str, field: GraphQLField):
        return_type = get_type_literal(field.type)
        args_value = ': '
        if field.args:
            args = [
                f'{to_snake_case(arg_name)}: {get_type_literal(arg.type)}'
                for arg_name, arg in field.args.items()
            ]
            args_value = '(parent, info, ' + ', '.join(args) + ') -> '

        return f'{to_snake_case(name)}{args_value}{return_type}'

    @staticmethod
    def input_field(name: str, field: GraphQLInputField):
        return_type = get_type_literal(field.type)
        return f"{to_snake_case(name)}: {return_type}"


class TypeGenerator:
    """
    kind show type kine, may be none, dataclass or pydantic.
    Example:
        none:
            class Person:
                name: Text
                age: int
        dataclass:
            from dataclasses import dataclass

            @dataclass
            class Person:
                name: Text
                age: int

        pydantic:
            from pydantic import BaseModel

            class Person(BaseModel):
                name: Text
                age: int
    """

    def __init__(self, kind: str = 'none'):
        # TODO: exception
        assert kind in ['none', 'dataclass', 'pydantic']
        self.kind = kind

    def interface_type(self, type_: GraphQLInterfaceType):
        def_ = f'\nclass {type_.name}'
        if self.kind == 'dataclass':
            def_ = '@dataclass' + def_
        elif self.kind == 'pydantic':
            def_ += '(BaseModel)'
        def_ += ':\n'

        for name, field in type_.fields.items():
            def_ += f'    {FieldGenerator.output_field(name, field)}\n'
        return def_

    def object_type(self, type_: GraphQLObjectType):
        def_ = f'\nclass {type_.name}'
        if self.kind == 'dataclass':
            def_ = '@dataclass' + def_

        if type_.interfaces:
            interfaces = ', '.join([i.name for i in type_.interfaces])
            def_ += f'({interfaces})'
        def_ += ':\n'
        for name, field in type_.fields.items():
            def_ += f'    {FieldGenerator.output_field(name, field)}\n'
        return def_

    def input_type(self, type_: GraphQLInputObjectType):
        def_ = f'\nclass {type_.name}'
        if self.kind == 'dataclass':
            def_ = '@dataclass' + def_
        elif self.kind == 'pydantic':
            def_ += '(BaseModel)'
        def_ += ':\n'

        for name, field in type_.fields.items():
            def_ += f'    {FieldGenerator.input_field(name, field)}\n'
        return def_

    def enum_type(self, type_: GraphQLEnumType):
        def_ = f'\n@enum_resolver\nclass {type_.name}(Enum):\n'

        i = 1
        for key in type_.values.keys():
            def_ += f'   {key} = {i}\n'
            i += 1
        return def_

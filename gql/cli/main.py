from typing import cast

import fire
from graphql import (
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    assert_interface_type,
    assert_object_type,
    build_schema,
    is_enum_type,
    is_input_object_type,
    is_interface_type,
    is_object_type,
)

from .generator import FieldGenerator, TypeGenerator, get_type_map


class Command:
    @staticmethod
    def types(file: str, kind: str = 'none'):
        """Print schema types.
        
        FILE: graphql sdl file
        KIND: none, dataclass or pydantic
        """
        if kind not in ['none', 'dataclass', 'pydantic']:
            print('KIND must be none, dataclass or pydantic')
            return

        with open(file, 'r') as f:
            type_defs = f.read()

        generator = TypeGenerator(kind)

        enum_types, interface_types, object_types, input_types = [], [], [], []
        for name, type_ in get_type_map(type_defs).items():
            if name in ['Query', 'Mutation']:
                continue
            elif is_enum_type(type_):
                enum_types.append(generator.enum_type(cast(GraphQLEnumType, type_)))
            elif is_object_type(type_):
                object_types.append(generator.object_type(cast(GraphQLObjectType, type_)))
            elif is_interface_type(type_):
                interface_types.append(generator.interface_type(cast(GraphQLInterfaceType, type_)))
            elif is_input_object_type(type_):
                input_types.append(generator.input_type(cast(GraphQLInputObjectType, type_)))
        imports, body = '', ''

        if enum_types:
            body += '\n'.join(enum_types) + '\n'
        if interface_types:
            body += '\n'.join(interface_types) + '\n'
        if object_types:
            body += '\n'.join(object_types) + '\n'
        if input_types:
            body += '\n'.join(input_types)

        if 'typing.' in body:
            imports += 'import typing\n'
        if kind == 'dataclass':
            imports += 'from dataclasses import dataclass\n'
        if enum_types:
            imports += 'from enum import Enum\n'
        if kind == 'pydantic':
            imports += 'from pydantic import BaseModel\n'
        imports += '\n'

        return imports + body

    @staticmethod
    def resolver(file: str, type_name: str, field_name: str):
        """Print resolver.

        FILE: graphql sdl file
        TYPE_NAME: graphql type name
        FIELD_NAME: graphql type field name
        """
        with open(file, 'r') as f:
            type_defs = f.read()

        schema = build_schema(type_defs)
        type_ = schema.get_type(type_name)
        if is_object_type(type_):
            type_ = assert_object_type(type_)
        elif is_interface_type(type_):
            type_ = assert_interface_type(type_)
        else:
            print(f'{type_name} is not type or not object type or not interface type')

        field = type_.fields.get(field_name)
        if not field:
            print(f'{type_name} has no {field_name} field')
            return

        output = f"@resolver('{type_name}', '{field_name}')\ndef "
        output += FieldGenerator.output_field(field_name, field) + ':\n    pass\n'
        return output


def main():
    fire.Fire(Command())

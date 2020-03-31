import os
from typing import cast

import click
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


@click.group()
def main():
    pass


def guess_schema_file():
    files = os.listdir(os.path.curdir)
    print(files)
    for f in files:
        if os.path.isdir(f):
            continue
        if f.endswith('.gql') or f.endswith('.graphql'):
            return f
    return None


@main.command()
@click.option('--file', help='graphql sdl file, file extension may be .gql or .graphql')
@click.option('--kind', default='none', help='generate class based: none, dataclass, pydantic')
def types(file: str, kind: str):
    """Print schema types."""
    if kind not in ['none', 'dataclass', 'pydantic']:
        print('KIND must be none, dataclass or pydantic')
        return

    if not file:
        file = guess_schema_file()
    if not file:
        print("Must has 'file' argument or has a graphql sdl file which endswith .gql or .graphql.")
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

    if kind == 'dataclass':
        imports += 'from dataclasses import dataclass\n'
    if enum_types:
        imports += 'from enum import Enum\n'
    imports += 'from typing import Any, Dict, List, Optional, Text, Union'
    if kind == 'pydantic':
        imports += 'from pydantic import BaseModel\n'
    imports += '\n'

    print(imports + body)


@main.command()
@click.option('--file', help='graphql sdl file, file extension may be .gql or .graphql')
@click.argument('type')
@click.argument('field')
def resolver(type: str, field: str, file: str):
    """Print resolver."""
    if not file:
        file = guess_schema_file()
    if not file:
        print("Must has 'file' argument or has a graphql sdl file which endswith .gql or .graphql.")
        return
    with open(file, 'r') as f:
        type_defs = f.read()

    schema = build_schema(type_defs)
    type_ = schema.get_type(type)
    if is_object_type(type_):
        type_ = assert_object_type(type_)
    elif is_interface_type(type_):
        type_ = assert_interface_type(type_)
    else:
        print(f'{type} is not type or not object type or not interface type')

    field = type_.fields.get(field)
    if not field:
        print(f'{type} has no {field} field')
        return

    output = f"@resolver('{type}', '{field}')\ndef "
    output += FieldGenerator.output_field(field, field) + ':\n    pass\n'
    print(output)

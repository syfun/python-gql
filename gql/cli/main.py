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

from .generator import FieldGenerator, TypeGenerator, TypeResolverGenerator, get_type_map


@click.group()
@click.option('-f', '--file', help='graphql sdl file, file extension may be .gql or .graphql')
@click.pass_context
def main(ctx, file):
    # ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)

    if not file:
        file = guess_schema_file()
    if not file:
        print("Must has 'file' argument or has a graphql sdl file which endswith .gql or .graphql.")
        return
    with open(file, 'r') as f:
        ctx.obj['type_defs'] = f.read()


def guess_schema_file():
    files = os.listdir(os.path.curdir)
    for f in files:
        if os.path.isdir(f):
            continue
        if f.endswith('.gql') or f.endswith('.graphql'):
            return f
    return None


@main.command()
@click.pass_context
@click.option(
    '--kind',
    default='pydantic',
    help='generate class based: none, dataclass, pydantic, default is pydantic',
)
@click.argument('typ')
def type(ctx, typ: str, kind: str):
    """Generate one type"""
    generator = TypeGenerator(kind)
    type_map = get_type_map(ctx.obj['type_defs'])
    if typ not in type_map:
        print(f"No '{typ}' type.")
        return

    type_ = type_map[typ]
    type_def = ''
    if is_enum_type(type_):
        type_def = generator.enum_type(cast(GraphQLEnumType, type_))
    if is_object_type(type_):
        type_def = generator.object_type(cast(GraphQLObjectType, type_))
    if is_interface_type(type_):
        type_def = generator.interface_type(cast(GraphQLInterfaceType, type_))
    if is_input_object_type(type_):
        type_def = generator.input_type(cast(GraphQLInputObjectType, type_))

    print(type_def)


@main.command()
@click.pass_context
@click.option(
    '--kind',
    default='pydantic',
    help='generate class based: none, dataclass, pydantic, default is pydantic',
)
def all(ctx, kind: str):
    """Generate all schema types"""
    if kind not in ['none', 'dataclass', 'pydantic']:
        print('KIND must be none, dataclass or pydantic')
        return

    generator = TypeGenerator(kind)

    enum_types, interface_types, object_types, input_types = [], [], [], []
    type_map = get_type_map(ctx.obj['type_defs'])
    for name, type_ in type_map.items():
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

    type_resolvers = TypeResolverGenerator(type_map).all_type_resolvers()
    imports, body = '', ''

    body += "ID = NewType('ID', Text)\n\n"
    if enum_types:
        body += '\n'.join(enum_types) + '\n'
    if interface_types:
        body += '\n'.join(interface_types) + '\n'
    if object_types:
        body += '\n'.join(object_types) + '\n'
    if input_types:
        body += '\n'.join(input_types)
    if type_resolvers:
        body += '\n'.join(type_resolvers)

    if kind == 'dataclass':
        imports += 'from dataclasses import dataclass\n'
    if enum_types:
        imports += 'from enum import Enum\n'
    imports += 'from typing import Any, Dict, List, NewType, Optional, Text, Union\n\n'
    imports += 'from gql import enum_type, type_resolver\n'
    if kind == 'pydantic':
        imports += 'from pydantic import BaseModel\n'
    imports += '\n'

    print(imports + body)


@main.command()
@click.pass_context
@click.argument('type')
@click.argument('field')
def field_resolver(ctx, type: str, field: str):
    """Generate field resolver."""
    schema = build_schema(ctx.obj['type_defs'])
    type_ = schema.get_type(type)
    if is_object_type(type_):
        type_ = assert_object_type(type_)
    elif is_interface_type(type_):
        type_ = assert_interface_type(type_)
    else:
        print(f'{type} is not type or not object type or not interface type')
        return

    field_ = type_.fields.get(field)
    if not field:
        print(f'{type} has no {field} field')
        return

    if type == 'Query':
        output = f'@query\ndef '
    elif type == 'Mutation':
        output = f'@mutate\ndef '
    elif type == 'Subscription':
        output = f'@subscribe\ndef '
    else:
        output = f"@field_resolver('{type}', '{field}')\ndef "
    output += FieldGenerator.resolver_field(field, field_) + ':\n    pass\n'
    print(output)


@main.command()
@click.pass_context
@click.argument('type_name')
def type_resolver(ctx, type_name: str):
    """Generate all schema types"""
    generator = TypeResolverGenerator(get_type_map(ctx.obj['type_defs']))
    print(generator.type_resolver(type_name))

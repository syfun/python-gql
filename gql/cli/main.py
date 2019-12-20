import fire
from graphql import is_enum_type, is_interface_type, is_object_type, build_schema, assert_interface_type, \
    assert_object_type, is_input_object_type

from .generator import (
    get_enum_def,
    get_field_def,
    get_interface_def,
    get_object_def,
    get_type_map,
    get_input_def,
)


class Command:
    def print_type(self, file: str):
        """Print schema types.
        
        FILE: graphql sdl file
        """
        with open(file, 'r') as f:
            SCHEMA = f.read()

        enum_types, interface_types, object_types, input_types = [], [], [], []
        for name, type_ in get_type_map(SCHEMA).items():
            if name in ['Query', 'Mutation']:
                continue
            elif is_enum_type(type_):
                enum_types.append(get_enum_def(type_))
            elif is_object_type(type_):
                object_types.append(get_object_def(type_))
            elif is_interface_type(type_):
                interface_types.append(get_interface_def(type_))
            elif is_input_object_type(type_):
                input_types.append(get_input_def(type_))
        imports, body = '', ''

        if enum_types:
            body += '\n'.join(enum_types) + '\n'
        if interface_types:
            body += '\n'.join(interface_types) + '\n'
        if object_types:
            body += '\n'.join(object_types)
        if input_types:
            body += '\n'.join(input_types)

        if 'typing.' in body:
            imports += 'import typing\n'
        if enum_types:
            imports += 'from enum import Enum\n\n'

        return imports + body

    def print_resolver(self, file: str, type_name: str, field_name: str):
        """Print resolver.

        FILE: graphql sdl file
        TYPE_NAME: graphql type name
        FIELD_NAME: graphql type field name
        """
        with open(file, 'r') as f:
            SCHEMA = f.read()

        schema = build_schema(SCHEMA)
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
        output += get_field_def(field_name, field) + ':\n    pass\n'
        return output


def main():
    fire.Fire(Command())

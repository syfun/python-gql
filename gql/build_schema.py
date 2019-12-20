from graphql import build_schema, GraphQLSchema

from .resolver import register_resolvers


def build_schema_from_file(file: str) -> GraphQLSchema:
    with open(file, 'r') as f:
        schema = build_schema(f.read())
        register_resolvers(schema)
        return schema

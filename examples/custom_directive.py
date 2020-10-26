import graphql

from gql import SchemaDirectiveVisitor, gql, make_schema, query
from gql.resolver import default_field_resolver


class UpperDirective(SchemaDirectiveVisitor):
    def visit_field_definition(self, field, object_type):
        original_resolver = field.resolve or default_field_resolver

        def resolve_upper(obj, info, **kwargs):
            result = original_resolver(obj, info, **kwargs)
            if result is None:
                return None
            return result.upper()

        field.resolve = resolve_upper
        return field


type_defs = gql(
    """
directive @upper on FIELD_DEFINITION

type Query {
    hello(name: String!): String! @upper
}
"""
)


@query
def hello(parent, info, name: str) -> str:
    return name


if __name__ == '__main__':
    schema = make_schema(type_defs, directives={'upper': UpperDirective})

    q = """
    query {
        hello(name: "graphql")
    }
    """
    result = graphql.graphql_sync(schema, q)
    print(result.data)

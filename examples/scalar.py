from gql import gql, make_schema, query
from graphql import graphql_sync


type_defs = gql(
    """
scalar JSON

type Query {
    me: JSON
}
"""
)


@query
def me(_, info):
    return {'name': 'Jack'}


schema = make_schema(type_defs=type_defs)

q = """
query {
    me
}
"""

result = graphql_sync(schema, q)
print(result.data)
print(result.errors)

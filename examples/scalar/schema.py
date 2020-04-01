from graphql import graphql_sync

from gql import gql, query
from gql.build_schema import build_schema

type_defs = gql(
    """
scalar Timestamp

type Person {
    id: String!
    name: String!
    birth: Timestamp
}

type Query {
    person(birth: Timestamp): Person!
}
"""
)


@query
def person(parent, info, birth):
    return {'id': '1', 'name': 'Jack', 'birth': birth}


schema = build_schema(type_defs)


if __name__ == '__main__':
    query = """
query {
    person(birth: 123456789){
        id
        name
        birth
    }
}
    """
    print(schema.type_map['Timestamp'].to_kwargs())
    r = graphql_sync(schema, query)
    print(r)

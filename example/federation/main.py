from gql import gql, make_schema

type_defs = gql(
    """
  type Query {
    me: User
  }

  type User @key(fields: "id") {
    id: ID!
    username: String
  }
"""
)
schema = make_schema(type_defs, federation=True)

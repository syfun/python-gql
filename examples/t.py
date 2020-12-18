import graphql


type_defs = """
type User {
    id: ID!
    name: String!
}
type Query {
    me: User!
}
type Mutation

type Address {
    id: ID!
    name: String!
}

extend type Query {
    addresses: [Address!]!
}

extend type Mutation {
    createAddress(name: String!): Address!
}
"""

if __name__ == '__main__':
    graphql.build_schema(type_defs)
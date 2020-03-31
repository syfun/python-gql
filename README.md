# python-gql

Schema-first python graphql library.

## Install

`pip install python-gql`

## Use `gqlgen` command.

### generate types

`gqlgen ./schema.graphql types --kind=dataclass`

### generator resolver

`gqlgen ./schema.graphql resolver Query hello`

### help info

For more info about `gqlgen`, please use `gqlgen -h`

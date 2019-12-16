from typing import Optional
import gql


@gql.type
class User:
    name: str
    age: int


@gql.input
class CreateUserInput:
    name: str
    age: Optional[int]


@gql.type
class Query:
    @gql.field
    def user(self, info) -> User:
        return User(name="Patrick", age=100)


@gql.type
class Mutation:
    @gql.field
    def create_user(self, info, user: CreateUserInput) -> User:
        print(user)
        return User(name=user.name, age=user.age or 0)


schema = gql.Schema(query=Query, mutation=Mutation)

app = gql.GraphQL(schema)

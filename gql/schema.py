from typing import Dict, Any, Union

from graphql import (
    GraphQLSchema,
    ExecutionResult,
    graphql,
    Source,
    graphql_sync,
    introspection_from_schema,
    print_schema,
)

from .type import ObjectType


class Schema(GraphQLSchema):
    def __init__(
            self, query: ObjectType, mutation: ObjectType = None, subscription: ObjectType = None, types: list = None
    ) -> None:
        super().__init__(
            query=query.field,
            mutation=mutation.field if mutation else None,
            subscription=subscription.field if subscription else None,
            types=[t.field for t in types] if types else None,
        )

    async def asyne_execute(
            self,
            query: Union[str, Source],
            variable_values: Dict[str, Any] = None,
            context_value: Any = None,
            operation_name: str = None,
    ) -> ExecutionResult:
        return await graphql(
            self, query, variable_values=variable_values, context_value=context_value, operation_name=operation_name
        )

    def execute(
            self,
            query: Union[str, Source],
            variable_values: Dict[str, Any] = None,
            context_value: Any = None,
            operation_name: str = None,
    ) -> ExecutionResult:
        return graphql_sync(
            self, query, variable_values=variable_values, context_value=context_value, operation_name=operation_name
        )

    def introspect(self) -> Dict[str, Any]:
        return introspection_from_schema(self)

    def print_sdl(self) -> str:
        return print_schema(self)

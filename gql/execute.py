from typing import Any, Callable, Dict, List, Optional, Union

import graphql
from graphql import located_error
from graphql.execution.execute import get_field_def
from graphql.execution.values import get_argument_values, get_variable_values

from graphql.pyutils import AwaitableOrValue, FrozenList, Path, Undefined, inspect

from .middleware import MiddlewareManager


class ExecutionContext(graphql.ExecutionContext):
    # custom Middleware Manager
    middleware_manager: MiddlewareManager

    @classmethod
    def build(
        cls,
        schema: graphql.GraphQLSchema,
        document: graphql.DocumentNode,
        root_value: Any = None,
        context_value: Any = None,
        raw_variable_values: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None,
        field_resolver: Optional[graphql.GraphQLFieldResolver] = None,
        type_resolver: Optional[graphql.GraphQLTypeResolver] = None,
        middleware: Optional[graphql.Middleware] = None,
        is_awaitable: Optional[Callable[[Any], bool]] = None,
    ) -> Union[List[graphql.GraphQLError], "ExecutionContext"]:
        """Build an execution context

        Constructs a ExecutionContext object from the arguments passed to execute, which
        we will pass throughout the other execution methods.

        Throws a GraphQLError if a valid execution context cannot be created.

        For internal use only.
        """
        operation: Optional[graphql.OperationDefinitionNode] = None
        fragments: Dict[str, graphql.FragmentDefinitionNode] = {}
        middleware_manager: Optional[graphql.MiddlewareManager] = None
        if middleware is not None:
            if isinstance(middleware, (list, tuple)):
                middleware_manager = MiddlewareManager(*middleware)
            elif isinstance(middleware, MiddlewareManager):
                middleware_manager = middleware
            else:
                raise TypeError(
                    "Middleware must be passed as a list or tuple of functions"
                    " or objects, or as a single MiddlewareManager object."
                    f" Got {inspect(middleware)} instead."
                )

        for definition in document.definitions:
            if isinstance(definition, graphql.OperationDefinitionNode):
                if operation_name is None:
                    if operation:
                        return [
                            graphql.GraphQLError(
                                "Must provide operation name"
                                " if query contains multiple operations."
                            )
                        ]
                    operation = definition
                elif definition.name and definition.name.value == operation_name:
                    operation = definition
            elif isinstance(definition, graphql.FragmentDefinitionNode):
                fragments[definition.name.value] = definition

        if not operation:
            if operation_name is not None:
                return [graphql.GraphQLError(f"Unknown operation named '{operation_name}'.")]
            return [graphql.GraphQLError("Must provide an operation.")]

        coerced_variable_values = get_variable_values(
            schema,
            operation.variable_definitions or FrozenList(),
            raw_variable_values or {},
            max_errors=50,
        )

        if isinstance(coerced_variable_values, list):
            return coerced_variable_values  # errors

        return cls(
            schema,
            fragments,
            root_value,
            context_value,
            operation,
            coerced_variable_values,  # coerced values
            field_resolver or graphql.default_field_resolver,
            type_resolver or graphql.default_type_resolver,
            [],
            middleware_manager,
            is_awaitable,
        )

    def resolve_field(
        self,
        parent_type: graphql.GraphQLObjectType,
        source: Any,
        field_nodes: List[graphql.FieldNode],
        path: Path,
    ) -> AwaitableOrValue[Any]:
        """Resolve the field on the given source object.

        In particular, this figures out the value that the field returns by calling its
        resolve function, then calls complete_value to await coroutine objects,
        serialize scalars, or execute the sub-selection-set for objects.
        """
        field_node = field_nodes[0]
        field_name = field_node.name.value

        field_def = get_field_def(self.schema, parent_type, field_name)
        if not field_def:
            return Undefined

        return_type = field_def.type
        resolve_fn = field_def.resolve or self.field_resolver

        if self.middleware_manager:
            resolve_fn = self.middleware_manager.get_field_resolver_by_parent(
                resolve_fn, parent_type.name, field_name
            )

        info = self.build_resolve_info(field_def, field_nodes, parent_type, path)

        # Get the resolve function, regardless of if its result is normal or abrupt
        # (error).
        try:
            # Build a dictionary of arguments from the field.arguments AST, using the
            # variables scope to fulfill any variable references.
            args = get_argument_values(field_def, field_nodes[0], self.variable_values)

            # Note that contrary to the JavaScript implementation, we pass the context
            # value as part of the resolve info.
            result = resolve_fn(source, info, **args)

            completed: AwaitableOrValue[Any]
            if self.is_awaitable(result):
                # noinspection PyShadowingNames
                async def await_result() -> Any:
                    try:
                        completed = self.complete_value(
                            return_type, field_nodes, info, path, await result
                        )
                        if self.is_awaitable(completed):
                            return await completed
                        return completed
                    except Exception as raw_error:
                        error = located_error(raw_error, field_nodes, path.as_list())
                        self.handle_field_error(error, return_type)
                        return None

                return await_result()

            completed = self.complete_value(return_type, field_nodes, info, path, result)
            if self.is_awaitable(completed):
                # noinspection PyShadowingNames
                async def await_completed() -> Any:
                    try:
                        return await completed
                    except Exception as raw_error:
                        error = located_error(raw_error, field_nodes, path.as_list())
                        self.handle_field_error(error, return_type)
                        return None

                return await_completed()

            return completed
        except Exception as raw_error:
            error = located_error(raw_error, field_nodes, path.as_list())
            self.handle_field_error(error, return_type)
            return None

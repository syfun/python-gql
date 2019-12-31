import json
import typing

from graphql import (
    ExecutionResult,
    GraphQLError,
    GraphQLSchema,
    format_error,
    graphql,
    parse,
    subscribe,
)
from starlette import status
from starlette.applications import Starlette
from starlette.background import BackgroundTasks
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from starlette.routing import BaseRoute, Route, WebSocketRoute
from starlette.types import Receive, Scope, Send
from starlette.websockets import Message, WebSocket

from .build_schema import build_schema, build_schema_from_file
from .playground import PLAYGROUND_HTML
from .resolver import register_resolvers
from .utils import place_files_in_operations
from .websockets import GraphQLWebSocket


class GraphQL(Starlette):
    def __init__(
        self,
        *,
        type_defs: str = None,
        schema_file: str = None,
        playground: bool = True,
        debug: bool = False,
        routes: typing.List[BaseRoute] = None
    ):
        routes = routes or []
        if type_defs:
            schema = build_schema(type_defs)
        elif schema_file:
            schema = build_schema_from_file(schema_file)
        else:
            raise Exception('Must provide type def string or file.')
        register_resolvers(schema)

        routes.extend(
            [
                Route('/graphql/', ASGIApp(schema, playground=playground)),
                WebSocketRoute('/graphql/', WebSocketApp(schema)),
            ]
        )
        super().__init__(debug=debug, routes=routes)


class ASGIApp:
    def __init__(self, schema: GraphQLSchema, playground: bool = True) -> None:
        self.schema = schema
        self.playground = playground

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope, receive=receive, send=send)
        response = await self.handle_graphql(request)
        await response(scope, receive, send)

    async def handle_graphql(self, request: Request) -> Response:
        if request.method in ('GET', 'HEAD'):
            if 'text/html' in request.headers.get('Accept', ''):
                if not self.playground:
                    return PlainTextResponse('Not Found', status_code=status.HTTP_404_NOT_FOUND)
                return HTMLResponse(PLAYGROUND_HTML)

            data = request.query_params  # type: typing.Mapping[str, typing.Any]

        elif request.method == 'POST':
            content_type = request.headers.get('Content-Type', '')

            if 'application/json' in content_type:
                data = await request.json()
            elif 'application/graphql' in content_type:
                body = await request.body()
                data = {'query': body.decode()}
            elif 'query' in request.query_params:
                data = request.query_params
            elif 'multipart/form-data' in content_type:
                form = await request.form()
                try:
                    operations = json.loads(form.get('operations', '{}'))
                    files_map = json.loads(form.get('map', '{}'))
                except (TypeError, ValueError):
                    return PlainTextResponse(
                        'operations or map sent invalid JSON',
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
                data = place_files_in_operations(operations, files_map, form)
            else:
                return PlainTextResponse(
                    'Unsupported Media Type', status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                )
        else:
            return PlainTextResponse(
                'Method Not Allowed', status_code=status.HTTP_405_METHOD_NOT_ALLOWED
            )

        try:
            query = data['query']
            variables = data.get('variables')
            operation_name = data.get('operationName')
        except KeyError:
            return PlainTextResponse(
                'No GraphQL query found in the request', status_code=status.HTTP_400_BAD_REQUEST,
            )

        background = BackgroundTasks()
        context = {'request': request, 'background': background}

        result = await graphql(
            self.schema,
            query,
            variable_values=variables,
            operation_name=operation_name,
            context_value=context,
        )
        error_data = [format_error(err) for err in result.errors] if result.errors else None
        response_data = {'data': result.data, 'errors': error_data}
        status_code = status.HTTP_400_BAD_REQUEST if result.errors else status.HTTP_200_OK

        return JSONResponse(response_data, status_code=status_code, background=background)


class WebSocketApp:
    def __init__(self, schema: GraphQLSchema):
        self.schema = schema

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        websocket = GraphQLWebSocket(scope, receive=receive, send=send)
        await websocket.accept('graphql-ws')

        close_code = status.WS_1000_NORMAL_CLOSURE

        try:
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.receive":
                    data = await self.decode(websocket, message)
                    await self.disptach(websocket, data)
                elif message["type"] == "websocket.disconnect":
                    close_code = int(message.get("code", status.WS_1000_NORMAL_CLOSURE))
                    break
        except Exception as exc:
            close_code = status.WS_1011_INTERNAL_ERROR
            raise exc from None
        finally:
            await websocket.close(close_code)

    async def decode(self, websocket: WebSocket, message: Message) -> dict:
        if message.get("text") is not None:
            text = message["text"]
        else:
            text = message["bytes"].decode("utf-8")

        try:
            return json.loads(text)
        except json.decoder.JSONDecodeError:
            await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
            raise RuntimeError("Malformed JSON data received.")

    async def disptach(self, websocket: GraphQLWebSocket, data: typing.Any) -> None:
        type_ = data.get('type')
        if type_ == 'connection_init':
            await websocket.client_init()
        elif type_ == 'connection_terminate':
            await websocket.client_terminate()
        elif type_ == 'start':
            websocket.client_id = data.get('id')
            await self.handle_graphql(websocket, data)
        elif type_ == 'stop':
            await websocket.client_stop()
        else:
            await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)

    async def handle_graphql(self, websocket: GraphQLWebSocket, data: dict) -> None:
        payload = data.get('payload')
        try:
            doc = parse(payload.get('query'))
        except GraphQLError as error:
            await websocket.send_execution_result(ExecutionResult(data=None, errors=[error]))
            return

        result_or_iterator = await subscribe(
            self.schema,
            doc,
            variable_values=payload.get('variables'),
            operation_name=payload.get('operationName'),
        )
        if isinstance(result_or_iterator, ExecutionResult):
            await websocket.send_execution_result(result_or_iterator)
            return

        async for result in result_or_iterator:
            await websocket.send_execution_result(result)

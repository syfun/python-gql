import asyncio
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncIterator, Dict

from graphql import ExecutionResult, GraphQLError, GraphQLSchema, format_error, parse, subscribe
from starlette import status
from starlette.types import Receive, Scope, Send
from starlette.websockets import Message, WebSocket

PROTOCOL = 'graphql-ws'


class MessageType(Enum):
    GQL_CONNECTION_INIT = 'connection_init'  # Client -> Server
    GQL_CONNECTION_ACK = 'connection_ack'  # Server -> Client
    GQL_CONNECTION_ERROR = 'connection_error'  # Server -> Client

    # NOTE: The keep alive message type does not follow the standard due to connection optimizations
    GQL_CONNECTION_KEEP_ALIVE = 'ka'  # Server -> Client
    GQL_CONNECTION_TERMINATE = 'connection_terminate'  # Client -> Server
    GQL_START = 'start'  # Client -> Server
    GQL_DATA = 'data'  # Server -> Client
    GQL_ERROR = 'error'  # Server -> Client
    GQL_COMPLETE = 'complete'  # Server -> Client
    GQL_STOP = 'stop'  # Client -> Server


@dataclass
class OperationMessagePayload:
    query: str = None
    variables: Dict[str, Any] = None
    operation_name: str = None

    @classmethod
    def build(cls, value: dict = None) -> 'OperationMessagePayload':
        if not value:
            return cls()
        return cls(
            query=value.get('query'),
            variables=value.get('variables'),
            operation_name=value.get('operationName'),
        )


@dataclass
class OperationMessage:
    type: MessageType

    id: str = None
    payload: OperationMessagePayload = None

    @classmethod
    def build(cls, value: dict) -> 'OperationMessage':
        assert value is not None
        return cls(
            type=MessageType(value.get('type')),
            id=value.get('id'),
            payload=OperationMessagePayload.build(value.get('payload')),
        )


@dataclass
class ConnectionContext:
    socket: WebSocket
    operations: Dict[str, AsyncIterator[ExecutionResult]]


class Subscription:
    schema: GraphQLSchema

    # socket: WebSocket
    # operations: Dict[str, AsyncIterator[ExecutionResult]]

    def __init__(self, schema: GraphQLSchema) -> None:
        self.schema = schema
        self.operations = {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        socket = WebSocket(scope, receive=receive, send=send)
        await socket.accept(PROTOCOL)

        context = ConnectionContext(socket=socket, operations={})
        await self.on_message(context)

    async def on_message(self, context: ConnectionContext) -> None:
        close_code = status.WS_1000_NORMAL_CLOSURE
        try:
            while True:
                message = await context.socket.receive()
                if message["type"] == "websocket.receive":
                    await self.dispatch(context, message)
                elif message["type"] == "websocket.disconnect":
                    close_code = int(message.get("code", status.WS_1000_NORMAL_CLOSURE))
                    break
        except Exception as exc:
            close_code = status.WS_1011_INTERNAL_ERROR
            raise exc from None
        finally:
            await context.socket.close(close_code)

    async def dispatch(self, context: ConnectionContext, data: OperationMessage) -> None:
        message = await self.decode(context, data)
        if message.type == MessageType.GQL_CONNECTION_INIT:
            await self.init(context)
        elif message.type == MessageType.GQL_CONNECTION_TERMINATE:
            await self.terminate(context)
        elif message.type == MessageType.GQL_START:
            future = asyncio.ensure_future(self.start(context, message))
            context.operations[data.id] = future
        elif message.type == MessageType.GQL_STOP:
            await self.stop(context, message.id)
        else:
            await context.socket.close(code=status.WS_1003_UNSUPPORTED_DATA)

    async def init(self, context: ConnectionContext) -> None:
        await self.send_message(context, MessageType.GQL_CONNECTION_ACK)

    async def stop(self, context: ConnectionContext, op_id: str) -> None:
        if op_id in self.operations:
            op = self.operations[op_id]
            op.stop()
            self.unsubscribe(op_id)
        await self.complete(context, op_id)

    async def terminate(self, context: ConnectionContext) -> None:
        await context.socket.close(code=status.WS_1000_NORMAL_CLOSURE)

    async def complete(self, context: ConnectionContext, op_id: str) -> None:
        await self.send_message(context, MessageType.GQL_COMPLETE, op_id=op_id)

    async def start(self, context: ConnectionContext, message: OperationMessage) -> None:
        # if message.id in self.operations:
        #     await self.unsubscribe(op_id=message.id)
        payload = message.payload
        assert payload
        try:
            doc = parse(payload.query)
        except GraphQLError as error:
            await self.send_execution_result(message.id, ExecutionResult(data=None, errors=[error]))
            return

        result_or_iterator = await subscribe(
            self.schema,
            doc,
            variable_values=payload.variables,
            operation_name=payload.operation_name,
        )
        if isinstance(result_or_iterator, ExecutionResult):
            await self.send_execution_result(message.id, result_or_iterator)
            return

        self.operations[message.id] = result_or_iterator
        async for result in result_or_iterator:
            await self.send_execution_result(message.id, result)

        await self.complete(context, message.id)

    def unsubscribe(self, op_id: str) -> None:
        self.operations.pop(op_id, None)

    async def send_execution_result(self, op_id: str, result: ExecutionResult) -> None:
        payload = {
            'data': result.data,
            'errors': [format_error(error) for error in result.errors] if result.errors else None,
        }
        await self.send_message(
            MessageType.GQL_DATA, op_id=op_id, payload=payload,
        )

    async def send_message(
        self, context: ConnectionContext, type: MessageType, op_id: str = None, payload: dict = None
    ) -> None:
        data = {'type': type.value}
        if op_id:
            data['id'] = op_id
        if payload:
            data['payload'] = payload
        await context.socket.send_json(data)

    async def decode(self, context: ConnectionContext, message: Message) -> OperationMessage:
        if message.get("text") is not None:
            text = message["text"]
        else:
            text = message["bytes"].decode("utf-8")

        try:
            return OperationMessage.build(json.loads(text))
        except json.decoder.JSONDecodeError:
            await context.socket.close(code=status.WS_1003_UNSUPPORTED_DATA)
            raise RuntimeError("Malformed JSON data received.")

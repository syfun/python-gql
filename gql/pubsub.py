import json
from enum import Enum
from typing import Any, AsyncIterator, Callable, List

from graphql import ExecutionResult, GraphQLError, format_error
from starlette import status
from starlette.websockets import WebSocket


class PubSub:
    def publish(self, trigger_name: str, payload: Any) -> None:
        return

    def subscribe(self, trigger_name: str, on_message: Callable, operations: dict) -> int:
        return

    def unsubscribe(self, sub_id: int) -> None:
        return

    def async_iterator(self, *triggers: str) -> AsyncIterator:
        return


class MessageTypes(Enum):
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


class MessageTypeJSONEncoder(json.JSONEncoder):
    def default(self, o: Any):
        if isinstance(o, MessageTypes):
            return o.value

        return super().default(self, o)


class GraphQLWebSocket(WebSocket):
    client_id: str

    async def client_init(self, errors: List[GraphQLError] = None) -> None:
        if errors:
            payload = {'errors': [format_error(error) for error in errors]}
            data = {'type': MessageTypes.GQL_CONNECTION_ERROR, 'payload': payload}
        else:
            data = {'type': MessageTypes.GQL_CONNECTION_ACK}
        await self.send_json(data)

    async def client_stop(self) -> None:
        await self.complete()

    async def client_terminate(self) -> None:
        await self.close(code=status.WS_1000_NORMAL_CLOSURE)

    async def complete(self) -> None:
        await self.send_json({'type': MessageTypes.GQL_COMPLETE, 'id': self.client_id})

    async def send_execution_result(self, result: ExecutionResult, complete: bool = True) -> None:
        payload = {
            'data': result.data,
            'errors': [format_error(error) for error in result.errors] if result.errors else None,
        }
        await self.send_json(
            {'type': MessageTypes.GQL_DATA, 'id': self.client_id, 'payload': payload}
        )
        if complete:
            await self.complete()

    async def send_json(self, data: Any, mode: str = "text") -> None:
        assert mode in ["text", "binary"]
        text = json.dumps(data, cls=MessageTypeJSONEncoder)
        if mode == "text":
            await self.send({"type": "websocket.send", "text": text})
        else:
            await self.send({"type": "websocket.send", "bytes": text.encode("utf-8")})

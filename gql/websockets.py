from typing import List

from graphql import ExecutionResult, GraphQLError, format_error
from starlette import status
from starlette.websockets import WebSocket


class GraphQLWebSocket(WebSocket):
    client_id: str

    async def client_init(self, errors: List[GraphQLError] = None) -> None:
        if errors:
            payload = {'errors': [format_error(error) for error in errors]}
            data = {'type': 'connection_error', 'payload': payload}
        else:
            data = {'type': 'connection_ack'}
        await self.send_json(data)

    async def client_stop(self) -> None:
        await self.complete()

    async def client_terminate(self) -> None:
        await self.close(code=status.WS_1000_NORMAL_CLOSURE)

    async def complete(self) -> None:
        await self.send_json({'type': 'complete', 'id': self.client_id})

    async def send_execution_result(self, result: ExecutionResult, complete: bool = True) -> None:
        payload = {
            'data': result.data,
            'errors': [format_error(error) for error in result.errors] if result.errors else None,
        }
        await self.send_json({'type': 'data', 'id': self.client_id, 'payload': payload})
        if complete:
            await self.complete()

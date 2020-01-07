from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict

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

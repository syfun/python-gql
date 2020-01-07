from typing import Any, AsyncIterator, Callable


class PubSub:
    def publish(self, trigger_name: str, payload: Any) -> None:
        return

    def subscribe(self, trigger_name: str, on_message: Callable, operations: dict) -> int:
        return

    def unsubscribe(self, sub_id: int) -> None:
        return

    def async_iterator(self, *triggers: str) -> AsyncIterator:
        return

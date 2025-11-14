from __future__ import annotations
from typing import List, Sequence
from pydantic_ai.messages import ModelMessage


def _trim_messages(messages: Sequence[ModelMessage], max_messages: int) -> List[ModelMessage]:
    if max_messages <= 0:
        return list(messages)
    return list(messages[-max_messages:])

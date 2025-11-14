from __future__ import annotations
from typing import Optional
from dataclasses import dataclass
from datetime import timedelta


@dataclass
class HistoryConfig:
    max_messages: int = 12
    ttl: Optional[timedelta] = timedelta(hours=24)
    namespace: str = "session"

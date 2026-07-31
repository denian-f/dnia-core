from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Card:

    id: int
    code: str
    target_url: Optional[str]
    activated: bool
    owner_id: Optional[int]
    created_at: datetime
    updated_at: datetime

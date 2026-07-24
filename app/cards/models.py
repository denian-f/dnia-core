from dataclasses import dataclass
from datetime import datetime


@dataclass
class Card:

    id: int
    code: str
    target_url: str
    activated: bool
    created_at: datetime
    updated_at: datetime

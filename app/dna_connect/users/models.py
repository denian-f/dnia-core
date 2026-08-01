from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:

    id: int
    name: str
    email: str
    password_hash: Optional[str]
    is_admin: bool
    created_at: datetime
    updated_at: datetime

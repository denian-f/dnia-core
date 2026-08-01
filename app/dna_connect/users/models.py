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
    email_verified: bool
    email_verification_token_hash: Optional[str]
    email_verification_expires_at: Optional[datetime]
    email_verification_last_sent_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

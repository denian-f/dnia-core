from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Card:

    id: int
    code: str
    target_url: Optional[str]
    activated: bool
    mode: str
    owner_id: Optional[int]
    created_at: datetime
    updated_at: datetime


@dataclass
class CardBusinessProfile:

    id: int
    card_id: int
    name: Optional[str]
    professional_title: Optional[str]
    company: Optional[str]
    profile_photo: Optional[str]
    whatsapp: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    website: Optional[str]
    pix_key: Optional[str]
    pix_key_type: Optional[str]
    pix_beneficiary_name: Optional[str]
    pix_beneficiary_city: Optional[str]
    bio: Optional[str]
    background_color: Optional[str]
    google_maps_url: Optional[str]
    accent_color: Optional[str]
    background_type: Optional[str]
    gradient_color_1: Optional[str]
    gradient_color_2: Optional[str]
    gradient_direction: Optional[str]
    background_image: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class CardLead:

    id: int
    card_id: int
    name: str
    email: Optional[str]
    phone: Optional[str]
    message: Optional[str]
    created_at: datetime

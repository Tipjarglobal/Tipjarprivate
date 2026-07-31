"""Pydantic request/input models for the TipJar API.

Extracted from server.py (pure data classes, no runtime dependencies) as part of a
behaviour-preserving refactor to keep server.py leaner. Import with:
    from models import RegisterInput, LoginInput, ...
"""
from typing import List, Optional

from pydantic import BaseModel, Field, EmailStr


class RegisterInput(BaseModel):
    email: Optional[EmailStr] = None
    password: str = Field(min_length=6)
    username: str = Field(min_length=2, max_length=24)
    timezone: str = "UTC"
    language: str = "en"
    ref: Optional[str] = None
    origin_url: Optional[str] = None


class VerifyInput(BaseModel):
    token: str


class OriginInput(BaseModel):
    origin_url: Optional[str] = None


class LoginInput(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: str


class ProfileUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=2, max_length=24)
    email: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None


class TipSaveInput(BaseModel):
    raw_text: str = ""
    image_path: Optional[str] = None
    home_team: str = ""
    away_team: str = ""
    match_time: str = ""
    country: str = ""
    league: str = ""
    market: str = ""
    odds: str = ""
    ai_rating: float = 0
    ai_analysis: str = ""
    legs: Optional[List[dict]] = None
    is_parlay: bool = False
    stake: str = ""
    potential_return: str = ""
    self_rating: int = 0
    image_paths: Optional[List[str]] = None
    timing: Optional[str] = None  # member-chosen: "live" | "today" | "later"
    bet_type: str = ""            # "" (parlay/single) | "system"
    system_from: int = 0          # X — minimum correct legs for a system bet
    system_total: int = 0         # Y — total legs in a system bet


class RateInput(BaseModel):
    stars: int = Field(ge=1, le=10)


class GiftInput(BaseModel):
    to_username: str
    amount: int = Field(gt=0)


class CheckoutInput(BaseModel):
    package_id: str
    origin_url: str


class SubscribeInput(BaseModel):
    anon_id: str


class StatusInput(BaseModel):
    status: str  # won | lost | pending


class SmartIdeaInput(BaseModel):
    text: str


class IdeaRateInput(BaseModel):
    stars: int = Field(ge=1, le=10)


class VisitInput(BaseModel):
    visitor_id: str = ""
    path: str = ""


class PushSubIn(BaseModel):
    endpoint: str
    keys: dict
    areas: Optional[dict] = None
    min_stars: Optional[int] = None


class PushPrefsIn(BaseModel):
    endpoint: str
    areas: dict
    min_stars: Optional[int] = None


class ClarifyInput(BaseModel):
    league: Optional[str] = None
    match_time: Optional[str] = None
    home_team: Optional[str] = None
    away_team: Optional[str] = None

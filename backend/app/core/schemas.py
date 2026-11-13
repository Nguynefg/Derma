"""Validated request bodies shared by API routes."""

import re
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(default="Bạn đọc", min_length=1, max_length=80)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Email không hợp lệ")
        return value


class SymptomChoice(BaseModel):
    id: str = Field(max_length=50)
    presence: Literal["present", "absent", "unknown"] = "present"


class SymptomSearch(BaseModel):
    symptoms: list[SymptomChoice] = Field(min_length=1, max_length=30)
    specialty: str = Field(default="", max_length=60)


class SaveHistory(BaseModel):
    consent: bool
    mode: Literal["keyword", "symptom", "question", "image"]
    query: str = Field(max_length=300)
    result_ids: list[str] = Field(max_length=30)


class DiseaseEdit(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    english_name: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=60)
    summary: str = Field(min_length=10, max_length=2000)
    details: str = Field(min_length=10, max_length=8000)
    risk_factors: str = Field(min_length=2, max_length=3000)
    prevention: str = Field(min_length=2, max_length=3000)
    published: bool = False
    symptom_ids: list[str] = Field(max_length=30)
    source_title: str = Field(min_length=3, max_length=200)
    source_url: str = Field(max_length=1000)

    @field_validator("source_url")
    @classmethod
    def validate_source(cls, value):
        from urllib.parse import urlparse

        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Nguồn phải là URL HTTPS hợp lệ")
        return value


class QuestionInput(BaseModel):
    question: str = Field(min_length=3, max_length=300)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ImageChatContext(BaseModel):
    observations: str = Field(default="", max_length=2000)
    explanation: str = Field(default="", max_length=3000)
    disease_ids: list[str] = Field(default_factory=list, max_length=3)
    external: bool = False


class ChatInput(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)
    image_context: ImageChatContext | None = None
    allow_external_ai: bool = False

    @field_validator("question")
    @classmethod
    def nonempty_question(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Tin nhắn không được để trống")
        return value


class DocumentEdit(BaseModel):
    disease_id: str = Field(min_length=1, max_length=60)
    title: str = Field(min_length=3, max_length=200)
    publisher: str = Field(min_length=2, max_length=150)
    source_url: str = Field(max_length=1000)
    usage_note: str = Field(min_length=5, max_length=1000)
    content: str = Field(min_length=20, max_length=12000)
    published: bool = False
    expected_version: int | None = Field(default=None, ge=1)

    @field_validator("source_url")
    @classmethod
    def source_https(cls, value):
        from urllib.parse import urlparse

        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Nguồn phải là URL HTTPS hợp lệ")
        return value

from datetime import datetime

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.validators import validate_http_url


class PlatformBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    website_url: str = Field(max_length=2048)

    model_config = ConfigDict(str_strip_whitespace=True)
    _validate_website_url = field_validator("website_url", mode="before")(validate_http_url)


class PlatformCreate(PlatformBase):
    pass


class PlatformUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    website_url: str | None = Field(default=None, max_length=2048)

    model_config = ConfigDict(str_strip_whitespace=True)
    _validate_website_url = field_validator("website_url", mode="before")(validate_http_url)

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> Self:
        for field in ("name", "website_url"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class PlatformRead(PlatformBase):
    id: int
    slug: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

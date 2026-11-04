from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    platform_id: int | None = Field(default=None, ge=1)

    model_config = ConfigDict(str_strip_whitespace=True)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    platform_id: int | None = Field(default=None, ge=1)

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def reject_null_name(self) -> Self:
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class CategoryRead(CategoryBase):
    id: int
    slug: str

    model_config = ConfigDict(from_attributes=True)

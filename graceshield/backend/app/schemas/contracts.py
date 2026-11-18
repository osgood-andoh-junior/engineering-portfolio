from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Credentials(Input):
    email: EmailStr
    password: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(
        min_length=12, max_length=128
    )


class Registration(Credentials):
    name: str = Field(min_length=2, max_length=160)


class EmailRequest(Input):
    email: EmailStr


class TokenRequest(Input):
    token: str = Field(min_length=30, max_length=100)


class ResetPassword(TokenRequest):
    password: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(
        min_length=12, max_length=128
    )


class CategoryInput(Input):
    name: str = Field(min_length=2, max_length=140)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=100)
    description: str = Field(default="", max_length=3000)
    icon: str = Field(default="book", pattern=r"^[a-z]+$", max_length=30)
    color: str = Field(default="#eaf0f8", pattern=r"^#[a-fA-F0-9]{6}$")
    parent_id: UUID | None = None


class ImageInput(Input):
    path: str = Field(pattern=r"^/images/[a-zA-Z0-9_-]+\.(svg|png|webp|jpg)$", max_length=300)
    alt: str = Field(min_length=3, max_length=300)


class ProductInput(Input):
    category_id: UUID
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=160)
    description: str = Field(min_length=5, max_length=10000)
    price_minor: int = Field(ge=0, le=100000000, strict=True)
    status: Literal["draft", "published", "archived"] = "draft"
    demonstration: bool = False
    sku: str = Field(pattern=r"^[A-Z0-9][A-Z0-9_-]{1,79}$")
    images: list[ImageInput] = Field(min_length=1, max_length=8)


class VariantInput(Input):
    name: str = Field(min_length=1, max_length=100)
    sku: str = Field(pattern=r"^[A-Z0-9][A-Z0-9_-]{1,79}$")


class CartChange(Input):
    variant_id: UUID
    quantity: int = Field(ge=1, le=20, strict=True)


class InventoryAdjustment(Input):
    delta: int = Field(ge=-100000, le=100000, strict=True)
    reason: str = Field(min_length=5, max_length=200)
    low_stock_threshold: int = Field(default=5, ge=0, le=10000)


REGIONS = {
    "Ahafo",
    "Ashanti",
    "Bono",
    "Bono East",
    "Central",
    "Eastern",
    "Greater Accra",
    "North East",
    "Northern",
    "Oti",
    "Savannah",
    "Upper East",
    "Upper West",
    "Volta",
    "Western",
    "Western North",
}


class CheckoutInput(Input):
    firstName: str = Field(min_length=2, max_length=80)
    lastName: str = Field(min_length=2, max_length=80)
    email: EmailStr
    phone: str = Field(pattern=r"^(?:\+233|0)[235]\d{8}$")
    address: str = Field(min_length=5, max_length=200)
    region: str
    city: str = Field(min_length=2, max_length=100)

    @field_validator("region")
    @classmethod
    def region_known(cls, value: str):
        if value not in REGIONS:
            raise ValueError("Choose a valid Ghana region.")
        return value


class TransitionInput(Input):
    status: Literal["processing", "shipped", "delivered", "cancelled"]


class PublicUser(BaseModel):
    id: str
    email: str
    name: str
    verified: bool
    roles: list[str]


class PublicCategory(BaseModel):
    id: str
    slug: str
    name: str
    shortName: str
    description: str
    icon: str
    color: str


class Money(BaseModel):
    amount: int
    currency: Literal["GHS"] = "GHS"


class PublicProduct(BaseModel):
    id: str
    slug: str
    name: str
    categoryId: str
    categoryName: str
    price: Money
    images: list[ImageInput]
    description: str
    details: list[str]
    availability: Literal["available", "unavailable"]
    featured: bool = False
    demonstration: bool
    variantId: str | None
    variants: list[dict]


class ProductPage(BaseModel):
    products: list[PublicProduct]
    total: int
    page: int
    pages: int

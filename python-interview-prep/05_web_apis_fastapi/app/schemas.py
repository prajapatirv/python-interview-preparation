"""Pydantic request/response DTOs. These are the API's public contract -- keep them separate
from any internal/ORM representation so the API shape can stay stable while internals change."""
from pydantic import BaseModel, Field


class OrderItemIn(BaseModel):
    sku: str
    qty: int = Field(gt=0)
    price: float = Field(gt=0)


class OrderIn(BaseModel):
    customer_id: int = Field(gt=0)
    items: list[OrderItemIn]


class OrderOut(BaseModel):
    id: str
    customer_id: int
    total: float
    status: str

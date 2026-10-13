"""Thin HTTP layer: parses the request, calls the service, shapes the response. No business
logic and no error-code mapping lives here -- domain exceptions (NotFoundError, ValidationError)
propagate up to the global handlers registered in app/main.py."""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user, get_order_service, rate_limit
from app.schemas import OrderIn, OrderOut
from app.services import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=201)
async def create_order(
    order: OrderIn,
    svc: Annotated[OrderService, Depends(get_order_service)],
    user: Annotated[dict, Depends(get_current_user)],
    _: Annotated[None, Depends(rate_limit)],
):
    return svc.place_order(order)


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: str,
    svc: Annotated[OrderService, Depends(get_order_service)],
    user: Annotated[dict, Depends(get_current_user)],
):
    # NotFoundError raised by the service is NOT caught here -- it propagates to the
    # @app.exception_handler(NotFoundError) registered in main.py, which maps it to a 404.
    # This is the "translate exceptions centrally" pattern from the REST notes.
    return svc.get_order(order_id)

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from app.schemas.item import ItemCreate, ItemResponse, ItemUpdate
from app.services.item_service import item_service

router = APIRouter()


@router.get(
    "/",
    response_model=List[ItemResponse],
    summary="List all items",
    description="Retrieve a paginated list of items with optional active status filter.",
)
async def list_items(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Max number of items to return"),
    active_only: Optional[bool] = Query(None, description="Filter by active status"),
) -> List[ItemResponse]:
    return item_service.list_items(skip=skip, limit=limit, active_only=active_only)


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Get item by ID",
    description="Retrieve details of a single item by its ID.",
)
async def get_item(item_id: int) -> ItemResponse:
    item = item_service.get_by_id(item_id=item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found",
        )
    return item


@router.post(
    "/",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create item",
    description="Create a new item with title, description, price, and active status.",
)
async def create_item(item_in: ItemCreate) -> ItemResponse:
    return item_service.create(item_in=item_in)


@router.put(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Update item",
    description="Update an existing item by ID. Only provided fields are updated.",
)
async def update_item(item_id: int, item_in: ItemUpdate) -> ItemResponse:
    updated = item_service.update(item_id=item_id, item_in=item_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found",
        )
    return updated


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete item",
    description="Delete an item by its ID.",
)
async def delete_item(item_id: int) -> None:
    deleted = item_service.delete(item_id=item_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found",
        )


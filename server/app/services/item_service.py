from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.schemas.item import ItemCreate, ItemResponse, ItemUpdate


class ItemService:
    """Service layer handling items operations and in-memory persistence."""

    def __init__(self) -> None:
        self._items: Dict[int, ItemResponse] = {}
        self._current_id: int = 1
        self._seed_default_items()

    def _seed_default_items(self) -> None:
        now = datetime.now(timezone.utc)
        self._items[1] = ItemResponse(
            id=1,
            title="Sample Item A",
            description="First demo item for FastAPI backend",
            price=29.99,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self._items[2] = ItemResponse(
            id=2,
            title="Sample Item B",
            description="Second demo item ready for testing",
            price=49.99,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self._current_id = 3

    def list_items(
        self,
        skip: int = 0,
        limit: int = 10,
        active_only: Optional[bool] = None,
    ) -> List[ItemResponse]:
        items = list(self._items.values())
        if active_only is not None:
            items = [item for item in items if item.is_active == active_only]
        return items[skip : skip + limit]

    def get_by_id(self, item_id: int) -> Optional[ItemResponse]:
        return self._items.get(item_id)

    def create(self, item_in: ItemCreate) -> ItemResponse:
        now = datetime.now(timezone.utc)
        new_id = self._current_id
        self._current_id += 1

        new_item = ItemResponse(
            id=new_id,
            title=item_in.title,
            description=item_in.description,
            price=item_in.price,
            is_active=item_in.is_active,
            created_at=now,
            updated_at=now,
        )
        self._items[new_id] = new_item
        return new_item

    def update(self, item_id: int, item_in: ItemUpdate) -> Optional[ItemResponse]:
        item = self._items.get(item_id)
        if not item:
            return None

        update_data = item_in.model_dump(exclude_unset=True)
        if not update_data:
            return item

        updated_dict = item.model_dump()
        updated_dict.update(update_data)
        updated_dict["updated_at"] = datetime.now(timezone.utc)

        updated_item = ItemResponse(**updated_dict)
        self._items[item_id] = updated_item
        return updated_item

    def delete(self, item_id: int) -> bool:
        if item_id in self._items:
            del self._items[item_id]
            return True
        return False


item_service = ItemService()


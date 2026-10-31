import pytest


@pytest.mark.anyio
async def test_root_endpoint(async_client):
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["docs"] == "/docs"


@pytest.mark.anyio
async def test_health_check(async_client):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app_name" in data
    assert "timestamp" in data


@pytest.mark.anyio
async def test_list_items(async_client):
    response = await async_client.get("/api/v1/items/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2


@pytest.mark.anyio
async def test_get_item_by_id(async_client):
    response = await async_client.get("/api/v1/items/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "Sample Item A"


@pytest.mark.anyio
async def test_get_nonexistent_item(async_client):
    response = await async_client.get("/api/v1/items/99999")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_create_item(async_client):
    payload = {
        "title": "New Test Item",
        "description": "Created during pytest execution",
        "price": 19.95,
        "is_active": True,
    }
    response = await async_client.post("/api/v1/items/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["price"] == payload["price"]
    assert "id" in data


@pytest.mark.anyio
async def test_create_item_invalid_price(async_client):
    payload = {
        "title": "Invalid Item",
        "price": -10.0,
    }
    response = await async_client.post("/api/v1/items/", json=payload)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_update_item(async_client):
    payload = {"title": "Updated Item Title", "price": 35.00}
    response = await async_client.put("/api/v1/items/1", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Item Title"
    assert data["price"] == 35.00


@pytest.mark.anyio
async def test_delete_item(async_client):
    # First create an item to delete
    create_res = await async_client.post(
        "/api/v1/items/",
        json={"title": "Item To Delete", "price": 9.99, "is_active": True},
    )
    item_id = create_res.json()["id"]

    # Delete item
    delete_res = await async_client.delete(f"/api/v1/items/{item_id}")
    assert delete_res.status_code == 204

    # Confirm it's gone
    get_res = await async_client.get(f"/api/v1/items/{item_id}")
    assert get_res.status_code == 404


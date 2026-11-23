from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1 import api_router


async def test_business_overview_is_mounted_and_requires_authentication() -> None:
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/admin/business/overview")
    assert response.status_code == 401

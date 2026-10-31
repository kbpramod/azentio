"""Bridge to Member 2's AI orchestration service (azentio/ai, default http://127.0.0.1:8001).

The AI service runs separately because both projects use a package named `app`.
The frontend only talks to this server; these helpers forward the calls.
"""
from typing import Any, Optional

import httpx
from fastapi import HTTPException

from app.core.config import settings

TIMEOUT = httpx.Timeout(60.0, connect=5.0)  # speech-to-text on CPU can take a few seconds


async def forward(method: str, path: str, *, json: Optional[dict] = None,
                  files: Optional[dict] = None, data: Optional[dict] = None) -> Any:
    url = f"{settings.AI_SERVICE_URL.rstrip('/')}/api/v1{path}"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            res = await client.request(method, url, json=json, files=files, data=data)
    except httpx.HTTPError:
        raise HTTPException(503, detail={"error": {
            "code": "AI_UNAVAILABLE", "message": "AI service is not reachable. Start it on port 8001.",
            "retryable": True}})
    body = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
    if res.status_code >= 400:
        raise HTTPException(res.status_code, detail=body.get("detail", body))
    return body

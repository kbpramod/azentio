from fastapi import APIRouter
from app.api.v1.endpoints import agent, auth, banking, health, items, sessions

api_router = APIRouter()

# Core & Health
api_router.include_router(health.router, tags=["Health"])

# Authentication (Customer Register, Login, Logout, /me)
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Banking Customer Portal
api_router.include_router(banking.router, prefix="/banking", tags=["Banking"])

# Customer Service AI Agent
api_router.include_router(agent.router, prefix="/agent", tags=["AI Customer Agent"])

# VaaniDesk voice sessions (forwarded to the AI service, Member 2)
api_router.include_router(sessions.router, prefix="/sessions", tags=["VaaniDesk Voice Sessions"])

# Legacy/Demo Items
api_router.include_router(items.router, prefix="/items", tags=["Demo Items"])

from fastapi import APIRouter
from app.api.v1.endpoints import agent, auth, banking, health, items, support

api_router = APIRouter()

# Core & Health
api_router.include_router(health.router, tags=["Health"])

# Authentication (Customer Register, Login, Logout, /me)
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Banking Customer Portal
api_router.include_router(banking.router, prefix="/banking", tags=["Banking"])

# 24/7 Priority Support (Voice Dispatch & Text Inquiries)
api_router.include_router(support.router, prefix="/support", tags=["Customer Support"])

# Customer Service AI Agent
api_router.include_router(agent.router, prefix="/agent", tags=["AI Customer Agent"])

# Legacy/Demo Items
api_router.include_router(items.router, prefix="/items", tags=["Demo Items"])

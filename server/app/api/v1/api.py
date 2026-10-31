from fastapi import APIRouter
from app.api.v1.endpoints import agent, auth, banking, health, items, support, sessions, mock_banking, ops, csm

api_router = APIRouter()

# Core & Health
api_router.include_router(health.router, tags=["Health"])

# VaaniDesk Sessions & Customer Verification
api_router.include_router(sessions.router, prefix="/sessions", tags=["Voice & Chat Sessions"])

# VaaniDesk Mock Banking (LOS, LMS, CBS)
api_router.include_router(mock_banking.router, prefix="/mock", tags=["Mock Banking Services"])

# VaaniDesk CSM Tickets
api_router.include_router(csm.router, prefix="/mock/csm", tags=["CSM Ticket Management"])

# VaaniDesk Operations Dashboard
api_router.include_router(ops.router, prefix="/ops", tags=["Operations Dashboard"])

# Existing Customer Portal Authentication (Customer Register, Login, Logout, /me)
api_router.include_router(auth.router, prefix="/auth", tags=["Customer Portal Auth"])

# Existing Customer Portal Banking
api_router.include_router(banking.router, prefix="/banking", tags=["Customer Portal Banking"])

# Existing Customer Service AI Agent
api_router.include_router(agent.router, prefix="/agent", tags=["Customer Portal Agent"])

# 24/7 Priority Support (Voice Dispatch & Text Inquiries)
api_router.include_router(support.router, prefix="/support", tags=["Customer Support"])

# Legacy/Demo Items
api_router.include_router(items.router, prefix="/items", tags=["Demo Items"])

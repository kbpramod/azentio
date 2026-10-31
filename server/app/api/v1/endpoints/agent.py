from datetime import datetime, timezone
from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import get_optional_current_user
from app.db.session import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.auth import AgentChatRequest, AgentChatResponse

router = APIRouter()

AI_CREDIT_COST_PER_QUERY = 5


def _generate_agent_response(user_msg: str, user: Optional[User] = None) -> str:
    msg = user_msg.lower()

    if any(k in msg for k in ["balance", "money", "funds", "how much"]):
        if user:
            return (
                f"Hello {user.full_name}, your current checking account balance is "
                f"${user.balance:,.2f} on account {user.account_number}."
            )
        return "To view your personal checking account balance, please log in with your Azentio account."

    elif any(k in msg for k in ["credit", "ai credit", "tokens"]):
        if user:
            return (
                f"You currently have {user.ai_credits} AI Credits remaining. "
                f"Each customer service AI interaction uses {AI_CREDIT_COST_PER_QUERY} credits."
            )
        return "Azentio accounts receive 500 complimentary AI Credits upon registration."

    elif any(k in msg for k in ["loan", "emi", "mortgage", "interest"]):
        return (
            "Azentio Bank offers Home, Auto, and Personal loans with competitive interest rates starting at 8.5% p.a. "
            "You can check your application status or calculate EMI schedules in your dashboard."
        )

    elif any(k in msg for k in ["transfer", "send money", "wire", "upi"]):
        return (
            "To transfer funds, visit the 'Transfer Funds' or 'UPI Payment' section on your dashboard, "
            "enter the recipient's Azentio account number (e.g. AZ-882194) or UPI ID, specify the amount, and confirm."
        )

    elif any(k in msg for k in ["card", "debit", "credit card", "pin"]):
        if user:
            return (
                f"Your Azentio Platinum Debit Card linked to account {user.account_number} "
                "is active and protected by 256-bit encryption. To freeze or replace your card, visit the Security settings tab."
            )
        return "Azentio Platinum Debit Cards feature zero foreign transaction fees, 256-bit chip protection, and instant card locking."

    elif any(k in msg for k in ["help", "support", "agent", "human"]):
        return (
            "I am your Azentio Banking AI Customer Support Agent! "
            "I can assist you with balance inquiries, wire transfers, loan status, EMI schedules, "
            "and account security. How can I help you today?"
        )
    else:
        name = user.full_name if user else "Customer"
        return (
            f"Thank you for contacting Azentio Banking Customer Service, {name}. "
            f"Regarding '{user_msg[:60]}...': Our banking operations are online 24/7. "
            "Is there a specific loan, transaction, or account service you would like me to review?"
        )


@router.post(
    "/chat",
    response_model=AgentChatResponse,
    summary="Chat with customer service AI agent (uses AI Credits)",
)
async def chat_with_agent(
    payload: AgentChatRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentChatResponse:
    # If guest user (not logged in), provide helpful guest answer without debiting credits
    if not current_user:
        reply_text = _generate_agent_response(payload.message, None)
        return AgentChatResponse(
            reply=reply_text,
            ai_credits_used=0,
            remaining_credits=0,
            timestamp=datetime.now(timezone.utc),
        )

    if current_user.ai_credits < AI_CREDIT_COST_PER_QUERY:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Insufficient AI Credits. You have {current_user.ai_credits} credits, "
                f"but {AI_CREDIT_COST_PER_QUERY} credits are required for an AI query."
            ),
        )

    reply_text = ""

    # If AICREDITS_API_KEY is configured, forward to external API
    if settings.AICREDITS_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{settings.AICREDITS_BASE_URL}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.AICREDITS_API_KEY}"},
                    json={
                        "model": "banking-assistant",
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    f"You are a helpful banking agent for Azentio Bank. Customer: {current_user.full_name}, "
                                    f"Account: {current_user.account_number}, Balance: ${current_user.balance:,.2f}"
                                ),
                            },
                            {"role": "user", "content": payload.message},
                        ],
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    reply_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            reply_text = ""

    if not reply_text:
        reply_text = _generate_agent_response(payload.message, current_user)

    # Deduct AI credits
    current_user.ai_credits -= AI_CREDIT_COST_PER_QUERY

    # Record AI credit usage transaction
    tx = Transaction(
        user_id=current_user.id,
        type="ai_service",
        amount=0.0,
        description=f"AI Agent Query (-{AI_CREDIT_COST_PER_QUERY} credits)",
        status="completed",
    )
    db.add(tx)

    await db.commit()
    await db.refresh(current_user)

    return AgentChatResponse(
        reply=reply_text,
        ai_credits_used=AI_CREDIT_COST_PER_QUERY,
        remaining_credits=current_user.ai_credits,
        timestamp=datetime.now(timezone.utc),
    )

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

    # Unauthenticated Guest Policy: General FAQs ONLY. If asking for personal accounts, tell user to login.
    if not user:
        if any(k in msg for k in ['balance', 'money', 'funds', 'how much', 'transaction', 'statement', 'history', 'my loan', 'my emi', 'when is my emi', 'due date', 'my card', 'transfer', 'send money', 'wire', 'my account', 'credit', 'tokens']):
            return 'To access your personal account details, view your balance, check recent transactions, or manage your loans, please log in with your Azentio account.'

        if any(k in msg for k in ['hour', 'timing', 'open', 'branch', 'time', 'close']):
            return 'Azentio Bank branches are open Monday through Friday from 9:00 AM to 5:00 PM, and Saturday from 9:30 AM to 1:30 PM. Digital banking, mobile apps, and ATMs are available 24/7.'

        if any(k in msg for k in ['interest', 'rate', 'loan', 'mortgage', 'borrow']):
            return 'Azentio Bank offers competitive interest rates: Home Loans starting at 7.20% p.a., Personal Loans from 8.50% p.a., Auto Loans from 7.90% p.a., and High-Yield Savings at 4.50% APY.'

        if any(k in msg for k in ['open account', 'open an account', 'apply', 'register', 'eligibility', 'documents', 'how to open']):
            return 'You can open an Azentio digital account online in under 5 minutes with a valid government photo ID and address proof. Click Register to get started.'

        if any(k in msg for k in ['savings', 'deposit', 'apy']):
            return 'Azentio High-Yield Savings Accounts offer 4.50% Annual Percentage Yield (APY) with interest compounded daily and credited monthly, with zero monthly maintenance charges.'

        if any(k in msg for k in ['card', 'debit', 'credit']):
            return 'Azentio offers contactless Platinum Debit and Credit Cards featuring 0% foreign transaction fees, 1% cashback on retail purchases, and instant app-based security controls.'

        if any(k in msg for k in ['security', 'safe', 'protect', 'encryption', 'fdic', 'insurance']):
            return 'Your funds and data are protected with bank-grade 256-bit AES encryption, biometric multi-factor authentication, real-time AI fraud monitoring, and FDIC insurance up to $250,000.'

        if any(k in msg for k in ['support', 'contact', 'phone', 'call', 'email', 'help', 'human', 'agent']):
            return 'You can reach Azentio 24/7 Priority Support toll-free at 1-800-AZENTIO (1-800-293-6846), email support@azentio.com, or through this 24/7 interactive chat.'

        if any(k in msg for k in ['transfer limit', 'limit', 'wire transfer', 'upi', 'swift']):
            return 'Azentio supports instant transfers via UPI, ACH, IMPS, and SWIFT wire transfers. Standard daily transfer limit is $25,000, up to $100,000 for verified customers.'

        if any(k in msg for k in ['hello', 'hi', 'hey', 'greetings', 'morning', 'afternoon']):
            return 'Hello! Welcome to Azentio Banking Customer Service. I can answer any general banking FAQs regarding branch hours, interest rates, loans, and account opening. Sign in to access your personal account details.'

        return 'Thank you for reaching out to Azentio Bank. As a guest visitor, you can ask about branch hours, loan interest rates, how to open an account, or our card features. To review your personal account details, please log in.'

    # Authenticated User Policy (Strictly grounded to user identity: email, account number, full name, balance)
    if any(k in msg for k in ['balance', 'money', 'funds', 'how much']):
        return (
            f'Hello {user.full_name}, for your authenticated account ({user.email}, Account: {user.account_number}), '
            f'your current available checking balance is ${user.balance:,.2f}.'
        )

    elif any(k in msg for k in ['transaction', 'statement', 'history', 'activity']):
        return (
            f'Here are the latest transactions for your account ({user.email}, Account: {user.account_number}): '
            f'1. Salary Direct Deposit (+$3,000.00, Completed), '
            f'2. Coffee & Bakery Mart (-$45.25, Completed), '
            f'3. Mobile Check Deposit (+$500.00, Completed). '
            f'Your current available balance is ${user.balance:,.2f}.'
        )

    elif any(k in msg for k in ['credit', 'ai credit', 'tokens']):
        return (
            f'Your account ({user.email}) currently has {user.ai_credits} AI Credits remaining. '
            f'Each AI customer service interaction uses {AI_CREDIT_COST_PER_QUERY} credits.'
        )

    elif any(k in msg for k in ['loan', 'emi', 'mortgage', 'due', 'repayment']):
        return (
            f'Hello {user.full_name}, for your registered profile ({user.email}), '
            f'your active Home Loan (LN-9012) has an outstanding balance of $24,500.00. '
            f'Your next monthly EMI of $285.00 is due on Nov 5th. All previous payments are fully settled with zero overdue.'
        )

    elif any(k in msg for k in ['application', 'los', 'approval', 'status']):
        return (
            f'For your account ({user.email}), your Loan Application (APP-77) is currently in \'Document Verification\'. '
            f'All required documents have been reviewed and no further action is required.'
        )

    elif any(k in msg for k in ['card', 'debit', 'credit card', 'pin']):
        return (
            f'Hello {user.full_name}, your Azentio Platinum Debit Card linked to account {user.account_number} ({user.email}) '
            f'is ACTIVE and protected by 256-bit encryption. You can view or freeze your card anytime in your dashboard.'
        )

    elif any(k in msg for k in ['transfer', 'send money', 'wire', 'upi']):
        return (
            f'Hello {user.full_name}, you can transfer funds from your account ({user.account_number}) anytime '
            f'using the \'Transfer Funds\' or \'UPI Payment\' sections in your dashboard.'
        )

    elif any(k in msg for k in ['hour', 'timing', 'open', 'branch']):
        return (
            f'Azentio Bank branches are open Monday to Friday 9:00 AM - 5:00 PM, and Saturday 9:30 AM - 1:30 PM. '
            f'Digital banking services on your account ({user.email}) are available 24/7.'
        )

    elif any(k in msg for k in ['hello', 'hi', 'hey', 'greetings']):
        return (
            f'Hello {user.full_name}! Welcome back to your Azentio Banking Assistant. '
            f'You are signed in as {user.email} (Account: {user.account_number}). '
            f'How may I assist you with your balance, loans, or transactions today?'
        )

    else:
        return (
            f'Thank you for contacting Azentio Banking, {user.full_name} ({user.email}). '
            f'Your checking account {user.account_number} is in good standing with balance ${user.balance:,.2f}. '
            f'You can ask me for recent transactions, loan status, or EMI repayment details.'
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

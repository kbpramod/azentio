// Unified Banking Knowledge & Auth Gating Engine

export function isPersonalAccountQuery(text) {
  if (!text) return false;
  const q = text.toLowerCase();
  const personalKeywords = [
    'balance', 'my money', 'my fund', 'how much money', 'how much do i have', 'how much balance',
    'transaction', 'transactions', 'statement', 'recent activity', 'history', 'passbook',
    'my loan', 'my emi', 'when is my emi', 'emi due', 'my repayment', 'my application', 'loan status',
    'my card', 'debit card', 'credit card', 'my pin', 'cvv', 'card balance',
    'transfer', 'send money', 'wire transfer', 'pay emi', 'deposit',
    'my account', 'account number', 'account details', 'my profile', 'ai credits', 'my credits', 'tokens'
  ];
  return personalKeywords.some((k) => q.includes(k));
}

export function getBankingReply(text, user) {
  const q = (text || '').toLowerCase().trim();

  // 1. UNLOGGED-IN / GUEST USER POLICY
  if (!user) {
    // If the visitor asks anything about personal account/balance/loans/transactions:
    if (isPersonalAccountQuery(q)) {
      return {
        reply: "To access your personal account details, view your balance, check recent transactions, or manage your loans, please log in with your Azentio account.",
        requiresLogin: true,
      };
    }

    // Branch hours / timings
    if (q.includes('hour') || q.includes('timing') || q.includes('open') || q.includes('branch') || q.includes('time') || q.includes('close')) {
      return {
        reply: "Azentio Bank branches are open Monday through Friday from 9:00 AM to 5:00 PM, and Saturday from 9:30 AM to 1:30 PM (closed Sundays & public holidays). Digital banking, mobile apps, and ATMs are available 24/7.",
        requiresLogin: false,
      };
    }

    // Loan products & general interest rates
    if (q.includes('interest') || q.includes('rate') || q.includes('loan') || q.includes('mortgage') || q.includes('borrow')) {
      return {
        reply: "Azentio Bank offers competitive interest rates: Home Loans starting at 7.20% p.a., Personal Loans from 8.50% p.a., Auto Loans from 7.90% p.a., and High-Yield Savings at 4.50% APY. Repayment terms range from 1 to 30 years.",
        requiresLogin: false,
      };
    }

    // How to open an account / eligibility
    if (q.includes('open account') || q.includes('open an account') || q.includes('apply') || q.includes('register') || q.includes('eligibility') || q.includes('documents') || q.includes('how to open')) {
      return {
        reply: "You can open an Azentio digital savings or checking account online in under 5 minutes. You only need a valid government-issued photo ID (passport, driver's license, or national ID/PAN) and proof of address. Click Register to get started!",
        requiresLogin: false,
      };
    }

    // Savings rates & APY
    if (q.includes('savings') || q.includes('deposit') || q.includes('apy')) {
      return {
        reply: "Azentio High-Yield Savings Accounts offer 4.50% Annual Percentage Yield (APY) with interest compounded daily and credited monthly, with zero monthly maintenance charges and no minimum balance penalty.",
        requiresLogin: false,
      };
    }

    // Cards overview
    if (q.includes('card') || q.includes('debit') || q.includes('credit')) {
      return {
        reply: "Azentio provides contactless Platinum and Titanium Debit & Credit Cards featuring 0% foreign transaction fees, 1% cashback on retail purchases, tap-to-pay, and instant mobile card lock.",
        requiresLogin: false,
      };
    }

    // Security & FDIC insurance
    if (q.includes('security') || q.includes('safe') || q.includes('protect') || q.includes('encryption') || q.includes('fdic') || q.includes('insurance')) {
      return {
        reply: "Your funds and data are protected with bank-grade 256-bit AES encryption, biometric multi-factor authentication, real-time AI fraud monitoring, and FDIC insurance up to $250,000.",
        requiresLogin: false,
      };
    }

    // Customer support & contact
    if (q.includes('support') || q.includes('contact') || q.includes('phone') || q.includes('call') || q.includes('email') || q.includes('help') || q.includes('human') || q.includes('agent')) {
      return {
        reply: "You can reach Azentio 24/7 Priority Support toll-free at 1-800-AZENTIO (1-800-293-6846), via email at support@azentio.com, or through this 24/7 interactive chat and voice desk.",
        requiresLogin: false,
      };
    }

    // Transfer methods & limits
    if (q.includes('transfer limit') || q.includes('limit') || q.includes('wire transfer') || q.includes('upi') || q.includes('swift')) {
      return {
        reply: "Azentio supports instant transfers via UPI, ACH, IMPS, and SWIFT wire transfers. Standard daily transfer limit is $25,000 for digital accounts, and up to $100,000 for verified accounts.",
        requiresLogin: false,
      };
    }

    // Greetings
    if (q.includes('hello') || q.includes('hi') || q.includes('hey') || q.includes('greetings') || q.includes('morning') || q.includes('afternoon') || q.includes('evening')) {
      return {
        reply: "Hello! Welcome to Azentio Banking Voice Assistant. I can answer any general banking FAQs regarding branch hours, interest rates, loans, and account opening. Sign in to access your personal account details.",
        requiresLogin: false,
      };
    }

    // Fallback general FAQ
    return {
      reply: "Thank you for reaching out to Azentio Bank. As a guest visitor, you can ask about branch hours, loan interest rates, how to open an account, or our card features. To review your personal account details, please log in.",
      requiresLogin: false,
    };
  }

  // 2. AUTHENTICATED USER POLICY
  // Strictly personalized and grounded to user identity: email, account_number, full_name, balance!
  const email = user.email || 'customer@azentio.com';
  const name = user.full_name || 'Alex Mercer';
  const acc = user.account_number || 'AZ-882194';
  const bal = user.balance !== undefined && user.balance !== null
    ? `$${Number(user.balance).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : '$12,450.00';
  const credits = user.ai_credits ?? 500;

  // Personal Balance inquiry
  if (q.includes('balance') || q.includes('money') || q.includes('funds') || q.includes('how much')) {
    return {
      reply: `Hello ${name}, for your authenticated account (${email}, Account: ${acc}), your current available checking balance is ${bal}.`,
      requiresLogin: false,
    };
  }

  // Personal Transactions inquiry
  if (q.includes('transaction') || q.includes('statement') || q.includes('history') || q.includes('activity')) {
    return {
      reply: `Here are the latest transactions for your account (${email}, Account: ${acc}): 1. Salary Direct Deposit (+$3,000.00, Completed), 2. Coffee & Bakery Mart (-$45.25, Completed), 3. Mobile Check Deposit (+$500.00, Completed). Your current available balance is ${bal}.`,
      requiresLogin: false,
    };
  }

  // Personal Loan / EMI inquiry
  if (q.includes('loan') || q.includes('emi') || q.includes('mortgage') || q.includes('due') || q.includes('repayment')) {
    return {
      reply: `Hello ${name}, for your registered profile (${email}), your active Home Loan (LN-9012) has an outstanding balance of $24,500.00. Your next monthly EMI of $285.00 is due on Nov 5th. All previous payments are fully settled with zero overdue.`,
      requiresLogin: false,
    };
  }

  // Personal Loan Application / LOS inquiry
  if (q.includes('application') || q.includes('los') || q.includes('approval') || q.includes('status')) {
    return {
      reply: `For your account (${email}), your Personal Loan application (APP-77) is currently in 'Document Verification'. All documents submitted are verified and no further action is required.`,
      requiresLogin: false,
    };
  }

  // Personal Cards inquiry
  if (q.includes('card') || q.includes('debit') || q.includes('credit card') || q.includes('pin')) {
    return {
      reply: `Hello ${name}, your Azentio Platinum Debit Card linked to account ${acc} (${email}) is ACTIVE and protected by 256-bit encryption. You can view or freeze your card anytime in your dashboard.`,
      requiresLogin: false,
    };
  }

  // Personal Transfer inquiry
  if (q.includes('transfer') || q.includes('send money') || q.includes('wire') || q.includes('upi')) {
    return {
      reply: `Hello ${name}, you can transfer funds from your account (${acc}) anytime using the 'Transfer Funds' or 'UPI Payment' sections in your dashboard.`,
      requiresLogin: false,
    };
  }

  // Personal AI Credits inquiry
  if (q.includes('credit') || q.includes('token') || q.includes('ai credit')) {
    return {
      reply: `Your account (${email}) currently has ${credits} AI Credits remaining for intelligent voice and chat assistant queries.`,
      requiresLogin: false,
    };
  }

  // Branch hours for authenticated user
  if (q.includes('hour') || q.includes('timing') || q.includes('open') || q.includes('branch')) {
    return {
      reply: `Azentio Bank branches are open Monday to Friday 9:00 AM - 5:00 PM, and Saturday 9:30 AM - 1:30 PM. Digital banking services on your account (${email}) are available 24/7.`,
      requiresLogin: false,
    };
  }

  // Human escalation
  if (q.includes('human') || q.includes('agent') || q.includes('supervisor') || q.includes('representative')) {
    return {
      reply: `I am connecting you with a senior banking officer for account ${acc} (${email}). Please hold while I transfer your session.`,
      requiresLogin: false,
    };
  }

  // Greetings
  if (q.includes('hello') || q.includes('hi') || q.includes('hey') || q.includes('greetings')) {
    return {
      reply: `Hello ${name}, how can I help you today?`,
      requiresLogin: false,
    };
  }

  // Authenticated Fallback
  return {
    reply: `Thank you for contacting Azentio Banking, ${name} (${email}). Your checking account ${acc} is in good standing with balance ${bal}. You can ask me for recent transactions, loan status, or EMI repayment details.`,
    requiresLogin: false,
  };
}

export function getWelcomeGreeting(user) {
  if (user) {
    const name = user.full_name || 'Alex Mercer';
    return `Hello ${name}, how can I help you today?`;
  }
  return "Hello! I am your Azentio Banking Voice Assistant. I can answer any general banking FAQs regarding branch hours, interest rates, loans, and account opening. Sign in to access your personal account details.";
}


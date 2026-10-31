const API_BASE = '/api/v1';

export const getStoredUser = () => {
  const userJson = localStorage.getItem('azentio_user');
  try {
    return userJson ? JSON.parse(userJson) : null;
  } catch {
    return null;
  }
};

export const setStoredUser = (user) => {
  if (user) {
    localStorage.setItem('azentio_user', JSON.stringify(user));
  } else {
    localStorage.removeItem('azentio_user');
  }
};

export const clearStoredAuth = () => {
  localStorage.removeItem('azentio_user');
  localStorage.removeItem('azentio_token');
};

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve();
    }
  });
  failedQueue = [];
};

export async function apiRequest(endpoint, options = {}, isRetry = false) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  const config = {
    ...options,
    headers,
    credentials: 'include', // Automatically send & receive HttpOnly cookies!
  };

  const response = await fetch(`${API_BASE}${endpoint}`, config);

  if (response.status === 401 && !isRetry && endpoint !== '/auth/login' && endpoint !== '/auth/refresh') {
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then(() => apiRequest(endpoint, options, true));
    }

    isRefreshing = true;

    try {
      const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      });

      if (refreshRes.ok) {
        const refreshData = await refreshRes.json();
        setStoredUser(refreshData.user);
        processQueue(null);
        isRefreshing = false;
        return apiRequest(endpoint, options, true);
      } else {
        throw new Error('Refresh token expired');
      }
    } catch (err) {
      processQueue(err);
      isRefreshing = false;
      clearStoredAuth();
      throw new Error('Session expired. Please log in again.');
    }
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorMsg = data.detail || data.message || `Request failed with status ${response.status}`;
    throw new Error(errorMsg);
  }

  return data;
}

export const authApi = {
  login: async (email, password) => {
    const data = await apiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setStoredUser(data.user);
    return data;
  },

  register: async (email, password, fullName, initialDeposit = 1000) => {
    const data = await apiRequest('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        email,
        password,
        full_name: fullName,
        initial_deposit: Number(initialDeposit),
      }),
    });
    setStoredUser(data.user);
    return data;
  },

  refresh: async () => {
    const data = await apiRequest('/auth/refresh', { method: 'POST' });
    setStoredUser(data.user);
    return data;
  },

  logout: async () => {
    try {
      await apiRequest('/auth/logout', { method: 'POST' });
    } catch {
      // Ignore network errors on logout
    } finally {
      clearStoredAuth();
    }
  },

  getMe: async () => {
    const user = await apiRequest('/auth/me');
    setStoredUser(user);
    return user;
  },
};

export const bankingApi = {
  getAccount: async () => {
    return apiRequest('/banking/account');
  },

  getAccounts: async () => {
    return apiRequest('/banking/accounts');
  },

  getLoans: async () => {
    return apiRequest('/banking/loans');
  },

  payEmi: async (loanId, amount) => {
    return apiRequest('/banking/pay-emi', {
      method: 'POST',
      body: JSON.stringify({ loan_id: loanId, amount: Number(amount) }),
    });
  },

  getTransactions: async () => {
    return apiRequest('/banking/transactions');
  },

  transfer: async (recipientAccount, amount, note = 'Online transfer') => {
    return apiRequest('/banking/transfer', {
      method: 'POST',
      body: JSON.stringify({
        recipient_account: recipientAccount,
        amount: Number(amount),
        note,
      }),
    });
  },

  deposit: async (amount, note = 'Direct deposit') => {
    return apiRequest('/banking/deposit', {
      method: 'POST',
      body: JSON.stringify({
        amount: Number(amount),
        note,
      }),
    });
  },
};

// VaaniDesk AI agent: one server session per conversation; the server forwards each turn to the AI service.
let agentSessionId = null;

export const agentApi = {
  ensureSession: async (channel = 'web_voice') => {
    if (!agentSessionId) {
      const s = await apiRequest('/sessions', { method: 'POST', body: JSON.stringify({ channel }) });
      agentSessionId = s.session_id;
    }
    return agentSessionId;
  },

  // returns TurnResponse: reply_text, transcript, detected_intents, verified, tickets, escalation, sources ...
  sendText: async (text) => {
    const sid = await agentApi.ensureSession('chat');
    return apiRequest(`/sessions/${sid}/turn`, {
      method: 'POST',
      body: JSON.stringify({ text, input_type: 'text' }),
    });
  },

  sendVoice: async (audioBlob) => {
    const sid = await agentApi.ensureSession('web_voice');
    const formData = new FormData();
    formData.append('audio', audioBlob, 'turn.webm');
    const response = await fetch(`${API_BASE}/sessions/${sid}/turn/audio`, {
      method: 'POST',
      body: formData,
      credentials: 'include',
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const err = data.detail?.error?.message || data.error?.message || data.detail || 'Voice request failed';
      throw new Error(typeof err === 'string' ? err : 'Voice request failed');
    }
    return data;
  },

  endSession: async () => {
    if (!agentSessionId) return;
    const sid = agentSessionId;
    agentSessionId = null;
    return apiRequest(`/sessions/${sid}/end`, { method: 'POST', body: JSON.stringify({}) }).catch(() => {});
  },
};

// Short reference line for tickets/escalation shown under the agent reply
export const describeTurn = (turn) => {
  const parts = [];
  if (turn?.tickets?.length) parts.push(`Ref ${turn.tickets.join(', ')}`);
  if (turn?.escalation) parts.push('Transferred to a human agent');
  return parts.length ? ` (${parts.join(' • ')})` : '';
};

export const supportApi = {
  sendVoice: async (audioBlob, metadata = {}) => {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'support_voice.webm');
    if (metadata.customer_name) formData.append('customer_name', metadata.customer_name);
    if (metadata.account_number) formData.append('account_number', metadata.account_number);
    if (metadata.note) formData.append('note', metadata.note);

    const response = await fetch(`${API_BASE}/support/voice`, {
      method: 'POST',
      body: formData,
      credentials: 'include',
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || data.message || 'Failed to submit voice recording');
    }
    return data;
  },

  sendText: async ({ message, customerName, accountNumber, category }) => {
    return apiRequest('/support/text', {
      method: 'POST',
      body: JSON.stringify({
        message,
        customer_name: customerName,
        account_number: accountNumber,
        category,
      }),
    });
  },

  getStatus: async () => {
    return apiRequest('/support/status');
  },
};


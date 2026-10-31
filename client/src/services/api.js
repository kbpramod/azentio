const API_BASE = '/api/v1';

export const getStoredToken = () => {
  return localStorage.getItem('azentio_token');
};

export const setStoredToken = (token) => {
  if (token) {
    localStorage.setItem('azentio_token', token);
  } else {
    localStorage.removeItem('azentio_token');
  }
};

export const clearStoredAuth = () => {
  localStorage.removeItem('azentio_token');
  localStorage.removeItem('azentio_user');
};

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

async function apiRequest(endpoint, options = {}) {
  const token = getStoredToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

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
    setStoredToken(data.access_token);
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
    setStoredToken(data.access_token);
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

export const agentApi = {
  chat: async (message) => {
    return apiRequest('/agent/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  },
};


import React, { useState } from 'react';

export default function AuthCard({ onLoginSuccess, onRegisterSuccess }) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [initialDeposit, setInitialDeposit] = useState('1500');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fillDemoCredentials = () => {
    setIsRegister(false);
    setEmail('customer@azentio.com');
    setPassword('password123');
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isRegister) {
        if (!fullName.trim()) {
          throw new Error('Please enter your full legal name.');
        }
        await onRegisterSuccess(email, password, fullName, initialDeposit);
      } else {
        await onLoginSuccess(email, password);
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-card-wrapper">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-icon-circle">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
          <h2>{isRegister ? 'Open Azentio Bank Account' : 'Customer Secure Portal'}</h2>
          <p className="auth-sub">
            {isRegister
              ? 'Complete registration with instant opening balance & 500 AI credits'
              : 'Sign in to access your accounts, transfers, and AI banking assistant'}
          </p>
        </div>

        {error && (
          <div className="auth-error-banner">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          {isRegister && (
            <div className="form-group">
              <label>Full Name</label>
              <input
                type="text"
                placeholder="e.g. Alex Mercer"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
              />
            </div>
          )}

          <div className="form-group">
            <label>Email Address</label>
            <input
              type="email"
              placeholder="customer@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {isRegister && (
            <div className="form-group">
              <label>Initial Deposit (USD)</label>
              <div className="input-prefix-wrapper">
                <span className="input-prefix">$</span>
                <input
                  type="number"
                  min="0"
                  step="50"
                  value={initialDeposit}
                  onChange={(e) => setInitialDeposit(e.target.value)}
                  required
                />
              </div>
              <span className="input-help">Bonus: Every new account receives 500 AI Agent Credits.</span>
            </div>
          )}

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? (
              <span className="loading-spinner"></span>
            ) : isRegister ? (
              'Create Customer Account'
            ) : (
              'Sign In to Customer Portal'
            )}
          </button>
        </form>

        <div className="auth-demo-shortcut">
          <button
            type="button"
            className="btn-demo-quickfill"
            onClick={fillDemoCredentials}
            title="Auto-fill with seeded demo customer account"
          >
            ⚡ Auto-Fill Demo Credentials (customer@azentio.com)
          </button>
        </div>

        <div className="auth-footer-toggle">
          {isRegister ? (
            <p>
              Already have an account?{' '}
              <button
                type="button"
                className="btn-link"
                onClick={() => {
                  setIsRegister(false);
                  setError('');
                }}
              >
                Sign In
              </button>
            </p>
          ) : (
            <p>
              New customer?{' '}
              <button
                type="button"
                className="btn-link"
                onClick={() => {
                  setIsRegister(true);
                  setError('');
                }}
              >
                Open an Account
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}


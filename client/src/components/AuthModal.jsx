import React, { useState } from 'react';

export default function AuthModal({
  isOpen,
  initialMode = 'login',
  onClose,
  onLoginSuccess,
  onRegisterSuccess,
}) {
  const [isRegister, setIsRegister] = useState(initialMode === 'register');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [initialDeposit, setInitialDeposit] = useState('25000');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

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
          throw new Error('Please enter your full legal name as per government ID.');
        }
        await onRegisterSuccess(email, password, fullName, initialDeposit);
      } else {
        await onLoginSuccess(email, password);
      }
      onClose();
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="auth-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="auth-modal-header">
          <div className="auth-header-text">
            <h3>{isRegister ? 'Open Azentio Bank Account' : 'NetBanking Secure Sign In'}</h3>
            <p className="auth-sub">
              {isRegister
                ? 'Digital KYC account opening with zero branch visits'
                : 'Enter your registered credentials to access your accounts'}
            </p>
          </div>
          <button className="btn-modal-close" onClick={onClose}>✕</button>
        </div>

        {error && (
          <div className="auth-error-banner">
            <span>⚠ {error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          {isRegister && (
            <div className="form-group">
              <label>Full Legal Name</label>
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
            <label>Registered Email Address</label>
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
              <label>Initial Opening Deposit (₹)</label>
              <div className="input-prefix-wrapper">
                <span className="input-prefix">₹</span>
                <input
                  type="number"
                  min="0"
                  step="1000"
                  value={initialDeposit}
                  onChange={(e) => setInitialDeposit(e.target.value)}
                  required
                />
              </div>
              <span className="input-help">Interest accrues daily from day of deposit.</span>
            </div>
          )}

          <button type="submit" className="btn-primary btn-auth-submit" disabled={loading}>
            {loading ? <span className="loading-spinner"></span> : isRegister ? 'Confirm Account Creation' : 'Sign In to NetBanking'}
          </button>
        </form>

        <div className="auth-demo-shortcut">
          <button
            type="button"
            className="btn-demo-quickfill"
            onClick={fillDemoCredentials}
          >
            ⚡ Auto-Fill Demo Credentials (customer@azentio.com)
          </button>
        </div>

        <div className="auth-footer-toggle">
          {isRegister ? (
            <p>
              Already an account holder?{' '}
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
              New to Azentio Bank?{' '}
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


import React from 'react';

export default function Navbar({
  user,
  activeTab,
  onTabChange,
  onLogout,
  onOpenAuth,
  onOpenInfo,
}) {
  return (
    <header className="navbar">
      <div className="nav-container">
        {/* Brand Logo */}
        <div className="nav-brand" onClick={() => onTabChange && onTabChange('accounts')}>
          <div className="brand-logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 21h18M3 10h18M5 10v11M9 10v11M15 10v11M19 10v11M12 2l10 5H2l10-5z" />
            </svg>
          </div>
          <div className="brand-text">
            <span className="brand-name">AZENTIO</span>
            <span className="brand-sub">BANK</span>
          </div>
        </div>

        {/* Logged Out Navigation */}
        {!user ? (
          <div className="nav-guest-actions">
            <nav className="guest-nav-links">
              <button className="nav-text-link" onClick={() => onOpenInfo('about')}>
                About Us
              </button>
              <button className="nav-text-link" onClick={() => onOpenInfo('terms')}>
                Terms & Disclosures
              </button>
              <button className="nav-text-link" onClick={() => onOpenInfo('security')}>
                Security
              </button>
            </nav>

            <div className="guest-cta-btns">
              <button className="btn-nav-signin" onClick={() => onOpenAuth('login')}>
                Sign In
              </button>
              <button className="btn-nav-signup" onClick={() => onOpenAuth('register')}>
                Open Account
              </button>
            </div>
          </div>
        ) : (
          /* Logged In Dashboard Navigation */
          <div className="nav-customer-bar">
            <nav className="customer-tabs-nav">
              <button
                className={`cust-tab-btn ${activeTab === 'accounts' ? 'active' : ''}`}
                onClick={() => onTabChange('accounts')}
              >
                🏛️ Accounts
              </button>
              <button
                className={`cust-tab-btn ${activeTab === 'cards' ? 'active' : ''}`}
                onClick={() => onTabChange('cards')}
              >
                💳 Cards
              </button>
              <button
                className={`cust-tab-btn ${activeTab === 'upi' ? 'active' : ''}`}
                onClick={() => onTabChange('upi')}
              >
                ⚡ UPI Payments
              </button>
              <button
                className={`cust-tab-btn ${activeTab === 'emi' ? 'active' : ''}`}
                onClick={() => onTabChange('emi')}
              >
                📈 EMI & Loans
              </button>
            </nav>

            <div className="customer-right-cluster">
              <div className="user-profile-badge">
                <div className="user-avatar">
                  {user.full_name ? user.full_name.charAt(0).toUpperCase() : 'C'}
                </div>
                <div className="user-info">
                  <span className="user-name">{user.full_name}</span>
                  <span className="user-account">{user.account_number}</span>
                </div>
              </div>

              <button onClick={onLogout} className="btn-logout" title="Sign out from NetBanking">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
                <span>Logout</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}

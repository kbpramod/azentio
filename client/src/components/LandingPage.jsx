import React, { useState } from 'react';

export default function LandingPage({ onOpenAuth, onOpenInfo }) {
  const [activeTab, setActiveTab] = useState('accounts');

  return (
    <div className="landing-page">
      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <div className="hero-trust-badge">
            <span className="trust-dot"></span>
            <span>Chartered Commercial Bank • Central Deposit Insured</span>
          </div>

          <h1 className="hero-headline">
            The Digital Bank <br />
            <span className="text-gradient">Engineered for Your Future</span>
          </h1>

          <p className="hero-subtext">
            Experience next-generation banking with instant account activation, up to 7.15% p.a.
            high-yield savings, zero-forex Platinum cards, lightning FastUPI transfers, and transparent low-interest EMI loans.
          </p>

          <div className="hero-cta-group">
            <button
              className="btn-hero-primary"
              onClick={() => onOpenAuth('register')}
            >
              Open Free Account in 3 Mins
            </button>
            <button
              className="btn-hero-secondary"
              onClick={() => onOpenAuth('login')}
            >
              Secure NetBanking Login →
            </button>
          </div>

          <div className="hero-quick-demo">
            <button
              type="button"
              className="btn-hero-demo"
              onClick={() => onOpenAuth('demo')}
            >
              ⚡ Instant 1-Click Demo Login (customer@azentio.com)
            </button>
          </div>

          {/* Key Trust Metrics */}
          <div className="hero-metrics-strip">
            <div className="metric-item">
              <strong>₹1,250 Cr+</strong>
              <span>Customer Assets Managed</span>
            </div>
            <div className="metric-divider"></div>
            <div className="metric-item">
              <strong>2.4M+</strong>
              <span>Active Account Holders</span>
            </div>
            <div className="metric-divider"></div>
            <div className="metric-item">
              <strong>99.99%</strong>
              <span>Core Banking Uptime</span>
            </div>
            <div className="metric-divider"></div>
            <div className="metric-item">
              <strong>Zero</strong>
              <span>Account Opening Charges</span>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Showcase Tabs */}
      <section className="banking-pillars-section">
        <div className="section-intro">
          <h2>Everything You Need in Modern Banking</h2>
          <p>Unified financial services designed for individuals, families, and growing businesses.</p>
        </div>

        <div className="pillar-tabs-nav">
          <button
            className={`pillar-tab-btn ${activeTab === 'accounts' ? 'active' : ''}`}
            onClick={() => setActiveTab('accounts')}
          >
            🏛️ Depository Accounts
          </button>
          <button
            className={`pillar-tab-btn ${activeTab === 'cards' ? 'active' : ''}`}
            onClick={() => setActiveTab('cards')}
          >
            💳 Platinum Cards
          </button>
          <button
            className={`pillar-tab-btn ${activeTab === 'upi' ? 'active' : ''}`}
            onClick={() => setActiveTab('upi')}
          >
            ⚡ Instant FastUPI
          </button>
          <button
            className={`pillar-tab-btn ${activeTab === 'emi' ? 'active' : ''}`}
            onClick={() => setActiveTab('emi')}
          >
            📈 EMI & Loans
          </button>
        </div>

        <div className="pillar-display-card">
          {activeTab === 'accounts' && (
            <div className="pillar-content-grid">
              <div className="pillar-text-col">
                <h3>High-Yield Savings & Salary Accounts</h3>
                <p>
                  Grow your wealth automatically with industry-leading daily interest crediting. Enjoy unlimited
                  domestic wire settlements, free checkbook issuance, and dedicated relationship management.
                </p>
                <ul className="pillar-benefits-list">
                  <li>✔ Up to 7.15% annual interest on daily balances</li>
                  <li>✔ Zero maintenance balance on salary & premier checking accounts</li>
                  <li>✔ Free RTGS, NEFT, IMPS & international SWIFT wire execution</li>
                  <li>✔ Download official stamped account statements instantly</li>
                </ul>
                <button className="btn-primary" onClick={() => onOpenAuth('register')}>
                  Apply for Savings Account
                </button>
              </div>
              <div className="pillar-visual-col">
                <div className="preview-stat-card">
                  <span className="stat-label">Savings Interest Yield</span>
                  <div className="stat-big">7.15% <span className="stat-unit">p.a.</span></div>
                  <p className="stat-desc">Calculated daily on balance and credited monthly into your primary account.</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'cards' && (
            <div className="pillar-content-grid">
              <div className="pillar-text-col">
                <h3>Contactless Platinum Debit & Credit Cards</h3>
                <p>
                  Accepted across 40+ million merchants worldwide. Protect your money with instant in-app freeze controls,
                  custom daily spending limits, and zero foreign exchange markup on international travel.
                </p>
                <ul className="pillar-benefits-list">
                  <li>✔ Zero forex markup across global currencies</li>
                  <li>✔ Tap-and-pay NFC contactless transactions up to ₹5,000 without PIN</li>
                  <li>✔ Instant in-app freeze/unfreeze controls</li>
                  <li>✔ 5% cashback on dining, fuel, and travel bookings</li>
                </ul>
                <button className="btn-primary" onClick={() => onOpenAuth('register')}>
                  Get Platinum Card
                </button>
              </div>
              <div className="pillar-visual-col">
                <div className="preview-card-art">
                  <div className="art-chip"></div>
                  <span className="art-number">4532 •••• •••• 4892</span>
                  <div className="art-footer">
                    <span>AZENTIO PLATINUM</span>
                    <span className="art-visa">VISA</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'upi' && (
            <div className="pillar-content-grid">
              <div className="pillar-text-col">
                <h3>Azentio FastUPI: Lightning Payments</h3>
                <p>
                  Link your primary account directly to your custom Azentio UPI handle. Send and receive money in seconds
                  to any bank UPI ID or phone number with zero transaction fees.
                </p>
                <ul className="pillar-benefits-list">
                  <li>✔ Instant 24/7 bank-to-bank settlement</li>
                  <li>✔ Custom handle: yourname@azentio</li>
                  <li>✔ Scan any QR code at offline retail merchants</li>
                  <li>✔ Biometric and 4-digit bank PIN security protection</li>
                </ul>
                <button className="btn-primary" onClick={() => onOpenAuth('login')}>
                  Link Your UPI Handle
                </button>
              </div>
              <div className="pillar-visual-col">
                <div className="preview-upi-box">
                  <span className="preview-upi-badge">⚡ Live FastUPI Network</span>
                  <div className="preview-upi-handle">customer@azentio</div>
                  <span className="preview-upi-status">Instant 24x7 Clearing Active</span>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'emi' && (
            <div className="pillar-content-grid">
              <div className="pillar-text-col">
                <h3>Flexible Low-Interest EMI & Personal Loans</h3>
                <p>
                  Convert high-value shopping into effortless 3, 6, 12, or 24-month installments. Or access pre-approved
                  personal, vehicle, and home financing with zero prepayment penalty.
                </p>
                <ul className="pillar-benefits-list">
                  <li>✔ Interest rates starting at 10.5% p.a. for pre-approved customers</li>
                  <li>✔ Instant digital documentation verification</li>
                  <li>✔ Transparent installment tracker with progress indicators</li>
                  <li>✔ Foreclose or prepay anytime with zero penalty charges</li>
                </ul>
                <button className="btn-primary" onClick={() => onOpenAuth('login')}>
                  Check Loan Eligibility
                </button>
              </div>
              <div className="pillar-visual-col">
                <div className="preview-loan-box">
                  <span className="preview-loan-title">Pre-Approved Personal Loan</span>
                  <div className="preview-loan-amount">Up to ₹15,00,000</div>
                  <span className="preview-loan-rate">Starting from 10.5% p.a. • Instant Disbursal</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Institutional Security Banner */}
      <section className="security-guarantee-section">
        <div className="security-guarantee-box">
          <div className="sec-icon-circle">🛡️</div>
          <div>
            <h3>Your Deposits are Protected by Institutional Safeguards</h3>
            <p>
              Azentio Bank complies with central regulatory capital standards. All retail deposits are insured up to
              statutory ceilings, and digital interactions are guarded by 256-bit cryptographic protocols.
            </p>
          </div>
          <button className="btn-secondary" onClick={() => onOpenInfo('security')}>
            Security Standards
          </button>
        </div>
      </section>

      {/* Institutional Footer */}
      <footer className="bank-official-footer">
        <div className="footer-cols-grid">
          <div className="footer-brand-col">
            <div className="footer-logo">
              <span className="footer-brand-title">AZENTIO BANK</span>
              <span className="footer-brand-license">Chartered Commercial Banking Corp.</span>
            </div>
            <p className="footer-brand-desc">
              Regulated commercial bank providing high-yield depository, credit, and clearinghouse solutions
              to millions of retail, commercial, and enterprise clients.
            </p>
          </div>

          <div className="footer-links-col">
            <h5>Products</h5>
            <ul>
              <li><button onClick={() => onOpenAuth('register')}>Savings Account</button></li>
              <li><button onClick={() => onOpenAuth('register')}>Salary Account</button></li>
              <li><button onClick={() => onOpenAuth('register')}>Platinum Debit Card</button></li>
              <li><button onClick={() => onOpenAuth('login')}>FastUPI Payments</button></li>
              <li><button onClick={() => onOpenAuth('login')}>Personal & Home Loans</button></li>
            </ul>
          </div>

          <div className="footer-links-col">
            <h5>Institutional Info</h5>
            <ul>
              <li><button onClick={() => onOpenInfo('about')}>About Azentio Bank</button></li>
              <li><button onClick={() => onOpenInfo('terms')}>Terms & Conditions</button></li>
              <li><button onClick={() => onOpenInfo('security')}>Security & Fraud Prevention</button></li>
              <li><button onClick={() => onOpenInfo('about')}>Leadership & Governance</button></li>
            </ul>
          </div>

          <div className="footer-links-col">
            <h5>Customer Support</h5>
            <ul>
              <li>Toll-Free: <strong>1800-AZENTIO</strong></li>
              <li>Support: <strong>support@azentiobank.com</strong></li>
              <li>ATM & Branch Locator</li>
              <li>Emergency Card Hotlisting (24x7)</li>
            </ul>
          </div>
        </div>

        <div className="footer-disclaimer-strip">
          <p>
            © 2026 Azentio Bank Corporation. All rights reserved. Azentio Bank is a licensed depository institution.
            Deposits are insured up to statutory regulatory limits. Unified Payments Interface (UPI) is a trademark of National Clearinghouses.
          </p>
        </div>
      </footer>
    </div>
  );
}


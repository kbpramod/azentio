import React, { useState } from 'react';

export default function CardsView({ user }) {
  const [isFrozen, setIsFrozen] = useState(false);
  const [showSensitive, setShowSensitive] = useState(false);
  const [onlineUsage, setOnlineUsage] = useState(true);
  const [intlUsage, setIntlUsage] = useState(false);
  const [tapAndPay, setTapAndPay] = useState(true);
  const [dailyLimit, setDailyLimit] = useState(5000);
  const [toast, setToast] = useState('');

  const triggerToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3000);
  };

  const cardNumber = showSensitive ? '4532 8901 3341 4892' : '•••• •••• •••• 4892';
  const cvv = showSensitive ? '834' : '•••';

  return (
    <div className="cards-view-container">
      {toast && <div className="card-toast-banner">{toast}</div>}

      <div className="cards-top-split">
        {/* Visual 3D Bank Card */}
        <div className={`platinum-bank-card ${isFrozen ? 'frozen' : ''}`}>
          <div className="card-top-row">
            <div className="card-brand-chip">
              <span className="card-bank-title">AZENTIO</span>
              <span className="card-tier-title">PLATINUM DEBIT</span>
            </div>
            <div className="contactless-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M8.5 16.5a5 5 0 0 1 0-7" />
                <path d="M12 19a8.5 8.5 0 0 1 0-12" />
                <path d="M15.5 21.5a12 12 0 0 1 0-17" />
              </svg>
            </div>
          </div>

          <div className="emv-chip"></div>

          <div className="card-middle-row">
            <span className="card-number-display">{cardNumber}</span>
          </div>

          <div className="card-bottom-row">
            <div className="card-holder-col">
              <span className="card-small-label">CARDHOLDER</span>
              <span className="card-holder-name">{user.full_name?.toUpperCase() || 'VALUED CUSTOMER'}</span>
            </div>
            <div className="card-valid-col">
              <span className="card-small-label">VALID THRU</span>
              <span className="card-valid-date">08/29</span>
            </div>
            <div className="card-cvv-col">
              <span className="card-small-label">CVV</span>
              <span className="card-cvv-code">{cvv}</span>
            </div>
            <div className="card-network-logo">
              <span className="visa-text">VISA</span>
            </div>
          </div>

          {isFrozen && (
            <div className="card-frozen-overlay">
              <span>❄ CARD LOCKED & FROZEN</span>
            </div>
          )}
        </div>

        {/* Card Quick Actions & Rewards */}
        <div className="card-meta-card">
          <div className="meta-header">
            <h4>Card Security Controls</h4>
            <button
              className="btn-reveal-details"
              onClick={() => setShowSensitive(!showSensitive)}
            >
              {showSensitive ? 'Hide Card Details' : 'Show CVV & Number'}
            </button>
          </div>

          <div className="card-action-switches">
            <div className="control-row">
              <div className="control-info">
                <span className="control-title">Freeze Card</span>
                <span className="control-desc">Instantly disable all POS, ATM, and online transactions</span>
              </div>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={isFrozen}
                  onChange={(e) => {
                    setIsFrozen(e.target.checked);
                    triggerToast(e.target.checked ? 'Card frozen successfully' : 'Card unfreezed and ready');
                  }}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>

            <div className="control-row">
              <div className="control-info">
                <span className="control-title">Online eCommerce Usage</span>
                <span className="control-desc">Enable 3D-Secure web checkout & subscription billing</span>
              </div>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={onlineUsage}
                  disabled={isFrozen}
                  onChange={(e) => {
                    setOnlineUsage(e.target.checked);
                    triggerToast('Online transactions updated');
                  }}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>

            <div className="control-row">
              <div className="control-info">
                <span className="control-title">Contactless Tap & Pay</span>
                <span className="control-desc">NFC contactless payments up to $100 without PIN</span>
              </div>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={tapAndPay}
                  disabled={isFrozen}
                  onChange={(e) => {
                    setTapAndPay(e.target.checked);
                    triggerToast('Contactless NFC setting updated');
                  }}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>

            <div className="control-row">
              <div className="control-info">
                <span className="control-title">International Roaming</span>
                <span className="control-desc">Allow transactions outside home country with zero forex markup</span>
              </div>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={intlUsage}
                  disabled={isFrozen}
                  onChange={(e) => {
                    setIntlUsage(e.target.checked);
                    triggerToast('International usage setting updated');
                  }}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>
          </div>

          {/* Daily Limit Slider */}
          <div className="limit-slider-container">
            <div className="slider-header">
              <span>Daily Spending Limit</span>
              <strong>${dailyLimit.toLocaleString()} / day</strong>
            </div>
            <input
              type="range"
              min="500"
              max="20000"
              step="500"
              value={dailyLimit}
              disabled={isFrozen}
              onChange={(e) => setDailyLimit(Number(e.target.value))}
            />
            <div className="slider-range-labels">
              <span>$500</span>
              <span>$10,000</span>
              <span>$20,000</span>
            </div>
          </div>
        </div>
      </div>

      {/* Rewards & Virtual Card Section */}
      <div className="cards-perks-grid">
        <div className="perk-card">
          <div className="perk-icon">🎁</div>
          <div>
            <h5>Azentio Rewards</h5>
            <p>14,820 points earned • Redeem for airline miles or statement credits</p>
          </div>
          <button className="btn-secondary-sm" onClick={() => triggerToast('Rewards catalog opening soon')}>
            Redeem
          </button>
        </div>

        <div className="perk-card">
          <div className="perk-icon">💳</div>
          <div>
            <h5>Instant Virtual Card</h5>
            <p>Generate single-use burnable cards for secure online subscriptions</p>
          </div>
          <button className="btn-secondary-sm" onClick={() => triggerToast('Virtual Card generated: 4912 •••• 9912')}>
            Generate Card
          </button>
        </div>
      </div>
    </div>
  );
}


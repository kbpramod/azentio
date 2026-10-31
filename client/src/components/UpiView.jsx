import React, { useState } from 'react';
import { bankingApi } from '../services/api';

export default function UpiView({ user, onTransferCompleted }) {
  const [payeeUpi, setPayeeUpi] = useState('');
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [upiPin, setUpiPin] = useState('');
  const [showPinModal, setShowPinModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  const upiId = `${user.email?.split('@')[0] || 'customer'}@azentio`;

  const copyUpiId = () => {
    navigator.clipboard.writeText(upiId);
    setMessage({ type: 'success', text: `UPI ID ${upiId} copied to clipboard!` });
    setTimeout(() => setMessage({ type: '', text: '' }), 3000);
  };

  const handleInitiatePay = (e) => {
    e.preventDefault();
    if (!payeeUpi.trim()) {
      setMessage({ type: 'error', text: 'Please enter a valid Payee UPI ID or mobile number.' });
      return;
    }
    if (Number(amount) <= 0) {
      setMessage({ type: 'error', text: 'Transfer amount must be greater than zero.' });
      return;
    }
    if (Number(amount) > user.balance) {
      setMessage({ type: 'error', text: `Insufficient balance. Available: $${user.balance.toFixed(2)}` });
      return;
    }
    setShowPinModal(true);
  };

  const handleConfirmPin = async () => {
    if (upiPin.length !== 4) {
      setMessage({ type: 'error', text: 'Please enter your 4-digit bank UPI PIN.' });
      return;
    }

    setLoading(true);
    setShowPinModal(false);

    try {
      // Execute transfer via backend banking API
      await bankingApi.transfer(
        payeeUpi,
        amount,
        `UPI/${note || 'Quick Payment'}/${payeeUpi}`
      );

      setMessage({
        type: 'success',
        text: `₹/${Number(amount).toFixed(2)} successfully sent to ${payeeUpi} via Azentio UPI!`,
      });
      setPayeeUpi('');
      setAmount('');
      setNote('');
      setUpiPin('');
      if (onTransferCompleted) {
        onTransferCompleted();
      }
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.message || 'UPI transaction failed. Please try again.',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="upi-view-container">
      {message.text && (
        <div className={`upi-banner ${message.type}`}>
          {message.text}
        </div>
      )}

      <div className="upi-grid">
        {/* UPI ID & QR Code Card */}
        <div className="upi-card upi-id-card">
          <div className="upi-card-header">
            <h4>Azentio FastUPI Profile</h4>
            <span className="upi-badge-live">● Instant 24x7</span>
          </div>

          <div className="upi-id-pill">
            <div className="upi-icon-circle">⚡</div>
            <div className="upi-text-group">
              <span className="upi-small-label">Your Active UPI ID</span>
              <strong className="upi-string">{upiId}</strong>
            </div>
            <button className="btn-copy-upi" onClick={copyUpiId} title="Copy UPI ID">
              Copy
            </button>
          </div>

          {/* QR Code Presentation */}
          <div className="upi-qr-box">
            <div className="qr-visual">
              <svg width="140" height="140" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="1.5">
                <rect x="3" y="3" width="7" height="7" />
                <rect x="14" y="3" width="7" height="7" />
                <rect x="3" y="14" width="7" height="7" />
                <rect x="14" y="14" width="3" height="3" />
                <rect x="18" y="18" width="3" height="3" />
                <rect x="14" y="18" width="3" height="3" />
                <rect x="18" y="14" width="3" height="3" />
                <rect x="5.5" y="5.5" width="2" height="2" fill="#3b82f6" />
                <rect x="16.5" y="5.5" width="2" height="2" fill="#3b82f6" />
                <rect x="5.5" y="16.5" width="2" height="2" fill="#3b82f6" />
              </svg>
            </div>
            <span className="qr-caption">Scan with any UPI App to Pay Directly</span>
            <span className="qr-linked-acc">Linked: Primary Checking ({user.account_number})</span>
          </div>
        </div>

        {/* Send Money via UPI Form */}
        <div className="upi-card upi-send-card">
          <div className="upi-card-header">
            <h4>Send Money via UPI</h4>
            <span className="upi-fee-tag">Zero Transfer Fee</span>
          </div>

          <form onSubmit={handleInitiatePay} className="upi-pay-form">
            <div className="form-group">
              <label>Payee UPI ID / Mobile Number</label>
              <input
                type="text"
                placeholder="e.g. merchant@okhdfcbank or 9876543210@paytm"
                value={payeeUpi}
                onChange={(e) => setPayeeUpi(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label>Amount (USD)</label>
              <div className="input-prefix-wrapper">
                <span className="input-prefix">$</span>
                <input
                  type="number"
                  step="0.01"
                  min="0.5"
                  placeholder="0.00"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label>Note / Remarks (Optional)</label>
              <input
                type="text"
                placeholder="Dinner, groceries, rent split"
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </div>

            <button type="submit" className="btn-primary btn-upi-submit" disabled={loading}>
              {loading ? <span className="loading-spinner"></span> : 'Proceed to Pay'}
            </button>
          </form>

          {/* Frequent Contacts */}
          <div className="frequent-upi-contacts">
            <span className="contacts-title">Quick Recipient Shortcuts:</span>
            <div className="contacts-chips">
              <button
                type="button"
                className="chip-recipient"
                onClick={() => setPayeeUpi('supermarket@azentio')}
              >
                🛒 City Supermarket
              </button>
              <button
                type="button"
                className="chip-recipient"
                onClick={() => setPayeeUpi('utilities@azentio')}
              >
                💡 Power & Electric
              </button>
              <button
                type="button"
                className="chip-recipient"
                onClick={() => setPayeeUpi('coffee@azentio')}
              >
                ☕ Artisan Cafe
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 4-Digit UPI PIN Verification Modal */}
      {showPinModal && (
        <div className="modal-overlay">
          <div className="modal-content pin-modal">
            <div className="modal-header">
              <h3>Enter 4-Digit UPI PIN</h3>
              <button className="btn-modal-close" onClick={() => setShowPinModal(false)}>✕</button>
            </div>
            <p className="pin-subtext">
              Authorizing transfer of <strong>${Number(amount).toFixed(2)}</strong> to <strong>{payeeUpi}</strong>
            </p>
            <div className="pin-input-wrapper">
              <input
                type="password"
                maxLength="4"
                placeholder="••••"
                className="upi-pin-field"
                value={upiPin}
                onChange={(e) => setUpiPin(e.target.value)}
                autoFocus
              />
            </div>
            <p className="pin-hint">Demo PIN: Any 4 digits (e.g. 1234)</p>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowPinModal(false)}>
                Cancel
              </button>
              <button className="btn-primary" onClick={handleConfirmPin}>
                Authorize & Pay
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


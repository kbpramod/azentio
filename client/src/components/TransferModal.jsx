import React, { useState } from 'react';
import { bankingApi } from '../services/api';

export default function TransferModal({ isOpen, onClose, onTransferCompleted }) {
  const [activeTab, setActiveTab] = useState('transfer'); // 'transfer' | 'deposit'
  const [recipient, setRecipient] = useState('');
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      if (activeTab === 'transfer') {
        if (!recipient.trim()) throw new Error('Recipient account number is required.');
        if (Number(amount) <= 0) throw new Error('Amount must be greater than zero.');
        await bankingApi.transfer(recipient, amount, note || 'Wire Transfer');
        setSuccess(`Successfully transferred $${Number(amount).toFixed(2)} to ${recipient}`);
      } else {
        if (Number(amount) <= 0) throw new Error('Deposit amount must be greater than zero.');
        await bankingApi.deposit(amount, note || 'Instant Mobile Deposit');
        setSuccess(`Successfully deposited $${Number(amount).toFixed(2)} into your account`);
      }
      setAmount('');
      setRecipient('');
      setNote('');
      if (onTransferCompleted) {
        onTransferCompleted();
      }
    } catch (err) {
      setError(err.message || 'Operation failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <div className="modal-tabs">
            <button
              className={`modal-tab ${activeTab === 'transfer' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('transfer');
                setError('');
                setSuccess('');
              }}
            >
              Transfer Funds
            </button>
            <button
              className={`modal-tab ${activeTab === 'deposit' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('deposit');
                setError('');
                setSuccess('');
              }}
            >
              Deposit Money
            </button>
          </div>
          <button className="btn-modal-close" onClick={onClose}>
            ✕
          </button>
        </div>

        {error && <div className="modal-error-banner">{error}</div>}
        {success && <div className="modal-success-banner">{success}</div>}

        <form onSubmit={handleSubmit} className="modal-form">
          {activeTab === 'transfer' && (
            <div className="form-group">
              <label>Recipient Account Number</label>
              <input
                type="text"
                placeholder="e.g. AZ-100234"
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
                required
              />
            </div>
          )}

          <div className="form-group">
            <label>Amount (USD)</label>
            <div className="input-prefix-wrapper">
              <span className="input-prefix">$</span>
              <input
                type="number"
                step="0.01"
                min="1"
                placeholder="0.00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label>Reference Note</label>
            <input
              type="text"
              placeholder={activeTab === 'transfer' ? 'Rent, Invoice, etc.' : 'Direct payroll, gift'}
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </div>

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? (
                <span className="loading-spinner"></span>
              ) : activeTab === 'transfer' ? (
                'Confirm Transfer'
              ) : (
                'Confirm Deposit'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}


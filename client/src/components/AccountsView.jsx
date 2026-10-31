import React, { useState, useEffect } from 'react';
import { bankingApi } from '../services/api';

export default function AccountsView({ user, onTransferClick, onDepositClick, refreshTrigger }) {
  const [accounts, setAccounts] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const [accs, txs] = await Promise.all([
        bankingApi.getAccounts(),
        bankingApi.getTransactions(),
      ]);
      setAccounts(accs);
      setTransactions(txs);
    } catch (err) {
      console.error('Failed to load accounts view data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [refreshTrigger]);

  const totalLiquidBalance = accounts.reduce((acc, a) => acc + (a.balance || 0), 0);

  return (
    <div className="accounts-view-container">
      {/* Total Portfolio Summary */}
      <div className="total-portfolio-banner">
        <div>
          <span className="banner-label">Total Liquid Net Worth</span>
          <h2 className="total-balance-h2">
            ₹{totalLiquidBalance.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </h2>
          <span className="portfolio-stat">Across {accounts.length} linked depository accounts</span>
        </div>
        <div className="portfolio-actions">
          <button className="btn-action-primary" onClick={onTransferClick}>
            <span>Transfer Funds</span>
          </button>
          <button className="btn-action-secondary" onClick={onDepositClick}>
            <span>Deposit Money</span>
          </button>
        </div>
      </div>

      {/* Linked Accounts Grid (From Neon DB) */}
      <div className="accounts-grid">
        {accounts.map((acc, idx) => (
          <div key={idx} className={`account-box ${acc.is_primary ? 'primary-account' : ''}`}>
            <div className="acc-box-top">
              <span className="acc-type-tag">{acc.type}</span>
              <span className="acc-number-code">{acc.account_id}</span>
            </div>
            <div className="acc-balance-row">
              <span className="currency-symbol">₹</span>
              <span className="acc-balance-num">
                {acc.balance.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
            <div className="acc-box-footer">
              <span className="acc-status-tag">● {acc.status}</span>
              <span className="acc-branch-tag">Azentio Financial District</span>
            </div>
          </div>
        ))}
      </div>

      {/* Comprehensive Statement Ledger */}
      <div className="transactions-section">
        <div className="section-header">
          <div>
            <h3>Official Account Statement</h3>
            <p className="statement-sub">Chronological ledger of debits, credits, and clearing transactions</p>
          </div>
          <button className="btn-refresh" onClick={loadData}>
            <span>Refresh Ledger</span>
          </button>
        </div>

        {loading ? (
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>Syncing statement records from core banking ledger...</p>
          </div>
        ) : transactions.length === 0 ? (
          <div className="empty-state">
            <p>No transaction history found for the current billing cycle.</p>
          </div>
        ) : (
          <div className="transactions-table-wrapper">
            <table className="transactions-table">
              <thead>
                <tr>
                  <th>Reference</th>
                  <th>Description</th>
                  <th>Posting Date</th>
                  <th>Status</th>
                  <th className="text-right">Amount (₹)</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx, idx) => {
                  const isCredit = tx.type === 'deposit' || tx.type === 'transfer_in';
                  return (
                    <tr key={idx}>
                      <td className="tx-ref-id">{tx.id || `TXN-${idx + 1}`}</td>
                      <td className="tx-desc">{tx.description}</td>
                      <td className="tx-date">
                        {new Date(tx.created_at).toLocaleDateString([], {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </td>
                      <td>
                        <span className={`tx-status-pill ${tx.status}`}>
                          {tx.status}
                        </span>
                      </td>
                      <td className={`tx-amount text-right ${isCredit ? 'positive' : 'negative'}`}>
                        {isCredit ? '+' : '-'}₹{Number(tx.amount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}


import React, { useState, useEffect } from 'react';
import { bankingApi, authApi } from '../services/api';
import AgentChat from './AgentChat';
import TransferModal from './TransferModal';

export default function Dashboard({ user, onUserUpdate }) {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeView, setActiveView] = useState('overview'); // 'overview' | 'agent'

  const loadBankingData = async () => {
    try {
      const [userData, txData] = await Promise.all([
        authApi.getMe(),
        bankingApi.getTransactions(),
      ]);
      onUserUpdate(userData);
      setTransactions(txData);
    } catch (err) {
      console.error('Failed to refresh banking data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBankingData();
  }, []);

  const handleCreditsUpdated = (newCredits) => {
    onUserUpdate({ ...user, ai_credits: newCredits });
    // Also quietly refresh transactions in the background to show the agent query
    bankingApi.getTransactions().then(setTransactions).catch(() => {});
  };

  return (
    <div className="dashboard-layout">
      {/* Welcome Banner */}
      <div className="welcome-banner">
        <div>
          <h2>Welcome back, {user.full_name}</h2>
          <p className="subtext">
            Online Banking Customer Portal • 24/7 AI-Powered Support Active
          </p>
        </div>
        <div className="banner-quick-actions">
          <button
            className="btn-action-primary"
            onClick={() => setIsModalOpen(true)}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            <span>Transfer / Deposit</span>
          </button>
          <button
            className={`btn-action-secondary ${activeView === 'agent' ? 'active' : ''}`}
            onClick={() => setActiveView(activeView === 'agent' ? 'overview' : 'agent')}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            <span>{activeView === 'agent' ? 'View Accounts' : 'Ask AI Agent'}</span>
          </button>
        </div>
      </div>

      {/* Metric Cards Row */}
      <div className="metrics-grid">
        {/* Account Balance Card */}
        <div className="metric-card balance-card">
          <div className="metric-top">
            <span className="metric-label">Checking Account</span>
            <span className="account-tag">{user.account_number}</span>
          </div>
          <div className="metric-amount">
            ${(user.balance ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="metric-footer">
            <span className="status-pill active">● Active & Protected</span>
            <span className="apy-tag">0.85% APY</span>
          </div>
        </div>

        {/* AI Credits Card */}
        <div className="metric-card credits-card">
          <div className="metric-top">
            <span className="metric-label">AI Agent Credits</span>
            <span className="credits-cost-tag">5 credits / query</span>
          </div>
          <div className="metric-amount">
            <span className="credits-number">{user.ai_credits ?? 0}</span>
            <span className="credits-unit">CR</span>
          </div>
          <div className="metric-footer">
            <span className="status-pill ready">● AI Service Online</span>
            <span className="powered-tag">Neon DB + AI Ready</span>
          </div>
        </div>

        {/* Security & Support Status Card */}
        <div className="metric-card security-card">
          <div className="metric-top">
            <span className="metric-label">Security & Authentication</span>
            <span className="status-pill active">● Protected</span>
          </div>
          <div className="security-details">
            <div className="security-item">
              <span className="sec-label">Auth Engine:</span>
              <span className="sec-val">Better Auth & JWT</span>
            </div>
            <div className="security-item">
              <span className="sec-label">Database:</span>
              <span className="sec-val">Neon PostgreSQL</span>
            </div>
          </div>
          <div className="metric-footer">
            <span className="timestamp-text">256-Bit SSL Enforced</span>
          </div>
        </div>
      </div>

      {/* Main View: Split or Tabbed */}
      {activeView === 'agent' ? (
        <div className="agent-view-container">
          <AgentChat user={user} onCreditsUpdated={handleCreditsUpdated} />
        </div>
      ) : (
        <div className="content-split-grid">
          {/* Transactions Ledger */}
          <div className="transactions-section">
            <div className="section-header">
              <h3>Recent Transactions</h3>
              <button
                className="btn-refresh"
                onClick={loadBankingData}
                disabled={loading}
                title="Refresh transaction records"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
                </svg>
                <span>Refresh</span>
              </button>
            </div>

            {loading ? (
              <div className="loading-state">
                <div className="loading-spinner"></div>
                <p>Loading transaction history...</p>
              </div>
            ) : transactions.length === 0 ? (
              <div className="empty-state">
                <p>No transactions found for this account yet.</p>
              </div>
            ) : (
              <div className="transactions-table-wrapper">
                <table className="transactions-table">
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Description</th>
                      <th>Date</th>
                      <th>Status</th>
                      <th className="text-right">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.map((tx) => {
                      const isPositive = tx.type === 'deposit' || tx.type === 'transfer_in';
                      const isAi = tx.type === 'ai_service';

                      return (
                        <tr key={tx.id}>
                          <td>
                            <span className={`tx-type-badge ${tx.type}`}>
                              {isAi ? '⚡ AI Agent' : isPositive ? '↓ Inflow' : '↑ Outflow'}
                            </span>
                          </td>
                          <td className="tx-desc">{tx.description}</td>
                          <td className="tx-date">
                            {new Date(tx.created_at).toLocaleDateString([], {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </td>
                          <td>
                            <span className="tx-status-pill">{tx.status}</span>
                          </td>
                          <td className={`tx-amount text-right ${isAi ? 'ai-cost' : isPositive ? 'positive' : 'negative'}`}>
                            {isAi ? '5 Credits' : `${isPositive ? '+' : '-'}$${tx.amount.toFixed(2)}`}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Quick AI Agent Preview Sidebar */}
          <div className="sidebar-agent-section">
            <AgentChat user={user} onCreditsUpdated={handleCreditsUpdated} />
          </div>
        </div>
      )}

      {/* Transfer & Deposit Modal */}
      <TransferModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onTransferCompleted={loadBankingData}
      />
    </div>
  );
}


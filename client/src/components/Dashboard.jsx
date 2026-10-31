import React, { useState, useEffect } from 'react';
import AccountsView from './AccountsView';
import CardsView from './CardsView';
import UpiView from './UpiView';
import EmiView from './EmiView';
import TicketsView from './TicketsView';
import TransferModal from './TransferModal';

export default function Dashboard({ user, activeTab = 'accounts', onUserUpdate }) {
  const [currentTab, setCurrentTab] = useState(activeTab);
  const [modalState, setModalState] = useState({ isOpen: false, defaultTab: 'transfer' });
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    if (activeTab) {
      setCurrentTab(activeTab);
    }
  }, [activeTab]);

  const handleDataRefresh = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  const formattedBalance = user?.balance !== undefined && user?.balance !== null
    ? Number(user.balance).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : '12,450.00';

  return (
    <div className="dashboard-container">
      {/* Neo-Brutalist Customer Header Banner */}
      <div className="dashboard-welcome-header">
        <div className="header-text-block">
          <div className="customer-badge-strip">
            <span className="badge-brutalist badge-yellow">CUSTOMER PORTAL</span>
            <span className="badge-brutalist badge-green">ACTIVE & VERIFIED</span>
            <span className="badge-brutalist badge-cyan">AI CREDITS: {user.ai_credits ?? 500}</span>
          </div>

          <h2>{user.full_name?.toUpperCase() || 'ALEX MERCER'}</h2>
          
          <div className="customer-meta-row">
            <div className="meta-item">
              <span className="meta-label">PRIMARY ACCOUNT</span>
              <strong className="meta-value">{user.account_number || 'AZ-882194'}</strong>
            </div>
            <div className="meta-item">
              <span className="meta-label">REGISTERED EMAIL</span>
              <span className="meta-value">{user.email || 'customer@azentio.com'}</span>
            </div>
            <div className="meta-item highlight-balance">
              <span className="meta-label">PRIMARY CHECKING BALANCE</span>
              <strong className="meta-balance">₹{formattedBalance}</strong>
            </div>
          </div>
        </div>

        <div className="header-actions-block">
          <button
            className="btn-action-primary"
            onClick={() => setModalState({ isOpen: true, defaultTab: 'transfer' })}
          >
            <span>⚡ Transfer Money</span>
          </button>
          <button
            className="btn-action-secondary"
            onClick={() => setModalState({ isOpen: true, defaultTab: 'deposit' })}
          >
            <span>↓ Deposit Funds</span>
          </button>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="dashboard-subtabs-nav">
        <button
          className={`subtab-btn ${currentTab === 'accounts' ? 'active' : ''}`}
          onClick={() => setCurrentTab('accounts')}
        >
          🏛️ Depository Accounts
        </button>
        <button
          className={`subtab-btn ${currentTab === 'cards' ? 'active' : ''}`}
          onClick={() => setCurrentTab('cards')}
        >
          💳 Platinum Cards
        </button>
        <button
          className={`subtab-btn ${currentTab === 'upi' ? 'active' : ''}`}
          onClick={() => setCurrentTab('upi')}
        >
          ⚡ FastUPI Payments
        </button>
        <button
          className={`subtab-btn ${currentTab === 'emi' ? 'active' : ''}`}
          onClick={() => setCurrentTab('emi')}
        >
          📈 EMI & Loans
        </button>
        <button
          className={`subtab-btn ${currentTab === 'tickets' ? 'active' : ''}`}
          onClick={() => setCurrentTab('tickets')}
        >
          🎫 Support & Escalations
        </button>
      </div>

      {/* Main Tab Panels */}
      <div className="dashboard-tab-panel">
        {currentTab === 'accounts' && (
          <AccountsView
            user={user}
            refreshTrigger={refreshTrigger}
            onTransferClick={() => setModalState({ isOpen: true, defaultTab: 'transfer' })}
            onDepositClick={() => setModalState({ isOpen: true, defaultTab: 'deposit' })}
          />
        )}

        {currentTab === 'cards' && (
          <CardsView user={user} />
        )}

        {currentTab === 'upi' && (
          <UpiView user={user} onTransferCompleted={handleDataRefresh} />
        )}

        {currentTab === 'emi' && (
          <EmiView user={user} onPaymentCompleted={handleDataRefresh} />
        )}

        {currentTab === 'tickets' && (
          <TicketsView user={user} />
        )}
      </div>

      {/* Transfer & Deposit Modal */}
      <TransferModal
        isOpen={modalState.isOpen}
        defaultTab={modalState.defaultTab}
        onClose={() => setModalState({ isOpen: false, defaultTab: 'transfer' })}
        onTransferCompleted={handleDataRefresh}
      />
    </div>
  );
}

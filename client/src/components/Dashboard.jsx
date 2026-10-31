import React, { useState } from 'react';
import AccountsView from './AccountsView';
import CardsView from './CardsView';
import UpiView from './UpiView';
import EmiView from './EmiView';
import TransferModal from './TransferModal';

export default function Dashboard({ user, activeTab = 'accounts', onUserUpdate }) {
  const [currentTab, setCurrentTab] = useState(activeTab);
  const [modalState, setModalState] = useState({ isOpen: false, defaultTab: 'transfer' });
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleDataRefresh = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <div className="dashboard-container">
      {/* Customer Header Banner */}
      <div className="dashboard-welcome-header">
        <div className="header-text-block">
          <h2>Welcome, {user.full_name}</h2>
          <p className="header-account-tag">
            Primary Account: <strong>{user.account_number}</strong> • Status: <span className="text-emerald">Active & Protected</span>
          </p>
        </div>

        <div className="header-actions-block">
          <button
            className="btn-action-primary"
            onClick={() => setModalState({ isOpen: true, defaultTab: 'transfer' })}
          >
            <span>Transfer Money</span>
          </button>
          <button
            className="btn-action-secondary"
            onClick={() => setModalState({ isOpen: true, defaultTab: 'deposit' })}
          >
            <span>Deposit Funds</span>
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

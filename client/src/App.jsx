import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import LandingPage from './components/LandingPage';
import Dashboard from './components/Dashboard';
import AuthModal from './components/AuthModal';
import InfoModal from './components/InfoModal';
import SupportWidget from './components/SupportWidget';
import {
  authApi,
  getStoredUser,
  setStoredUser,
  clearStoredAuth,
} from './services/api';
import './App.css';

export default function App() {
  const [user, setUser] = useState(getStoredUser());
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('accounts');

  // Modals
  const [authModal, setAuthModal] = useState({ isOpen: false, mode: 'login' });
  const [infoModal, setInfoModal] = useState({ isOpen: false, type: 'about' });

  useEffect(() => {
    // Check active session via HttpOnly cookies
    authApi
      .getMe()
      .then((userData) => {
        setUser(userData);
      })
      .catch(() => {
        clearStoredAuth();
        setUser(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const handleOpenAuth = (mode) => {
    if (mode === 'demo') {
      // 1-Click Demo Login
      setLoading(true);
      authApi
        .login('customer@azentio.com', 'password123')
        .then((res) => {
          setUser(res.user);
        })
        .catch((err) => {
          alert('Demo login failed: ' + err.message);
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setAuthModal({ isOpen: true, mode });
    }
  };

  const handleOpenInfo = (type) => {
    setInfoModal({ isOpen: true, type });
  };

  const handleLogin = async (email, password) => {
    const response = await authApi.login(email, password);
    setUser(response.user);
  };

  const handleRegister = async (email, password, fullName, initialDeposit) => {
    const response = await authApi.register(email, password, fullName, initialDeposit);
    setUser(response.user);
  };

  const handleLogout = async () => {
    await authApi.logout();
    setUser(null);
  };

  const handleUserUpdate = (updatedUser) => {
    setUser(updatedUser);
    setStoredUser(updatedUser);
  };

  if (loading) {
    return (
      <div className="app-loading-screen">
        <div className="app-spinner"></div>
        <p>Connecting to Azentio Banking Network...</p>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Universal Bank Header */}
      <Navbar
        user={user}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onLogout={handleLogout}
        onOpenAuth={handleOpenAuth}
        onOpenInfo={handleOpenInfo}
      />

      {/* Main Experience */}
      <main className="main-content-flow">
        {user ? (
          <Dashboard
            user={user}
            activeTab={activeTab}
            onUserUpdate={handleUserUpdate}
          />
        ) : (
          <LandingPage
            onOpenAuth={handleOpenAuth}
            onOpenInfo={handleOpenInfo}
          />
        )}
      </main>

      {/* Authentication Modal */}
      <AuthModal
        isOpen={authModal.isOpen}
        initialMode={authModal.mode}
        onClose={() => setAuthModal({ isOpen: false, mode: 'login' })}
        onLoginSuccess={handleLogin}
        onRegisterSuccess={handleRegister}
      />

      {/* Institutional Information Modal (About, Terms, Security) */}
      <InfoModal
        isOpen={infoModal.isOpen}
        type={infoModal.type}
        onClose={() => setInfoModal({ isOpen: false, type: 'about' })}
      />

      {/* Floating 24/7 Support Desk (Speak / Voice & Type) */}
      <SupportWidget user={user} />
    </div>
  );
}

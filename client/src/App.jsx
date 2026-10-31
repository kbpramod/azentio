import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import AuthCard from './components/AuthCard';
import Dashboard from './components/Dashboard';
import {
  authApi,
  getStoredToken,
  getStoredUser,
  setStoredUser,
  clearStoredAuth,
} from './services/api';
import './App.css';

export default function App() {
  const [user, setUser] = useState(getStoredUser());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getStoredToken();
    if (token) {
      authApi
        .getMe()
        .then((userData) => {
          setUser(userData);
        })
        .catch(() => {
          // Token expired or invalid
          clearStoredAuth();
          setUser(null);
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

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

  return (
    <div className="app-container">
      <Navbar user={user} onLogout={handleLogout} />

      <main className="main-content">
        {loading ? (
          <div className="app-loading-screen">
            <div className="app-spinner"></div>
            <p>Connecting to Azentio Banking Core...</p>
          </div>
        ) : user ? (
          <Dashboard user={user} onUserUpdate={handleUserUpdate} />
        ) : (
          <AuthCard
            onLoginSuccess={handleLogin}
            onRegisterSuccess={handleRegister}
          />
        )}
      </main>

      <footer className="app-footer">
        <div className="footer-content">
          <div className="footer-status">
            <span className="footer-dot"></span>
            <span>FastAPI Core: Online</span>
            <span className="footer-divider">•</span>
            <span>Database: Neon PostgreSQL</span>
            <span className="footer-divider">•</span>
            <span>Auth: Better Auth & JWT</span>
            <span className="footer-divider">•</span>
            <span>AI: AICredits Ready</span>
          </div>
          <p className="footer-copy">© 2026 Azentio Banking System. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

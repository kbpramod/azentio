import React, { useState, useEffect } from 'react';
import { sessionApi } from '../services/api';

export default function TicketsView({ user }) {
  const [tickets, setTickets] = useState([]);
  const [escalations, setEscalations] = useState([]);
  const [activeTab, setActiveTab] = useState('tickets'); // 'tickets' | 'escalations'
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const [tList, escList] = await Promise.all([
        sessionApi.getTickets().catch(() => []),
        sessionApi.getEscalationTickets().catch(() => []),
      ]);
      setTickets(Array.isArray(tList) ? tList : []);
      setEscalations(Array.isArray(escList) ? escList : []);
    } catch (err) {
      console.warn('Failed to load tickets ledger:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="tickets-view-container">
      {/* Top Banner */}
      <div className="tickets-summary-banner">
        <div>
          <span className="banner-label">Customer Support & Escalations Desk</span>
          <h2 className="total-balance-h2">
            {tickets.length} Registered Support Tickets
          </h2>
          <span className="portfolio-stat">
            {escalations.length} inquiries escalated to human specialist review
          </span>
        </div>
        <div className="portfolio-actions">
          <button className="btn-action-primary" onClick={loadData}>
            <span>↻ Refresh Tickets</span>
          </button>
        </div>
      </div>

      {/* Sub-selector tabs */}
      <div className="tickets-subtab-strip">
        <button
          className={`ticket-subtab-btn ${activeTab === 'tickets' ? 'active' : ''}`}
          onClick={() => setActiveTab('tickets')}
        >
          📋 All Tickets ({tickets.length})
        </button>
        <button
          className={`ticket-subtab-btn ${activeTab === 'escalations' ? 'active' : ''}`}
          onClick={() => setActiveTab('escalations')}
        >
          🚨 Unhandled AI Escalations ({escalations.length})
        </button>
      </div>

      {loading ? (
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Syncing ticket registry from banking network...</p>
        </div>
      ) : activeTab === 'tickets' ? (
        /* All Tickets Table */
        <div className="transactions-section">
          <div className="section-header">
            <div>
              <h3>Support Interaction Tickets</h3>
              <p className="statement-sub">Turn-by-turn records generated upon session completion</p>
            </div>
          </div>

          {tickets.length === 0 ? (
            <div className="empty-state">
              <p>No support tickets filed yet. When you complete a voice or chat session, it will be automatically logged here.</p>
            </div>
          ) : (
            <div className="transactions-table-wrapper">
              <table className="transactions-table">
                <thead>
                  <tr>
                    <th>Ticket ID</th>
                    <th>Session ID</th>
                    <th>Category</th>
                    <th>Summary</th>
                    <th>Status</th>
                    <th>Priority</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((t, idx) => (
                    <tr key={t.ticket_id || idx}>
                      <td>
                        <strong className="brutalist-code-tag">{t.ticket_id}</strong>
                      </td>
                      <td>
                        <span className="text-monospace">{t.session_id || 'N/A'}</span>
                      </td>
                      <td>
                        <span className="category-pill">{t.category || t.type || 'Support'}</span>
                      </td>
                      <td className="ticket-summary-cell">
                        {t.summary || 'Session completed'}
                      </td>
                      <td>
                        <span className={`status-pill status-${(t.status || 'CLOSED').toLowerCase()}`}>
                          {t.status || 'CLOSED'}
                        </span>
                      </td>
                      <td>
                        <span className={`priority-pill priority-${(t.priority || 'NORMAL').toLowerCase()}`}>
                          {t.priority || 'NORMAL'}
                        </span>
                      </td>
                      <td className="text-muted">
                        {t.created_at ? new Date(t.created_at).toLocaleString() : 'Recent'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        /* Escalation Tickets Table */
        <div className="transactions-section">
          <div className="section-header">
            <div>
              <h3>Unhandled AI Escalation Tickets</h3>
              <p className="statement-sub">Inquiries where AI requested human supervisor assistance</p>
            </div>
          </div>

          {escalations.length === 0 ? (
            <div className="empty-state">
              <p>Zero unhandled escalations! AI assistant successfully resolved all inquiries.</p>
            </div>
          ) : (
            <div className="transactions-table-wrapper">
              <table className="transactions-table">
                <thead>
                  <tr>
                    <th>Escalation ID</th>
                    <th>Linked Ticket</th>
                    <th>Reason</th>
                    <th>Query Summary</th>
                    <th>AI Turns</th>
                    <th>Status</th>
                    <th>Logged At</th>
                  </tr>
                </thead>
                <tbody>
                  {escalations.map((esc, idx) => (
                    <tr key={esc.escalation_ticket_id || idx}>
                      <td>
                        <strong className="brutalist-code-tag esc-tag">{esc.escalation_ticket_id}</strong>
                      </td>
                      <td>
                        <span className="text-monospace">{esc.ticket_id || 'N/A'}</span>
                      </td>
                      <td className="escalation-reason-cell">
                        <span className="reason-badge">⚠️ {esc.reason}</span>
                      </td>
                      <td className="ticket-summary-cell">
                        {esc.query_summary || 'Customer inquiry'}
                      </td>
                      <td>
                        <span className="turns-badge">{esc.ai_turns_count || 1} turns</span>
                      </td>
                      <td>
                        <span className="status-pill status-escalated">
                          {esc.status || 'PENDING_HUMAN_REVIEW'}
                        </span>
                      </td>
                      <td className="text-muted">
                        {esc.created_at ? new Date(esc.created_at).toLocaleString() : 'Recent'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}


import React, { useState } from 'react';
import { agentApi } from '../services/api';

export default function AgentChat({ user, onCreditsUpdated }) {
  const [messages, setMessages] = useState([
    {
      sender: 'agent',
      text: `Hello ${user.full_name}! I am your Azentio Banking Customer Service Agent. I can help with balance inquiries, wire transfers, and account security. How may I assist you today?`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const quickPrompts = [
    'What is my account balance?',
    'How do I transfer funds?',
    'How many AI credits do I have left?',
    'Is my debit card secure?',
  ];

  const handleSendMessage = async (textToSend) => {
    const text = textToSend || input;
    if (!text.trim() || loading) return;

    const userMsg = {
      sender: 'user',
      text,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setError('');
    setLoading(true);

    try {
      const response = await agentApi.chat(text);
      const agentMsg = {
        sender: 'agent',
        text: response.reply,
        creditsUsed: response.ai_credits_used,
        time: new Date(response.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, agentMsg]);
      if (onCreditsUpdated && response.remaining_credits !== undefined) {
        onCreditsUpdated(response.remaining_credits);
      }
    } catch (err) {
      setError(err.message || 'Failed to communicate with Customer Agent.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="agent-chat-card">
      <div className="agent-chat-header">
        <div className="agent-avatar-badge">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </div>
        <div>
          <h3>Azentio Banking AI Agent</h3>
          <span className="agent-status-indicator">
            <span className="agent-pulse"></span> Online (5 AI Credits / query)
          </span>
        </div>
      </div>

      <div className="quick-prompts-bar">
        <span>Quick questions:</span>
        <div className="quick-prompt-chips">
          {quickPrompts.map((q, idx) => (
            <button
              key={idx}
              type="button"
              className="prompt-chip"
              disabled={loading}
              onClick={() => handleSendMessage(q)}
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      <div className="agent-chat-messages">
        {messages.map((m, idx) => (
          <div key={idx} className={`chat-bubble-row ${m.sender}`}>
            <div className={`chat-bubble ${m.sender}`}>
              <p>{m.text}</p>
              <div className="chat-meta">
                <span>{m.time}</span>
                {m.creditsUsed && (
                  <span className="credits-deducted-tag">
                    ⚡ -{m.creditsUsed} Credits
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="chat-bubble-row agent">
            <div className="chat-bubble agent typing">
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </div>
          </div>
        )}
      </div>

      {error && <div className="chat-error-banner">{error}</div>}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSendMessage();
        }}
        className="agent-chat-input-bar"
      >
        <input
          type="text"
          placeholder="Ask your banking customer service agent..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button type="submit" className="btn-chat-send" disabled={loading || !input.trim()}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </form>
    </div>
  );
}


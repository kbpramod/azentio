import React, { useState, useRef, useEffect } from 'react';
import { supportApi, agentApi, describeTurn } from '../services/api';
import { getBankingReply, getWelcomeGreeting, isPersonalAccountQuery } from '../services/bankingKnowledge';
import LiveVoiceAgent from './LiveVoiceAgent';

export default function SupportWidget({ user, onOpenAuth }) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeMode, setActiveMode] = useState('chat'); // 'chat' | 'live_voice'
  const [inputText, setInputText] = useState('');
  const [isSending, setIsSending] = useState(false);

  // Chat message history
  const [messages, setMessages] = useState([
    {
      id: 'welcome-1',
      sender: 'assistant',
      type: 'text',
      content: getWelcomeGreeting(user),
      requiresLogin: !user,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  // Keep greeting in sync when user logs in or out
  useEffect(() => {
    setMessages((prev) => {
      // Only replace if there's only the initial welcome message
      if (prev.length <= 1 && (prev[0]?.id === 'welcome-1' || prev[0]?.id?.startsWith('welcome-'))) {
        return [
          {
            id: 'welcome-1',
            sender: 'assistant',
            type: 'text',
            content: getWelcomeGreeting(user),
            requiresLogin: !user,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ];
      }
      return prev;
    });
  }, [user]);

  // Quick Voice recording state (inside chat mode)
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [recordedAudio, setRecordedAudio] = useState(null); // { blob, url, duration }
  const [voiceError, setVoiceError] = useState('');

  // Refs
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll chat stream to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen && activeMode === 'chat') {
      scrollToBottom();
      inputRef.current?.focus();
    }
  }, [messages, isOpen, activeMode, isSending, recordedAudio]);

  // Cleanup audio URLs on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (recordedAudio?.url) URL.revokeObjectURL(recordedAudio.url);
    };
  }, [recordedAudio]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Start quick voice recording in chat
  const startRecording = async () => {
    setVoiceError('');
    setRecordedAudio(null);
    audioChunksRef.current = [];

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Microphone recording is not supported in this browser.');
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const options = { mimeType: 'audio/webm;codecs=opus' };
      let mediaRecorder;

      if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(options.mimeType)) {
        mediaRecorder = new MediaRecorder(stream, options);
      } else {
        mediaRecorder = new MediaRecorder(stream);
      }

      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const mimeType = mediaRecorder.mimeType || 'audio/webm';
        const blob = new Blob(audioChunksRef.current, { type: mimeType });
        const url = URL.createObjectURL(blob);
        setRecordedAudio({
          blob,
          url,
          duration: recordingTime,
        });
        setIsRecording(false);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start(250);
      setIsRecording(true);
      setRecordingTime(0);

      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error('Error starting audio recording:', err);
      setVoiceError(
        err.name === 'NotAllowedError'
          ? 'Microphone permission denied. Please allow microphone access.'
          : err.message || 'Microphone error.'
      );
      setIsRecording(false);
    }
  };

  // Stop quick recording
  const stopRecording = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  };

  // Cancel/Discard recording
  const cancelRecording = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    if (recordedAudio?.url) {
      URL.revokeObjectURL(recordedAudio.url);
    }
    setIsRecording(false);
    setRecordingTime(0);
    setRecordedAudio(null);
    setVoiceError('');
  };

  // Send typed text message (routes through AI Banking Agent with security login gating)
  const handleSendText = async (e) => {
    if (e) e.preventDefault();
    const text = inputText.trim();
    if (!text || isSending) return;

    const userMessageId = 'msg-' + Date.now();
    const timeNow = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    setMessages((prev) => [
      ...prev,
      {
        id: userMessageId,
        sender: 'user',
        type: 'text',
        content: text,
        timestamp: timeNow,
      },
    ]);

    setInputText('');
    setIsSending(true);

    try {
      let replyContent = '';
      let requiresLogin = false;
      let turnDesc = '';

      // Security Check: If guest is asking about personal accounts, prompt login immediately
      if (!user && isPersonalAccountQuery(text)) {
        const local = getBankingReply(text, null);
        replyContent = local.reply;
        requiresLogin = local.requiresLogin;
      } else {
        try {
          const result = await agentApi.sendText(text);
          replyContent = result.reply_text || result.reply || '';
          turnDesc = describeTurn(result);
        } catch (chatErr) {
          console.warn('agentApi sendText failed, attempting local fallback:', chatErr);
          try {
            const res = await agentApi.chat(text);
            replyContent = res.reply;
          } catch (_) {
            const local = getBankingReply(text, user);
            replyContent = local.reply;
            requiresLogin = local.requiresLogin;
          }
        }
      }

      if (!replyContent) {
        const local = getBankingReply(text, user);
        replyContent = local.reply;
        requiresLogin = local.requiresLogin;
      }

      if (!user && (replyContent.includes('please log in') || isPersonalAccountQuery(text))) {
        requiresLogin = true;
      }

      setMessages((prev) => [
        ...prev,
        {
          id: 'bot-' + Date.now(),
          sender: 'assistant',
          type: 'text',
          content: `${replyContent}${turnDesc}`,
          requiresLogin,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: 'bot-err-' + Date.now(),
          sender: 'assistant',
          type: 'error',
          content: `Could not process request: ${err.message || 'Server error'}. Please try again.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  // Send recorded voice note to backend
  const handleSendVoice = async () => {
    if (!recordedAudio?.blob || isSending) return;

    const timeNow = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const currentAudio = recordedAudio;

    setMessages((prev) => [
      ...prev,
      {
        id: 'user-voice-' + Date.now(),
        sender: 'user',
        type: 'voice',
        audioUrl: currentAudio.url,
        duration: currentAudio.duration,
        timestamp: timeNow,
      },
    ]);

    setRecordedAudio(null);
    setRecordingTime(0);
    setIsSending(true);

    try {
      const result = await agentApi.sendVoice(currentAudio.blob);

      setMessages((prev) => [
        ...prev,
        {
          id: 'bot-voice-' + Date.now(),
          sender: 'assistant',
          type: 'text',
          content: `${result.transcript ? `Heard: "${result.transcript}"\n\n` : ''}${result.reply_text}${describeTurn(result)}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: 'bot-err-' + Date.now(),
          sender: 'assistant',
          type: 'error',
          content: `Failed to transmit voice note: ${err.message || 'Network error'}.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  // Clear chat history
  const handleResetChat = () => {
    setMessages([
      {
        id: 'welcome-reset-' + Date.now(),
        sender: 'assistant',
        type: 'text',
        content: getWelcomeGreeting(user),
        requiresLogin: !user,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  return (
    <div className="support-widget-anchor">
      {/* Collapsed Launchers in Bottom Corner */}
      {!isOpen && (
        <div className="support-fab-cluster">
          {/* Hands-Free Live Voice Trigger Pill */}
          <button
            type="button"
            className="support-fab-voice-pill"
            onClick={() => {
              setActiveMode('live_voice');
              setIsOpen(true);
            }}
            title="Start hands-free real-time voice assistant"
          >
            <span className="fab-voice-orb"></span>
            <span className="fab-voice-text">🎙️ Live Voice</span>
          </button>

          {/* Standard Chat FAB */}
          <button
            type="button"
            className="support-fab"
            onClick={() => {
              setActiveMode('chat');
              setIsOpen(true);
            }}
            aria-label="Open 24/7 Support Chat"
            title="Open Azentio Chat Support"
          >
            <div className="support-fab-icon-wrap">
              <span className="support-fab-icon">💬</span>
              <span className="support-fab-pulse"></span>
            </div>
            <div className="support-fab-text">
              <span className="support-fab-title">Support</span>
            </div>
          </button>
        </div>
      )}

      {/* Expanded Interface */}
      {isOpen && (
        <>
          {activeMode === 'live_voice' ? (
            /* Live Continuous Duplex Voice Agent */
            <LiveVoiceAgent
              user={user}
              onOpenAuth={onOpenAuth}
              onSwitchToChat={() => setActiveMode('chat')}
              onClose={() => setIsOpen(false)}
            />
          ) : (
            /* ChatGPT-style Chat Window */
            <div className="chatgpt-window animate-fade-in">
              {/* Header */}
              <div className="chatgpt-header">
                <div className="chatgpt-header-profile">
                  <div className="chatgpt-avatar">
                    <span>🎧</span>
                    <span className="status-dot-active"></span>
                  </div>
                  <div className="chatgpt-header-text">
                    <div className="chatgpt-title">Azentio Support</div>
                    <div className="chatgpt-status">
                      {user ? `Signed in: ${user.email}` : 'Guest Visitor • General FAQs'}
                    </div>
                  </div>
                </div>

                <div className="chatgpt-header-actions">
                  <button
                    type="button"
                    className="btn-launch-live-voice"
                    onClick={() => setActiveMode('live_voice')}
                    title="Switch to hands-free live voice conversation"
                  >
                    🎙️ Voice Mode
                  </button>
                  <button
                    className="chat-action-btn"
                    onClick={handleResetChat}
                    title="Clear conversation"
                  >
                    ↺
                  </button>
                  <button
                    className="chat-action-btn"
                    onClick={() => {
                      if (isRecording) cancelRecording();
                      setIsOpen(false);
                    }}
                    title="Close chat"
                  >
                    ✕
                  </button>
                </div>
              </div>

              {/* Messages Stream */}
              <div className="chatgpt-messages-container">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`chat-bubble-row ${msg.sender === 'user' ? 'row-user' : 'row-bot'}`}
                  >
                    {msg.sender === 'assistant' && (
                      <div className="bot-bubble-avatar">🎧</div>
                    )}

                    <div
                      className={`chat-bubble ${
                        msg.sender === 'user'
                          ? 'bubble-user'
                          : msg.type === 'error'
                          ? 'bubble-error'
                          : 'bubble-bot'
                      }`}
                    >
                      {msg.type === 'voice' ? (
                        <div className="voice-message-bubble">
                          <div className="voice-bubble-meta">
                            <span>🎙️ Voice Note</span>
                            <span className="voice-bubble-duration">
                              {formatTime(msg.duration || 0)}
                            </span>
                          </div>
                          <audio controls src={msg.audioUrl} className="bubble-audio-player" />
                        </div>
                      ) : (
                        <div className="chat-bubble-text">
                        <div>{msg.content}</div>
                        {!user && (msg.requiresLogin || msg.content?.includes("please log in")) && onOpenAuth && (
                          <button
                            type="button"
                            className="btn-voice-login-prompt"
                            onClick={() => onOpenAuth('login')}
                          >
                            🔑 Sign In to Your Account
                          </button>
                        )}
                      </div>
                      )}

                      <div className="chat-bubble-time">{msg.timestamp}</div>
                    </div>
                  </div>
                ))}

                {isSending && (
                  <div className="chat-bubble-row row-bot">
                    <div className="bot-bubble-avatar">🎧</div>
                    <div className="chat-bubble bubble-bot typing-indicator-bubble">
                      <div className="typing-dot dot-1"></div>
                      <div className="typing-dot dot-2"></div>
                      <div className="typing-dot dot-3"></div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {voiceError && (
                <div className="chat-inline-error">
                  <span>⚠️ {voiceError}</span>
                  <button onClick={() => setVoiceError('')}>✕</button>
                </div>
              )}

              {/* Pending Voice Review Strip */}
              {recordedAudio && (
                <div className="voice-pending-strip">
                  <div className="voice-pending-info">
                    <span className="pulse-circle"></span>
                    <span>Voice ready ({formatTime(recordedAudio.duration || 0)})</span>
                    <audio controls src={recordedAudio.url} className="strip-audio-player" />
                  </div>
                  <div className="voice-pending-btns">
                    <button
                      type="button"
                      className="btn-strip-discard"
                      onClick={cancelRecording}
                      title="Discard voice recording"
                    >
                      Discard
                    </button>
                    <button
                      type="button"
                      className="btn-strip-send"
                      onClick={handleSendVoice}
                      disabled={isSending}
                    >
                      {isSending ? 'Sending...' : 'Send Voice →'}
                    </button>
                  </div>
                </div>
              )}

              {/* Quick Audio Recording Bar Overlay */}
              {isRecording ? (
                <div className="chat-recording-bar">
                  <div className="recording-status-wrap">
                    <span className="red-rec-dot"></span>
                    <span className="rec-time-text">Recording: {formatTime(recordingTime)}</span>
                    <div className="inline-wave">
                      <span className="wave-line w-1"></span>
                      <span className="wave-line w-2"></span>
                      <span className="wave-line w-3"></span>
                      <span className="wave-line w-4"></span>
                    </div>
                  </div>

                  <div className="recording-bar-actions">
                    <button
                      type="button"
                      className="btn-cancel-rec"
                      onClick={cancelRecording}
                      title="Cancel recording"
                    >
                      ✕ Discard
                    </button>
                    <button
                      type="button"
                      className="btn-finish-rec"
                      onClick={stopRecording}
                      title="Stop and review"
                    >
                      ✓ Done
                    </button>
                  </div>
                </div>
              ) : (
                /* ChatGPT-style Message Input Form */
                <form onSubmit={handleSendText} className="chatgpt-input-bar">
                  <input
                    ref={inputRef}
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Type a message or tap mic..."
                    className="chatgpt-text-input"
                    disabled={isSending || !!recordedAudio}
                  />

                  <div className="chatgpt-input-actions">
                    <button
                      type="button"
                      className="chat-mic-btn"
                      onClick={startRecording}
                      disabled={isSending || !!recordedAudio}
                      title="Record quick voice note"
                      aria-label="Speak into microphone"
                    >
                      🎙️
                    </button>

                    <button
                      type="submit"
                      className="chat-send-btn"
                      disabled={!inputText.trim() || isSending}
                      title="Send message"
                      aria-label="Send message"
                    >
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                      </svg>
                    </button>
                  </div>
                </form>
              )}

              <div className="chatgpt-footer-bar">
                <span>🔒 Bank-Grade 256-Bit SSL Encrypted Support Channel</span>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { sessionApi, agentApi, describeTurn } from '../services/api';
import { getBankingReply, getWelcomeGreeting, isPersonalAccountQuery } from '../services/bankingKnowledge';

export default function LiveVoiceAgent({ user, onSwitchToChat, onClose, onOpenAuth }) {
  // Agent states: 'connecting' | 'listening' | 'user_speaking' | 'processing' | 'assistant_speaking' | 'muted' | 'error'
  const [agentState, setAgentState] = useState('connecting');
  const [liveVolume, setLiveVolume] = useState(0); // 0 to 100
  const [transcripts, setTranscripts] = useState([
    {
      id: 'init-1',
      sender: 'assistant',
      text: getWelcomeGreeting(user),
      requiresLogin: !user,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  // Keep greeting in sync when user logs in or out
  useEffect(() => {
    setTranscripts((prev) => {
      if (prev.length <= 1 && (prev[0]?.id === 'init-1' || prev[0]?.id?.startsWith('init-'))) {
        return [
          {
            id: 'init-1',
            sender: 'assistant',
            text: getWelcomeGreeting(user),
            requiresLogin: !user,
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ];
      }
      return prev;
    });
  }, [user]);
  const [statusMessage, setStatusMessage] = useState('Connecting to Azentio Voice Agent...');
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeakerEnabled, setIsSpeakerEnabled] = useState(true);
  const [playingBubbleId, setPlayingBubbleId] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [manualInput, setManualInput] = useState('');

  // Audio, VAD & Session references
  const streamRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const animFrameRef = useRef(null);
  const recognitionRef = useRef(null);
  const transcriptContainerRef = useRef(null);
  const sessionIdRef = useRef(null);
  const latestTranscriptRef = useRef('');
  const interimTranscriptRef = useRef('');
  const silenceTimerRef = useRef(null);
  const activeUtteranceRef = useRef(null);
  const isAssistantSpeakingRef = useRef(false);
  const isProcessingRef = useRef(false);
  const isClosingRef = useRef(false);

  // Configuration constants
  const SPEECH_THRESHOLD = 8;
  const SILENCE_DURATION_MS = 400; // 400ms pause after finalized speech triggers assistant response

  // Auto-scroll transcript log
  useEffect(() => {
    if (transcriptContainerRef.current) {
      transcriptContainerRef.current.scrollTop = transcriptContainerRef.current.scrollHeight;
    }
  }, [transcripts]);

  // Robust Text-To-Speech (Speech-to-Speech audio output)
  const speakText = useCallback((text, onFinishCallback, bubbleId = null) => {
    if (isClosingRef.current) return;
    if (!('speechSynthesis' in window)) {
      if (onFinishCallback) onFinishCallback();
      return;
    }

    try {
      // Chrome unfreeze: resume paused audio pipeline
      window.speechSynthesis.cancel();
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
      }

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;

      // Select natural English voice
      const voices = window.speechSynthesis.getVoices();
      if (voices && voices.length > 0) {
        const naturalVoice = voices.find(
          (v) =>
            v.lang.startsWith('en') &&
            (v.name.includes('Natural') ||
              v.name.includes('Google') ||
              v.name.includes('Online') ||
              v.name.includes('David') ||
              v.name.includes('Zira') ||
              v.name.includes('Samantha') ||
              v.name.includes('Mark'))
        ) || voices.find((v) => v.lang.startsWith('en')) || voices[0];

        if (naturalVoice) utterance.voice = naturalVoice;
      }

      // Store in ref to prevent V8 garbage collection mid-speech
      activeUtteranceRef.current = utterance;
      isAssistantSpeakingRef.current = true;
      setAgentState('assistant_speaking');
      setStatusMessage('Azentio Assistant speaking (audio output active)...');
      if (bubbleId) setPlayingBubbleId(bubbleId);

      utterance.onend = () => {
        isAssistantSpeakingRef.current = false;
        activeUtteranceRef.current = null;
        setPlayingBubbleId(null);
        if (onFinishCallback && !isClosingRef.current) onFinishCallback();
      };

      utterance.onerror = (e) => {
        console.warn('Speech synthesis state:', e);
        isAssistantSpeakingRef.current = false;
        activeUtteranceRef.current = null;
        setPlayingBubbleId(null);
        if (onFinishCallback && !isClosingRef.current) onFinishCallback();
      };

      // Slight delay ensures audio context is primed in Chromium
      setTimeout(() => {
        if (!isClosingRef.current) {
          window.speechSynthesis.speak(utterance);
        }
      }, 40);
    } catch (e) {
      console.warn('TTS execution error:', e);
      isAssistantSpeakingRef.current = false;
      activeUtteranceRef.current = null;
      setPlayingBubbleId(null);
      if (onFinishCallback && !isClosingRef.current) onFinishCallback();
    }
  }, []);

  // Send recognized user speech to backend AI model (or smart offline banking fallback)
  const processUserTurn = useCallback(async (spokenText) => {
    if (isClosingRef.current || isProcessingRef.current) return;

    const text = (spokenText || latestTranscriptRef.current || interimTranscriptRef.current || '').trim();
    if (!text) {
      setAgentState('listening');
      setStatusMessage('Listening to you... (speak naturally)');
      return;
    }

    isProcessingRef.current = true;
    latestTranscriptRef.current = '';
    interimTranscriptRef.current = '';
    setAgentState('processing');
    setStatusMessage('Azentio AI is thinking...');

    const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // 1. Add user's spoken text to transcript
    setTranscripts((prev) => [
      ...prev,
      {
        id: 'user-' + Date.now(),
        sender: 'user',
        text: text,
        time: nowTime,
      },
    ]);

    let responseText = '';
    let requiresLogin = false;

    // Fast-path client security check: If guest and inquiring about personal account/balance/loans
    if (!user && isPersonalAccountQuery(text)) {
      const gRes = getBankingReply(text, null);
      responseText = gRes.reply;
      requiresLogin = gRes.requiresLogin;
    } else {
      // Query Backend AI Pipeline
      try {
        let sid = sessionIdRef.current;
        if (!sid) {
          const customerId = user?.customer_id || (user?.email === 'customer@azentio.com' ? 'C1023' : (user?.email || null));
          const newSession = await sessionApi.createSession(customerId, 'web_voice');
          sid = newSession.session_id;
          sessionIdRef.current = sid;
        }

        const turnRes = await sessionApi.sendTurn(sid, text, 'voice_transcript');
        responseText = turnRes.reply_text || '';
        if (turnRes && (turnRes.tickets?.length || turnRes.escalation)) {
          responseText += describeTurn(turnRes);
        }
      } catch (err) {
        console.warn('Session turn failed, attempting agentApi:', err);
        try {
          const chatRes = await agentApi.chat(text);
          responseText = chatRes.reply;
        } catch (fallbackErr) {
          console.warn('Backend unavailable, using banking knowledge engine:', fallbackErr);
          const localRes = getBankingReply(text, user);
          responseText = localRes.reply;
          requiresLogin = localRes.requiresLogin;
        }
      }

      if (!responseText) {
        const localRes = getBankingReply(text, user);
        responseText = localRes.reply;
        requiresLogin = localRes.requiresLogin;
      }
    }

    if (isClosingRef.current) return;

    if (!user && (responseText.includes('please log in') || isPersonalAccountQuery(text))) {
      requiresLogin = true;
    }

    const newBotBubbleId = 'bot-' + Date.now();

    // 3. Add assistant's response to transcript
    setTranscripts((prev) => [
      ...prev,
      {
        id: newBotBubbleId,
        sender: 'assistant',
        text: responseText,
        requiresLogin: requiresLogin,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);

    // 4. Speak response through speaker if audio output is enabled
    if (isSpeakerEnabled) {
      speakText(responseText, () => {
        isProcessingRef.current = false;
        if (!isClosingRef.current) {
          setAgentState('listening');
          setStatusMessage('Listening to you... (speak naturally)');
        }
      }, newBotBubbleId);
    } else {
      isProcessingRef.current = false;
      setAgentState('listening');
      setStatusMessage('Listening to you... (speaker is muted)');
    }
  }, [user, isSpeakerEnabled, speakText]);

  // Safe End Session Action (logs session details in tickets & routes unhandled to escalation_tickets)
  const handleEndSession = useCallback(() => {
    isClosingRef.current = true;
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (_) {}
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
    }
    if (sessionIdRef.current) {
      const hasEscalation = transcripts.some(
        (t) => t.sender === 'user' && /human|agent|supervisor|representative|escalat|complaint|not help/i.test(t.text)
      );
      const closeReason = hasEscalation
        ? 'Customer requested human supervisor or inquiry unhandled by AI'
        : 'Customer ended interaction normally';
      sessionApi.endSession(sessionIdRef.current, closeReason).catch(() => {});
    }
    onClose();
  }, [onClose, transcripts]);

  // Initialize Session & preload voices
  useEffect(() => {
    let active = true;

    // Preload system speech voices
    if ('speechSynthesis' in window) {
      window.speechSynthesis.getVoices();
      if (window.speechSynthesis.onvoiceschanged !== undefined) {
        window.speechSynthesis.onvoiceschanged = () => {
          window.speechSynthesis.getVoices();
        };
      }
    }

    async function initSession() {
      try {
        const customerId = user?.customer_id || (user?.email === 'customer@azentio.com' ? 'C1023' : null);
        const res = await sessionApi.createSession(customerId, 'web_voice');
        if (active && res?.session_id) {
          sessionIdRef.current = res.session_id;
          const greetingText = res.greeting || (user ? `Hello ${user.full_name}, how can I help you today?` : "Hello! I am your Azentio Banking Voice Assistant. I can answer any general banking FAQs regarding branch hours, interest rates, loans, and account opening. Sign in to access your personal account details.");
          setTranscripts([
            {
              id: 'init-1',
              sender: 'assistant',
              text: greetingText,
              time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ]);
          if (isSpeakerEnabled) {
            speakText(greetingText, null, 'init-1');
          }
        }
      } catch (err) {
        console.warn('Backend session init delay, offline voice assistant active:', err);
      }
    }

    initSession();

    return () => {
      active = false;
      if (sessionIdRef.current && !isClosingRef.current) {
        sessionApi.endSession(sessionIdRef.current).catch(() => {});
      }
    };
  }, [user, isSpeakerEnabled, speakText]);

  // Main Audio & Speech Recognition Engine
  useEffect(() => {
    let active = true;

    async function initAudioEngine() {
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          throw new Error('Microphone access is not supported by your browser.');
        }

        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });

        if (!active || isClosingRef.current) return;
        streamRef.current = stream;

        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        const audioCtx = new AudioContextClass();
        audioContextRef.current = audioCtx;

        if (audioCtx.state === 'suspended') {
          await audioCtx.resume();
        }

        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 256;
        analyser.smoothingTimeConstant = 0.3;
        analyserRef.current = analyser;

        const source = audioCtx.createMediaStreamSource(stream);
        source.connect(analyser);

        setAgentState('listening');
        setStatusMessage('Listening... speak whenever you are ready.');

        // Initialize Web Speech Recognition
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRec) {
          try {
            const recognition = new SpeechRec();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            recognition.onresult = (event) => {
              if (isClosingRef.current || isProcessingRef.current) return;

              let interimTranscript = '';
              let finalTranscript = '';

              for (let i = event.resultIndex; i < event.results.length; i++) {
                const textChunk = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                  finalTranscript += textChunk;
                } else {
                  interimTranscript += textChunk;
                }
              }

              // Barge-in: interrupt assistant if user speaks
              if ((finalTranscript || interimTranscript).trim() && isAssistantSpeakingRef.current) {
                window.speechSynthesis.cancel();
                isAssistantSpeakingRef.current = false;
              }

              // Case A: User completed a full thought/sentence (isFinal)
              if (finalTranscript.trim()) {
                const completedSentence = finalTranscript.trim();
                latestTranscriptRef.current = completedSentence;
                interimTranscriptRef.current = '';
                setAgentState('user_speaking');
                setStatusMessage(`You: "${completedSentence}"`);

                if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
                // 400ms pause after sentence completion triggers response
                silenceTimerRef.current = setTimeout(() => {
                  if (latestTranscriptRef.current && !isClosingRef.current && !isProcessingRef.current) {
                    const toSend = latestTranscriptRef.current;
                    latestTranscriptRef.current = '';
                    processUserTurn(toSend);
                  }
                }, SILENCE_DURATION_MS);
              }
              // Case B: User is speaking words mid-sentence (interim)
              else if (interimTranscript.trim()) {
                const currentDraft = interimTranscript.trim();
                interimTranscriptRef.current = currentDraft;
                setAgentState('user_speaking');
                setStatusMessage(`You: "${currentDraft}..."`);

                // Give 1000ms breathing room while user is still speaking mid-sentence
                if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
                silenceTimerRef.current = setTimeout(() => {
                  if (interimTranscriptRef.current && !isClosingRef.current && !isProcessingRef.current) {
                    const toSend = interimTranscriptRef.current;
                    interimTranscriptRef.current = '';
                    processUserTurn(toSend);
                  }
                }, 1000);
              }
            };

            recognition.onerror = (e) => {
              if (e.error !== 'no-speech') {
                console.warn('Speech recognition status:', e.error);
              }
            };

            recognition.onend = () => {
              if (active && !isMuted && !isClosingRef.current) {
                try { recognition.start(); } catch (_) {}
              }
            };

            recognition.start();
            recognitionRef.current = recognition;
          } catch (recErr) {
            console.warn('Browser speech recognition not active:', recErr);
          }
        }

        // Real-time audio volume visualizer & barge-in
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const analyzeAudio = () => {
          if (!active || isClosingRef.current) return;

          analyser.getByteFrequencyData(dataArray);

          // Vocal frequency volume range (bins 2 to 32)
          let voiceSum = 0;
          const binsToCheck = Math.min(32, bufferLength);
          for (let i = 2; i < binsToCheck; i++) {
            voiceSum += dataArray[i];
          }
          const vocalVolume = voiceSum / (binsToCheck - 2);
          setLiveVolume(Math.min(100, Math.round((vocalVolume / 100) * 100)));

          // Barge-in check while assistant is speaking
          if (isAssistantSpeakingRef.current) {
            if (vocalVolume > SPEECH_THRESHOLD + 4) {
              window.speechSynthesis.cancel();
              isAssistantSpeakingRef.current = false;
              setAgentState('user_speaking');
              setStatusMessage('Interrupted. Listening to you...');
            }
          }

          animFrameRef.current = requestAnimationFrame(analyzeAudio);
        };

        animFrameRef.current = requestAnimationFrame(analyzeAudio);
      } catch (err) {
        console.error('Error starting live voice assistant:', err);
        setErrorMessage(
          err.name === 'NotAllowedError'
            ? 'Microphone permission was denied. Please allow microphone access in your browser.'
            : err.message || 'Microphone initialization failed.'
        );
        setAgentState('error');
      }
    }

    initAudioEngine();

    return () => {
      active = false;
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (_) {}
      }
      if (window.speechSynthesis) window.speechSynthesis.cancel();
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close().catch(() => {});
      }
    };
  }, [isMuted, processUserTurn]);

  // Toggle Mute
  const toggleMute = () => {
    if (streamRef.current) {
      streamRef.current.getAudioTracks().forEach((track) => {
        track.enabled = isMuted;
      });
      setIsMuted(!isMuted);
      if (!isMuted) {
        setStatusMessage('Microphone muted.');
      } else {
        setStatusMessage('Listening... speak whenever you are ready.');
      }
    }
  };

  // Immediate send trigger
  const handleImmediateSend = () => {
    const textToSend = latestTranscriptRef.current || interimTranscriptRef.current || manualInput;
    if (textToSend.trim()) {
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      setManualInput('');
      processUserTurn(textToSend.trim());
    }
  };

  return (
    <div className="live-voice-window animate-fade-in">
      {/* Top Header */}
      <div className="voice-agent-header">
        <div className="voice-header-brand">
          <div className="voice-pulse-indicator">
            <span className={`pulse-orb ${agentState}`}></span>
          </div>
          <div>
            <div className="voice-title">Azentio Live Voice Agent</div>
            <div className="voice-sub">Speech-to-Speech • 400ms Response • Speaker Output</div>
          </div>
        </div>

        <div className="voice-header-actions">
          {/* Speaker Mute/Unmute Toggle */}
          <button
            type="button"
            className={`btn-voice-control ${!isSpeakerEnabled ? 'active-muted' : ''}`}
            onClick={() => {
              const nextState = !isSpeakerEnabled;
              setIsSpeakerEnabled(nextState);
              if (!nextState && window.speechSynthesis) {
                window.speechSynthesis.cancel();
              }
            }}
            title={isSpeakerEnabled ? 'Mute speaker voice' : 'Enable speaker voice'}
          >
            <span>{isSpeakerEnabled ? '🔊 Speaker: ON' : '🔇 Speaker: OFF'}</span>
          </button>

          <button
            type="button"
            className="btn-switch-chat"
            onClick={onSwitchToChat}
            title="Switch to text chat mode"
          >
            💬 Text Chat
          </button>
          <button
            type="button"
            className="btn-close-voice"
            onClick={handleEndSession}
            title="End voice session"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Authentication Mode Status Bar */}
      {user ? (
        <div className="voice-auth-status-bar authenticated">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <span className="auth-status-dot green"></span>
            <span className="auth-status-label">
              Signed in: <strong>{user.full_name}</strong> ({user.email})
            </span>
          </div>
          <span className="auth-account-badge">A/C: {user.account_number}</span>
        </div>
      ) : (
        <div className="voice-auth-status-bar guest">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <span className="auth-status-dot amber"></span>
            <span className="auth-status-label">
              Guest Visitor Mode: <strong>General FAQs Only</strong>
            </span>
          </div>
          {onOpenAuth && (
            <button
              type="button"
              className="btn-quick-signin-pill"
              onClick={() => onOpenAuth('login')}
            >
              🔑 Sign In
            </button>
          )}
        </div>
      )}

      {/* Central Visualizer & Status Area */}
      <div className="voice-visualizer-stage">
        {/* Animated Voice Orb */}
        <div className="voice-orb-container">
          <div
            className={`voice-orb ${agentState}`}
            style={{
              transform: `scale(${1 + (agentState === 'user_speaking' ? liveVolume / 140 : 0.05)})`,
            }}
          >
            <div className="orb-core">
              <span className="orb-icon">
                {agentState === 'user_speaking' && '🎙️'}
                {agentState === 'assistant_speaking' && '🔊'}
                {agentState === 'processing' && '⏳'}
                {agentState === 'listening' && '🟢'}
                {agentState === 'muted' && '🔇'}
                {agentState === 'error' && '⚠️'}
                {agentState === 'connecting' && '🔄'}
              </span>
            </div>
            <div className="orb-halo halo-1"></div>
            <div className="orb-halo halo-2"></div>
            <div className="orb-halo halo-3"></div>
          </div>
        </div>

        {/* Dynamic Status Badge */}
        <div className={`voice-status-pill pill-${agentState}`}>
          <span className="status-blink-dot"></span>
          <span>{statusMessage}</span>
        </div>

        {/* Dynamic VAD Equalizer bars */}
        <div className="voice-eq-strip">
          {[...Array(16)].map((_, i) => {
            const barHeight =
              agentState === 'user_speaking'
                ? Math.max(6, Math.min(36, Math.round((liveVolume * ((i % 4) + 1)) / 4)))
                : agentState === 'assistant_speaking'
                ? Math.max(6, ((i % 3) + 1) * 7)
                : 6;
            return (
              <span
                key={i}
                className="eq-bar"
                style={{ height: `${barHeight}px` }}
              ></span>
            );
          })}
        </div>
      </div>

      {/* Live Transcript Stream */}
      <div className="voice-transcripts-box" ref={transcriptContainerRef}>
        <div className="transcript-hint">
          <span>💡 Hands-free mode: speak naturally. Tap <strong>🔊 Listen</strong> on any message to hear it aloud through your speakers.</span>
        </div>

        {transcripts.map((item) => (
          <div
            key={item.id}
            className={`voice-log-row ${item.sender === 'user' ? 'log-user' : 'log-bot'}`}
          >
            <span className="log-sender-tag">
              {item.sender === 'user' ? 'You' : 'Azentio Voice'}
            </span>
            <div className="log-bubble">
              <p>{item.text}</p>
              {item.sender === 'assistant' && (
                <div className="voice-bubble-actions-row">
                  <button
                    type="button"
                    className={`btn-replay-speaker ${playingBubbleId === item.id ? 'speaker-playing' : ''}`}
                    onClick={() => speakText(item.text, null, item.id)}
                    title="Play this message through your speaker"
                  >
                    <span>{playingBubbleId === item.id ? '🔊 Speaking...' : '🔊 Listen'}</span>
                  </button>

                  {!user && (item.requiresLogin || item.text.includes('please log in')) && onOpenAuth && (
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
            </div>
            <span className="log-time">{item.time}</span>
          </div>
        ))}

        {errorMessage && (
          <div className="voice-error-box">
            <strong>Error:</strong> {errorMessage}
          </div>
        )}
      </div>

      {/* Quick Input & Immediate Send Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleImmediateSend();
        }}
        className="voice-inline-input-bar"
      >
        <input
          type="text"
          placeholder="Speak or type a banking question..."
          value={manualInput}
          onChange={(e) => setManualInput(e.target.value)}
          disabled={agentState === 'processing'}
        />
        <button
          type="submit"
          className="btn-voice-send"
          disabled={(!manualInput.trim() && !latestTranscriptRef.current && !interimTranscriptRef.current) || agentState === 'processing'}
        >
          ⚡ Send Now
        </button>
      </form>

      {/* Controls Bar */}
      <div className="voice-controls-bar">
        <button
          type="button"
          className={`btn-voice-control ${isMuted ? 'active-muted' : ''}`}
          onClick={toggleMute}
          title={isMuted ? 'Unmute microphone' : 'Mute microphone'}
        >
          <span>{isMuted ? '🔇 Unmute Mic' : '🎙️ Mic Active'}</span>
        </button>

        {/* Dedicated Test Speaker Button */}
        <button
          type="button"
          className="btn-voice-control btn-test-speaker"
          onClick={() => {
            speakText("Speaker test successful. Audio output is loud and clear. How can I assist you today?");
          }}
          title="Test your audio speaker output"
        >
          <span>🔊 Test Speaker</span>
        </button>

        <button
          type="button"
          className="btn-voice-control btn-end-call"
          onClick={handleEndSession}
        >
          <span>⏹️ End Voice Session</span>
        </button>
      </div>

      {/* Secure footer */}
      <div className="voice-footer-secure">
        <span>🛡️ Real-time Speech-to-Speech Channel • Interactive Speaker Playback • Grounded Banking Assistance</span>
      </div>
    </div>
  );
}

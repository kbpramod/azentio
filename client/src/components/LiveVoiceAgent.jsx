import React, { useState, useEffect, useRef, useCallback } from 'react';
import { agentApi, describeTurn } from '../services/api';

export default function LiveVoiceAgent({ user, onSwitchToChat, onClose }) {
  // Agent states: 'connecting' | 'listening' | 'user_speaking' | 'processing' | 'assistant_speaking' | 'muted' | 'error'
  const [agentState, setAgentState] = useState('connecting');
  const [liveVolume, setLiveVolume] = useState(0); // 0 to 100 for visualizer
  const [transcripts, setTranscripts] = useState([
    {
      id: 'init-1',
      sender: 'assistant',
      text: "I am listening. Speak naturally, and I will respond once you finish.",
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [statusMessage, setStatusMessage] = useState('Connecting to live audio stream...');
  const [isMuted, setIsMuted] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  // Audio & VAD references
  const streamRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const animFrameRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const silenceTimerRef = useRef(null);
  const isSpeakingRef = useRef(false);
  const isAssistantSpeakingRef = useRef(false);
  const recognitionRef = useRef(null);
  const transcriptContainerRef = useRef(null);

  // Configuration constants
  const SPEECH_THRESHOLD = 18; // Audio RMS volume threshold to trigger speech
  const SILENCE_DURATION_MS = 1400; // Silence time before concluding user has stopped talking
  const MIN_SPEECH_DURATION_MS = 600; // Minimum duration to consider real speech

  const speechStartTimeRef = useRef(0);

  // Auto-scroll transcript log
  useEffect(() => {
    if (transcriptContainerRef.current) {
      transcriptContainerRef.current.scrollTop = transcriptContainerRef.current.scrollHeight;
    }
  }, [transcripts]);

  // Text-To-Speech Output
  const speakText = useCallback((text, onFinishCallback) => {
    if (!('speechSynthesis' in window)) {
      if (onFinishCallback) onFinishCallback();
      return;
    }

    // Stop any existing speech
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Pick a natural English voice if available
    const voices = window.speechSynthesis.getVoices();
    const naturalVoice = voices.find(
      (v) =>
        v.lang.startsWith('en') &&
        (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Zira') || v.name.includes('Samantha'))
    ) || voices.find((v) => v.lang.startsWith('en'));

    if (naturalVoice) utterance.voice = naturalVoice;

    isAssistantSpeakingRef.current = true;
    setAgentState('assistant_speaking');
    setStatusMessage('Azentio Assistant speaking...');

    utterance.onend = () => {
      isAssistantSpeakingRef.current = false;
      if (onFinishCallback) onFinishCallback();
    };

    utterance.onerror = (e) => {
      console.warn('Speech synthesis error or interrupt:', e);
      isAssistantSpeakingRef.current = false;
      if (onFinishCallback) onFinishCallback();
    };

    window.speechSynthesis.speak(utterance);
  }, []);

  // Send captured voice note to backend
  const sendVoiceToBackend = useCallback(async (blob) => {
    setAgentState('processing');
    setStatusMessage('Transmitting audio & processing...');

    const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    try {
      // server -> AI service: speech-to-text, understanding, banking lookup, grounded reply
      const result = await agentApi.sendVoice(blob);
      const responseText = result.reply_text;

      setTranscripts((prev) => [
        ...prev,
        ...(result.transcript
          ? [{ id: 'user-' + Date.now(), sender: 'user', text: result.transcript, time: nowTime }]
          : []),
        {
          id: 'bot-' + Date.now(),
          sender: 'assistant',
          text: `${responseText}${describeTurn(result)}`,
          time: nowTime,
        },
      ]);

      // Speak response out loud, then return to listening
      speakText(responseText, () => {
        setAgentState('listening');
        setStatusMessage('Listening to you... (speak naturally)');
        isSpeakingRef.current = false;
      });
    } catch (err) {
      console.error('Failed to send voice to backend:', err);
      const errReply = "Sorry, I couldn't process that just now. Please try again, or switch to chat.";
      speakText(errReply, () => {
        setAgentState('listening');
        setStatusMessage('Listening to you...');
        isSpeakingRef.current = false;
      });
    }
  }, [speakText]);

  // Stop recording user speech and finalize utterance
  const finalizeUtterance = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  }, []);

  // Start a fresh recording slice
  const startUtteranceRecording = useCallback(() => {
    if (!streamRef.current) return;
    audioChunksRef.current = [];

    try {
      const options = { mimeType: 'audio/webm;codecs=opus' };
      let recorder;
      if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(options.mimeType)) {
        recorder = new MediaRecorder(streamRef.current, options);
      } else {
        recorder = new MediaRecorder(streamRef.current);
      }

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const mimeType = recorder.mimeType || 'audio/webm';
        const blob = new Blob(audioChunksRef.current, { type: mimeType });
        const speechDuration = Date.now() - speechStartTimeRef.current;

        // If speech was long enough to be a genuine question, send it to backend
        if (speechDuration >= MIN_SPEECH_DURATION_MS && blob.size > 1000) {
          sendVoiceToBackend(blob);
        } else {
          // False trigger or too short, resume listening
          setAgentState('listening');
          setStatusMessage('Listening to you...');
          isSpeakingRef.current = false;
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start(150);
      speechStartTimeRef.current = Date.now();
    } catch (err) {
      console.error('Could not initialize MediaRecorder:', err);
    }
  }, [sendVoiceToBackend]);

  // Main Audio & VAD loop
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

        if (!active) return;
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

        // Initialize Web Speech Recognition for live captions if available
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRec) {
          try {
            const recognition = new SpeechRec();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            recognition.onresult = (event) => {
              let currentTranscript = '';
              for (let i = event.resultIndex; i < event.results.length; i++) {
                currentTranscript += event.results[i][0].transcript;
              }
              if (currentTranscript.trim()) {
                // If assistant is speaking and user speaks, interrupt!
                if (isAssistantSpeakingRef.current) {
                  window.speechSynthesis.cancel();
                  isAssistantSpeakingRef.current = false;
                  setAgentState('user_speaking');
                  setStatusMessage('Listening to your interruption...');
                }
              }
            };

            recognition.onerror = () => {};
            recognition.onend = () => {
              if (active && !isMuted) {
                try { recognition.start(); } catch (_) {}
              }
            };

            recognition.start();
            recognitionRef.current = recognition;
          } catch (recErr) {
            console.log('Live captions not active:', recErr);
          }
        }

        // Real-time audio volume analysis & VAD processing
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const analyzeAudio = () => {
          if (!active) return;

          analyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < bufferLength; i++) {
            sum += dataArray[i];
          }
          const averageVolume = sum / bufferLength;
          setLiveVolume(Math.min(100, Math.round((averageVolume / 128) * 100)));

          // Check for Interruption (Barge-In) while assistant is speaking
          if (isAssistantSpeakingRef.current) {
            if (averageVolume > SPEECH_THRESHOLD + 6) {
              // User interrupted the assistant!
              console.log('User interruption detected! Halting assistant speech.');
              window.speechSynthesis.cancel();
              isAssistantSpeakingRef.current = false;
              isSpeakingRef.current = true;
              setAgentState('user_speaking');
              setStatusMessage('Interrupted. Listening to you...');
              startUtteranceRecording();
            }
            animFrameRef.current = requestAnimationFrame(analyzeAudio);
            return;
          }

          // If muted, skip VAD trigger
          if (isMuted) {
            animFrameRef.current = requestAnimationFrame(analyzeAudio);
            return;
          }

          // Normal VAD: Listening for User Speech
          if (averageVolume > SPEECH_THRESHOLD) {
            // Volume above threshold => User is speaking
            if (silenceTimerRef.current) {
              clearTimeout(silenceTimerRef.current);
              silenceTimerRef.current = null;
            }

            if (!isSpeakingRef.current) {
              isSpeakingRef.current = true;
              setAgentState('user_speaking');
              setStatusMessage('Listening... (detecting voice)');
              startUtteranceRecording();
            }
          } else {
            // Volume below threshold => Silence
            if (isSpeakingRef.current && !silenceTimerRef.current) {
              silenceTimerRef.current = setTimeout(() => {
                // User has paused long enough; conclude utterance and transmit
                console.log('Silence detected after speech. Finalizing utterance.');
                isSpeakingRef.current = false;
                silenceTimerRef.current = null;
                finalizeUtterance();
              }, SILENCE_DURATION_MS);
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
  }, [isMuted, startUtteranceRecording, finalizeUtterance]);

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
            <div className="voice-sub">Continuous Duplex • Automatic VAD</div>
          </div>
        </div>

        <div className="voice-header-actions">
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
            onClick={onClose}
            title="End voice session"
          >
            ✕
          </button>
        </div>
      </div>

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
                {agentState === 'assistant_speaking' && '🗣️'}
                {agentState === 'processing' && '⏳'}
                {agentState === 'listening' && '🟢'}
                {agentState === 'muted' && '🔇'}
                {agentState === 'error' && '⚠️'}
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
                ? Math.max(6, Math.min(36, Math.round((liveVolume * (i % 4 + 1)) / 4)))
                : agentState === 'assistant_speaking'
                ? Math.max(6, (i % 3 + 1) * 7)
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
          <span>💡 Hands-free mode: speak anytime. If the assistant is talking, you can interrupt and speak freely.</span>
        </div>

        {transcripts.map((item) => (
          <div
            key={item.id}
            className={`voice-log-row ${item.sender === 'user' ? 'log-user' : 'log-bot'}`}
          >
            <span className="log-sender-tag">
              {item.sender === 'user' ? 'You' : 'Azentio Voice'}
            </span>
            <div className="log-bubble">{item.text}</div>
            <span className="log-time">{item.time}</span>
          </div>
        ))}

        {errorMessage && (
          <div className="voice-error-box">
            <strong>Error:</strong> {errorMessage}
          </div>
        )}
      </div>

      {/* Controls Bar */}
      <div className="voice-controls-bar">
        <button
          type="button"
          className={`btn-voice-control ${isMuted ? 'active-muted' : ''}`}
          onClick={toggleMute}
          title={isMuted ? 'Unmute microphone' : 'Mute microphone'}
        >
          <span>{isMuted ? '🔇 Unmute' : '🎙️ Mute'}</span>
        </button>

        <button
          type="button"
          className="btn-voice-control btn-end-call"
          onClick={onClose}
        >
          <span>⏹️ End Voice Session</span>
        </button>
      </div>

      {/* Secure footer */}
      <div className="voice-footer-secure">
        <span>🛡️ Real-time Duplex Voice Channel • Automatic VAD Silence Routing</span>
      </div>
    </div>
  );
}


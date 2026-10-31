# Voice integration guide (for Member 3, frontend)

The frontend talks only to the server: `http://127.0.0.1:8000/api/v1`.
The server forwards to the AI service (port 8001), which does speech-to-text, understanding, banking lookups and the reply.

## Flow

1. `POST /sessions` → `{ session_id, reply_text }` — show and speak the greeting.
2. Each customer turn → `POST /sessions/{id}/turn`
   - **Voice:** `multipart/form-data` with field `audio` (any browser recording: webm/ogg/mp3/wav)
   - **Typed fallback:** JSON `{ "text": "..." }`
3. Show the response, speak `reply_text`, repeat.
4. "Talk to a human" button → `POST /sessions/{id}/escalate`. End button → `POST /sessions/{id}/end`.
5. Ops dashboard: `GET /sessions` (list) and `GET /sessions/{id}` (turns, tickets, escalation, audit trace).

## Turn response fields to display

| Field | Show as |
|---|---|
| `transcript` | What the customer said (live transcript) |
| `stt_confidence` | Optional; low values mean the agent will ask them to repeat |
| `intents[].name` | Intent chips |
| `verified` | Lock icon: "Verified" / "Not verified" |
| `state` | Status: GREET, IDENTIFY, VERIFY, ACT, CLARIFY, ESCALATED, LOCKED, CLOSED |
| `reply_text` | Agent bubble + speak it |
| `reply_audio_url` | If not null, play this mp3 instead of browser speech |
| `sources[]` | Small tag under the answer, e.g. "Source: LOS (simulated)" |
| `tickets[]` | Ticket card with `ticket_id` (SR-… / CMP-…) |
| `escalation` | Handoff card: `reason`, `priority`, `summary` |

## Recording + sending audio (React)

```js
const API = "http://127.0.0.1:8000/api/v1";

// hold-to-talk: call start() on press, stop() on release
let recorder, chunks = [];
export async function start() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true }); // needs mic permission
  recorder = new MediaRecorder(stream);
  chunks = [];
  recorder.ondataavailable = (e) => chunks.push(e.data);
  recorder.start();
}

export function stop(sessionId) {
  return new Promise((resolve) => {
    recorder.onstop = async () => {
      recorder.stream.getTracks().forEach((t) => t.stop());
      const form = new FormData();
      form.append("audio", new Blob(chunks, { type: recorder.mimeType }), "turn.webm");
      const res = await fetch(`${API}/sessions/${sessionId}/turn`, { method: "POST", body: form });
      resolve(await res.json());
    };
    recorder.stop();
  });
}

export function speak(turn) {
  if (turn.reply_audio_url) return new Audio(`http://127.0.0.1:8001${turn.reply_audio_url}`).play();
  window.speechSynthesis.cancel();                       // stop any previous reply
  const u = new SpeechSynthesisUtterance(turn.reply_text);
  u.lang = "en-IN";
  window.speechSynthesis.speak(u);
}
```

## States to design for

- **Thinking:** a voice turn takes about 4–8 s today (speech-to-text ~2 s + database). Show a spinner.
- **Mic blocked:** `getUserMedia` throws → show "Allow microphone access, or type your question."
- **Errors:** body `{ "detail": { "error": { "code", "message", "retryable" } } }`. Code `AI_UNAVAILABLE` (503) means the AI service on port 8001 is not running.
- **Low confidence:** the agent itself replies "Sorry, I didn't catch that…" — just show it.
- Keep a **typed input** box always visible as a fallback.

import { useState, useRef, useEffect } from "react";
import "./ChatWidget.css";

function buildContext(vessels, heatmapPoints) {
  const flagged = (vessels || []).filter(v => v.status !== "Compliant");
  const compliant = (vessels || []).filter(v => v.status === "Compliant");

  const vesselLines = flagged.map(v =>
    `- ${v.name} (IMO ${v.imo}): ${v.status} at ${Number(v.point?.lat ?? v.lat).toFixed(3)}°N, ${Number(v.point?.lon ?? v.lon).toFixed(3)}°E`
  ).join("\n");

  const topZones = (heatmapPoints || [])
    .sort((a, b) => b[2] - a[2])
    .slice(0, 5)
    .map(p => `  Lat ${p[0].toFixed(3)}°N, Lon ${p[1].toFixed(3)}°E (intensity ${(p[2] * 100).toFixed(0)}%)`)
    .join("\n");

  return [
    `Flagged vessels (${flagged.length}):`,
    vesselLines || "  None",
    "",
    `Compliant vessels: ${compliant.length}`,
    "",
    topZones ? `Top danger zones (heatmap hotspots):\n${topZones}` : "No active heatmap zones.",
  ].join("\n");
}

const WELCOME = {
  role: "assistant",
  text: "Popeye Advisor online. I have real-time threat intelligence from this sector. Ask me about safe routes, flagged vessels, or danger zones.",
};

export default function ChatWidget({ vessels = [], heatmapPoints = [] }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send() {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setMessages(prev => [...prev, { role: "user", text }]);
    setLoading(true);

    const context = buildContext(vessels, heatmapPoints);

    try {
      const res = await fetch("/api/v1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, context }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, {
        role: "assistant",
        text: data.response || "No advisory returned.",
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role: "assistant",
        text: "Connection error — is the backend running?",
      }]);
    } finally {
      setLoading(false);
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div className="chat-widget">
      {open && (
        <div className="chat-panel">
          <div className="chat-header">
            <div className="chat-header-left">
              <div className="chat-status-dot" />
              <div className="chat-header-title">
                <strong>Popeye</strong>
                <span>Navigation Advisor</span>
              </div>
            </div>
            <button className="chat-close-btn" onClick={() => setOpen(false)}>×</button>
          </div>

          <div className="chat-messages">
            {messages.map((m, i) => (
              <div key={i} className={`chat-message ${m.role}`}>
                <span className="chat-label">{m.role === "user" ? "You" : "Advisor"}</span>
                <div className="chat-bubble">{m.text}</div>
              </div>
            ))}
            {loading && (
              <div className="chat-message assistant">
                <span className="chat-label">Advisor</span>
                <div className="chat-typing">
                  <span /><span /><span />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="chat-footer">
            <textarea
              className="chat-input"
              rows={1}
              placeholder="Ask about safe routes, threats…"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              disabled={loading}
            />
            <button className="chat-send-btn" onClick={send} disabled={!input.trim() || loading}>
              <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16" style={{ color: "#fff" }}>
                <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
              </svg>
            </button>
          </div>
        </div>
      )}

      <button className="chat-toggle-btn" onClick={() => setOpen(o => !o)} title="Popeye Advisor">
        {open ? (
          <svg viewBox="0 0 20 20" fill="currentColor" width="20" height="20" style={{ color: "#fff" }}>
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        ) : (
          <svg viewBox="0 0 20 20" fill="currentColor" width="20" height="20" style={{ color: "#fff" }}>
            <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
          </svg>
        )}
      </button>
    </div>
  );
}

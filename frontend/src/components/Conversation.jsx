import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { formatFull, formatPhone, formatTime, windowOpen } from "../format.js";
import StatusBadge from "./StatusBadge.jsx";

export default function Conversation({ phone, messages, onSent, onBack, onOpenTemplate }) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  // messages arrive newest-first; show oldest at the top like a chat
  const ordered = [...messages].reverse();
  const name = messages.find((m) => m.contact_name)?.contact_name;
  const open = windowOpen(messages);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, phone]);

  useEffect(() => {
    setError("");
    setText("");
  }, [phone]);

  async function send(e) {
    e.preventDefault();
    if (!text.trim() || sending) return;
    setSending(true);
    setError("");
    try {
      await api.sendText(phone, text.trim());
      setText("");
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
      onSent();
    }
  }

  return (
    <section className="chat">
      <header className="chat-head">
        <button className="back" onClick={onBack} aria-label="Back to chats">‹</button>
        <span className="avatar">{(name || phone).slice(0, 1).toUpperCase()}</span>
        <div className="chat-title">
          <strong>{name || formatPhone(phone)}</strong>
          {name && <span className="muted">{formatPhone(phone)}</span>}
        </div>
        <span className={`window ${open ? "open" : "closed"}`}>
          {open ? "24h window open" : "Window closed"}
        </span>
      </header>

      <div className="chat-body">
        {ordered.map((m) => (
          <div key={m.id} className={`bubble-row ${m.direction}`}>
            <div className={`bubble ${m.direction} ${m.status === "failed" ? "failed" : ""}`}>
              {m.msg_type === "template" && <span className="tag">Template</span>}
              <p>{m.body}</p>
              <span className="meta" title={formatFull(m.created_at)}>
                {formatTime(m.created_at)}
                {m.direction === "outgoing" && <StatusBadge status={m.status} title={m.error_message} />}
              </span>
              {m.status === "failed" && m.error_message && (
                <span className="err">Error {m.error_code}: {m.error_message}</span>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {!open && (
        <div className="notice">
          Free-form messages only reach customers who messaged you in the last 24 hours.{" "}
          <button className="link" onClick={() => onOpenTemplate(phone)}>Send a template instead</button>
        </div>
      )}
      {error && <div className="alert error">{error}</div>}

      <form className="composer" onSubmit={send}>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Type a message"
          aria-label="Message"
          maxLength={4096}
        />
        <button className="btn" disabled={sending || !text.trim()}>
          {sending ? "Sending…" : "Send"}
        </button>
      </form>
    </section>
  );
}

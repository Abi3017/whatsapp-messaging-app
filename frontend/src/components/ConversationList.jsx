import { formatPhone, formatTime } from "../format.js";
import StatusBadge from "./StatusBadge.jsx";

export default function ConversationList({ conversations, selected, onSelect, onNew }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-head">
        <h2>Chats</h2>
        <button className="btn btn-small" onClick={onNew}>+ New</button>
      </div>
      {conversations.length === 0 ? (
        <p className="empty">
          No conversations yet. Send a message from your phone to the test number, or start one with <b>+ New</b>.
        </p>
      ) : (
        <ul className="conv-list">
          {conversations.map((c) => (
            <li key={c.phone}>
              <button
                className={`conv ${selected === c.phone ? "active" : ""}`}
                onClick={() => onSelect(c.phone)}
              >
                <span className="avatar">{(c.contact_name || c.phone).slice(0, 1).toUpperCase()}</span>
                <span className="conv-main">
                  <span className="conv-top">
                    <span className="conv-name">{c.contact_name || formatPhone(c.phone)}</span>
                    <span className="conv-time">{formatTime(c.created_at)}</span>
                  </span>
                  <span className="conv-preview">
                    {c.direction === "outgoing" && <StatusBadge status={c.status} />}
                    <span className="truncate">{c.body}</span>
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}

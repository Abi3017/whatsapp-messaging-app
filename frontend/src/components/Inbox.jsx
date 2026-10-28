import { formatFull, formatPhone } from "../format.js";
import StatusBadge from "./StatusBadge.jsx";

// Every incoming and outgoing message, newest first.
export default function Inbox({ messages, onOpen }) {
  return (
    <section className="panel wide">
      <h2>All messages</h2>
      <p className="muted">Incoming and outgoing messages, latest first. Updates automatically.</p>
      {messages.length === 0 ? (
        <p className="empty">No messages yet.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Direction</th>
                <th>Phone</th>
                <th>Message</th>
                <th>Time</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {messages.map((m) => (
                <tr key={m.id} onClick={() => onOpen(m.phone)}>
                  <td data-label="Direction">
                    <span className={`dir dir-${m.direction}`}>{m.direction === "incoming" ? "In" : "Out"}</span>
                  </td>
                  <td data-label="Phone">{formatPhone(m.phone)}</td>
                  <td data-label="Message" className="msg-cell">
                    {m.body}
                    {m.status === "failed" && m.error_message && (
                      <span className="err">Error {m.error_code}: {m.error_message}</span>
                    )}
                  </td>
                  <td data-label="Time">{formatFull(m.created_at)}</td>
                  <td data-label="Status"><StatusBadge status={m.status} variant="pill" title={m.error_message} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

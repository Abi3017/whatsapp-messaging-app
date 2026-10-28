// sent ✓ · delivered ✓✓ · read ✓✓ (blue) · failed ! · received (incoming)
const LABELS = {
  received: "Received",
  sent: "Sent",
  delivered: "Delivered",
  read: "Read",
  failed: "Failed",
};

function Ticks({ double }) {
  return (
    <svg width={double ? 16 : 11} height="11" viewBox={double ? "0 0 16 11" : "0 0 11 11"} aria-hidden="true">
      <path d="M1 6l3 3 6-7" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      {double && (
        <path d="M6 9l1 0 6-7" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      )}
    </svg>
  );
}

export default function StatusBadge({ status, variant = "icon", title }) {
  const label = LABELS[status] || status;
  if (variant === "pill") {
    return <span className={`pill pill-${status}`} title={title}>{label}</span>;
  }
  if (status === "received") return null;
  return (
    <span className={`ticks ticks-${status}`} title={title || label} aria-label={label}>
      {status === "failed" ? "!" : <Ticks double={status === "delivered" || status === "read"} />}
    </span>
  );
}

export function formatPhone(phone) {
  if (!phone) return "";
  // 919876543210 -> +91 98765 43210 (Indian numbers); others just get a +
  if (phone.length === 12 && phone.startsWith("91")) {
    return `+91 ${phone.slice(2, 7)} ${phone.slice(7)}`;
  }
  return `+${phone}`;
}

export function formatTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const today = new Date();
  const sameDay = d.toDateString() === today.toDateString();
  const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return sameDay ? time : `${d.toLocaleDateString([], { day: "numeric", month: "short" })}, ${time}`;
}

export function formatFull(iso) {
  return iso ? new Date(iso).toLocaleString() : "";
}

// The 24-hour customer service window is open if the customer messaged us in the last 24h.
export function windowOpen(messages) {
  const lastIncoming = messages.find((m) => m.direction === "incoming");
  if (!lastIncoming) return false;
  return Date.now() - new Date(lastIncoming.created_at).getTime() < 24 * 60 * 60 * 1000;
}

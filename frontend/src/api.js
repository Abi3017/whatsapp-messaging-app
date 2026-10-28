// All calls to our Flask backend. The browser never talks to Meta directly,
// so the access token is never exposed to the frontend.

// Empty = same origin (Vite proxy in dev, Flask serves the build in production).
const BASE = import.meta.env.VITE_API_BASE || "";

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new Error("Cannot reach the backend. Is Flask running on port 5000?");
  }
  let data = null;
  try {
    data = await response.json();
  } catch {
    // non-JSON error page
  }
  if (!response.ok) {
    throw new Error(data?.error_message || `Request failed (${response.status})`);
  }
  return data;
}

export const api = {
  health: () => request("/api/health"),
  conversations: () => request("/api/conversations"),
  messages: (phone) => request(`/api/messages${phone ? `?phone=${encodeURIComponent(phone)}` : ""}`),
  templates: () => request("/api/templates"),
  sendText: (to, text) =>
    request("/api/send-text", { method: "POST", body: JSON.stringify({ to, text }) }),
  sendTemplate: (payload) =>
    request("/api/send-template", { method: "POST", body: JSON.stringify(payload) }),
};

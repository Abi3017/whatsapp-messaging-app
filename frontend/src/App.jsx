import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import Conversation from "./components/Conversation.jsx";
import ConversationList from "./components/ConversationList.jsx";
import Inbox from "./components/Inbox.jsx";
import SendTemplate from "./components/SendTemplate.jsx";

const POLL_MS = 3000; // refresh every 3 seconds so new messages and statuses appear

export default function App() {
  const [view, setView] = useState("chats"); // chats | inbox | template
  const [messages, setMessages] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [selected, setSelected] = useState(null);
  const [templatePhone, setTemplatePhone] = useState("");
  const [health, setHealth] = useState(null);
  const [connError, setConnError] = useState("");

  const refresh = useCallback(async () => {
    try {
      const [msgs, convs] = await Promise.all([api.messages(), api.conversations()]);
      setMessages(msgs);
      setConversations(convs);
      setConnError("");
    } catch (err) {
      setConnError(err.message);
    }
  }, []);

  useEffect(() => {
    api.health().then(setHealth).catch(() => {});
    refresh();
    const id = setInterval(refresh, POLL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  function openChat(phone) {
    setSelected(phone);
    setView("chats");
  }

  function openTemplate(phone) {
    setTemplatePhone(phone || "");
    setView("template");
  }

  function afterTemplateSent(phone) {
    refresh();
    if (phone) setTimeout(() => openChat(phone.replace(/\D/g, "").replace(/^0+/, "")), 600);
  }

  const chatMessages = selected ? messages.filter((m) => m.phone === selected) : [];

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="18" height="18"><path fill="currentColor" d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm5.3 14.1c-.2.6-1.3 1.2-1.8 1.3-.5.1-1 .1-3.3-.8-2.8-1.1-4.6-4-4.7-4.2-.1-.2-1.1-1.5-1.1-2.9s.7-2 1-2.3c.2-.3.5-.3.7-.3h.5c.2 0 .4 0 .6.5l.8 2c.1.2.1.4 0 .5l-.3.5-.4.4c-.1.1-.3.3-.1.6.2.3.8 1.3 1.7 2.1 1.2 1 2.1 1.3 2.4 1.5.3.1.5.1.6-.1l.9-1.1c.2-.3.4-.2.6-.1l1.9.9c.3.1.5.2.5.3.1.2.1.7-.1 1.4Z"/></svg>
          </span>
          <span>WhatsApp Dashboard</span>
        </div>
        <nav className="tabs" aria-label="Views">
          <button className={view === "chats" ? "active" : ""} onClick={() => setView("chats")}>Chats</button>
          <button className={view === "inbox" ? "active" : ""} onClick={() => setView("inbox")}>All messages</button>
          <button className={view === "template" ? "active" : ""} onClick={() => openTemplate("")}>Send template</button>
        </nav>
      </header>

      {health && !health.ok && (
        <div className="alert warn banner">
          Backend is missing: {health.missing_settings.join(", ")}. Add them to backend/.env and restart Flask.
        </div>
      )}
      {connError && <div className="alert error banner">{connError}</div>}

      <main className={`main view-${view} ${selected ? "has-chat" : ""}`}>
        {view === "chats" && (
          <div className="chats">
            <ConversationList
              conversations={conversations}
              selected={selected}
              onSelect={setSelected}
              onNew={() => openTemplate("")}
            />
            {selected ? (
              <Conversation
                phone={selected}
                messages={chatMessages}
                onSent={refresh}
                onBack={() => setSelected(null)}
                onOpenTemplate={openTemplate}
              />
            ) : (
              <section className="chat placeholder">
                <p>Select a chat to view messages and reply.</p>
              </section>
            )}
          </div>
        )}
        {view === "inbox" && <Inbox messages={messages} onOpen={openChat} />}
        {view === "template" && <SendTemplate initialPhone={templatePhone} onSent={afterTemplateSent} />}
      </main>
    </div>
  );
}

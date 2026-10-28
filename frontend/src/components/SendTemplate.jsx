import { useEffect, useState } from "react";
import { api } from "../api.js";

// Used when the Meta template list can't be loaded (e.g. WABA ID not set)
const FALLBACK_TEMPLATES = [
  { name: "hello_world", language: "en_US", body: "Hello World", param_count: 0 },
];

export default function SendTemplate({ initialPhone = "", onSent }) {
  const [templates, setTemplates] = useState([]);
  const [loadNote, setLoadNote] = useState("");
  const [to, setTo] = useState(initialPhone);
  const [selected, setSelected] = useState("");
  const [params, setParams] = useState([]);
  const [result, setResult] = useState(null);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    api.templates()
      .then((data) => {
        const list = data.templates?.length ? data.templates : FALLBACK_TEMPLATES;
        if (!data.ok) setLoadNote(`Couldn't load templates from Meta (${data.error_message}). Showing hello_world only.`);
        setTemplates(list);
        setSelected(list[0].name);
      })
      .catch((err) => {
        setLoadNote(err.message);
        setTemplates(FALLBACK_TEMPLATES);
        setSelected("hello_world");
      });
  }, []);

  useEffect(() => setTo(initialPhone), [initialPhone]);

  const template = templates.find((t) => t.name === selected);

  useEffect(() => {
    setParams(Array(template?.param_count || 0).fill(""));
  }, [selected, template?.param_count]);

  const preview = (template?.body || "").replace(/\{\{(\d+)\}\}/g, (m, n) => params[n - 1] || m);

  async function submit(e) {
    e.preventDefault();
    setSending(true);
    setResult(null);
    try {
      const data = await api.sendTemplate({
        to, template: template.name, language: template.language, params, body: template.body,
      });
      setResult({ ok: true, text: `Sent! Message ID: ${data.wamid}` });
      onSent(to);
    } catch (err) {
      setResult({ ok: false, text: err.message });
      onSent(null);
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="panel">
      <h2>Send a template message</h2>
      <p className="muted">
        Templates are pre-approved by Meta and can be sent any time, even outside the 24-hour window.
      </p>
      {loadNote && <div className="alert warn">{loadNote}</div>}

      <form className="form" onSubmit={submit}>
        <label>
          Recipient phone number
          <input
            value={to}
            onChange={(e) => setTo(e.target.value)}
            placeholder="919876543210 (country code + number)"
            required
          />
          <span className="hint">The Meta test number can only message numbers in your allowed list.</span>
        </label>

        <label>
          Template
          <select value={selected} onChange={(e) => setSelected(e.target.value)}>
            {templates.map((t) => (
              <option key={`${t.name}-${t.language}`} value={t.name}>
                {t.name} ({t.language})
              </option>
            ))}
          </select>
        </label>

        {params.map((value, i) => (
          <label key={i}>
            Variable {`{{${i + 1}}}`}
            <input
              value={value}
              onChange={(e) => setParams(params.map((p, j) => (j === i ? e.target.value : p)))}
              required
            />
          </label>
        ))}

        {template && (
          <div className="preview">
            <span className="hint">Preview</span>
            <p>{preview}</p>
          </div>
        )}

        <button className="btn" disabled={sending || !template}>
          {sending ? "Sending…" : "Send template"}
        </button>
      </form>

      {result && <div className={`alert ${result.ok ? "success" : "error"}`}>{result.text}</div>}
    </section>
  );
}

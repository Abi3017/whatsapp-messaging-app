# WhatsApp Messaging App

A small web application built on the **Meta WhatsApp Cloud API**. It sends template and text
messages, receives customer messages through a webhook, replies automatically based on keywords,
and shows every message with its live delivery status in a dashboard.

Built for the Unntangle Developer Intern technical assessment.

- **Live app:** `https://<your-app>.onrender.com` *(add after deploying)*
- **Webhook URL:** `https://<your-app>.onrender.com/webhook`

---

## Features

| Feature | Status |
|---|---|
| Secure configuration via environment variables, `.env.example` provided | ✅ Done |
| Send an approved template (choose template, fill `{{1}}`, `{{2}}`, live preview) | ✅ Done |
| Send free-form text replies from a chat view (inside the 24-hour window) | ✅ Done |
| Webhook verification (`GET /webhook`) | ✅ Done |
| Receive incoming messages and status updates (`POST /webhook`), stored in the DB | ✅ Done |
| Webhook signature check (`X-Hub-Signature-256` with the App Secret) | ✅ Done |
| Keyword auto-reply: `hi`, `price`, `hours` + fallback reply | ✅ Done |
| Inbox of all messages (phone, text, time, status), newest first, auto-refresh | ✅ Done |
| Status tracking: sent → delivered → read / failed (with Meta's error reason) | ✅ Done |
| Error handling: invalid numbers, expired token, network errors, unexpected payloads | ✅ Done |
| Responsive UI (desktop and mobile) | ✅ Done |
| Automated tests (27 backend tests, Meta API mocked) | ✅ Done |

**Not included / known limits**
- Media messages (images, documents) are stored as `[image message]` placeholders; their content is not downloaded.
- The dashboard refreshes by polling every 3 seconds rather than WebSockets.
- There is no login; the dashboard is meant for a single operator during the demo.
- WhatsApp formatting like `*bold*` shows as plain text in the dashboard (it renders as bold on the phone).
- The Meta test number can only message up to 5 numbers added to its allowed list.

---

## Architecture

```
 Browser (React)  ──/api/*──▶  Flask backend  ──HTTPS + token──▶  Meta Cloud API  ──▶  Customer's WhatsApp
                               │        ▲                                │
                               ▼        └────────── POST /webhook ───────┘
                          Database                (messages + status updates)
                 (SQLite local / Postgres prod)
```

- The **browser never talks to Meta**. Only the backend holds the access token, so it can't leak
  through the frontend.
- **One webhook endpoint, two kinds of events:** `value.messages` = a customer wrote to us,
  `value.statuses` = an update on a message we sent.
- **Fast webhook responses:** the backend stores the event and returns `200` immediately; the
  auto-reply is sent in a background thread. Meta retries slow webhooks, and stored message IDs
  (`wamid`, unique in the DB) make sure a retry never creates a duplicate or a second auto-reply.
- **Statuses only move forward.** Webhooks can arrive out of order (e.g. `read` before
  `delivered`), so a status is never downgraded.

### Send flow
1. User fills the form → `POST /api/send-template`.
2. Backend validates the phone number, calls `POST /{PHONE_NUMBER_ID}/messages`.
3. Meta returns a `wamid`; the message is stored with status `sent` (or `failed` with the error).
4. Meta later posts `delivered` / `read` / `failed` to `/webhook`, matched by `wamid`.

### Receive flow
1. Customer sends "price?" → Meta posts it to `/webhook` (opens the 24-hour window).
2. Backend verifies the signature, stores the message, returns `200`.
3. `auto_reply.py` picks the reply by keyword; it's sent as a free-form text (allowed inside the window).

### Project structure

```
whatsapp-messaging-app/
├── backend/
│   ├── app.py              # Flask routes: dashboard API + Meta webhook; serves the built frontend
│   ├── config.py           # reads environment variables (secrets never logged)
│   ├── db.py               # SQLAlchemy table + queries (SQLite or Postgres)
│   ├── whatsapp.py         # every call to Meta: send text, send template, list templates
│   ├── auto_reply.py       # keyword → reply rules (edit here to add keywords)
│   ├── requirements.txt
│   ├── .env.example
│   └── tests/              # pytest suite + mock Meta server for local end-to-end testing
├── frontend/
│   ├── src/App.jsx         # tabs, polling, layout
│   ├── src/api.js          # all fetch calls to the backend
│   └── src/components/     # ConversationList, Conversation, Inbox, SendTemplate, StatusBadge
├── docs/screenshots/
├── render.yaml             # one-click Render deployment
└── README.md
```

### API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Which required settings are missing (names only) |
| GET | `/api/conversations` | One row per customer with their latest message |
| GET | `/api/messages?phone=` | All messages newest first, optionally one customer |
| GET | `/api/templates` | Approved templates from the WhatsApp Business Account |
| POST | `/api/send-template` | `{to, template, language, params[], body}` |
| POST | `/api/send-text` | `{to, text}` |
| GET | `/webhook` | Meta verification (`hub.mode`, `hub.verify_token`, `hub.challenge`) |
| POST | `/webhook` | Incoming messages and status updates |

### Database (`messages` table)

| Column | Meaning |
|---|---|
| `wamid` | WhatsApp message ID (unique, used to match status updates and skip retries) |
| `direction` | `incoming` or `outgoing` |
| `phone`, `contact_name` | Customer number (digits only) and WhatsApp profile name |
| `msg_type`, `body` | `text` / `template` / other, and the message text |
| `status` | `received`, `sent`, `delivered`, `read`, `failed` |
| `error_code`, `error_message` | Meta's reason when a send fails |
| `created_at`, `updated_at` | Timestamps (UTC) |

---

## Environment variables

Copy `backend/.env.example` to `backend/.env` and fill it in. **Never commit `.env`** (it's in `.gitignore`).

| Variable | Where to find it |
|---|---|
| `WHATSAPP_ACCESS_TOKEN` | Meta App Dashboard → WhatsApp → API Setup (temporary token lasts 24h; see below for a long-lived one) |
| `WHATSAPP_PHONE_NUMBER_ID` | Same page, under the test "From" number |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | Same page (needed to load the template list) |
| `GRAPH_API_VERSION` | The version in the curl example on the API Setup page, e.g. `v23.0` |
| `WEBHOOK_VERIFY_TOKEN` | Any random string you make up; paste the same value in Meta's webhook config |
| `META_APP_SECRET` | App settings → Basic → App secret. Enables signature checks on webhooks |
| `DATABASE_URL` | `sqlite:///whatsapp.db` locally; a Postgres URL in production |
| `FRONTEND_ORIGIN` | `http://localhost:5173` (dev CORS) |

**Long-lived token (recommended for the deployed app):** Meta Business Settings → Users → System users
→ Add (Admin) → Assign assets: your app and WhatsApp account → Generate token with
`whatsapp_business_messaging` and `whatsapp_business_management` permissions.

---

## Run locally

Requirements: Python 3.10+, Node.js 18+, ngrok (only to receive webhooks locally).

**1. Backend** (terminal 1)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env  — then fill in values
python app.py                      # http://localhost:5000
```
Check: open `http://localhost:5000/api/health` → `{"ok": true, "missing_settings": []}`.

**2. Frontend** (terminal 2)
```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173
```
Vite forwards `/api` calls to Flask, so no extra config is needed.

**3. Expose the webhook with ngrok** (terminal 3, local testing only)
```bash
ngrok http 5000
```
Copy the `https://….ngrok-free.app` URL and configure Meta as below with `<url>/webhook`.

---

## Configure the Meta webhook

1. Meta App Dashboard → **WhatsApp → Configuration** → Webhook → **Edit**.
2. **Callback URL:** `https://<public-url>/webhook` (ngrok locally, Render in production).
3. **Verify token:** the exact value of `WEBHOOK_VERIFY_TOKEN`.
4. Click **Verify and save**. The backend log shows `Webhook verified by Meta`.
5. Under **Webhook fields**, click **Subscribe** next to **messages**.
6. Make sure your own phone is in the test number's recipient list (API Setup → *To* → Manage phone number list).

---

## Testing

**Automated tests** (no real token; the Meta API is mocked):
```bash
cd backend && source .venv/bin/activate
python -m pytest -q          # 27 passed
```
They cover webhook verification, signature rejection, saving messages, duplicate-retry handling,
each keyword + fallback, status ordering, failed statuses, template variables, invalid numbers,
expired token (code 190), recipient not allowed (131030), network errors and malformed payloads.

**Local end-to-end without Meta** (optional):
```bash
python tests/mock_meta_server.py    # fake Graph API on :8099
# in another terminal, run the backend with:
# META_API_BASE=http://localhost:8099 WHATSAPP_ACCESS_TOKEN=test-token ...
```

**Manual tests with the real API**
```bash
# Webhook verification (should print 12345)
curl "http://localhost:5000/webhook?hub.mode=subscribe&hub.verify_token=<YOUR_VERIFY_TOKEN>&hub.challenge=12345"

# Send hello_world to your phone through the app's API
curl -X POST http://localhost:5000/api/send-template -H "Content-Type: application/json" \
  -d '{"to":"91XXXXXXXXXX","template":"hello_world","language":"en_US"}'
```
Then from your phone, message the test number `hi`, `price`, `hours` and something random, and
watch them appear in **Chats** and **All messages** with the auto-replies and status changes.

### Common errors

| Code | Meaning | Fix |
|---|---|---|
| 190 | Access token expired or invalid | Generate a new token (or a system user token), update `.env` / Render |
| 131030 | Recipient not in allowed list | Add the number under API Setup → Manage phone number list |
| 131047 | More than 24h since the customer's last message | Send a template instead of free text |
| 132001 | Template doesn't exist in that language | Check the template name and language code / approval status |
| 403 on webhook verify | Verify token mismatch | Make `WEBHOOK_VERIFY_TOKEN` match exactly |

---

## Deploy (Render, free)

The assessment requires a public HTTPS URL without ngrok and a hosted database
(free hosts wipe local files, so SQLite would lose data).

1. **Database:** create a free Postgres on Neon (neon.tech) or Supabase and copy its connection string.
2. **Push to GitHub** (`.env` stays local; check with `git status` before committing).
3. **Render:** New → **Blueprint** → select the repo (uses `render.yaml`), or New → Web Service with:
   - Build: `cd frontend && npm ci && npm run build && cd ../backend && pip install -r requirements.txt`
   - Start: `cd backend && gunicorn -w 2 -b 0.0.0.0:$PORT app:app`
4. **Environment:** add the variables from the table above in Render's dashboard, with
   `DATABASE_URL` = the Postgres URL. Use a long-lived system user token.
5. Open `https://<app>.onrender.com/api/health` → `ok: true`.
6. Point the Meta webhook to `https://<app>.onrender.com/webhook` (section above).

Flask serves the built React app, so one URL is both the dashboard and the webhook.

> **Free plan note:** Render's free web services sleep after ~15 minutes without traffic. The first
> request after that (including a webhook) can take 30–60 seconds while it wakes up. Open the
> dashboard once before demoing.

---

## Security

- Secrets live only in `backend/.env` (git-ignored) or Render's environment settings.
- The token is used only in `whatsapp.py` request headers; it is never sent to the browser or logged.
- Webhook POSTs are rejected unless the `X-Hub-Signature-256` HMAC matches the App Secret.
- The verify token is compared in constant time.
- Customer phone numbers are masked in logs (last 4 digits only).
- Only Meta's test number is used.

## Adding a keyword

Edit `backend/auto_reply.py`:
```python
KEYWORD_REPLIES = [
    ...
    (("location", "address"), "We're at 12 Anna Salai, Chennai."),
]
```
Add a test in `tests/test_auto_reply.py`, restart the backend, done.

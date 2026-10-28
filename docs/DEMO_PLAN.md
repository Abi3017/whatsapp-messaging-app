# Demo video plan (3–5 minutes)

Record the laptop screen with the phone visible (or mirror the phone with scrcpy / screen-record
it separately and show both). Wake the Render app 2 minutes before recording.

| Time | Show | Say (short) |
|---|---|---|
| 0:00–0:30 | README architecture diagram, repo structure | "React dashboard, Flask backend, Postgres. Only the backend talks to Meta, so the token never reaches the browser." |
| 0:30–1:00 | Meta dashboard → WhatsApp → Configuration (webhook URL verified, `messages` subscribed). Hide the token. | "Meta delivers incoming messages and status updates to this endpoint." |
| 1:00–2:00 | Phone: send `hi`, then `price`, then `hours`, then `random text`. Dashboard **Chats** updates within 3 s, auto-replies arrive on the phone. | "Keywords are matched as whole words; anything else gets the fallback reply." |
| 2:00–3:00 | **Send template** tab: pick `order_update`, fill name + order number, show preview, send. Phone receives it. Open the chat: ✓ → ✓✓ → blue ✓✓ as you open it on the phone. | "Templates can be sent outside the 24-hour window. Status comes back through the webhook, matched by message ID." |
| 3:00–3:40 | **All messages** tab: direction, phone, text, time, status, newest first. Show one failed message with its error (send to a number not in the allowed list). | "Failures are stored with Meta's error code so the operator knows why." |
| 3:40–4:30 | Code tour: `app.py` webhook handler, `auto_reply.py`, `whatsapp.py` error handling. Run `pytest -q`. | "Duplicates from Meta retries are ignored, statuses never move backwards, and bad payloads are logged, not crashed on." |
| 4:30–5:00 | Wrap up: what's done, what's not (README "Known limits"). | |

# Practice "live changes" (likely in the next round)

1. **Add a keyword** — add `(("location",), "We're in Chennai")` to `auto_reply.py`, restart, test from phone.
2. **Change the fallback text** — edit `FALLBACK_REPLY`.
3. **Show failed rows in red in the inbox** — CSS class already exists (`.pill-failed`); try changing its color.
4. **Add a column** (e.g. message type) to the inbox table in `Inbox.jsx`.
5. **Change polling to 5 seconds** — `POLL_MS` in `App.jsx`.

# Submission checklist (reply to the task email before 6:00 PM)

- [ ] Document (Google Doc/PDF): Part 1 answers, Part 2 screenshots, error log
- [ ] GitHub repo link (public), no `.env` committed
- [ ] Live Render URL
- [ ] README (this repo)
- [ ] 3–5 min recording link (Drive/Loom), access: anyone with the link can view
- [ ] Token not visible in any screenshot or the video

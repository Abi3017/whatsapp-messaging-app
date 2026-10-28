"""Database layer.

Uses SQLAlchemy so the same code works with SQLite (local) and Postgres (Render).
One table, `messages`, holds both incoming and outgoing messages.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Column, DateTime, Integer, MetaData, String, Table, Text,
    create_engine, func, select, update,
)

metadata = MetaData()

messages = Table(
    "messages",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    # WhatsApp message ID from Meta. Unique so webhook retries can't create duplicates.
    Column("wamid", String(255), unique=True, nullable=True),
    Column("direction", String(10), nullable=False),      # "incoming" or "outgoing"
    Column("phone", String(32), nullable=False, index=True),  # customer number, digits only
    Column("contact_name", String(255), nullable=True),
    Column("msg_type", String(32), nullable=False, default="text"),  # text, template, ...
    Column("body", Text, nullable=False, default=""),
    Column("status", String(20), nullable=False),          # received, sent, delivered, read, failed
    Column("error_code", String(32), nullable=True),
    Column("error_message", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

# Status can only move forward. Webhooks may arrive out of order
# (e.g. "read" before "delivered"), so we never downgrade.
STATUS_RANK = {"pending": 0, "sent": 1, "delivered": 2, "read": 3, "failed": 4}

_engine = None


def init_db(database_url):
    """Create the engine and the table if it does not exist."""
    global _engine
    # Render/Heroku give "postgres://", SQLAlchemy needs "postgresql://"
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    _engine = create_engine(database_url, pool_pre_ping=True)
    metadata.create_all(_engine)
    return _engine


def _now():
    return datetime.now(timezone.utc)


def _row_to_dict(row):
    d = dict(row._mapping)
    for key in ("created_at", "updated_at"):
        if d.get(key) is not None:
            value = d[key]
            if value.tzinfo is None:  # SQLite drops tz info; values are stored as UTC
                value = value.replace(tzinfo=timezone.utc)
            d[key] = value.isoformat()
    return d


def wamid_exists(wamid):
    with _engine.connect() as conn:
        return conn.execute(select(messages.c.id).where(messages.c.wamid == wamid)).first() is not None


def save_incoming(wamid, phone, body, msg_type="text", contact_name=None, timestamp=None):
    """Store a customer message. Returns False if this wamid was already stored (Meta retry)."""
    if wamid and wamid_exists(wamid):
        return False
    when = timestamp or _now()
    with _engine.begin() as conn:
        conn.execute(messages.insert().values(
            wamid=wamid, direction="incoming", phone=phone, contact_name=contact_name,
            msg_type=msg_type, body=body, status="received",
            created_at=when, updated_at=when,
        ))
    return True


def save_outgoing(phone, body, msg_type, wamid=None, status="sent", error_code=None, error_message=None):
    """Store a message we sent (or tried to send). Failed sends are stored too, for the inbox."""
    now = _now()
    with _engine.begin() as conn:
        result = conn.execute(messages.insert().values(
            wamid=wamid, direction="outgoing", phone=phone, msg_type=msg_type, body=body,
            status=status, error_code=error_code, error_message=error_message,
            created_at=now, updated_at=now,
        ))
        return result.inserted_primary_key[0]


def update_status(wamid, new_status, error_code=None, error_message=None):
    """Apply a status webhook. Returns True if the row changed."""
    with _engine.begin() as conn:
        row = conn.execute(select(messages.c.status).where(messages.c.wamid == wamid)).first()
        if row is None:
            return False
        current = row.status
        if STATUS_RANK.get(new_status, -1) <= STATUS_RANK.get(current, -1):
            return False
        values = {"status": new_status, "updated_at": _now()}
        if new_status == "failed":
            values.update(error_code=error_code, error_message=error_message)
        conn.execute(update(messages).where(messages.c.wamid == wamid).values(**values))
        return True


def list_messages(phone=None, limit=200):
    """Newest first. Optionally only one customer's messages."""
    query = select(messages).order_by(messages.c.created_at.desc(), messages.c.id.desc()).limit(limit)
    if phone:
        query = query.where(messages.c.phone == phone)
    with _engine.connect() as conn:
        return [_row_to_dict(r) for r in conn.execute(query)]


def list_conversations():
    """One entry per customer with their latest message, newest conversation first."""
    latest = (
        select(messages.c.phone, func.max(messages.c.id).label("last_id"))
        .group_by(messages.c.phone)
        .subquery()
    )
    query = (
        select(messages)
        .join(latest, messages.c.id == latest.c.last_id)
        .order_by(messages.c.created_at.desc(), messages.c.id.desc())
    )
    with _engine.connect() as conn:
        rows = [_row_to_dict(r) for r in conn.execute(query)]
        # Name from the most recent incoming message, if any
        names = dict(conn.execute(
            select(messages.c.phone, messages.c.contact_name)
            .where(messages.c.contact_name.is_not(None))
            .order_by(messages.c.id)
        ).all())
    for r in rows:
        r["contact_name"] = names.get(r["phone"])
    return rows

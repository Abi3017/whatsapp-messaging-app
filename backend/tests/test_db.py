import db


def setup_function():
    db.init_db("sqlite:///:memory:")


def test_incoming_is_saved_once():
    assert db.save_incoming("wamid.1", "919800000000", "hi", contact_name="Asha") is True
    # Same wamid again (Meta retry) is ignored
    assert db.save_incoming("wamid.1", "919800000000", "hi") is False
    rows = db.list_messages()
    assert len(rows) == 1
    assert rows[0]["direction"] == "incoming"
    assert rows[0]["status"] == "received"


def test_status_only_moves_forward():
    db.save_outgoing("919800000000", "hello", "text", wamid="wamid.2")
    assert db.update_status("wamid.2", "read") is True
    # "delivered" arriving late must not downgrade "read"
    assert db.update_status("wamid.2", "delivered") is False
    assert db.list_messages()[0]["status"] == "read"


def test_failed_status_stores_error():
    db.save_outgoing("919800000000", "hello", "text", wamid="wamid.3")
    db.update_status("wamid.3", "failed", "131026", "Message undeliverable")
    row = db.list_messages()[0]
    assert row["status"] == "failed"
    assert row["error_code"] == "131026"


def test_unknown_wamid_status_is_ignored():
    assert db.update_status("wamid.unknown", "delivered") is False


def test_conversations_newest_first_and_filter():
    db.save_incoming("wamid.a", "911111111111", "first", contact_name="A")
    db.save_incoming("wamid.b", "922222222222", "second", contact_name="B")
    db.save_outgoing("911111111111", "reply to A", "text", wamid="wamid.c")
    convs = db.list_conversations()
    assert [c["phone"] for c in convs] == ["911111111111", "922222222222"]
    assert convs[0]["body"] == "reply to A"
    assert convs[0]["contact_name"] == "A"
    assert len(db.list_messages(phone="922222222222")) == 1

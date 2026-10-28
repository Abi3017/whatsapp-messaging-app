from auto_reply import FALLBACK_REPLY, get_reply


def test_keywords_case_insensitive_and_in_sentences():
    assert "Hello" in get_reply("HI there")
    assert "₹499" in get_reply("what's the price?")
    assert "9:00 AM" in get_reply("Are you open today")


def test_whole_word_match_only():
    # "this" contains "hi" but must not trigger the greeting
    assert get_reply("this is something") == FALLBACK_REPLY


def test_empty_and_none():
    assert get_reply("") == FALLBACK_REPLY
    assert get_reply(None) == FALLBACK_REPLY

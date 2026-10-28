import pytest

from auto_reply import FALLBACK_REPLY, get_reply

HI = "Hello! Welcome. How can we help you?"
PRICE = "Please tell us which product or service you are interested in."
HOURS = "Our business hours are 9 AM to 6 PM."
INFO = "Thank you for contacting us. Could you please share more details about your enquiry?"


@pytest.mark.parametrize("message, expected", [
    ("Hi", HI), ("hi", HI), ("HI", HI), ("hello there", HI),
    ("Price", PRICE), ("price", PRICE), ("What is the price?", PRICE),
    ("Hours", HOURS), ("hours", HOURS), ("business hours", HOURS),
    ("I need some information", INFO), ("Can I get more info?", INFO),
    ("hi, what is the price?", PRICE),
])
def test_customer_script(message, expected):
    assert get_reply(message) == expected


def test_whole_word_match_only():
    assert get_reply("this is something") == FALLBACK_REPLY


def test_empty_and_none():
    assert get_reply("") == FALLBACK_REPLY
    assert get_reply(None) == FALLBACK_REPLY
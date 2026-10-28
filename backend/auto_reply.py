"""Keyword-based automatic replies.

To add a keyword, add one entry to KEYWORD_REPLIES. Matching is case-insensitive
and checks whole words, so "price" matches "What's the price?" but "hi" does
not match "this".

Rules are checked top to bottom and the first match wins. The greeting is last,
so "hi, what is the price?" gets the price answer instead of a greeting.
"""
import re

KEYWORD_REPLIES = [
    (("price", "prices", "pricing", "cost"),
     "Please tell us which product or service you are interested in."),
    (("hours", "timing", "timings", "open"),
     "Our business hours are 9 AM to 6 PM."),
    (("information", "info", "details", "enquiry", "inquiry"),
     "Thank you for contacting us. Could you please share more details about your enquiry?"),
    (("hi", "hello", "hey"),
     "Hello! Welcome. How can we help you?"),
]

FALLBACK_REPLY = (
    "Thanks for your message! I didn't catch that. "
    "Try *hi*, *price* or *hours*, and our team will follow up soon."
)


def get_reply(text):
    """Return the reply for the first matching keyword, or the fallback."""
    words = set(re.findall(r"[a-z]+", (text or "").lower()))
    for keywords, reply in KEYWORD_REPLIES:
        if words.intersection(keywords):
            return reply
    return FALLBACK_REPLY
"""Keyword-based automatic replies.

To add a keyword, add one entry to KEYWORD_REPLIES. Matching is case-insensitive
and checks whole words, so "price" matches "What's the price?" but "hi" does
not match "this".
"""
import re

KEYWORD_REPLIES = [
    (("hi", "hello", "hey"),
     "Hello! 👋 Thanks for messaging us. Reply *price* for our pricing or *hours* for our opening hours."),
    (("price", "prices", "pricing", "cost"),
     "Our plans start at ₹499/month. Reply *hours* to know when you can reach us."),
    (("hours", "timing", "timings", "open"),
     "We're open Monday to Saturday, 9:00 AM to 7:00 PM IST."),
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

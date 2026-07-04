"""
fallbacks.py — hardcoded regex patterns for common use cases.

If both LLM providers fail, we attempt to match the user's natural language
prompt against these known patterns before giving up entirely.
This means the app keeps working even with no API credits.
"""

import re

# Each entry: list of keywords that trigger this pattern
FALLBACK_PATTERNS = [
    {
        "keywords": ["email", "e-mail", "email address"],
        "pattern": r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        "description": "Email addresses",
    },
    {
        "keywords": ["phone", "phone number", "telephone", "mobile", "cell"],
        "pattern": r"(\+?1[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}",
        "description": "Phone numbers",
    },
    {
        "keywords": ["url", "link", "website", "http", "https", "web address"],
        "pattern": r"https?://[^\s]+",
        "description": "URLs",
    },
    {
        "keywords": ["date", "dates", "dd/mm", "mm/dd", "yyyy"],
        "pattern": r"\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b",
        "description": "Dates",
    },
    {
        "keywords": ["postcode", "postal code", "zip", "zip code"],
        "pattern": r"\b\d{5}(?:[\-]\d{4})?\b",
        "description": "Zip/postal codes",
    },
    {
        "keywords": ["ip address", "ip", "ipv4"],
        "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "description": "IP addresses",
    },
    {
        "keywords": ["credit card", "card number", "visa", "mastercard"],
        "pattern": r"\b(?:\d{4}[\s\-]?){3}\d{4}\b",
        "description": "Credit card numbers",
    },
    {
        "keywords": ["ssn", "social security", "social security number"],
        "pattern": r"\b\d{3}[\-]\d{2}[\-]\d{4}\b",
        "description": "Social Security Numbers",
    },
    {
        "keywords": ["number", "digits", "numeric", "integer"],
        "pattern": r"\b\d+\b",
        "description": "Numbers",
    },
    {
        "keywords": ["whitespace", "spaces", "blank", "empty"],
        "pattern": r"\s+",
        "description": "Whitespace",
    },
]


def get_fallback_regex(nl_prompt: str) -> str | None:
    """
    Try to match the prompt against known patterns.
    Returns a regex string if a match is found, None otherwise.
    """
    prompt_lower = nl_prompt.lower()
    for entry in FALLBACK_PATTERNS:
        if any(kw in prompt_lower for kw in entry["keywords"]):
            return entry["pattern"]
    return None

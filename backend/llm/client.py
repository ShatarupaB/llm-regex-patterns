"""
client.py — LLM client with three-tier fallback:
  1. Anthropic API
  2. Gemini API  
  3. Hardcoded fallback dictionary (works with zero API credits)
"""

import re
import os
import logging

logger = logging.getLogger(__name__)

DANGEROUS_PATTERNS = [
    r"\(\?=.*\(\?=",
    r"\(\w+\+\)\+",
    r"\(\w+\*\)\*",
]


def _validate_regex(pattern: str) -> str:
    try:
        re.compile(pattern)
    except re.error as e:
        raise ValueError(f"Invalid regex: {e}") from e
    for danger in DANGEROUS_PATTERNS:
        if re.search(danger, pattern):
            raise ValueError(f"Dangerous backtracking pattern rejected: {pattern!r}")
    if len(pattern.strip()) < 2:
        raise ValueError(f"Regex too short: {pattern!r}")
    return pattern


def _clean_response(raw: str) -> str:
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return raw.strip()


def _try_anthropic(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=256,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return _clean_response(message.content[0].text)


def _try_gemini(prompt: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    return _clean_response(response.text)


def generate_regex_from_prompt(nl_prompt: str) -> str:
    from .prompts import build_regex_prompt
    from .fallbacks import get_fallback_regex

    prompt = build_regex_prompt(nl_prompt)
    errors = []

    # Tier 1: Anthropic
    try:
        raw = _try_anthropic(prompt)
        logger.info("Regex generated via Anthropic")
        return _validate_regex(raw)
    except Exception as e:
        logger.warning(f"Anthropic failed: {e}")
        errors.append(f"Anthropic: {type(e).__name__}")

    # Tier 2: Gemini
    try:
        raw = _try_gemini(prompt)
        logger.info("Regex generated via Gemini")
        return _validate_regex(raw)
    except Exception as e:
        logger.warning(f"Gemini failed: {e}")
        errors.append(f"Gemini: {type(e).__name__}")

    # Tier 3: Hardcoded fallback dictionary
    fallback = get_fallback_regex(nl_prompt)
    if fallback:
        logger.info(f"Using hardcoded fallback regex for: {nl_prompt[:50]}")
        return _validate_regex(fallback)

    # All three failed
    raise RuntimeError(
        f"Could not generate regex. API services unavailable and no fallback "
        f"pattern matched '{nl_prompt[:60]}'. Try describing the pattern differently "
        f"(e.g. 'find email addresses', 'find phone numbers')."
    )

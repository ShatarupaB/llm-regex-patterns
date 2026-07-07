"""
client.py — LLM client with Anthropic primary and Gemini fallback.
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

    prompt = build_regex_prompt(nl_prompt)

    # Tier 1: Anthropic
    try:
        raw = _try_anthropic(prompt)
        logger.info("Regex generated via Anthropic")
        return _validate_regex(raw)
    except Exception as e:
        logger.warning(f"Anthropic failed: {e}")

    # Tier 2: Gemini fallback
    try:
        raw = _try_gemini(prompt)
        logger.info("Regex generated via Gemini")
        return _validate_regex(raw)
    except Exception as e:
        logger.warning(f"Gemini failed: {e}")

    raise RuntimeError(
        "Could not generate a regex pattern. Both LLM providers are currently "
        "unavailable. Please try again later."
    )

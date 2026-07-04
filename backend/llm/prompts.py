"""
prompts.py — prompt templates for LLM calls.

Keeping prompts in their own module means you can iterate on them
without touching client.py, and they're easy to unit test in isolation.
"""


def build_regex_prompt(nl_description: str) -> str:
    """
    Returns a prompt that instructs the LLM to output ONLY a regex pattern.
    The strict output format is critical — we use the raw text as the regex.
    """
    return f"""You are a regex generation assistant. Your ONLY job is to convert
a natural language description into a single, valid Python regex pattern.

Rules:
- Output ONLY the raw regex pattern — no explanation, no markdown, no code fences.
- The pattern must be compatible with Python's `re` module.
- Do not wrap the pattern in quotes or slashes.
- Avoid nested quantifiers that could cause catastrophic backtracking.
- If the description is ambiguous, choose the most common interpretation.
- Do not use ^ or $ anchors unless the user explicitly asks to match the entire cell value.
- Prefer patterns that match within a larger string rather than requiring an exact full match.

Natural language description:
"{nl_description}"

Regex pattern:"""

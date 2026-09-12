"""Tolerant single-object JSON decoding for model output.

Providers wrap the requested object in fences, prepend prose, or append a
second candidate. Only the first top-level object is honoured: extra text is
model noise, never a second instruction, and the caller still schema-validates.
"""
import json

DECODER = json.JSONDecoder()


def decode(raw, *, limit=30000):
    if not isinstance(raw, str) or len(raw) > limit:
        raise ValueError("model output missing or over budget")
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    start = text.find("{")
    if start < 0:
        raise ValueError("model output contains no JSON object")
    try:
        value, _ = DECODER.raw_decode(text, start)
    except json.JSONDecodeError:
        raise ValueError("model output is not valid JSON") from None
    if not isinstance(value, dict):
        raise ValueError("model output must be a JSON object")
    return value

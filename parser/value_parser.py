"""
Value parsing: △/▲/－ aware numeric parser and Japanese date normaliser.
"""
from __future__ import annotations
import re
import unicodedata
from typing import Optional

# Nil markers (fullwidth and standard)
NIL_CHARS: frozenset[str] = frozenset([
    '－',   # U+FF0D FULLWIDTH HYPHEN-MINUS
    '—',    # U+2014 EM DASH
    '−',    # U+2212 MINUS SIGN
    '\uff0d', '\u2014', '\u2212',
    '―',    # U+2015 HORIZONTAL BAR
])

# Negative prefix characters
NEG_PREFIXES: tuple[str, ...] = ('△', '▲')  # U+25B3, U+25B2


def parse_value(raw: str) -> tuple[Optional[float], bool, bool, list[str]]:
    """
    Parse a raw cell string.
    Returns: (numeric, nil, negative, flags)
      numeric  – float value, or None if nil / parse failed
      nil      – True when an explicit nil marker was the entire token
      negative – True when △ or ▲ prefix was present
      flags    – list of flag strings ('negative_zero', 'parse_failed', ...)
    """
    flags: list[str] = []
    text = raw.strip()

    if not text:
        return None, True, False, flags

    # Nil check first
    if text in NIL_CHARS:
        return None, True, False, flags

    # Strip negative prefix
    negative = False
    if text.startswith(NEG_PREFIXES):
        negative = True
        text = text[1:]

    # Normalise full-width digits/commas/decimal points to ASCII
    text = unicodedata.normalize('NFKC', text)

    # Remove thousands commas
    text = text.replace(',', '')

    try:
        val = float(text)
        if negative:
            val = -val
        if val == 0.0 and negative:
            flags.append('negative_zero')
        return val, False, negative, flags
    except ValueError:
        flags.append('parse_failed')
        return None, False, negative, flags


# Patterns for Japanese date components
_DATE_RE = re.compile(
    r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日'
)


def normalize_japanese_date(raw: str) -> tuple[str, bool]:
    """
    Convert a Japanese date string to ISO-8601.
    Handles full-width digits, spaces between components, surrounding parens.
    Returns: (result, was_successfully_normalised)
    """
    # Normalise full-width to ASCII first
    s = unicodedata.normalize('NFKC', raw.strip())
    # Strip surrounding parens/brackets
    s = re.sub(r'^[(（\[]|[)）\]]$', '', s).strip()
    m = _DATE_RE.search(s)
    if m:
        y, mo, d = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2)
        return f"{y}-{mo}-{d}", True
    return raw, False

"""PII-redacting log filter.

Maschera email, sequenze telefoniche e codici fiscali italiani nei messaggi
di log. Non sostituisce la regola operativa (non passare PII a logger.*),
ma offre una rete di sicurezza in caso di sviste.
"""

from __future__ import annotations

import logging
import re

_PII_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[email-redacted]"),
    (
        re.compile(r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b"),
        "[fiscalcode-redacted]",
    ),
    (re.compile(r"\+?\d[\d\s().-]{8,}\d"), "[phone-redacted]"),
]


class RedactPIIFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = message
        for pattern, replacement in _PII_PATTERNS:
            redacted = pattern.sub(replacement, redacted)
        if redacted != message:
            record.msg = redacted
            record.args = None
        return True

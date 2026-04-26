"""
Helper riusabili per legal_sources.

`compute_file_sha256` calcola l'hash di un file caricato senza esaurire
la memoria con `read()` su file grandi. È usato in `LegalSourceAttachment.save`
e `LegalSourceVersion` per garantire l'integrità documentale.
"""

from __future__ import annotations

import hashlib
from typing import IO


def compute_sha256(file_obj: IO[bytes], chunk_size: int = 65536) -> str:
    """SHA-256 esadecimale di un file-like object. Riposiziona il cursore a 0."""
    file_obj.seek(0)
    hasher = hashlib.sha256()
    for chunk in iter(lambda: file_obj.read(chunk_size), b""):
        if not chunk:
            break
        hasher.update(chunk)
    file_obj.seek(0)
    return hasher.hexdigest()


def compute_bytes_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()

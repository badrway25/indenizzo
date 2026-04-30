"""
Celery app entrypoint.

Iter: F-local-product-hardening-pass7-celery-async.

Disegno minimale:
- nome app: `badrane_legaltech` (riconoscibile nei log/UI di flower);
- config caricata dai settings Django con prefisso `CELERY_*`;
- autodiscover dei task in tutte le `apps.*` (Celery cerca un
  modulo `tasks.py` per ogni AppConfig).

Avvio worker (in Docker compose locale, vedi pass 6):
    celery -A config worker -l INFO

Locale-first: il modulo è importabile anche senza broker raggiungibile.
Nessun task viene eseguito al momento dell'import.
"""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("badrane_legaltech")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

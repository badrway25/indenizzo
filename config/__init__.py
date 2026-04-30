"""Config package: espone `celery_app` per la discovery dei task.

Il pattern è quello standard Celery+Django: importare l'app qui
così che Django (e i management command) garantiscano `shared_task`
working anche senza un worker attivo. Il broker non viene contattato
all'import — `app.config_from_object(...)` è lazy.
"""

from .celery import app as celery_app

__all__ = ("celery_app",)

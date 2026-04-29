"""
Pacchetto `engines`: implementazioni concrete di `BaseCalculator`.

Importare questo pacchetto forza l'import di tutti i submodule paese,
i quali registrano i propri calculator nel `registry`. È il punto
unico in cui le registrazioni diventano "vive".

Calculator registrati:
- ``italy`` — Italia, road_accident e inheritance_basic placeholder;
- ``france`` — Francia, road_accident scaffold (F-france-road-accident-
  bootstrap), placeholder che ritorna sempre ``unavailable`` finché lo
  Studio non promuove fonti/dataset/formula a ``approved``.

Belgio, Marocco, Tunisia restano nella roadmap.
"""

from __future__ import annotations

# Forzare il side-effect delle registrazioni.
from . import france, italy  # noqa: F401

"""
Pacchetto `engines`: implementazioni concrete di `BaseCalculator`.

Importare questo pacchetto forza l'import di tutti i submodule paese,
i quali registrano i propri calculator nel `registry`. È il punto
unico in cui le registrazioni diventano "vive".

Calculator registrati:
- ``italy`` — Italia, road_accident (operativo, range min/mid/max) e
  inheritance_basic placeholder;
- ``france`` — Francia, road_accident scaffold (F-france-road-accident-
  bootstrap), placeholder che ritorna sempre ``unavailable``;
- ``belgium`` — Belgio, road_accident scaffold (F-belgium-road-accident-
  bootstrap), placeholder che ritorna sempre ``unavailable``;
- ``morocco`` — Marocco, international_inheritance scaffold
  (F-ma-tn-international-inheritance-bootstrap), placeholder;
- ``tunisia`` — Tunisia, international_inheritance scaffold
  (F-ma-tn-international-inheritance-bootstrap), placeholder.
"""

from __future__ import annotations

# Forzare il side-effect delle registrazioni.
from . import belgium, france, italy, morocco, tunisia  # noqa: F401

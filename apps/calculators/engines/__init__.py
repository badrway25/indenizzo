"""
Pacchetto `engines`: implementazioni concrete di `BaseCalculator`.

Importare questo pacchetto forza l'import di tutti i submodule paese,
i quali registrano i propri calculator nel `registry`. È il punto
unico in cui le registrazioni diventano "vive".

In F4 c'è solo `italy`. Francia, Belgio, Marocco, Tunisia restano nella
roadmap di F5+: la struttura per aggiungerli è già pronta (basta creare
`france.py` con classi che ereditano da `BaseCalculator` e si auto-
registrano a fine modulo, esattamente come `italy.py`).
"""

from __future__ import annotations

# Forzare il side-effect delle registrazioni.
from . import italy  # noqa: F401

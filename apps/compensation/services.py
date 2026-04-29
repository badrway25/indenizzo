"""
Service layer per il dominio compensation.

Funzioni pure e leggere che incapsulano l'interrogazione al DB delle
strutture validate e l'applicazione delle regole di calcolo dichiarate
nelle `CalculationFormula`. Nessuna costante economica vive qui:

- importi e coefficienti stanno in `CompensationTableRow` (popolata
  manualmente dallo Studio dopo legal review);
- la regola da applicare alla riga sta in `CalculationFormula.parameters`
  (JSON dichiarativo, non codice eseguibile);
- questa modulo contiene solo l'**interpretazione** delle regole note,
  con un registro esplicito (`SUPPORTED_ENGINES`, `SUPPORTED_AMOUNT_RULES`).

Estendere il motore in futuro = aggiungere un nuovo identificatore al
registro e una nuova funzione `_rule_*`. Questo costringe ogni nuovo
"engine" a passare per code review e test, invece di essere un side
effect di un campo JSON cambiato in admin.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as _date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from django.db.models import Q

from apps.legal_sources.enums import SourceStatus

from .models import (
    CalculationFormula,
    CompensationDataset,
    CompensationTableRow,
    DatasetStatus,
)

# ---------------------------------------------------------------------------
# Registro esplicito degli engine e delle amount_rule supportate.
# Chi vuole aggiungere un engine DEVE registrarlo qui e implementare la
# corrispondente funzione `_rule_*`. Senza questo gate chiunque potrebbe
# scrivere `engine=foo` in admin e attivare un calcolo non vetting-ato.
# ---------------------------------------------------------------------------
SUPPORTED_ENGINES: frozenset[str] = frozenset({"italy_tun_point_value_v1"})
SUPPORTED_AMOUNT_RULES: frozenset[str] = frozenset(
    {
        # Cell value is a per-point amount: final = point_value × disability%.
        "point_value_times_disability_percentage",
        # Cell value is the FINAL amount for the (age, disability) cell:
        # final = row.point_value (no further multiplication). Used by tables
        # that are "comprensive" / pre-computed, e.g. the Italian TUN
        # Tabella 1 of the D.P.R. 12/2025.
        "row_amount_direct",
        # Range version of `row_amount_direct`: reads THREE rows (one per
        # row_type) from a SECONDARY APPROVED dataset, returning three
        # distinct amounts (min/mid/max) for the same (age, disability)
        # cell. Used by the Italian TUN Tabelle 2.A/2.B/2.C (danno morale)
        # of the D.P.R. 12/2025 once the moral dataset has been promoted
        # to APPROVED. While the moral dataset is DRAFT the calculator
        # MUST refuse to execute (see `get_approved_dataset_by_version_label`).
        "row_amount_range_direct",
    }
)

# Subset of SUPPORTED_AMOUNT_RULES that operate on three rows (min/mid/max)
# instead of one. The calculator dispatches differently for these.
RANGE_AMOUNT_RULES: frozenset[str] = frozenset({"row_amount_range_direct"})


def is_range_rule(rule: str) -> bool:
    """Return True iff ``rule`` is a range rule (3 rows in, 3 amounts out)."""
    return rule in RANGE_AMOUNT_RULES


# ---------------------------------------------------------------------------
# Resolver: dataset approvato per una lista di fonti / case_type
# ---------------------------------------------------------------------------


def get_approved_dataset_for_sources(
    sources,
    case_type: str,
    *,
    calculation_date: _date | None = None,
) -> CompensationDataset | None:
    """
    Primo `CompensationDataset` APPROVED collegato a una delle `sources`,
    coerente con `case_type` e vigente alla data di riferimento.

    `valid_from`/`valid_to` sono rispettati: un dataset con `valid_from`
    futura o `valid_to` passata non viene considerato. Se `valid_from`
    o `valid_to` sono NULL, il vincolo non si applica (dataset "aperto").

    Importante: la query verifica esplicitamente che `source.status` sia
    `APPROVED`. Un dataset il cui source è stato deprecato dopo la
    promozione del dataset NON è usabile, anche se il dataset stesso è
    ancora `APPROVED`. Questo evita inconsistenze nel workflow.
    """
    ref = calculation_date or _date.today()
    qs = (
        CompensationDataset.objects.filter(
            source__in=sources,
            case_type=case_type,
            status=DatasetStatus.APPROVED,
            source__status=SourceStatus.APPROVED,
        )
        .filter(Q(valid_from__isnull=True) | Q(valid_from__lte=ref))
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=ref))
        .select_related("source")
        .order_by("-valid_from", "-pk")
    )
    candidates = list(qs)
    if not candidates:
        return None
    # Prefer the dataset that holds at least one APPROVED formula. This
    # handles the case where a single LegalSource has multiple approved
    # datasets (e.g. base + moral): only the formula-bearing one is the
    # calculator's primary; the secondary is referenced via
    # `range_dataset_version_label` in the formula's parameters and looked
    # up explicitly via `get_approved_dataset_by_version_label`.
    for ds in candidates:
        if ds.formulas.filter(status=DatasetStatus.APPROVED).exists():
            return ds
    return candidates[0]


def get_approved_dataset_by_version_label(
    *,
    source,
    case_type: str,
    version_label: str,
    calculation_date: _date | None = None,
) -> CompensationDataset | None:
    """
    Lookup di un dataset secondario per `version_label`, **solo se APPROVED**.

    Pensata per la regola di range: la formula primaria, attaccata al
    dataset base, dichiara `range_dataset_version_label="DPR-12-2025-MORAL"`.
    Questo helper recupera quel dataset solo se:
    - lo `version_label` corrisponde esattamente;
    - lo status è `APPROVED`;
    - la fonte è `APPROVED`;
    - la data di riferimento è dentro `valid_from`/`valid_to`.

    Se il dataset moral è ancora `DRAFT` (status iniziale post-import)
    ritorna ``None``: il calculator pubblico non potrà mai leggerlo.
    Questa è la difesa applicativa contro l'attivazione prematura del
    range — la regola gating è in code, non solo in admin.
    """
    ref = calculation_date or _date.today()
    return (
        CompensationDataset.objects.filter(
            source=source,
            case_type=case_type,
            version_label=version_label,
            status=DatasetStatus.APPROVED,
            source__status=SourceStatus.APPROVED,
        )
        .filter(Q(valid_from__isnull=True) | Q(valid_from__lte=ref))
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=ref))
        .select_related("source")
        .first()
    )


# ---------------------------------------------------------------------------
# Resolver: formula eseguibile per un dataset
# ---------------------------------------------------------------------------


class FormulaResolutionStatus(StrEnum):
    OK = "ok"
    NO_APPROVED = "no_approved"
    ENGINE_UNKNOWN = "engine_unknown"
    AMOUNT_RULE_UNKNOWN = "amount_rule_unknown"


@dataclass(frozen=True)
class FormulaResolution:
    formula: CalculationFormula | None
    status: FormulaResolutionStatus


def get_executable_formula(dataset: CompensationDataset) -> FormulaResolution:
    """
    Cerca una formula APPROVED associata al dataset il cui `engine` e
    `amount_rule` siano nei registri supportati.

    - se non esistono formule APPROVED → `NO_APPROVED`;
    - se ne esistono ma nessuna ha un `engine` riconosciuto → `ENGINE_UNKNOWN`;
    - se l'engine è riconosciuto ma `amount_rule` non lo è → `AMOUNT_RULE_UNKNOWN`;
    - altrimenti restituisce la prima formula utilizzabile.

    La diagnostica granulare permette al calculator di esporre
    `missing_documents` precisi al chiamante (e quindi all'admin).
    """
    approved = list(dataset.formulas.filter(status=DatasetStatus.APPROVED))
    if not approved:
        return FormulaResolution(formula=None, status=FormulaResolutionStatus.NO_APPROVED)

    # Cerchiamo prima una formula completamente eseguibile.
    for formula in approved:
        params = formula.parameters or {}
        if params.get("engine") not in SUPPORTED_ENGINES:
            continue
        if params.get("amount_rule") not in SUPPORTED_AMOUNT_RULES:
            continue
        return FormulaResolution(formula=formula, status=FormulaResolutionStatus.OK)

    # Nessuna formula è completamente eseguibile: diagnostichiamo perché.
    # Se almeno una ha un engine riconosciuto, la regola è il problema.
    has_known_engine = any(
        (f.parameters or {}).get("engine") in SUPPORTED_ENGINES for f in approved
    )
    if has_known_engine:
        return FormulaResolution(formula=None, status=FormulaResolutionStatus.AMOUNT_RULE_UNKNOWN)
    return FormulaResolution(formula=None, status=FormulaResolutionStatus.ENGINE_UNKNOWN)


# ---------------------------------------------------------------------------
# Row matching
# ---------------------------------------------------------------------------


class RowMatchKind(StrEnum):
    OK = "ok"
    NONE = "none"
    MULTIPLE = "multiple"


@dataclass(frozen=True)
class RowMatch:
    kind: RowMatchKind
    row: CompensationTableRow | None = None
    candidates: int = 0


def find_matching_row_by_type(
    dataset: CompensationDataset,
    *,
    row_type: str,
    row_match_fields: list[str],
    input_data: dict[str, Any],
) -> RowMatch:
    """
    Variante di `find_matching_row` che pre-filtra per `row_type`.

    Necessaria per il range engine: il dataset moral DPR-12-2025-MORAL
    contiene 3 row_type sovrapposti per ogni (age, inv) — chiamare
    `find_matching_row` senza filtro restituisce sempre `MULTIPLE`. Il
    range engine cerca invece UN row per ciascun row_type e li combina.

    NB: filtrare a livello SQL via `dataset.rows.filter(row_type=...)`
    riduce il working set da 27.573 a 9.191 righe per chiamata, evitando
    di scansionarle tutte in Python.
    """
    rows = list(dataset.rows.filter(row_type=row_type))
    matches = [r for r in rows if _row_matches(r, row_match_fields, input_data)]
    if not matches:
        return RowMatch(kind=RowMatchKind.NONE, candidates=0)
    if len(matches) > 1:
        return RowMatch(kind=RowMatchKind.MULTIPLE, candidates=len(matches))
    return RowMatch(kind=RowMatchKind.OK, row=matches[0], candidates=1)


def find_matching_row(
    dataset: CompensationDataset,
    *,
    row_match_fields: list[str],
    input_data: dict[str, Any],
) -> RowMatch:
    """
    Trova l'unica riga del dataset che soddisfa tutti i predicati di
    matching dichiarati in `row_match_fields`.

    Predicati attualmente supportati:
    - `victim_age`: `row.age_min <= age <= row.age_max` (NULL = unbounded)
    - `permanent_disability_percentage`: idem su `disability_min/max`

    Se nessuna riga matcha → `NONE`. Se più di una matcha → `MULTIPLE`
    (il calculator NON sceglie a caso: blocca il calcolo). Solo con una
    riga unica → `OK`.

    L'enumerazione delle righe avviene in Python (non SQL): le tabelle
    realisticamente hanno < 1000 righe (TUN ne ha ~91 voci di età ×
    classi di invalidità) e questo permette regole più espressive senza
    moltiplicare gli indici.
    """
    rows = list(dataset.rows.all())
    matches = [r for r in rows if _row_matches(r, row_match_fields, input_data)]

    if not matches:
        return RowMatch(kind=RowMatchKind.NONE, candidates=0)
    if len(matches) > 1:
        return RowMatch(kind=RowMatchKind.MULTIPLE, candidates=len(matches))
    return RowMatch(kind=RowMatchKind.OK, row=matches[0], candidates=1)


def _row_matches(
    row: CompensationTableRow,
    fields: list[str],
    input_data: dict[str, Any],
) -> bool:
    if "victim_age" in fields:
        age = _to_int_or_none(input_data.get("victim_age"))
        if age is None:
            return False
        if row.age_min is not None and age < row.age_min:
            return False
        if row.age_max is not None and age > row.age_max:
            return False
    if "permanent_disability_percentage" in fields:
        disability = _to_int_or_none(input_data.get("permanent_disability_percentage"))
        if disability is None:
            return False
        if row.disability_min is not None and disability < row.disability_min:
            return False
        if row.disability_max is not None and disability > row.disability_max:
            return False
    return True


# ---------------------------------------------------------------------------
# Application of `amount_rule`
# ---------------------------------------------------------------------------


def apply_amount_rule(
    rule: str,
    *,
    row: CompensationTableRow,
    input_data: dict[str, Any],
    fault_reduction_enabled: bool,
) -> Decimal:
    """
    Calcola l'importo applicando la regola dichiarata dalla formula.

    Solleva `ValueError` se la regola non è nel registro supportato.
    Il chiamante (calculator) deve aver già verificato che
    `rule in SUPPORTED_AMOUNT_RULES` via `get_executable_formula`.

    La ragione per cui è una `ValueError` invece di un fallback silenzioso:
    se mai una regola sconosciuta arriva fin qui, è un bug del wiring fra
    services e calculator; meglio crashare il singolo calcolo che produrre
    un numero inventato.
    """
    if rule == "point_value_times_disability_percentage":
        return _rule_point_value_times_disability(
            row=row,
            input_data=input_data,
            fault_reduction_enabled=fault_reduction_enabled,
        )
    if rule == "row_amount_direct":
        return _rule_row_amount_direct(
            row=row,
            input_data=input_data,
            fault_reduction_enabled=fault_reduction_enabled,
        )
    raise ValueError(f"Unsupported amount_rule: {rule!r}")


def _rule_point_value_times_disability(
    *,
    row: CompensationTableRow,
    input_data: dict[str, Any],
    fault_reduction_enabled: bool,
) -> Decimal:
    """
    amount = row.point_value × permanent_disability_percentage

    Con `fault_reduction_enabled=True` e un `fault_percentage` fornito,
    applica la riduzione: amount × (100 - fault) / 100.

    `point_value` NULL viene trattato come 0: non vogliamo crashare se
    il revisore promuove per errore una riga incompleta. L'effetto è un
    importo zero, ben visibile nel report come "il dataset non contiene
    valori utili per questa fattispecie".
    """
    point_value = row.point_value or Decimal(0)
    disability = _to_decimal_or_none(input_data.get("permanent_disability_percentage"))
    if disability is None:
        return Decimal(0)

    amount = point_value * disability

    if fault_reduction_enabled:
        fault = _to_decimal_or_none(input_data.get("fault_percentage"))
        if fault is not None and Decimal(0) <= fault <= Decimal(100):
            amount = amount * (Decimal(100) - fault) / Decimal(100)

    return amount


@dataclass(frozen=True)
class RangeAmounts:
    """Result of a range rule: three amounts for the same (age, disability)."""

    min_amount: Decimal
    mid_amount: Decimal
    max_amount: Decimal

    def is_monotone(self) -> bool:
        """True if min ≤ mid ≤ max. Sanity contract for any range output."""
        return self.min_amount <= self.mid_amount <= self.max_amount


def apply_amount_range_rule(
    rule: str,
    *,
    row_min: CompensationTableRow,
    row_mid: CompensationTableRow,
    row_max: CompensationTableRow,
    input_data: dict[str, Any],
    fault_reduction_enabled: bool,
) -> RangeAmounts:
    """
    Range version of `apply_amount_rule`. Operates on THREE rows
    (one per row_type) and returns three amounts.

    Caller must have verified that ``rule in RANGE_AMOUNT_RULES`` via
    `is_range_rule`. As with `apply_amount_rule`, an unknown rule
    raises `ValueError` rather than falling back silently.
    """
    if rule == "row_amount_range_direct":
        return _rule_row_amount_range_direct(
            row_min=row_min,
            row_mid=row_mid,
            row_max=row_max,
            input_data=input_data,
            fault_reduction_enabled=fault_reduction_enabled,
        )
    raise ValueError(f"Unsupported range amount_rule: {rule!r}")


def _rule_row_amount_range_direct(
    *,
    row_min: CompensationTableRow,
    row_mid: CompensationTableRow,
    row_max: CompensationTableRow,
    input_data: dict[str, Any],
    fault_reduction_enabled: bool,
) -> RangeAmounts:
    """
    Range counterpart of ``row_amount_direct``: each row's `point_value`
    is interpreted as the FINAL amount for the (age, disability) cell,
    one per row_type. Returns the three values verbatim, with optional
    fault reduction applied uniformly.

    No multiplication by disability%: as for the single-row variant, the
    cells of TUN Tabelle 2.A/2.B/2.C are precomputed totals (biological +
    moral increment), already comprehensive of the disability factor.
    """
    fault = (
        _to_decimal_or_none(input_data.get("fault_percentage")) if fault_reduction_enabled else None
    )

    def _value_of(row: CompensationTableRow) -> Decimal:
        amount = row.point_value or Decimal(0)
        if fault is not None and Decimal(0) <= fault <= Decimal(100):
            amount = amount * (Decimal(100) - fault) / Decimal(100)
        return amount

    return RangeAmounts(
        min_amount=_value_of(row_min),
        mid_amount=_value_of(row_mid),
        max_amount=_value_of(row_max),
    )


def _rule_row_amount_direct(
    *,
    row: CompensationTableRow,
    input_data: dict[str, Any],
    fault_reduction_enabled: bool,
) -> Decimal:
    """
    amount = row.point_value (interpretato come importo FINALE della cella).

    Pensata per le tabelle "comprensive" (precomputate) come la TUN
    italiana Tabella 1: la cella contiene direttamente l'importo per la
    combinazione (età, % invalidità) che il `row_match` ha trovato. Non
    moltiplichiamo di nuovo per `permanent_disability_percentage`,
    altrimenti l'importo sarebbe doppio-contato.

    Il nome del campo `point_value` è preservato per back-compat dello
    schema; la sua semantica viene determinata dall'`amount_rule` della
    formula (un campo a uso del registro, non del DB).

    Fault reduction si applica come per l'altra rule, se abilitata.
    """
    amount = row.point_value or Decimal(0)

    if fault_reduction_enabled:
        fault = _to_decimal_or_none(input_data.get("fault_percentage"))
        if fault is not None and Decimal(0) <= fault <= Decimal(100):
            amount = amount * (Decimal(100) - fault) / Decimal(100)

    return amount


# ---------------------------------------------------------------------------
# helpers parsing
# ---------------------------------------------------------------------------


def _to_int_or_none(value) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_decimal_or_none(value) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None

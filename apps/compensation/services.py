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
SUPPORTED_ENGINES: frozenset[str] = frozenset(
    {
        "italy_tun_point_value_v1",
        # France: scaffolded engine for road accident bodily injury, fed by
        # the Mornet 2024 DFP table once Studio promotes it to APPROVED.
        # Until then the engine returns ``unavailable`` on the public path
        # because the gating still requires APPROVED source/dataset/formula.
        # See ``apps/calculators/engines/france.py`` and
        # ``docs/architecture/FRANCE_ENGINE_INACTIVE_FIXTURE_ONLY.md``.
        "france_road_accident_v1",
        # Belgium: scaffolded engine for road accident bodily injury, fed
        # by the Tableau Indicatif 2020 candidate dataset once Studio
        # promotes it to APPROVED. Until then the engine returns
        # ``unavailable`` on the public path. Three amount rules are wired
        # for the engine's three pass-1 perimeters: souffrances endurées,
        # indemnité forfaitaire, prejudice de décès / affection. Vehicule
        # de remplacement is intentionally out of pass-1.
        # See ``apps/calculators/engines/belgium.py`` and
        # ``docs/architecture/BELGIUM_ENGINE_INACTIVE_FIXTURE_ONLY.md``.
        "belgium_road_accident_v1",
        # Morocco inheritance: scaffolded engine for international
        # inheritance with Moroccan elements (Moudawana Livre III faraïd
        # framework). Until Studio approves the source/dataset/formula
        # the engine returns ``unavailable`` on the public path. Pass-1
        # wires a single amount rule
        # (``morocco_inheritance_fixed_share_direct``) that reads the
        # share spec from the formula's parameters; the rule is fixture-
        # only and intentionally not a complete legal codification.
        # See ``apps/calculators/engines/morocco.py`` and
        # ``docs/architecture/MOROCCO_INHERITANCE_ENGINE_INACTIVE_FIXTURE_ONLY.md``.
        "morocco_inheritance_v1",
        # Tunisia inheritance: scaffolded engine for international
        # inheritance with Tunisian elements (Code du statut personnel
        # Livre IX + Loi n° 98-97 framework). Until Studio approves the
        # source/dataset/formula the engine returns ``unavailable`` on
        # the public path. Pass-1 wires a single amount rule
        # (``tunisia_inheritance_fixed_share_direct``) that mirrors the
        # MA dispatch family — same shape, same rational arithmetic,
        # different country activation gate.
        # See ``apps/calculators/engines/tunisia.py`` and
        # ``docs/architecture/TUNISIA_INHERITANCE_ENGINE_INACTIVE_FIXTURE_ONLY.md``.
        "tunisia_inheritance_v1",
    }
)
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
        # France DFP table (Référentiel Mornet 2024): single-row range rule.
        # The matched row provides a per-point amount in ``row.point_value``
        # and an optional ``row.extra.amount_min/amount_mid/amount_max``
        # triple. Final per-bucket amount = per_point × disability%, with
        # min/mid/max applied uniformly when distinct (Mornet today emits
        # equal min=mid=max but the range support is wired upfront).
        # See ``_rule_france_dfp_point_value_direct``.
        "france_dfp_point_value_direct",
        # Belgium Tableau Indicatif 2020 — souffrances endurées per
        # (age band × severity scale 1/7..7/7). Reads ONE row with the
        # range stored in ``row.extra.amount_min/mid/max``. Returns the
        # range verbatim with optional fault-reduction applied uniformly.
        # See ``_rule_belgium_souffrances_age_severity_direct``.
        "belgium_souffrances_age_severity_direct",
        # Belgium Tableau Indicatif 2020 — indemnité forfaitaire per age
        # (annual amount). Reads ONE row with ``row.extra.annual_amount``.
        # Optional ``incapacity_percentage`` input scales the annual
        # amount linearly (annual × incapacity / 100). The scalar is
        # broadcast across (min, mid, max). See
        # ``_rule_belgium_forfait_age_annual_direct``.
        "belgium_forfait_age_annual_direct",
        # Belgium Tableau Indicatif 2020 — prejudice de décès / affection
        # per relation_code. Reads ONE row keyed by ``relation_code`` with
        # the range stored in ``row.extra.amount_min/mid/max``. Returns
        # the range verbatim with optional fault-reduction applied
        # uniformly. See ``_rule_belgium_deces_affection_relation_direct``.
        "belgium_deces_affection_relation_direct",
        # Morocco inheritance fixed-share rule (fixture-only). Reads the
        # share specification from ``formula.parameters["shares"]`` (a
        # mapping ``heir_class → "p/q"`` for fixed fractions, or
        # ``"remainder_2_to_1"`` for the residual quote between sons /
        # daughters under the classic 2:1 ratio). Computes per-heir
        # rational allocations from the heirs structure provided in
        # ``input_data["heirs"]`` and, when ``estate_value`` is supplied,
        # converts each share into a Decimal amount. This rule does NOT
        # belong to the scalar / range / single-row-range families: it
        # consumes the formula directly and emits a structured
        # ``InheritanceShareResult`` from
        # :func:`apply_amount_inheritance_share_rule`.
        # See ``_rule_morocco_inheritance_fixed_share_direct``.
        "morocco_inheritance_fixed_share_direct",
        # Tunisia inheritance fixed-share rule (fixture-only). Twin of
        # the MA rule: same ``parameters["shares"]`` shape (``heir_class
        # → "p/q"`` for fixed fractions, ``"remainder_2_to_1"`` for the
        # residual quote between sons / daughters), same exact rational
        # arithmetic via ``fractions.Fraction``. Distinct entry point
        # so the country activation gate stays per-jurisdiction:
        # promoting the Moroccan source does not silently activate
        # Tunisia and vice versa. Reads ``input_data["heirs"]`` and the
        # optional ``estate_value``. Detects an invalid share spec
        # (negative residual when the fixed shares overshoot unity) and
        # surfaces it via the engine's gating chain.
        # See ``_rule_tunisia_inheritance_fixed_share_direct``.
        "tunisia_inheritance_fixed_share_direct",
    }
)

# Subset of SUPPORTED_AMOUNT_RULES that operate on three rows (min/mid/max)
# instead of one. The calculator dispatches differently for these.
RANGE_AMOUNT_RULES: frozenset[str] = frozenset({"row_amount_range_direct"})

# Subset of SUPPORTED_AMOUNT_RULES that operate on **one** row but emit a
# (min, mid, max) triple — typically because the row carries a range under
# its ``extra`` JSON, not because the dataset is split into three row_types.
# Used by France DFP and the three Belgium pass-1 rules; can host future
# single-row range rules.
SINGLE_ROW_RANGE_AMOUNT_RULES: frozenset[str] = frozenset(
    {
        "france_dfp_point_value_direct",
        "belgium_souffrances_age_severity_direct",
        "belgium_forfait_age_annual_direct",
        "belgium_deces_affection_relation_direct",
    }
)


def is_range_rule(rule: str) -> bool:
    """Return True iff ``rule`` is a range rule (3 rows in, 3 amounts out)."""
    return rule in RANGE_AMOUNT_RULES


def is_single_row_range_rule(rule: str) -> bool:
    """Return True iff ``rule`` is a single-row range rule (1 row in, 3
    amounts out). The matched row carries the range either via
    ``row.extra.amount_min/mid/max`` or by collapsing to a single value
    duplicated across min/mid/max."""
    return rule in SINGLE_ROW_RANGE_AMOUNT_RULES


# Subset of SUPPORTED_AMOUNT_RULES that operate on a structured input
# (e.g. an ``heirs`` mapping) rather than a single matched row. These
# rules read their share specification directly from
# ``formula.parameters`` and emit a per-heir-class allocation map.
INHERITANCE_SHARE_AMOUNT_RULES: frozenset[str] = frozenset(
    {
        "morocco_inheritance_fixed_share_direct",
        "tunisia_inheritance_fixed_share_direct",
    }
)


def is_inheritance_share_rule(rule: str) -> bool:
    """Return True iff ``rule`` belongs to the inheritance-share family."""
    return rule in INHERITANCE_SHARE_AMOUNT_RULES


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
    # Belgium Tableau Indicatif 2020 keys (case-sensitive equality on
    # ``row.extra``). Used by the three pass-1 BE rules; the FR/IT
    # engines never declare these fields in their ``row_match`` and are
    # therefore unaffected.
    if "severity_scale" in fields:
        wanted = (input_data.get("severity_scale") or "").strip()
        if not wanted:
            return False
        if str((row.extra or {}).get("severity_code") or "").strip() != wanted:
            return False
    if "relation_code" in fields:
        wanted = (input_data.get("relation_code") or "").strip()
        if not wanted:
            return False
        if str((row.extra or {}).get("relation_code") or "").strip() != wanted:
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


def apply_amount_single_row_range_rule(
    rule: str,
    *,
    row: CompensationTableRow,
    input_data: dict[str, Any],
    fault_reduction_enabled: bool,
) -> RangeAmounts:
    """Single-row range version of ``apply_amount_rule``.

    Reads ONE matched row, returns three amounts (``min``, ``mid``, ``max``).
    The triple typically comes from ``row.extra.amount_min/mid/max`` when
    the upstream extractor emits a range; if those are absent the rule
    falls back to ``row.point_value`` duplicated across all three.

    Caller must have verified ``rule in SINGLE_ROW_RANGE_AMOUNT_RULES`` via
    :func:`is_single_row_range_rule`. Unknown rules raise ``ValueError``,
    matching :func:`apply_amount_rule` and :func:`apply_amount_range_rule`.
    """
    if rule == "france_dfp_point_value_direct":
        return _rule_france_dfp_point_value_direct(
            row=row,
            input_data=input_data,
            fault_reduction_enabled=fault_reduction_enabled,
        )
    if rule == "belgium_souffrances_age_severity_direct":
        return _rule_belgium_souffrances_age_severity_direct(
            row=row,
            input_data=input_data,
            fault_reduction_enabled=fault_reduction_enabled,
        )
    if rule == "belgium_forfait_age_annual_direct":
        return _rule_belgium_forfait_age_annual_direct(
            row=row,
            input_data=input_data,
            fault_reduction_enabled=fault_reduction_enabled,
        )
    if rule == "belgium_deces_affection_relation_direct":
        return _rule_belgium_deces_affection_relation_direct(
            row=row,
            input_data=input_data,
            fault_reduction_enabled=fault_reduction_enabled,
        )
    raise ValueError(f"Unsupported single-row range amount_rule: {rule!r}")


def _rule_france_dfp_point_value_direct(
    *,
    row: CompensationTableRow,
    input_data: dict[str, Any],
    fault_reduction_enabled: bool,
) -> RangeAmounts:
    """France DFP per-point single-row range rule.

    For the Mornet 2024 DFP table (per-age × per-disability), each cell
    declares a per-point indemnity. The final per-victim amount is::

        amount_X = point_value_per_point_X × permanent_disability_percentage

    where ``point_value_per_point_X`` is taken from
    ``row.extra.amount_min/amount_mid/amount_max`` if present, otherwise
    falls back to ``row.point_value`` duplicated across the three. This
    matches the upstream Mornet extractor, which emits all three columns
    today (currently equal because Mornet publishes a point-value, not a
    range — the range support is wired upfront so future per-cell
    fourchettes can flow through unchanged).

    Fault reduction is applied uniformly to min/mid/max when the formula
    declares ``fault_reduction=true`` and a valid ``fault_percentage`` is
    in the input. ``permanent_disability_percentage`` missing or zero
    yields zero across the triple — the calculator never invents a
    fallback.
    """
    disability = _to_decimal_or_none(input_data.get("permanent_disability_percentage"))
    if disability is None:
        return RangeAmounts(
            min_amount=Decimal(0),
            mid_amount=Decimal(0),
            max_amount=Decimal(0),
        )

    extra = row.extra or {}
    fallback = row.point_value or Decimal(0)
    pp_min = _to_decimal_or_none(extra.get("amount_min"))
    pp_mid = _to_decimal_or_none(extra.get("amount_mid"))
    pp_max = _to_decimal_or_none(extra.get("amount_max"))
    if pp_min is None:
        pp_min = fallback
    if pp_mid is None:
        pp_mid = fallback
    if pp_max is None:
        pp_max = fallback

    amount_min = pp_min * disability
    amount_mid = pp_mid * disability
    amount_max = pp_max * disability

    if fault_reduction_enabled:
        fault = _to_decimal_or_none(input_data.get("fault_percentage"))
        if fault is not None and Decimal(0) <= fault <= Decimal(100):
            factor = (Decimal(100) - fault) / Decimal(100)
            amount_min = amount_min * factor
            amount_mid = amount_mid * factor
            amount_max = amount_max * factor

    return RangeAmounts(
        min_amount=amount_min,
        mid_amount=amount_mid,
        max_amount=amount_max,
    )


@dataclass(frozen=True)
class InheritanceAllocation:
    """One heir-class allocation in an inheritance share computation.

    The fraction is exposed verbatim (``share_numerator`` /
    ``share_denominator``) so callers can render "1/8" without
    reconstructing it from a Decimal. ``amount`` is ``None`` when the
    caller did not provide ``estate_value`` — the fraction is still
    meaningful, the absolute amount simply cannot be computed.
    """

    heir_class: str
    label: str
    share_numerator: int
    share_denominator: int
    amount: Decimal | None
    head_count: int


@dataclass(frozen=True)
class InheritanceShareResult:
    """Result of an inheritance-share rule.

    ``estate_total`` is the parsed ``estate_value`` when provided; it
    is ``None`` when the input did not include one (the rule still
    succeeds but emits fractions only).

    ``residual`` is the unallocated fraction of the estate. Always
    non-negative; the engine can surface it as a warning or as an
    additional breakdown line.
    """

    estate_total: Decimal | None
    allocations: tuple[InheritanceAllocation, ...]
    residual_numerator: int
    residual_denominator: int


def apply_amount_inheritance_share_rule(
    rule: str,
    *,
    formula_params: dict[str, Any],
    input_data: dict[str, Any],
) -> InheritanceShareResult:
    """Inheritance-share dispatcher.

    Parallel to :func:`apply_amount_rule` /
    :func:`apply_amount_range_rule` /
    :func:`apply_amount_single_row_range_rule`, but for rules that
    consume the formula's ``parameters["shares"]`` directly rather than
    a matched table row.

    Caller must have verified ``rule in INHERITANCE_SHARE_AMOUNT_RULES``
    via :func:`is_inheritance_share_rule`. Unknown rules raise
    ``ValueError``.
    """
    if rule == "morocco_inheritance_fixed_share_direct":
        return _rule_morocco_inheritance_fixed_share_direct(
            formula_params=formula_params,
            input_data=input_data,
        )
    if rule == "tunisia_inheritance_fixed_share_direct":
        return _rule_tunisia_inheritance_fixed_share_direct(
            formula_params=formula_params,
            input_data=input_data,
        )
    raise ValueError(f"Unsupported inheritance-share amount_rule: {rule!r}")


class InvalidInheritanceShareSpec(ValueError):
    """Raised when a share spec is structurally invalid.

    Used today by the Tunisia rule when the sum of fixed-fraction shares
    exceeds 1, producing a negative residual the rule cannot honour. The
    engine catches this and routes to ``UNAVAILABLE`` so the formula's
    misconfiguration never leaks into a public estimate.
    """


def _rule_morocco_inheritance_fixed_share_direct(
    *,
    formula_params: dict[str, Any],
    input_data: dict[str, Any],
) -> InheritanceShareResult:
    """Morocco inheritance fixed-share rule (fixture-only).

    Computes per-heir-class allocations from a synthetic share spec.
    The shape of ``formula_params["shares"]`` is::

        {
            "spouse":          "1/8",          # fixed fraction
            "father":          "1/6",          # fixed fraction
            "mother":          "1/6",          # fixed fraction
            "sons_group":      "remainder_2_to_1",
            "daughters_group": "remainder_2_to_1",
        }

    Fixed-fraction entries are applied first; the residual fraction of
    the estate is then split between ``sons_group`` and
    ``daughters_group`` in the classic 2:1 ratio (2 parts per son, 1
    part per daughter). Only heir classes whose ``input_data["heirs"]``
    count is > 0 receive an allocation.

    Notes & limits:

    - This is **not** a complete codification of Moudawana Livre III.
      Real ``faraïd`` involve hajb (exclusion), 'awl (proportional
      reduction when fixed shares exceed unity), radd (return of the
      residual to non-residuary heirs) and a far richer family-status
      taxonomy than the spec above. Activation requires legal review
      and a much wider mapping.
    - The rule expects integer counts (``int`` or castable). Strings
      that don't parse become 0.
    - Fractions are computed exactly (Python ``fractions.Fraction``)
      so 1/3 of an estate stays 1/3 — no decimal drift between sons
      and daughters.

    Output: ``InheritanceShareResult`` with one ``InheritanceAllocation``
    per heir class that received a positive allocation, plus the
    residual fraction (typically zero when the spec covers all classes).
    """
    from fractions import Fraction

    shares_spec = formula_params.get("shares") or {}
    heirs_raw = input_data.get("heirs") or {}
    estate = _to_decimal_or_none(input_data.get("estate_value"))

    def _count(name: str) -> int:
        v = heirs_raw.get(name)
        try:
            n = int(v) if v not in (None, "") else 0
        except (TypeError, ValueError):
            return 0
        return max(n, 0)

    # Step 1: fixed-fraction shares. Order is preserved from the spec
    # for stable breakdown rendering.
    used = Fraction(0)
    fixed_allocations: list[tuple[str, Fraction, int]] = []
    remainder_classes: list[str] = []
    for heir_class, spec in shares_spec.items():
        if not isinstance(spec, str):
            continue
        spec_clean = spec.strip()
        if spec_clean == "remainder_2_to_1":
            remainder_classes.append(heir_class)
            continue
        if "/" not in spec_clean:
            continue
        try:
            num_str, den_str = spec_clean.split("/", 1)
            frac = Fraction(int(num_str), int(den_str))
        except (ValueError, ZeroDivisionError):
            continue
        count = _count(heir_class)
        if count <= 0:
            continue
        fixed_allocations.append((heir_class, frac, count))
        used += frac

    # Step 2: distribute residual between sons / daughters under the
    # 2:1 ratio. The hand-coded class names mirror the spec keys.
    residual = Fraction(1) - used
    if residual < 0:
        # Over-allocation: refuse to split a negative residual. The
        # engine surfaces this via the residual fraction; allocations
        # stay as the fixed fractions sum (which the engine flags).
        residual = Fraction(0)

    sons_count = _count("sons")
    daughters_count = _count("daughters")
    sons_in_remainder = "sons_group" in remainder_classes and sons_count > 0
    daughters_in_remainder = "daughters_group" in remainder_classes and daughters_count > 0
    total_parts = (2 * sons_count if sons_in_remainder else 0) + (
        daughters_count if daughters_in_remainder else 0
    )

    sons_share = Fraction(0)
    daughters_share = Fraction(0)
    if total_parts > 0 and residual > 0:
        per_part = residual / total_parts
        if sons_in_remainder:
            sons_share = per_part * 2 * sons_count
        if daughters_in_remainder:
            daughters_share = per_part * 1 * daughters_count

    allocations: list[InheritanceAllocation] = []

    def _to_amount(frac: Fraction) -> Decimal | None:
        if estate is None:
            return None
        # Fraction × Decimal: convert via numerator / denominator to
        # preserve precision; then quantize as the caller's estate
        # precision dictates.
        return estate * Decimal(frac.numerator) / Decimal(frac.denominator)

    for heir_class, frac, count in fixed_allocations:
        allocations.append(
            InheritanceAllocation(
                heir_class=heir_class,
                label=_inheritance_label(heir_class),
                share_numerator=frac.numerator,
                share_denominator=frac.denominator,
                amount=_to_amount(frac),
                head_count=count,
            )
        )
    if sons_in_remainder and sons_share > 0:
        allocations.append(
            InheritanceAllocation(
                heir_class="sons_group",
                label=_inheritance_label("sons_group"),
                share_numerator=sons_share.numerator,
                share_denominator=sons_share.denominator,
                amount=_to_amount(sons_share),
                head_count=sons_count,
            )
        )
    if daughters_in_remainder and daughters_share > 0:
        allocations.append(
            InheritanceAllocation(
                heir_class="daughters_group",
                label=_inheritance_label("daughters_group"),
                share_numerator=daughters_share.numerator,
                share_denominator=daughters_share.denominator,
                amount=_to_amount(daughters_share),
                head_count=daughters_count,
            )
        )

    final_used = used + sons_share + daughters_share
    final_residual = Fraction(1) - final_used
    if final_residual < 0:
        final_residual = Fraction(0)

    return InheritanceShareResult(
        estate_total=estate,
        allocations=tuple(allocations),
        residual_numerator=final_residual.numerator,
        residual_denominator=final_residual.denominator,
    )


def _rule_tunisia_inheritance_fixed_share_direct(
    *,
    formula_params: dict[str, Any],
    input_data: dict[str, Any],
) -> InheritanceShareResult:
    """Tunisia inheritance fixed-share rule (fixture-only).

    Twin of :func:`_rule_morocco_inheritance_fixed_share_direct`. The
    spec shape is identical: ``formula_params["shares"]`` maps each
    heir class either to a literal fraction ``"p/q"`` or to the marker
    ``"remainder_2_to_1"`` for the residual sons/daughters split.

    Two deliberate differences from the MA rule:

    1. **Strict over-allocation handling.** When the sum of fixed-
       fraction shares exceeds unity, this rule raises
       :class:`InvalidInheritanceShareSpec` instead of clamping the
       residual to zero. The TN engine catches the exception and
       routes to ``UNAVAILABLE`` with a ``shares_spec_invalid``
       diagnostic. Real Tunisian inheritance under the Code du statut
       personnel applies 'awl (proportional reduction) in this case;
       fixture-only tests must not silently mask the problem.
    2. **No residual heirs ⇒ residual stays explicit.** When fixed
       shares allocate < 1 and no class is wired to ``remainder_2_to_1``
       (or the residual classes have zero head_count), the residual is
       reported verbatim in the result rather than being absorbed
       silently. Real ``radd`` mechanics belong to the Studio mapping
       iter, not this scaffold.

    Notes & limits (same as MA):

    - Not a complete codification of Code du statut personnel, Livre IX.
    - Integer counts only; non-numeric heir entries become 0.
    - Exact rational arithmetic via ``fractions.Fraction``.
    """
    from fractions import Fraction

    shares_spec = formula_params.get("shares") or {}
    heirs_raw = input_data.get("heirs") or {}
    estate = _to_decimal_or_none(input_data.get("estate_value"))

    def _count(name: str) -> int:
        v = heirs_raw.get(name)
        try:
            n = int(v) if v not in (None, "") else 0
        except (TypeError, ValueError):
            return 0
        return max(n, 0)

    # Step 1: parse the fixed-fraction part of the spec. Note: parsing
    # uses the full spec (not just classes with head_count > 0) so an
    # over-allocation in the spec itself is detected even when some
    # heirs are absent from the case.
    used = Fraction(0)
    fixed_allocations: list[tuple[str, Fraction, int]] = []
    remainder_classes: list[str] = []
    spec_total = Fraction(0)
    for heir_class, spec in shares_spec.items():
        if not isinstance(spec, str):
            continue
        spec_clean = spec.strip()
        if spec_clean == "remainder_2_to_1":
            remainder_classes.append(heir_class)
            continue
        if "/" not in spec_clean:
            continue
        try:
            num_str, den_str = spec_clean.split("/", 1)
            frac = Fraction(int(num_str), int(den_str))
        except (ValueError, ZeroDivisionError):
            continue
        spec_total += frac
        count = _count(heir_class)
        if count <= 0:
            continue
        fixed_allocations.append((heir_class, frac, count))
        used += frac

    # Strict guard: the SPEC must not declare fixed fractions whose sum
    # exceeds 1. This is the structural invariant; do not mask it.
    if spec_total > 1:
        raise InvalidInheritanceShareSpec(
            "Sum of fixed-fraction shares exceeds 1 "
            f"({spec_total.numerator}/{spec_total.denominator}). "
            "Tunisia rule does not auto-apply 'awl; the share spec "
            "must be corrected by Studio before activation."
        )

    # Step 2: residual split between sons/daughters under 2:1.
    residual = Fraction(1) - used
    sons_count = _count("sons")
    daughters_count = _count("daughters")
    sons_in_remainder = "sons_group" in remainder_classes and sons_count > 0
    daughters_in_remainder = "daughters_group" in remainder_classes and daughters_count > 0
    total_parts = (2 * sons_count if sons_in_remainder else 0) + (
        daughters_count if daughters_in_remainder else 0
    )

    sons_share = Fraction(0)
    daughters_share = Fraction(0)
    if total_parts > 0 and residual > 0:
        per_part = residual / total_parts
        if sons_in_remainder:
            sons_share = per_part * 2 * sons_count
        if daughters_in_remainder:
            daughters_share = per_part * 1 * daughters_count

    allocations: list[InheritanceAllocation] = []

    def _to_amount(frac: Fraction) -> Decimal | None:
        if estate is None:
            return None
        return estate * Decimal(frac.numerator) / Decimal(frac.denominator)

    for heir_class, frac, count in fixed_allocations:
        allocations.append(
            InheritanceAllocation(
                heir_class=heir_class,
                label=_inheritance_label(heir_class),
                share_numerator=frac.numerator,
                share_denominator=frac.denominator,
                amount=_to_amount(frac),
                head_count=count,
            )
        )
    if sons_in_remainder and sons_share > 0:
        allocations.append(
            InheritanceAllocation(
                heir_class="sons_group",
                label=_inheritance_label("sons_group"),
                share_numerator=sons_share.numerator,
                share_denominator=sons_share.denominator,
                amount=_to_amount(sons_share),
                head_count=sons_count,
            )
        )
    if daughters_in_remainder and daughters_share > 0:
        allocations.append(
            InheritanceAllocation(
                heir_class="daughters_group",
                label=_inheritance_label("daughters_group"),
                share_numerator=daughters_share.numerator,
                share_denominator=daughters_share.denominator,
                amount=_to_amount(daughters_share),
                head_count=daughters_count,
            )
        )

    final_used = used + sons_share + daughters_share
    final_residual = Fraction(1) - final_used
    if final_residual < 0:
        final_residual = Fraction(0)

    return InheritanceShareResult(
        estate_total=estate,
        allocations=tuple(allocations),
        residual_numerator=final_residual.numerator,
        residual_denominator=final_residual.denominator,
    )


_INHERITANCE_LABELS: dict[str, str] = {
    "spouse": "Surviving spouse",
    "father": "Father",
    "mother": "Mother",
    "sons_group": "Sons (collective)",
    "daughters_group": "Daughters (collective)",
}


def _inheritance_label(heir_class: str) -> str:
    return _INHERITANCE_LABELS.get(heir_class, heir_class.replace("_", " ").title())


def _rule_belgium_souffrances_age_severity_direct(
    *,
    row: CompensationTableRow,
    input_data: dict[str, Any],
    fault_reduction_enabled: bool,
) -> RangeAmounts:
    """Belgium souffrances endurées single-row range rule.

    The matched row is keyed by (age band × severity scale 1/7..7/7) and
    carries the (min, mid, max) amount triple under
    ``row.extra.amount_min/amount_mid/amount_max``. When the upstream CSV
    publishes a single value (today the Tableau Indicatif 2020 emits
    equal min/mid/max) all three collapse to that value; the range
    support is wired upfront so future per-cell fourchettes can flow
    through unchanged.

    Falls back to ``row.point_value`` duplicated across the triple when
    ``extra`` is missing — defensive default that yields zero rather
    than crashing on a malformed row.

    Fault reduction applied uniformly when the formula declares
    ``fault_reduction=true`` and a valid ``fault_percentage`` is in
    the input.
    """
    extra = row.extra or {}
    fallback = row.point_value or Decimal(0)
    a_min = _to_decimal_or_none(extra.get("amount_min"))
    a_mid = _to_decimal_or_none(extra.get("amount_mid"))
    a_max = _to_decimal_or_none(extra.get("amount_max"))
    if a_min is None:
        a_min = fallback
    if a_mid is None:
        a_mid = fallback
    if a_max is None:
        a_max = fallback

    if fault_reduction_enabled:
        fault = _to_decimal_or_none(input_data.get("fault_percentage"))
        if fault is not None and Decimal(0) <= fault <= Decimal(100):
            factor = (Decimal(100) - fault) / Decimal(100)
            a_min = a_min * factor
            a_mid = a_mid * factor
            a_max = a_max * factor

    return RangeAmounts(min_amount=a_min, mid_amount=a_mid, max_amount=a_max)


def _rule_belgium_forfait_age_annual_direct(
    *,
    row: CompensationTableRow,
    input_data: dict[str, Any],
    fault_reduction_enabled: bool,
) -> RangeAmounts:
    """Belgium indemnité forfaitaire single-row scalar rule.

    The matched row is keyed by an age band and carries the annual
    amount under ``row.extra.annual_amount`` (fallback ``row.point_value``).
    The optional ``incapacity_percentage`` input scales the annual
    amount linearly:

        amount = annual_amount × incapacity_percentage / 100

    When ``incapacity_percentage`` is missing or zero the rule returns
    the annual amount as-is (interpreted as the 100% reference).

    The scalar is broadcast across (min, mid, max) — the Tableau
    Indicatif 2020 publishes one value per age, no per-cell fourchette.
    Fault reduction applies on top, uniformly.
    """
    extra = row.extra or {}
    annual = _to_decimal_or_none(extra.get("annual_amount"))
    if annual is None:
        annual = row.point_value or Decimal(0)

    incapacity = _to_decimal_or_none(input_data.get("incapacity_percentage"))
    if incapacity is not None and Decimal(0) < incapacity <= Decimal(100):
        scaled = annual * incapacity / Decimal(100)
    elif incapacity is not None and incapacity > Decimal(100):
        # Out-of-range incapacity → caller is the gating logic; the rule
        # itself returns zero rather than a runaway figure.
        scaled = Decimal(0)
    else:
        # No incapacity provided (or zero) → return the annual reference.
        scaled = annual

    if fault_reduction_enabled:
        fault = _to_decimal_or_none(input_data.get("fault_percentage"))
        if fault is not None and Decimal(0) <= fault <= Decimal(100):
            factor = (Decimal(100) - fault) / Decimal(100)
            scaled = scaled * factor

    return RangeAmounts(min_amount=scaled, mid_amount=scaled, max_amount=scaled)


def _rule_belgium_deces_affection_relation_direct(
    *,
    row: CompensationTableRow,
    input_data: dict[str, Any],
    fault_reduction_enabled: bool,
) -> RangeAmounts:
    """Belgium prejudice de décès / affection single-row range rule.

    The matched row is keyed by ``relation_code`` (e.g. spouse, parent,
    child) and carries the (min, mid, max) amount triple under
    ``row.extra.amount_min/amount_mid/amount_max``. Falls back to
    ``row.point_value`` duplicated across the triple when ``extra`` is
    missing.

    Fault reduction applied uniformly when the formula declares
    ``fault_reduction=true``.
    """
    extra = row.extra or {}
    fallback = row.point_value or Decimal(0)
    a_min = _to_decimal_or_none(extra.get("amount_min"))
    a_mid = _to_decimal_or_none(extra.get("amount_mid"))
    a_max = _to_decimal_or_none(extra.get("amount_max"))
    if a_min is None:
        a_min = fallback
    if a_mid is None:
        a_mid = fallback
    if a_max is None:
        a_max = fallback

    if fault_reduction_enabled:
        fault = _to_decimal_or_none(input_data.get("fault_percentage"))
        if fault is not None and Decimal(0) <= fault <= Decimal(100):
            factor = (Decimal(100) - fault) / Decimal(100)
            a_min = a_min * factor
            a_mid = a_mid * factor
            a_max = a_max * factor

    return RangeAmounts(min_amount=a_min, mid_amount=a_mid, max_amount=a_max)


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

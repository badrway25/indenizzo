"""
Generatore READ-ONLY del template CSV vuoto e del review_tasks CSV per
le voci NARRATIVE del Référentiel Mornet 2024 (le voci che NON sono
auto-estraibili in modo sicuro: SE, esthétique, agrément, sexuel,
établissement, tierce personne, scolaire, perte gains futurs,
incidence professionnelle, ecc.).

Iter: F-france-mornet-manual-fourchettes · iter1
Stato: scaffold-only — NON contiene importi. NON importa nel DB.
NON crea LegalReview/Dataset/Formula. Output: solo 2 CSV in
legal_data/sources/france/mornet_2024/ (gitignored).

Uso:
    .venv/Scripts/python.exe scripts/legal_data/seed_france_mornet_manual_fourchettes.py

Esegue:
- Crea fr-mornet-2024-manual-fourchettes-template.csv con SOLO header
  (no righe dati). Lo Studio lo copierà o riempirà inline.
- Crea fr-mornet-2024-manual-fourchettes-review_tasks.csv con UNA RIGA
  per head_of_loss con instructions, source_pages, transcription_status
  = "pending" (NESSUN importo).
"""

from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parents[2]
PDF_PATH = (
    ROOT / "legal_data" / "sources" / "france" / "downloaded" / "fr-referentiel-mornet-2024.pdf"
)
OUTPUT_DIR = ROOT / "legal_data" / "sources" / "france" / "mornet_2024"

EXPECTED_PDF_SHA256 = "2dd2e760bc057b38275a7a6de24a62c009f6d04dd79573c00ee052f4f6df72b4"

TEMPLATE_FIELDS = [
    "row_type",
    "head_of_loss_code",
    "head_of_loss_label_fr",
    "severity_code",
    "severity_label_fr",
    "victim_age_min",
    "victim_age_max",
    "amount_min",
    "amount_mid",
    "amount_max",
    "unit",
    "currency",
    "source_page",
    "source_quote_short",
    "transcription_status",
    "reviewer_notes",
    "source_note",
]

REVIEW_TASK_FIELDS = [
    "head_of_loss_code",
    "head_of_loss_label_fr",
    "expected_structure",
    "source_pages",
    "instructions",
    "transcription_status",
    "reviewer",
    "reviewer_notes",
]


# Le voci sono ordinate come in Mornet 2024 (PLAN p.3-5).
# expected_structure è un'etichetta umana per orientare lo Studio:
#   - scale_1_to_7        : tabella 1/7 -> 7/7 + Exceptionnel (8 livelli)
#   - daily_or_monthly_forfait : DFT, forfait €/jour o €/mois
#   - hourly_rate         : taux horaire (tierce personne)
#   - case_by_case        : valutazione personalizzata, no fourchette generale
#   - formula_based       : formula numerica (perte gains, capitalisation)
#   - narrative_range     : range testuale embedded nel narrativo
HEAD_OF_LOSS = [
    # Préjudices patrimoniaux temporaires (avant consolidation)
    (
        "fr_depenses_sante_actuelles",
        "Dépenses de santé actuelles (frais médicaux et assimilés)",
        "case_by_case",
        "42-43",
        (
            "Importi reali da fattura medica/CPAM/mutuelle. NON c'è "
            "fourchette indicativa dottrinale. Lasciare vuoto: il "
            "calcolatore userà i valori del caso concreto, non un barème."
        ),
    ),
    (
        "fr_perte_gains_professionnels_actuels",
        "Perte de gains professionnels actuels (perte de revenus avant consolidation)",
        "formula_based",
        "43-45",
        (
            "Calcolo basato su salaire net x durée arrêt de travail. "
            "Mornet pp.43-45 fornisce esempi di calcolo non fourchette. "
            "Compilare solo se lo Studio identifica un coefficiente "
            "indicativo riutilizzabile (es. taux moyen IJ)."
        ),
    ),
    (
        "fr_prejudice_scolaire_universitaire_formation",
        "Préjudice scolaire, universitaire ou de formation",
        "case_by_case",
        "45-46",
        (
            "Mornet non fornisce fourchette numerica fissa. "
            "Compilare solo se lo Studio identifica una pratica "
            "giurisprudenziale stabile (es. forfait année redoublée). "
            "Altrimenti lasciare in pending."
        ),
    ),
    (
        "fr_frais_divers",
        "Frais divers (avant consolidation)",
        "case_by_case",
        "46-48",
        (
            "Voce eterogenea (transports, gardiennage animaux, etc.). "
            "Compilare solo voci stabili individuate dallo Studio. "
            "Altrimenti lasciare in pending."
        ),
    ),
    # Préjudices patrimoniaux permanents (après consolidation)
    (
        "fr_depenses_sante_futures",
        "Dépenses de santé futures",
        "case_by_case",
        "50-51",
        (
            "Stima basata su devis prospettici / capitalisation. "
            "Nessuna fourchette indicativa Mornet. Lasciare in pending "
            "salvo voci ricorrenti standardizzate."
        ),
    ),
    (
        "fr_perte_gains_professionnels_futurs",
        "Perte de gains professionnels futurs",
        "formula_based",
        "51-55",
        (
            "Calcolo: (revenus avant - revenus après) x coefficient "
            "capitalisation Gazette du Palais. Nessuna fourchette diretta "
            "in Mornet; il valore deriva dal barème di capitalisation "
            "(già estratto in iter Gazette 2022). Lasciare in pending: il "
            "calcolatore deve combinare Gazette + revenus utente."
        ),
    ),
    (
        "fr_incidence_professionnelle",
        "Incidence professionnelle",
        "case_by_case",
        "55-58",
        (
            "Componente non economica del préjudice professionnel. "
            "Mornet non fornisce barème: indemnité forfaitaire variabile "
            "tra ~10.000-100.000 € secondo gravità. Lo Studio può "
            "compilare fourchette di larga massima dietro propria "
            "responsabilità."
        ),
    ),
    (
        "fr_frais_logement_adapte",
        "Frais de logement adapté",
        "case_by_case",
        "59-65",
        ("Importi reali da devis architettonici. Nessuna fourchette. " "Lasciare in pending."),
    ),
    (
        "fr_frais_vehicule_adapte",
        "Frais de véhicule adapté",
        "case_by_case",
        "59-65",
        ("Importi reali da devis aménagement. Nessuna fourchette. " "Lasciare in pending."),
    ),
    (
        "fr_assistance_tierce_personne",
        "Assistance tierce personne",
        "hourly_rate",
        "59-65",
        (
            "Taux horaire indicativo + maggiorazioni notturne / dimanche / "
            "jours fériés. Mornet cita il SMIC come base e talvolta "
            "fourchette ~14-25 €/heure. Se lo Studio identifica taux "
            "stabile, compilare con unit=EUR_per_hour. Altrimenti lasciare "
            "in pending."
        ),
    ),
    # Préjudices extra-patrimoniaux temporaires (avant consolidation)
    (
        "fr_deficit_fonctionnel_temporaire",
        "Déficit fonctionnel temporaire (DFT)",
        "daily_or_monthly_forfait",
        "65-66",
        (
            "Forfait giornaliero/mensile per la durata del DFT, di solito "
            "20-30 €/jour per DFT total, prorata pro DFT partial 25/50/75%. "
            "Lo Studio compila se identifica forfait stabile, con "
            "unit=EUR_per_day."
        ),
    ),
    (
        "fr_souffrances_endurees",
        "Souffrances endurées",
        "scale_1_to_7",
        "66-68",
        (
            "Tabella 8 livelli a p.68: 1/7 jusqu'à 2.000; 2/7 2.000-4.000; "
            "3/7 4.000-8.000; 4/7 8.000-20.000; 5/7 20.000-35.000; "
            "6/7 35.000-50.000; 7/7 50.000-80.000; Exceptionnel 80.000+. "
            "Lo Studio trascrive in 8 righe (severity_code = 1_7 .. 7_7 + "
            "exceptional), unit=EUR. Per 1/7 lasciare amount_min vuoto "
            "(jusqu'à 2.000)."
        ),
    ),
    (
        "fr_angoisse_mort_imminente",
        "Préjudice d'angoisse de mort imminente",
        "case_by_case",
        "67-68",
        (
            "Indennità autonoma cumulabile con SE (Ch. Mixte 25/3/2022). "
            "Mornet non fornisce fourchette fissa. Lasciare in pending "
            "salvo identificazione di pratica costante."
        ),
    ),
    (
        "fr_esthetique_temporaire",
        "Préjudice esthétique temporaire",
        "scale_1_to_7",
        "68",
        (
            "Stessa scala 1/7 -> 7/7 dell'esthétique permanent (Mornet "
            "rinvia spesso alla stessa cotazione médico-légale). Lo Studio "
            "verifica se Mornet 2024 cita una fourchette specifica per la "
            "fase temporanea o se applica la stessa di p.72."
        ),
    ),
    # Préjudices extra-patrimoniaux permanents
    # (DFP è già stato auto-estratto in iter precedente — fr-mornet-2024-dfp-per-age-disability.csv)
    (
        "fr_esthetique_permanent",
        "Préjudice esthétique permanent",
        "scale_1_to_7",
        "71-72",
        (
            "Tabella 8 livelli a p.72: identica a SE (1/7 jusqu'à 2.000 -> "
            "Exceptionnel 80.000+). Lo Studio trascrive 8 righe parallele a "
            "fr_souffrances_endurees, severity_code = 1_7 .. exceptional, "
            "unit=EUR."
        ),
    ),
    (
        "fr_prejudice_agrement",
        "Préjudice d'agrément",
        "case_by_case",
        "71-73",
        (
            "Trouble lié à l'impossibilité de pratiquer activité spécifique "
            "sportive/loisir. Valutazione per attività concreta. Mornet non "
            "fornisce fourchette: la giurisprudenza varia ampiamente. "
            "Lasciare in pending salvo voci stabili identificate dallo Studio."
        ),
    ),
    (
        "fr_prejudice_sexuel",
        "Préjudice sexuel",
        "case_by_case",
        "73-74",
        (
            "3 componenti (acte sexuel / plaisir / procréation). Mornet "
            "discute giurisprudenza (Civ.2 17/6/2010) ma non propone "
            "fourchette generale. Lasciare in pending."
        ),
    ),
    (
        "fr_prejudice_etablissement",
        "Préjudice d'établissement",
        "case_by_case",
        "73-75",
        (
            "Riservato a vittime giovani con handicap grave (perte de chance "
            "de fonder famille/avoir enfants). Mornet sottolinea il "
            "carattere strettamente personalizzato. Lasciare in pending."
        ),
    ),
    (
        "fr_prejudices_permanents_exceptionnels",
        "Préjudices permanents exceptionnels",
        "case_by_case",
        "75-76",
        (
            "Voce atypica per circostanze speciali (catastrofi, attentati). "
            "Per definizione non parametrabile. Lasciare in pending."
        ),
    ),
    # Préjudices extra-patrimoniaux évolutifs (hors consolidation)
    (
        "fr_prejudices_evolutifs_hors_consolidation",
        "Préjudices évolutifs hors consolidation",
        "case_by_case",
        "75-76",
        ("Maladie évolutive (ex. exposition amiante). Caso per caso. " "Lasciare in pending."),
    ),
    # Préjudice d'impréparation médicale
    (
        "fr_prejudice_impreparation_medicale",
        "Préjudice d'impréparation en matière médicale",
        "case_by_case",
        "76-77",
        (
            "Défaut d'information sur risque di un acte médical. "
            "Indennità simbolica/réduite. Lasciare in pending salvo "
            "valori stabili identificati."
        ),
    ),
    # Section 4 — préjudices des victimes indirectes (vittima vivante)
    (
        "fr_perte_revenus_proches_victime_vivante",
        "Perte de revenus des proches (victime survivante)",
        "formula_based",
        "89",
        (
            "Calcolo: contribution aux charges du foyer x durée. "
            "Combina con Gazette del barème di capitalisation. "
            "Lasciare in pending: il calcolatore userà Gazette + dati utente."
        ),
    ),
    (
        "fr_frais_divers_proches_victime_vivante",
        "Frais divers des proches (victime survivante)",
        "case_by_case",
        "89",
        (
            "Trasferte, hôtel, restauration durante l'ospedalizzazione. "
            "Importi reali. Lasciare in pending."
        ),
    ),
    (
        "fr_prejudice_affection_victime_vivante",
        "Préjudice d'affection (victime survivante, hors décès)",
        "case_by_case",
        "90",
        (
            "Mornet pp.90 NON è la stessa tabella di p.94 (che è per il "
            "décès, già auto-estratta). Per victime vivante con handicap "
            "grave la giurisprudenza è più variabile. Lasciare in pending "
            "salvo identificazione fourchette stabile."
        ),
    ),
    (
        "fr_prejudices_extra_patrimoniaux_exceptionnels_proches",
        "Préjudices extra-patrimoniaux exceptionnels des proches (victime survivante)",
        "case_by_case",
        "90",
        "Voce atypica. Lasciare in pending.",
    ),
    # Chapitre 4 — préjudices subis en cas de décès
    # (préjudice d'affection en cas de décès è già auto-estratto da p.94)
    (
        "fr_prejudice_accompagnement_deces",
        "Préjudice d'accompagnement (en cas de décès)",
        "case_by_case",
        "93-95",
        (
            "Trouble dans les conditions d'existence des proches durante "
            "la malattia traumatica fino al décès. Compilare solo se "
            "Mornet 2024 cita fourchette specifica."
        ),
    ),
    (
        "fr_frais_obseques",
        "Frais d'obsèques",
        "case_by_case",
        "95",
        (
            "Importi reali (cap raisonnable in giurisprudenza ~5.000 €). "
            "Compilare con unit=EUR se lo Studio identifica cap stabile."
        ),
    ),
    (
        "fr_frais_divers_deces",
        "Frais divers (en cas de décès)",
        "case_by_case",
        "95",
        "Voce eterogenea. Lasciare in pending.",
    ),
    (
        "fr_perte_revenus_proches_deces",
        "Pertes de revenus des proches (en cas de décès)",
        "formula_based",
        "96-100",
        (
            "Calcolo: contribution du défunt aux revenus du foyer x "
            "coefficient capitalisation. Combina con Gazette. Lasciare "
            "in pending."
        ),
    ),
]


def main() -> int:
    if not PDF_PATH.exists():
        print(f"[FATAL] PDF non trovato: {PDF_PATH}")
        return 2
    pdf_sha256 = hashlib.sha256(PDF_PATH.read_bytes()).hexdigest()
    if pdf_sha256 != EXPECTED_PDF_SHA256:
        print(f"[FATAL] hash PDF non corrisponde: {pdf_sha256!r} != {EXPECTED_PDF_SHA256!r}")
        return 2

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Template — header only, no rows
    template_path = OUTPUT_DIR / "fr-mornet-2024-manual-fourchettes-template.csv"
    with template_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TEMPLATE_FIELDS)
        w.writeheader()

    # 2. Review tasks — one row per head_of_loss, transcription_status=pending
    review_path = OUTPUT_DIR / "fr-mornet-2024-manual-fourchettes-review_tasks.csv"
    with review_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REVIEW_TASK_FIELDS)
        w.writeheader()
        for code, label, structure, pages, instructions in HEAD_OF_LOSS:
            w.writerow(
                {
                    "head_of_loss_code": code,
                    "head_of_loss_label_fr": label,
                    "expected_structure": structure,
                    "source_pages": pages,
                    "instructions": instructions,
                    "transcription_status": "pending",
                    "reviewer": "",
                    "reviewer_notes": "",
                }
            )

    # 3. Summary JSON
    summary = {
        "iter": "F-france-mornet-manual-fourchettes · iter1",
        "pdf_sha256": pdf_sha256,
        "pdf_slug": "fr-referentiel-mornet-2024",
        "totals": {
            "template_rows": 0,
            "review_tasks_rows": len(HEAD_OF_LOSS),
        },
        "files_written": [
            template_path.name,
            review_path.name,
        ],
        "note": (
            "Template intenzionalmente vuoto (solo header). Lo Studio "
            "compila riga-per-riga via review_tasks. Nessun importo è "
            "stato dedotto automaticamente: anche le voci con tabella "
            "embedded nel PDF (souffrances endurées p.68 + esthétique "
            "permanent p.72) sono lasciate al review umano per evitare "
            "qualsiasi rischio di mis-extraction."
        ),
    }
    (OUTPUT_DIR / "manual_fourchettes_seed_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"[OK] PDF sha256 = {pdf_sha256}")
    print(f"[OK] Template scritto (solo header): {template_path.name}")
    print(f"[OK] Review tasks scritti ({len(HEAD_OF_LOSS)} righe pending): " f"{review_path.name}")
    print("[OK] Summary JSON: manual_fourchettes_seed_summary.json")
    print(f"[OK] Tutti i file in {OUTPUT_DIR.relative_to(ROOT)} (gitignored)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

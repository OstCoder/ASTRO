
import csv
import math
import re
import time
from pathlib import Path

import lightkurve as lk
from astroquery.vizier import Vizier

# ==========================================
# TJSEF Ellipsoidal Binary Research
# PHASE 2: Automated Catalog Expansion
# ==========================================

# Configuration
GOAL_NEW_SYSTEMS = 15
MAX_ARCHIVE_CHECKS = 80
MIN_SPOC_SECTORS = 3
SECTORS_PER_SYSTEM = 3
MIN_CATALOG_SCORE = 0.99
CATALOG_ROW_LIMIT = 2000
PAUSE_BETWEEN_CHECKS_SECONDS = 0.25

CATALOG = "J/MNRAS/522/29/table3"

FEATURES_DIR = Path("features")
FEATURES_DIR.mkdir(exist_ok=True)

MASTER_FILE = FEATURES_DIR / "binary_features.csv"
CHECKPOINT_FILE = FEATURES_DIR / "expansion_search_log.csv"
SHORTLIST_FILE = FEATURES_DIR / "expansion_candidates.csv"
CONFIG_FILE = FEATURES_DIR / "expansion_target_config.csv"

LOG_COLUMNS = [
    "tic_id",
    "score",
    "catalog_period_days",
    "catalog_t0_bjd",
    "n_spoc_sectors",
    "spoc_sectors",
    "status",
    "note"
]

CONFIG_COLUMNS = [
    "tic_id",
    "sector",
    "pipeline",
    "catalog_period_days",
    "catalog_t0_bjd",
    "catalog_score"
]


# ==========================================
# Helper Functions
# ==========================================

def read_csv_rows(path):
    if not path.exists():
        return []

    with path.open("r", newline="") as file:
        return list(csv.DictReader(file))


def write_csv_atomic(path, fieldnames, rows):
    temp = path.with_name(path.name + ".tmp")

    with temp.open("w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)

    temp.replace(path)


def to_float(value):
    try:
        result = float(value)

    except (TypeError, ValueError, OverflowError):
        return None

    return result if math.isfinite(result) else None


# ==========================================
# STEP 1: Retrieve Catalog Candidates
# ==========================================

def catalog_candidates():

    vizier = Vizier(
        columns=["TIC", "Score", "Porb", "T0"],
        row_limit=CATALOG_ROW_LIMIT
    )

    vizier.VIZIER_SERVER = "vizier.cfa.harvard.edu"
    vizier.TIMEOUT = 60

    results = vizier.query_constraints(
        catalog=CATALOG,
        Score=f">{MIN_CATALOG_SCORE}"
    )

    if len(results) == 0 or len(results[0]) == 0:
        raise RuntimeError(
            "No catalog rows returned. Check VizieR."
        )

    table = results[0]

    required = {"TIC", "Score", "Porb", "T0"}

    missing = required - set(table.colnames)

    if missing:
        raise RuntimeError(
            f"Missing catalog columns: {sorted(missing)}"
        )

    candidates = {}

    for row in table:

        try:
            tic = int(row["TIC"])
        except (ValueError, TypeError):
            continue

        score = to_float(row["Score"])
        period = to_float(row["Porb"])
        t0 = to_float(row["T0"])

        if (
            score is None
            or period is None
            or period <= 0
            or t0 is None
            or score <= MIN_CATALOG_SCORE
        ):
            continue

        if (
            tic not in candidates
            or score > candidates[tic]["score"]
        ):
            candidates[tic] = {
                "tic_id": tic,
                "score": score,
                "catalog_period_days": period,
                "catalog_t0_bjd": t0
            }

    return sorted(
        candidates.values(),
        key=lambda item: (
            -item["score"],
            item["tic_id"]
        )
    )


# ==========================================
# STEP 2: Discover TESS-SPOC Sectors
# ==========================================

def get_sectors(tic):

    results = lk.search_lightcurve(
        f"TIC {tic}",
        mission="TESS",
        author="TESS-SPOC"
    )

    sectors = set()

    if len(results) == 0:
        return []

    for mission in results.table["mission"]:

        match = re.search(
            r"Sector\s*0*(\d+)",
            str(mission),
            re.IGNORECASE
        )

        if match:
            sectors.add(int(match.group(1)))

    return sorted(sectors)


# ==========================================
# STEP 3: Prepare Qualified Target List
# ==========================================

def write_outputs(log_rows, already_done):

    qualified = [
        row for row in log_rows
        if (
            row["status"] == "qualified"
            and int(row["tic_id"]) not in already_done
        )
    ]

    qualified.sort(
        key=lambda row: (
            -float(row["score"]),
            -int(row["n_spoc_sectors"])
        )
    )

    chosen = qualified[:GOAL_NEW_SYSTEMS]

    write_csv_atomic(
        SHORTLIST_FILE,
        LOG_COLUMNS,
        qualified
    )

    configurations = []

    for item in chosen:

        sectors = [
            int(sector)
            for sector in item["spoc_sectors"].split(";")
            if sector
        ]

        for sector in sectors[:SECTORS_PER_SYSTEM]:

            configurations.append({
                "tic_id": item["tic_id"],
                "sector": sector,
                "pipeline": "TESS-SPOC",
                "catalog_period_days":
                    item["catalog_period_days"],
                "catalog_t0_bjd":
                    item["catalog_t0_bjd"],
                "catalog_score":
                    item["score"]
            })

    write_csv_atomic(
        CONFIG_FILE,
        CONFIG_COLUMNS,
        configurations
    )

    return qualified, chosen, configurations


# ==========================================
# STEP 4: Run Automated Discovery
# ==========================================

def main():

    master_rows = read_csv_rows(MASTER_FILE)

    if not MASTER_FILE.exists() or not master_rows:
        raise RuntimeError(
            f"Existing dataset not found: {MASTER_FILE}"
        )

    already_done = {
        int(row["tic_id"])
        for row in master_rows
    }

    log_rows = read_csv_rows(CHECKPOINT_FILE)

    log_by_tic = {
        int(row["tic_id"]): row
        for row in log_rows
    }

    print("\n====================================")
    print("TJSEF AUTOMATED CATALOG EXPANSION")
    print("====================================")

    print(f"Existing systems: {len(already_done)}")
    print(f"New systems target: {GOAL_NEW_SYSTEMS}")

    print(
        "\nMetadata search only. "
        "No light curves will be downloaded."
    )

    candidates = catalog_candidates()

    print(
        f"\nCatalog candidates found: "
        f"{len(candidates)}"
    )

    archive_checks = 0

    for candidate in candidates:

        tic = candidate["tic_id"]

        # Skip previously analyzed systems
        if tic in already_done:
            continue

        old = log_by_tic.get(tic)

        # Avoid repeating completed archive searches
        if old and old["status"] in (
            "qualified",
            "insufficient_coverage"
        ):
            continue

        qualified_count = sum(
            1 for row in log_by_tic.values()
            if (
                row["status"] == "qualified"
                and int(row["tic_id"]) not in already_done
            )
        )

        if qualified_count >= GOAL_NEW_SYSTEMS:
            break

        if archive_checks >= MAX_ARCHIVE_CHECKS:
            break

        archive_checks += 1

        try:

            sectors = get_sectors(tic)

            if len(sectors) >= MIN_SPOC_SECTORS:
                status = "qualified"
            else:
                status = "insufficient_coverage"

            note = ""

            print(
                f"[{archive_checks:02d}] "
                f"TIC {tic}: "
                f"{len(sectors)} TESS-SPOC sectors "
                f"-> {status}",
                flush=True
            )

        except Exception as error:

            sectors = []
            status = "search_error"

            note = (
                f"{type(error).__name__}: "
                f"{str(error)[:160]}"
            )

            print(
                f"[{archive_checks:02d}] "
                f"TIC {tic}: ERROR ({note})",
                flush=True
            )

        log_by_tic[tic] = {
            "tic_id": tic,
            "score": candidate["score"],
            "catalog_period_days":
                candidate["catalog_period_days"],
            "catalog_t0_bjd":
                candidate["catalog_t0_bjd"],
            "n_spoc_sectors": len(sectors),
            "spoc_sectors": ";".join(
                map(str, sectors)
            ),
            "status": status,
            "note": note
        }

        # Save progress after every target
        write_csv_atomic(
            CHECKPOINT_FILE,
            LOG_COLUMNS,
            list(log_by_tic.values())
        )

        time.sleep(
            PAUSE_BETWEEN_CHECKS_SECONDS
        )

    # ======================================
    # STEP 5: Export Results
    # ======================================

    qualified, chosen, configurations = (
        write_outputs(
            list(log_by_tic.values()),
            already_done
        )
    )

    print("\n====================================")
    print("EXPANSION SEARCH SUMMARY")
    print("====================================")

    print(
        f"New archive searches: "
        f"{archive_checks}"
    )

    print(
        f"Qualified new systems: "
        f"{len(qualified)}"
    )

    print(
        f"Selected new systems: "
        f"{len(chosen)}"
    )

    print(
        f"Target-sector configurations: "
        f"{len(configurations)}"
    )

    print(f"\nCheckpoint: {CHECKPOINT_FILE}")
    print(f"Candidate list: {SHORTLIST_FILE}")
    print(f"Batch configuration: {CONFIG_FILE}")

    if len(chosen) < GOAL_NEW_SYSTEMS:
        print(
            "\nPartial shortlist generated. "
            "More archive checks may be needed."
        )

    print(
        "\nOriginal research files "
        "were not modified."
    )


if __name__ == "__main__":
    main()

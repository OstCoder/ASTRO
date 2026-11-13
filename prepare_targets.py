
import csv
from pathlib import Path

import lightkurve as lk
from astroquery.vizier import Vizier

# ==========================================
# TJSEF Ellipsoidal Binary Research
# STEP 38: Prepare Targets Automatically
# ==========================================

# Candidates selected from Green et al. (2023)
candidates = [
    372446253,
    384999832,
    408041054,
    383622574,
    138098461,
    100522274,
    48755579
]

catalog_id = "J/MNRAS/522/29/table3"

vizier = Vizier(
    columns=["**"],
    row_limit=10
)

vizier.VIZIER_SERVER = "vizier.cfa.harvard.edu"
vizier.TIMEOUT = 30

Path("features").mkdir(exist_ok=True)

prepared_targets = []

print("\n====================================")
print("TJSEF AUTOMATED TARGET PREPARATION")
print("====================================")

for tic in candidates:

    print(f"\n--- TIC {tic} ---")

    # Retrieve published parameters
    try:
        catalog_results = vizier.query_constraints(
            catalog=catalog_id,
            TIC=str(tic)
        )

        if len(catalog_results) == 0:
            print("No catalog match. Skipping.")
            continue

        table = catalog_results[0]

        if len(table) != 1:
            print("Unexpected catalog match count. Skipping.")
            continue

        row = table[0]

        period = float(row["Porb"])
        t0_bjd = float(row["T0"])
        score = float(row["Score"])

        print(f"Catalog score: {score:.6f}")
        print(f"Orbital period: {period:.6f} days")
        print(f"Reference epoch: {t0_bjd:.6f} BJD")

        # Find available TESS-SPOC observations
        results = lk.search_lightcurve(
            f"TIC {tic}",
            mission="TESS",
            author="TESS-SPOC"
        )

        sectors = sorted({
            int(str(mission).split()[-1])
            for mission in results.table["mission"]
        }) if len(results) > 0 else []

        print(f"Available TESS-SPOC sectors: {sectors}")

        if len(sectors) < 3:
            print("Insufficient sector coverage. Skipping.")
            continue

        # Choose three distinct sectors
        selected_sectors = sectors[:3]

        print(f"Selected sectors: {selected_sectors}")

        for sector in selected_sectors:
            prepared_targets.append({
                "tic_id": tic,
                "sector": sector,
                "pipeline": "TESS-SPOC",
                "catalog_period_days": period,
                "catalog_t0_bjd": t0_bjd,
                "catalog_score": score
            })

    except Exception as error:
        print(f"Error preparing TIC {tic}: {error}")

# Export target configuration
output_file = Path("features/target_config.csv")

fieldnames = [
    "tic_id",
    "sector",
    "pipeline",
    "catalog_period_days",
    "catalog_t0_bjd",
    "catalog_score"
]

with open(output_file, "w", newline="") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(prepared_targets)

print("\n====================================")
print("PREPARATION COMPLETE")
print("====================================")

print(f"Target-sector configurations: {len(prepared_targets)}")
print(f"Configuration saved: {output_file}")

print("\nNo light curves were downloaded or analyzed.")

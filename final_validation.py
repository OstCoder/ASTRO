
import csv
import math
from collections import defaultdict
from pathlib import Path

feature_file = Path("features/binary_features.csv")

with feature_file.open(newline="") as file:
    records = list(csv.DictReader(file))

groups = defaultdict(list)
issues = []

required_fields = [
    "catalog_period_days",
    "measured_photometric_period_days",
    "candidate_orbital_period_days",
    "H1", "H2", "H3",
    "H2_H1_ratio", "rmse", "r_squared"
]

for row in records:
    tic = row["tic_id"]
    sector = row["sector"]
    groups[tic].append(row)

    for field in required_fields:
        try:
            value = float(row[field])
            if not math.isfinite(value):
                issues.append(
                    f"TIC {tic} S{sector}: nonfinite {field}"
                )
        except (ValueError, KeyError, TypeError):
            issues.append(
                f"TIC {tic} S{sector}: invalid {field}"
            )

    try:
        catalog = float(row["catalog_period_days"])
        candidate = float(row["candidate_orbital_period_days"])
        r2 = float(row["r_squared"])
        h1 = float(row["H1"])
        h2 = float(row["H2"])

        relative_error = abs(candidate - catalog) / catalog

        if relative_error > 0.01:
            issues.append(
                f"TIC {tic} S{sector}: period error >1%"
            )

        if r2 < 0.90:
            issues.append(
                f"TIC {tic} S{sector}: R² below 0.90"
            )

        if h2 <= h1:
            issues.append(
                f"TIC {tic} S{sector}: H2 not dominant"
            )

    except (ValueError, KeyError, TypeError, ZeroDivisionError):
        pass

print("\n====================================")
print("TJSEF FINAL NUMERICAL VALIDATION")
print("====================================")

print(f"\nTotal records: {len(records)}")
print(f"Distinct systems: {len(groups)}")

for tic, rows in sorted(groups.items()):
    sectors = sorted(int(r["sector"]) for r in rows)
    print(f"TIC {tic}: sectors {sectors}")

print("\n--- Validation Findings ---")

if issues:
    for issue in issues:
        print("FLAG:", issue)
else:
    print("No issues detected by the preliminary checks.")

print(f"\nTotal flags: {len(issues)}")
print("\nValidation finished.")

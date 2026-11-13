
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path

# ==========================================
# TJSEF Scientific Quality Control
# Phase 2: Cross-Sector Consistency
# ==========================================

SOURCE = Path("features/binary_features.csv")
OUTPUT = Path("features/scientific_qc")

OUTPUT.mkdir(parents=True, exist_ok=True)

R2_THRESHOLD = 0.90

# Exploratory threshold, not a formal
# astrophysical rejection criterion.
H2_CV_THRESHOLD = 10.0


def read_csv(path):
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path, rows, columns):
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=columns
        )
        writer.writeheader()
        writer.writerows(rows)


def variation(values):
    mean = statistics.mean(values)

    sd = (
        statistics.stdev(values)
        if len(values) > 1 else 0.0
    )

    cv = (
        100 * sd / abs(mean)
        if mean != 0 else math.nan
    )

    return mean, sd, cv


def main():

    records = read_csv(SOURCE)

    groups = defaultdict(list)
    sector_results = []

    for row in records:
        tic = row["tic_id"]
        sector = int(row["sector"])

        groups[tic].append(row)

        r2 = float(row["r_squared"])

        flags = []

        if not math.isfinite(r2):
            flags.append("INVALID_R2")
        elif r2 < R2_THRESHOLD:
            flags.append("LOW_R2")

        sector_results.append({
            "tic_id": tic,
            "sector": sector,
            "r_squared": r2,
            "H1": row["H1"],
            "H2": row["H2"],
            "H2_H1_ratio": row["H2_H1_ratio"],
            "status": (
                "REVIEW" if flags else "SCREEN_PASS"
            ),
            "flags": ";".join(flags)
        })

    system_results = []

    for tic, rows in sorted(groups.items()):

        h1 = [float(r["H1"]) for r in rows]
        h2 = [float(r["H2"]) for r in rows]

        ratios = [
            float(r["H2_H1_ratio"])
            for r in rows
        ]

        mean_h1, sd_h1, cv_h1 = variation(h1)
        mean_h2, sd_h2, cv_h2 = variation(h2)

        mean_ratio, sd_ratio, cv_ratio = (
            variation(ratios)
        )

        low_r2_count = sum(
            float(r["r_squared"]) < R2_THRESHOLD
            for r in rows
        )

        flags = []

        if low_r2_count:
            flags.append("HAS_LOW_R2_SECTORS")

        if cv_h2 > H2_CV_THRESHOLD:
            flags.append("HIGH_H2_VARIATION")

        if len(rows) < 3:
            flags.append("FEWER_THAN_3_SECTORS")

        system_results.append({
            "tic_id": tic,
            "n_sectors": len(rows),
            "mean_H1": mean_h1,
            "sd_H1": sd_h1,
            "cv_H1_percent": cv_h1,
            "mean_H2": mean_h2,
            "sd_H2": sd_h2,
            "cv_H2_percent": cv_h2,
            "mean_ratio": mean_ratio,
            "sd_ratio": sd_ratio,
            "cv_ratio_percent": cv_ratio,
            "low_r2_sectors": low_r2_count,
            "status": (
                "REVIEW" if flags else "SCREEN_PASS"
            ),
            "flags": ";".join(flags)
        })

    sector_file = OUTPUT / "sector_qc.csv"
    system_file = OUTPUT / "system_qc.csv"

    write_csv(
        sector_file,
        sector_results,
        list(sector_results[0].keys())
    )

    write_csv(
        system_file,
        system_results,
        list(system_results[0].keys())
    )

    print("\n====================================")
    print("TJSEF SCIENTIFIC QUALITY CONTROL")
    print("====================================")

    print(f"Systems analyzed: {len(groups)}")
    print(f"Sector records: {len(records)}")

    print("\n--- System-Level Findings ---")

    for row in system_results:

        print(
            f"TIC {row['tic_id']}: "
            f"H2 CV={row['cv_H2_percent']:.2f}% | "
            f"Low-R2 sectors={row['low_r2_sectors']} | "
            f"{row['status']}"
        )

    review_systems = sum(
        row["status"] == "REVIEW"
        for row in system_results
    )

    print("\n--- Summary ---")

    print(f"Systems requiring review: {review_systems}")
    print(
        f"Systems passing current screens: "
        f"{len(system_results) - review_systems}"
    )

    print(f"\nSector QC saved: {sector_file}")
    print(f"System QC saved: {system_file}")

    print("\nOriginal dataset was not modified.")
    print(
        "Screen passes are preliminary, "
        "not scientific acceptance decisions."
    )


if __name__ == "__main__":
    main()
    

import csv
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ==========================================
# TJSEF Ellipsoidal Binary Research
# STEP 28: Multi-Sector Statistical Comparison
# ==========================================

tic_id = 388183492

# Read previously calculated features
feature_file = Path("features/binary_features.csv")

with open(feature_file, "r", newline="") as file:
    reader = csv.DictReader(file)
    rows = [
        row for row in reader
        if int(row["tic_id"]) == tic_id
    ]

# Sort measurements by TESS sector
rows.sort(key=lambda row: int(row["sector"]))

if len(rows) < 3:
    raise RuntimeError(
        "At least three sector records are required."
    )

sectors = np.array([
    int(row["sector"]) for row in rows
])

# Features to compare across sectors
features = {
    "Photometric Period": "measured_photometric_period_days",
    "H1": "H1",
    "H2": "H2",
    "H3": "H3",
    "H2/H1": "H2_H1_ratio",
    "RMSE": "rmse",
    "R-squared": "r_squared"
}

print("\n====================================")
print("MULTI-SECTOR STATISTICAL COMPARISON")
print("====================================")
print(f"Target: TIC {tic_id}")
print(f"Sectors: {list(sectors)}")

# Create the output folder
Path("features").mkdir(exist_ok=True)
Path("plots").mkdir(exist_ok=True)

summary_rows = []

for name, column in features.items():

    values = np.array([
        float(row[column]) for row in rows
    ])

    # Descriptive statistics
    mean = np.mean(values)
    standard_deviation = np.std(values, ddof=1)

    coefficient_of_variation = (
        standard_deviation / abs(mean) * 100
        if mean != 0 else np.nan
    )

    minimum = np.min(values)
    maximum = np.max(values)

    print(f"\n--- {name} ---")
    print(f"Mean: {mean:.8f}")
    print(f"Standard deviation: {standard_deviation:.8f}")
    print(f"Coefficient of variation: {coefficient_of_variation:.3f}%")
    print(f"Minimum: {minimum:.8f}")
    print(f"Maximum: {maximum:.8f}")

    summary_rows.append({
        "tic_id": tic_id,
        "feature": name,
        "n_sectors": len(values),
        "mean": mean,
        "sample_std": standard_deviation,
        "cv_percent": coefficient_of_variation,
        "minimum": minimum,
        "maximum": maximum
    })

    # Plot each feature across sectors
    plt.figure(figsize=(8, 4))
    plt.plot(sectors, values, marker="o")
    plt.axhline(mean, linestyle="--", label="Mean")
    plt.xticks(sectors)
    plt.xlabel("TESS Sector")
    plt.ylabel(name)
    plt.title(f"{name} Across TESS Sectors")
    plt.legend()
    plt.tight_layout()

    filename = column.replace("/", "_")
    plt.savefig(
        f"plots/TIC_{tic_id}_sector_comparison_{filename}.png",
        dpi=300
    )
    plt.close()

# Save statistics to CSV
summary_file = Path(
    f"features/TIC_{tic_id}_sector_statistics.csv"
)

with open(summary_file, "w", newline="") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=list(summary_rows[0].keys())
    )

    writer.writeheader()
    writer.writerows(summary_rows)

print("\n--- Export Complete ---")
print(f"Statistics saved: {summary_file}")
print(f"Features compared: {len(features)}")
print(f"Sectors analyzed: {len(sectors)}")

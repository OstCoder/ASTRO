
import csv
import subprocess
import sys
from pathlib import Path

# ==========================================
# TJSEF PHASE 2: Expansion Pilot
# ==========================================

config_file = Path(
    "features/expansion_target_config.csv"
)

with config_file.open(newline="") as file:
    targets = list(csv.DictReader(file))

if not targets:
    raise RuntimeError("No expansion targets found.")

# Select the first new candidate
selected_tic = targets[0]["tic_id"]

pilot_targets = [
    row for row in targets
    if row["tic_id"] == selected_tic
]

print("\n====================================")
print("TJSEF EXPANSION PILOT")
print("====================================")
print(f"Target: TIC {selected_tic}")
print(f"Sectors to process: {len(pilot_targets)}")

successful = 0
failed = 0

for target in pilot_targets:

    sector = target["sector"]

    print(
        f"\nProcessing TIC {selected_tic}, "
        f"Sector {sector}",
        flush=True
    )

    command = [
        sys.executable,
        "main.py",
        "--tic", target["tic_id"],
        "--sector", sector,
        "--period",
        target["catalog_period_days"],
        "--t0",
        target["catalog_t0_bjd"]
    ]

    result = subprocess.run(
        command,
        check=False
    )

    if result.returncode == 0:
        successful += 1
    else:
        failed += 1

print("\n====================================")
print("EXPANSION PILOT SUMMARY")
print("====================================")

print(f"Successful: {successful}")
print(f"Failed: {failed}")
print(f"Target: TIC {selected_tic}")
print("Pilot complete.")

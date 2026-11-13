
import csv
import subprocess
import sys
from pathlib import Path

# ==========================================
# TJSEF Automated Batch Analysis
# ==========================================

config_file = Path("features/target_config.csv")

with open(config_file, newline="") as file:
    targets = list(csv.DictReader(file))

print("\n--- TJSEF Batch Analysis ---")
print(f"Configurations loaded: {len(targets)}")

successful = []
failed = []

for target in targets:

    tic = target["tic_id"]
    sector = target["sector"]

    print(f"\nProcessing TIC {tic}, Sector {sector}")

    command = [
        sys.executable,
        "main.py",
        "--tic", tic,
        "--sector", sector,
        "--period", target["catalog_period_days"],
        "--t0", target["catalog_t0_bjd"]
    ]

    result = subprocess.run(
        command,
        check=False
    )

    if result.returncode == 0:
        successful.append((tic, sector))
    else:
        failed.append((tic, sector))

print("\n====================================")
print("BATCH ANALYSIS SUMMARY")
print("====================================")

print(f"Successful: {len(successful)}")
print(f"Failed: {len(failed)}")

for tic, sector in failed:
    print(f"FAILED: TIC {tic}, Sector {sector}")

print("\nBatch processing finished.")

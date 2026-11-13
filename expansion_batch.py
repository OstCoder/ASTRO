
import csv
import subprocess
import sys
from pathlib import Path

# ==========================================
# TJSEF PHASE 2: Resumable Batch Processing
# ==========================================

CONFIG = Path("features/expansion_target_config.csv")
MASTER = Path("features/binary_features.csv")
FAILURE_LOG = Path("features/expansion_failures.csv")

# Process six new sector configurations per run
# Set to None later for all remaining records.
MAX_NEW_PER_RUN = 6


def read_csv(path):
    if not path.exists():
        return []

    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def key(row):
    return (
        str(row["tic_id"]).strip(),
        str(int(row["sector"])),
        str(row["pipeline"]).strip()
    )


def completed_keys():
    return {
        key(row)
        for row in read_csv(MASTER)
    }


def main():
    if not CONFIG.exists():
        raise FileNotFoundError(CONFIG)

    targets = read_csv(CONFIG)

    if not targets:
        raise RuntimeError("Expansion configuration is empty.")

    print("\n====================================", flush=True)
    print("TJSEF RESUMABLE EXPANSION BATCH", flush=True)
    print("====================================", flush=True)

    print(f"Configurations: {len(targets)}", flush=True)

    completed = completed_keys()

    pending = [
        row for row in targets
        if key(row) not in completed
    ]

    print(f"Already completed: {len(targets) - len(pending)}")
    print(f"Pending: {len(pending)}")

    if MAX_NEW_PER_RUN is not None:
        pending = pending[:MAX_NEW_PER_RUN]

    print(f"Processing this run: {len(pending)}", flush=True)

    success = 0
    failures = []

    for i, target in enumerate(pending, 1):
        tic = target["tic_id"]
        sector = target["sector"]

        print(
            f"\n[{i}/{len(pending)}] "
            f"TIC {tic}, Sector {sector}",
            flush=True
        )

        command = [
            sys.executable,
            "main.py",
            "--tic", tic,
            "--sector", sector,
            "--period", target["catalog_period_days"],
            "--t0", target["catalog_t0_bjd"]
        ]

        try:
            result = subprocess.run(command, check=False)

            # Confirm that a feature record was actually saved
            if (
                result.returncode == 0
                and key(target) in completed_keys()
            ):
                success += 1
                print("SUCCESS", flush=True)
            else:
                failures.append({
                    "tic_id": tic,
                    "sector": sector,
                    "reason": f"Exit code {result.returncode}"
                })
                print("FAILED", flush=True)

        except Exception as error:
            failures.append({
                "tic_id": tic,
                "sector": sector,
                "reason": str(error)
            })
            print(f"ERROR: {error}", flush=True)

    if failures:
        with FAILURE_LOG.open("w", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["tic_id", "sector", "reason"]
            )
            writer.writeheader()
            writer.writerows(failures)

    final_rows = read_csv(MASTER)

    print("\n====================================")
    print("EXPANSION BATCH SUMMARY")
    print("====================================")

    print(f"Successful this run: {success}")
    print(f"Failed this run: {len(failures)}")
    print(f"Total feature records: {len(final_rows)}")

    systems = {row["tic_id"] for row in final_rows}
    print(f"Total distinct systems: {len(systems)}")

    remaining = [
        row for row in targets
        if key(row) not in completed_keys()
    ]

    print(f"Remaining configurations: {len(remaining)}")

    if failures:
        print(f"Failure log: {FAILURE_LOG}")

    print("\nBatch finished.")


if __name__ == "__main__":
    main()

"""TJSEF pilot photometric dataset: consolidate and visualize existing results.

Run from the TJSEF-Ellipsoidal-Binaries project root:
    python final_report.py

Reads features/binary_features.csv without modifying it.
"""

import csv
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

INPUT = Path("features/binary_features.csv")
OUT = Path("features/final_report")
PLOTS = OUT / "plots"
EXPECTED_SYSTEMS = 5
EXPECTED_SECTORS_EACH = 3

NUMERIC = (
    "n_measurements", "catalog_period_days", "measured_photometric_period_days",
    "candidate_orbital_period_days", "H1", "H2", "H3", "H2_H1_ratio",
    "baseline_flux", "rmse", "r_squared",
)
FEATURES = ("H1", "H2", "H3", "H2_H1_ratio", "rmse", "r_squared")


def load_rows(path):
    if not path.is_file():
        raise FileNotFoundError(f"Missing input file: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"tic_id", "sector", "pipeline", *NUMERIC}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing CSV columns: {', '.join(sorted(missing))}")
        rows = []
        seen = set()
        for line_num, raw in enumerate(reader, start=2):
            row = dict(raw)
            row["tic_id"] = str(row["tic_id"]).strip()
            row["pipeline"] = str(row["pipeline"]).strip()
            row["sector"] = int(row["sector"])
            if not row["tic_id"] or not row["pipeline"]:
                raise ValueError(f"Line {line_num}: blank TIC ID or pipeline")
            key = (row["tic_id"], row["sector"], row["pipeline"])
            if key in seen:
                raise ValueError(f"Duplicate target/sector/pipeline at line {line_num}: {key}")
            seen.add(key)
            for field in NUMERIC:
                row[field] = float(row[field])
                if not math.isfinite(row[field]):
                    raise ValueError(f"Line {line_num}: nonfinite {field}")
            if row["catalog_period_days"] <= 0 or row["n_measurements"] <= 0:
                raise ValueError(f"Line {line_num}: period or measurement count must be positive")
            if any(row[f] < 0 for f in ("H1", "H2", "H3", "rmse")):
                raise ValueError(f"Line {line_num}: negative amplitude/RMSE")
            rows.append(row)
    if not rows:
        raise ValueError("Input CSV has no records")
    return rows


def write_csv(path, rows, columns):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def sample_std(values):
    return float(np.std(values, ddof=1)) if len(values) >= 2 else float("nan")


def main():
    rows = load_rows(INPUT)
    groups = defaultdict(list)
    for row in rows:
        groups[row["tic_id"]].append(row)
    ordered_tics = sorted(groups, key=int)
    warnings = []
    if len(groups) != EXPECTED_SYSTEMS:
        warnings.append(f"Expected {EXPECTED_SYSTEMS} systems; found {len(groups)}")
    for tic in ordered_tics:
        if len(groups[tic]) != EXPECTED_SECTORS_EACH:
            warnings.append(f"TIC {tic}: expected {EXPECTED_SECTORS_EACH} sectors, found {len(groups[tic])}")
        catalog_values = {r["catalog_period_days"] for r in groups[tic]}
        if len(catalog_values) != 1:
            warnings.append(f"TIC {tic}: inconsistent catalog periods across sectors")
        for r in groups[tic]:
            if abs(r["candidate_orbital_period_days"] / r["catalog_period_days"] - 1) > 0.01:
                warnings.append(f"TIC {tic} sector {r['sector']}: candidate period differs >1% from catalog")
            if r["r_squared"] < 0.90:
                warnings.append(f"TIC {tic} sector {r['sector']}: R² <0.90")
            if r["H2"] <= r["H1"]:
                warnings.append(f"TIC {tic} sector {r['sector']}: H₂ not greater than H₁")

    summaries = []
    for tic in ordered_tics:
        subset = sorted(groups[tic], key=lambda x: x["sector"])
        summary = {
            "tic_id": tic,
            "sectors": ";".join(str(r["sector"]) for r in subset),
            "n_sectors": len(subset),
            "total_valid_measurements": int(sum(r["n_measurements"] for r in subset)),
            "catalog_period_days": subset[0]["catalog_period_days"],
        }
        for field in ("measured_photometric_period_days", "candidate_orbital_period_days", *FEATURES):
            vals = np.array([r[field] for r in subset], dtype=float)
            summary[f"{field}_mean"] = float(np.mean(vals))
            summary[f"{field}_sd_across_sectors"] = sample_std(vals)
            summary[f"{field}_cv_percent"] = (100 * sample_std(vals) / abs(np.mean(vals))) if np.mean(vals) != 0 else float("nan")
        summary["max_candidate_period_absolute_error_days"] = max(
            abs(r["candidate_orbital_period_days"] - r["catalog_period_days"]) for r in subset
        )
        summaries.append(summary)

    OUT.mkdir(parents=True, exist_ok=True)
    PLOTS.mkdir(parents=True, exist_ok=True)
    columns = list(summaries[0])
    write_csv(OUT / "system_summary.csv", summaries, columns)
    write_csv(OUT / "sector_features_copy.csv", rows, list(rows[0]))

    # Mean harmonic amplitudes across sectors: comparisons of H1 and H2.
    x = np.arange(len(summaries))
    fig, ax = plt.subplots(figsize=(11, 5.5))
    width = 0.36
    for offset, field, label in [(-width / 2, "H1", "H₁"), (width / 2, "H2", "H₂")]:
        vals = [s[f"{field}_mean"] for s in summaries]
        errors = [s[f"{field}_sd_across_sectors"] for s in summaries]
        ax.bar(x + offset, vals, width, yerr=errors, capsize=3, label=label)
    ax.set_xticks(x, [f"TIC {s['tic_id']}" for s in summaries], rotation=25, ha="right")
    ax.set_ylabel("Harmonic amplitude (normalized flux)")
    ax.set_title("Mean harmonic amplitudes by binary system")
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS / "harmonic_amplitudes.png", dpi=250)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    ratio_means = [s["H2_H1_ratio_mean"] for s in summaries]
    ratio_sd = [s["H2_H1_ratio_sd_across_sectors"] for s in summaries]
    ax.bar([s["tic_id"] for s in summaries], ratio_means, yerr=ratio_sd, capsize=4)
    ax.set_ylabel("Mean H₂/H₁ (dimensionless)")
    ax.set_xlabel("TIC ID")
    ax.set_title("Sector-averaged harmonic amplitude ratios")
    fig.tight_layout()
    fig.savefig(PLOTS / "harmonic_ratios.png", dpi=250)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 6))
    for tic in ordered_tics:
        subset = groups[tic]
        ax.scatter(
            [r["catalog_period_days"] for r in subset],
            [r["candidate_orbital_period_days"] for r in subset],
            label=f"TIC {tic}", s=38,
        )
    periods = [r["catalog_period_days"] for r in rows] + [r["candidate_orbital_period_days"] for r in rows]
    pmin, pmax = min(periods), max(periods)
    margin = max((pmax - pmin) * 0.06, 0.01)
    ax.plot([pmin - margin, pmax + margin], [pmin - margin, pmax + margin], linestyle="--", label="Perfect agreement")
    ax.set_xlim(pmin - margin, pmax + margin)
    ax.set_ylim(pmin - margin, pmax + margin)
    ax.set_xlabel("Published orbital period (days)")
    ax.set_ylabel("2 × Lomb–Scargle photometric period (days)")
    ax.set_title("Preliminary orbital-period agreement")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(PLOTS / "period_agreement.png", dpi=250)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    for tic in ordered_tics:
        subset = sorted(groups[tic], key=lambda row: row["sector"])
        ax.scatter([f"{tic}\nS{r['sector']}" for r in subset], [r["r_squared"] for r in subset], label=f"TIC {tic}")
    ax.axhline(0.90, linestyle="--", label="Screening threshold: R² = 0.90")
    ax.set_ylabel("Fourier fit R²")
    ax.set_xlabel("Target and TESS sector")
    ax.set_title("Three-harmonic Fourier fit quality")
    ax.tick_params(axis="x", labelrotation=60)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(PLOTS / "fit_quality.png", dpi=250)
    plt.close(fig)

    warning_text = "\n".join(f"- {w}" for w in warnings) if warnings else "- None under these preliminary screening rules"
    report = f"""# TJSEF Preliminary Photometric Dataset Report

Generated (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

## Scope

- Distinct TIC systems: {len(groups)}
- TESS sector records: {len(rows)}
- Input: `{INPUT}` (not modified)
- Outputs: `system_summary.csv`, `sector_features_copy.csv`, and four graphs in `plots/`

## Processing methodology

The previously generated sector records used TESS-SPOC light curves, removal of missing values, per-sector median normalization, a Lomb–Scargle photometric period search (0.2–3 days), a doubled-period candidate, phase folding using catalog orbital period and reference epoch, an unweighted least-squares fit with three Fourier harmonics, and calculation of H₁, H₂, H₃, H₂/H₁, RMSE, and R². The present script aggregates these already-computed features; it does not reprocess light curves.

System-level means are arithmetic means of sector values. The reported standard deviations use sample SD (ddof=1), and CV is 100 × SD / |mean|. These reflect *between-sector descriptive variation*, not measurement error bars or formal confidence intervals. The error bars on mean-feature plots are between-sector SDs.

The mean of the sector-by-sector H₂/H₁ ratios is not generally equal to the ratio of mean H₂ to mean H₁. This report uses the former.

## Preliminary screening flags

{warning_text}

## Important scientific limitations

1. Five catalog-selected candidates are a pilot sample, not a statistically representative sample of formation pathways.
2. Sector median normalization alone does not constitute tested detrending or systematics removal. TESS data products and quality-mask choices may differ across sectors.
3. No per-point flux uncertainties or uncertainty-weighted Fourier fitting have been incorporated; fitted amplitudes and periods lack robust inferential uncertainties.
4. Fourier H₂ dominance and close agreement between the doubled photometric period and catalog orbital period support internal consistency but do not prove classification, system geometry, or formation history.
5. R² and RMSE assess fit quality, not astrophysical model validity. Compare different sectors cautiously because noise, cadence count, and instrument conditions can differ.
6. Catalog reference epoch/period, contamination from nearby stars, eclipses, orbital-period aliases, and time-system conventions should be independently checked before physical inference.
7. Roche-lobe properties, mass ratios, physical modeling, evolutionary labels, and hypothesis testing are **not** performed here.

## Output files

- `features/final_report/system_summary.csv`: one row per system, means, between-sector SD, CV, and max period difference
- `features/final_report/sector_features_copy.csv`: copy of the input feature table
- `features/final_report/plots/harmonic_amplitudes.png`
- `features/final_report/plots/harmonic_ratios.png`
- `features/final_report/plots/period_agreement.png`
- `features/final_report/plots/fit_quality.png`
"""
    (OUT / "README.md").write_text(report, encoding="utf-8")

    print("\n--- TJSEF FINAL PHOTOMETRIC REPORT ---")
    print(f"Systems: {len(groups)} | Sector records: {len(rows)}")
    for s in summaries:
        print(f"TIC {s['tic_id']}: sectors {s['sectors']}, "
              f"mean H2/H1={s['H2_H1_ratio_mean']:.3f}, "
              f"mean R²={s['r_squared_mean']:.4f}")
    print(f"Preliminary screening warnings: {len(warnings)}")
    for w in warnings:
        print(f"  WARNING: {w}")
    print(f"\nReport directory: {OUT}")
    print("Original input CSV was not modified.")


if __name__ == "__main__":
    main()

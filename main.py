"""TJSEF TESS light-curve analysis; one TIC/sector per execution.

Example:
python main.py --tic 470123809 --sector 18 --period 0.982388 --t0 2458925.614269
"""
import argparse
import csv
from pathlib import Path

import lightkurve as lk
import matplotlib.pyplot as plt
import numpy as np
from astropy.timeseries import LombScargle


def arguments():
    parser = argparse.ArgumentParser(description="TJSEF TESS photometry pipeline")
    parser.add_argument("--tic", type=int, default=388183492, help="TESS Input Catalog ID")
    parser.add_argument("--sector", type=int, default=5, help="TESS observing sector")
    parser.add_argument("--period", type=float, default=0.711983, help="Published orbital period (days)")
    parser.add_argument("--t0", type=float, default=2458461.578613, help="Published reference epoch (BJD)")
    parser.add_argument("--pipeline", default="TESS-SPOC", help="Light curve author")
    args = parser.parse_args()
    if args.tic <= 0 or args.sector <= 0 or not np.isfinite(args.period) or args.period <= 0 or not np.isfinite(args.t0):
        parser.error("TIC, sector, period and T0 must be valid; period must be positive")
    return args


def as_numeric(values):
    return np.asarray(np.ma.filled(np.ma.asarray(values, dtype=float), np.nan), dtype=float)


def save_plot(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def main():
    args = arguments()
    tic_number, sector = args.tic, args.sector
    tic_id = f"TIC {tic_number}"
    pipeline = args.pipeline
    catalog_orbital_period = args.period
    catalog_t0_btjd = args.t0 - 2457000
    prefix = f"TIC_{tic_number}_sector{sector}"

    for folder in ("data", "plots", "features"):
        Path(folder).mkdir(parents=True, exist_ok=True)

    print("\n--- Target Information ---")
    print(f"Target: {tic_id}")
    print(f"TESS Sector: {sector}")
    print(f"Processing pipeline: {pipeline}")
    print(f"Catalog orbital period: {catalog_orbital_period:.6f} days")
    print(f"Catalog T0: {args.t0:.6f} BJD")

    # 1. Download a single sector from the requested processing pipeline.
    results = lk.search_lightcurve(tic_id, mission="TESS", sector=sector, author=pipeline)
    if len(results) == 0:
        raise RuntimeError(f"No {pipeline} light curves found for {tic_id}, sector {sector}")
    lc = results[0].download()
    if lc is None:
        raise RuntimeError("Light curve download failed")
    print(f"\nOriginal measurements: {len(lc)}")

    # 2. Remove unavailable flux samples and normalize by median.
    normalized_lc = lc.remove_nans().normalize()
    time = as_numeric(normalized_lc.time.value)
    flux = as_numeric(normalized_lc.flux.value)
    valid = np.isfinite(time) & np.isfinite(flux)
    time, flux = time[valid], flux[valid]
    if len(time) < 10:
        raise RuntimeError("Insufficient valid measurements")
    print(f"Valid measurements: {len(flux)}")

    normalized_file = Path("data") / f"{prefix}_normalized.csv"
    np.savetxt(normalized_file, np.column_stack((time, flux)),
               delimiter=",", header="time_btjd,normalized_flux", comments="")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(time, flux, linewidth=0.7)
    ax.set(xlabel="Time (BTJD)", ylabel="Normalized Flux",
           title=f"Normalized Light Curve: {tic_id} - Sector {sector}")
    save_plot(fig, f"plots/{prefix}_normalized.png")
    print(f"Normalized data saved: {normalized_file}")

    # 3. Search for photometric periodicity.
    frequency, power = LombScargle(time, flux).autopower(
        minimum_frequency=1 / 3.0,
        maximum_frequency=1 / 0.2,
        samples_per_peak=20,
    )
    photometric_period = 1 / frequency[np.argmax(power)]
    orbital_period_candidate = 2 * photometric_period
    period_difference = abs(orbital_period_candidate - catalog_orbital_period)
    print("\n--- Period Analysis ---")
    print(f"Photometric period: {photometric_period:.6f} days")
    print(f"Double-period candidate: {orbital_period_candidate:.6f} days")
    print(f"Catalog orbital period: {catalog_orbital_period:.6f} days")
    print(f"Absolute difference: {period_difference:.6f} days")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(1 / frequency, power)
    ax.axvline(photometric_period, color="red", linestyle="--", label="Measured photometric period")
    ax.axvline(catalog_orbital_period / 2, color="green", linestyle=":", label="Half catalog orbital period")
    ax.set(xlabel="Period (days)", ylabel="Lomb-Scargle Power",
           title=f"Periodogram: {tic_id} - Sector {sector}")
    ax.legend()
    save_plot(fig, f"plots/{prefix}_periodogram.png")

    # 4. Fold on published orbital period. T0 is BJD; time uses BTJD.
    phase = ((time - catalog_t0_btjd) / catalog_orbital_period) % 1
    order = np.argsort(phase)
    np.savetxt(f"data/{prefix}_phase_folded.csv",
               np.column_stack((phase[order], flux[order])),
               delimiter=",", header="orbital_phase,normalized_flux", comments="")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(phase, flux, s=5, alpha=0.5)
    ax.set(xlabel="Orbital Phase (0 to 1)", ylabel="Normalized Flux",
           title=f"Phase-Folded Light Curve: {tic_id} - Sector {sector}")
    save_plot(fig, f"plots/{prefix}_phase_folded.png")
    print(f"\n--- Phase Folding Complete ---\nPhase-folded measurements: {len(phase)}")

    # 5. Fourier series: C + sum_n[A_n cos(2 pi n phase) + B_n sin(...)].
    harmonics = 3
    cols = [np.ones_like(phase)]
    for n in range(1, harmonics + 1):
        cols.extend([np.cos(2 * np.pi * n * phase), np.sin(2 * np.pi * n * phase)])
    X = np.column_stack(cols)
    coefficients, _, _, _ = np.linalg.lstsq(X, flux, rcond=None)
    C = coefficients[0]
    amplitudes = []
    print(f"\n--- Fourier Harmonic Analysis ---\nBaseline flux C: {C:.8f}")
    for n in range(1, harmonics + 1):
        A_n, B_n = coefficients[2 * n - 1:2 * n + 1]
        H_n = np.hypot(A_n, B_n)
        amplitudes.append(H_n)
        print(f"\nHarmonic {n}:\nA{n}: {A_n:.8f}\nB{n}: {B_n:.8f}\nH{n}: {H_n:.8f}")
    H1, H2, H3 = amplitudes
    ratio = H2 / H1 if H1 > 0 else np.nan
    print(f"\n--- Key Research Features ---\nH1: {H1:.8f}\nH2: {H2:.8f}\nH2/H1: {ratio:.6f}")

    phase_model = np.linspace(0, 1, 1000)
    model_cols = [np.ones_like(phase_model)]
    for n in range(1, harmonics + 1):
        model_cols.extend([np.cos(2 * np.pi * n * phase_model),
                           np.sin(2 * np.pi * n * phase_model)])
    flux_model = np.column_stack(model_cols) @ coefficients
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(phase, flux, s=4, alpha=0.3, label="TESS observations")
    ax.plot(phase_model, flux_model, color="red", linewidth=2, label="Fourier fit")
    ax.set(xlabel="Orbital Phase", ylabel="Normalized Flux",
           title=f"Fourier Harmonic Fit: {tic_id} - Sector {sector}")
    ax.legend()
    save_plot(fig, f"plots/{prefix}_fourier_fit.png")

    # 6. Residual goodness-of-fit diagnostics.
    residuals = flux - X @ coefficients
    rmse = np.sqrt(np.mean(residuals ** 2))
    ss_total = np.sum((flux - np.mean(flux)) ** 2)
    r_squared = 1 - np.sum(residuals ** 2) / ss_total if ss_total > 0 else np.nan
    print(f"\n--- Fourier Fit Quality ---\nRMSE: {rmse:.8f}\nR-squared: {r_squared:.6f}")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.scatter(phase, residuals, s=4, alpha=0.4)
    ax.axhline(0, color="red", linestyle="--")
    ax.set(xlabel="Orbital Phase", ylabel="Flux Residual",
           title=f"Fourier Residuals: {tic_id} - Sector {sector}")
    save_plot(fig, f"plots/{prefix}_residuals.png")

    # 7. Preserve other targets/sectors while replacing an existing matching record.
    feature_file = Path("features/binary_features.csv")
    features = {
        "tic_id": tic_number,
        "sector": sector,
        "pipeline": pipeline,
        "n_measurements": len(flux),
        "catalog_period_days": catalog_orbital_period,
        "measured_photometric_period_days": photometric_period,
        "candidate_orbital_period_days": orbital_period_candidate,
        "H1": H1,
        "H2": H2,
        "H3": H3,
        "H2_H1_ratio": ratio,
        "baseline_flux": C,
        "rmse": rmse,
        "r_squared": r_squared,
    }
    existing_rows = []
    if feature_file.exists():
        with feature_file.open(newline="") as f:
            existing_rows = list(csv.DictReader(f))
    existing_rows = [
        row for row in existing_rows
        if not (str(row["tic_id"]) == str(tic_number)
                and str(row["sector"]) == str(sector)
                and row["pipeline"] == pipeline)
    ]
    existing_rows.append(features)
    # Keep existing CSV columns compatible with the earlier pipeline.
    fieldnames = list(features.keys())
    with feature_file.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing_rows)
    print(f"\n--- Feature Export Complete ---\nFeature file: {feature_file}")
    print(f"Total target-sector records: {len(existing_rows)}")
    print(f"\nSector {sector} processing completed successfully!")


if __name__ == "__main__":
    main()

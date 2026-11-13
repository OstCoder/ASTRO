
import lightkurve as lk
import numpy as np

tic_id = "TIC 364768528"
sectors = [14, 15, 16]

print("\n--- TESS Quality and Missing-Flux Audit ---")

for sector in sectors:
    results = lk.search_lightcurve(
        tic_id,
        mission="TESS",
        sector=sector,
        author="TESS-SPOC"
    )

    if len(results) == 0:
        print(f"Sector {sector}: No data found")
        continue

    lc = results[0].download(quality_bitmask="none")

    if lc is None:
        print(f"Sector {sector}: Download failed")
        continue

    quality = np.asarray(lc["quality"], dtype=int)

    flux = np.ma.asarray(lc.flux.value, dtype=float)
    flux_values = np.ma.filled(flux, np.nan)
    finite = np.isfinite(flux_values)

    print(f"\n--- Sector {sector} ---")
    print(f"Total observations: {len(lc)}")
    print(f"Finite flux: {np.sum(finite)}")
    print(f"Missing flux: {np.sum(~finite)}")

    print(f"Flagged with finite flux: "
          f"{np.sum((quality != 0) & finite)}")

    print(f"Flagged with missing flux: "
          f"{np.sum((quality != 0) & ~finite)}")

    print(f"Unflagged with missing flux: "
          f"{np.sum((quality == 0) & ~finite)}")

    for flag in [4096, 32768]:
        selected = (quality & flag) != 0

        print(
            f"Bit {flag}: "
            f"{np.sum(selected)} observations, "
            f"{np.sum(selected & ~finite)} missing flux"
        )

print("\nQuality audit complete.")

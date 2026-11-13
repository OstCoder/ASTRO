
import lightkurve as lk
import numpy as np

# ==========================================
# TJSEF Ellipsoidal Binary Research
# STEP 29: Data Quality Assessment
# ==========================================

tic_id = "TIC 364768528"

sectors = [14, 15, 16]

print("\n====================================")
print("TESS DATA QUALITY ASSESSMENT")
print("====================================")

for sector in sectors:

    print(f"\n--- Sector {sector} ---")

    results = lk.search_lightcurve(
        tic_id,
        mission="TESS",
        sector=sector,
        author="TESS-SPOC"
    )

    if len(results) == 0:
        print("No data available.")
        continue

    lc = results[0].download()

    if lc is None:
        print("Download unsuccessful.")
        continue

    # Original observation count
    original_count = len(lc)

    # Access flux measurements as a masked array
    flux = np.ma.asarray(
        lc.flux.value,
        dtype=float
    )

    # Identify missing and nonfinite flux values
    missing_mask = (
        np.ma.getmaskarray(flux)
        | ~np.isfinite(np.ma.filled(flux, np.nan))
    )

    missing_count = int(np.sum(missing_mask))
    valid_count = original_count - missing_count

    missing_percentage = (
        100 * missing_count / original_count
        if original_count > 0 else np.nan
    )

    print(f"Original observations: {original_count}")
    print(f"Missing/nonfinite flux: {missing_count}")
    print(f"Valid flux measurements: {valid_count}")
    print(f"Missing percentage: {missing_percentage:.2f}%")

    # Inspect quality flag distribution in returned product
    if "quality" in lc.columns:

        quality = np.asarray(
            lc["quality"],
            dtype=int
        )

        flagged = np.sum(quality != 0)

        print(f"Nonzero quality flags in downloaded curve: {flagged}")

    else:
        print("Quality flag column unavailable.")

print("\nQuality assessment complete!")

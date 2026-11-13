
import lightkurve as lk
import numpy as np

# ==========================================
# TJSEF Ellipsoidal Binary Research
# STEP 30: Inspect TESS Quality Flags
# ==========================================

tic_id = "TIC 364768528"
sectors = [14, 15, 16]

for sector in sectors:

    print(f"\n--- Sector {sector} ---")

    results = lk.search_lightcurve(
        tic_id,
        mission="TESS",
        sector=sector,
        author="TESS-SPOC"
    )

    if len(results) == 0:
        print("No observations found.")
        continue

    # Disable Lightkurve quality masking to inspect
    # flags in the source light-curve product.
    lc = results[0].download(
        quality_bitmask="none"
    )

    if lc is None:
        print("Download failed.")
        continue

    quality = np.asarray(lc["quality"], dtype=int)

    flags, counts = np.unique(
        quality,
        return_counts=True
    )

    print(f"Total observations: {len(lc)}")

    for flag, count in zip(flags, counts):

        print(
            f"Quality flag value: {flag} | "
            f"Observations: {count}"
        )

    print(
        f"Total nonzero quality flags: "
        f"{np.sum(quality != 0)}"
    )

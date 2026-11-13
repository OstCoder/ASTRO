
import lightkurve as lk

# ==========================================
# TJSEF Ellipsoidal Binary Research
# STEP 34: Multi-Candidate Sector Search
# ==========================================

# High-scoring candidates from Green et al. (2023)
candidates = [
    120000024,
    384999832,
    372446253,
    388183492,
    408041054,
    279283191,
    351899015,
    470123809
]

print("\n--- MULTI-CANDIDATE SECTOR SEARCH ---")

qualified = []

for tic in candidates:

    print(f"\nChecking TIC {tic}...")

    try:
        results = lk.search_lightcurve(
            f"TIC {tic}",
            mission="TESS"
        )

        sectors = sorted({
            str(mission)
            for mission in results.table["mission"]
        }) if len(results) > 0 else []

        # Identify which sectors have TESS-SPOC products
        tess_spoc_sectors = sorted({
            str(row["mission"])
            for row in results.table
            if str(row["author"]) == "TESS-SPOC"
        }) if len(results) > 0 else []

        print(f"Distinct sectors: {len(sectors)}")
        print(f"TESS-SPOC sectors: {len(tess_spoc_sectors)}")

        if len(sectors) >= 3:
            qualified.append(tic)

            print("Coverage requirement: PASSED")
            print(f"Available sectors: {sectors}")

        else:
            print("Coverage requirement: NOT MET")

    except Exception as error:
        print(f"Search failed: {error}")

print("\n====================================")
print("QUALIFIED CANDIDATES")
print("====================================")

if qualified:
    for tic in qualified:
        print(f"TIC {tic}")
else:
    print("No candidates met the coverage criterion.")

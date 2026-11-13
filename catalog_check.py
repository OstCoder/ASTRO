
from astroquery.vizier import Vizier

# ==========================================
# TJSEF Ellipsoidal Binary Research
# Catalog Verification
# ==========================================

catalog_id = "J/MNRAS/522/29/table3"

# Targets to verify
tic_ids = [
    149603524,
    364768528
]

# Configure VizieR
vizier = Vizier(
    columns=["**"],
    row_limit=10
)

# Use the working Harvard mirror
vizier.VIZIER_SERVER = "vizier.cfa.harvard.edu"
vizier.TIMEOUT = 20

print("\n====================================")
print("TJSEF CATALOG VERIFICATION")
print("====================================")

print("Catalog: Green et al. (2023)")
print(f"Catalog ID: {catalog_id}")

for tic_id in tic_ids:

    print("\n------------------------------------")
    print(f"Searching for TIC {tic_id}...")
    print("------------------------------------")

    try:
        results = vizier.query_constraints(
            catalog=catalog_id,
            TIC=str(tic_id)
        )

        if len(results) > 0 and len(results[0]) > 0:

            print("\nMATCH FOUND!")
            print("Listed as an ellipsoidal-binary candidate.")

            print("\nCatalog Measurements:")
            print(results[0])

            print("\nResearch Status: CANDIDATE")
            print("Further scientific validation required.")

        else:
            print("\nNO MATCH FOUND")
            print("Not found in the selected candidate catalog.")

            print("\nResearch Status: UNVERIFIED")
            print("This does not rule out a binary system.")

    except Exception as error:

        print("\nCatalog lookup failed.")
        print(f"Error: {error}")

        print("\nResearch Status: UNKNOWN")

print("\n====================================")
print("CATALOG CHECK COMPLETE")
print("====================================")

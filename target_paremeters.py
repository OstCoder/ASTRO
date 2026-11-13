
from astroquery.vizier import Vizier

# ==========================================
# TJSEF Ellipsoidal Binary Research
# STEP 35: Retrieve Published Target Parameters
# ==========================================

tic_id = 388183492

catalog_id = "J/MNRAS/522/29/table3"

vizier = Vizier(
    columns=["**"],
    row_limit=10
)

vizier.VIZIER_SERVER = "vizier.cfa.harvard.edu"
vizier.TIMEOUT = 20

print("\n--- Published Binary Parameters ---")
print(f"Target: TIC {tic_id}")

try:
    results = vizier.query_constraints(
        catalog=catalog_id,
        TIC=str(tic_id)
    )

    if len(results) == 0 or len(results[0]) == 0:
        print("No catalog match found.")

    else:
        row = results[0][0]

        print(f"Catalog score: {row['Score']}")
        print(f"Orbital period: {row['Porb']} days")
        print(f"Period uncertainty: {row['e_Porb']} days")
        print(f"Reference epoch T0: {row['T0']} BJD")
        print(f"Epoch uncertainty: {row['e_T0']} days")

except Exception as error:
    print(f"Catalog lookup failed: {error}")

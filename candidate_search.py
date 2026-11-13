
from astroquery.vizier import Vizier

# ==========================================
# TJSEF Ellipsoidal Binary Research
# STEP 32: Find Additional Catalog Candidates
# ==========================================

catalog_id = "J/MNRAS/522/29/table3"

vizier = Vizier(
    columns=["TIC", "Score", "Porb", "e_Porb"],
    row_limit=100
)

vizier.VIZIER_SERVER = "vizier.cfa.harvard.edu"
vizier.TIMEOUT = 30

print("\n--- Searching Published Candidates ---")

try:
    results = vizier.query_constraints(
        catalog=catalog_id,
        Score=">0.99"
    )

    if len(results) == 0 or len(results[0]) == 0:
        print("No matching candidates returned.")

    else:
        table = results[0]

        print(f"Candidates returned: {len(table)}")
        print("\n--- Candidate List ---")

        for row in table[:20]:
            print(
                f"TIC {row['TIC']} | "
                f"Score: {row['Score']} | "
                f"Orbital period: {row['Porb']} days"
            )

except Exception as error:
    print(f"Catalog query failed: {error}")

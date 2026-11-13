import lightkurve as lk
import matplotlib.pyplot as plt
import numpy as np
from astropy.timeseries import LombScargle

tic_id = "TIC 364768528"

# Search for a specific TESS observation
results = lk.search_lightcurve(
    tic_id,
    mission="TESS",
    sector=1,
    author="SPOC"
)

# Download one light curve
lc = results[0].download()

# Remove missing measurements
clean_lc = lc.remove_nans()

# Normalize flux using its median
normalized_lc = clean_lc.normalize()

# Plot the normalized measurements
normalized_lc.plot()

plt.title(f"Normalized TESS Light Curve: {tic_id}")
plt.ylabel("Normalized Flux")
plt.savefig("plots/normalized_lightcurve.png", dpi=300)
plt.show()

# Display basic statistics
print("Original measurements:", len(lc))
print("Valid measurements:", len(clean_lc))
print("Mean normalized flux:", normalized_lc.flux.value.mean())

# Extract numerical measurements
time = np.asarray(normalized_lc.time.value, dtype=float)
flux = np.asarray(normalized_lc.flux.value, dtype=float)

# Convert masked arrays into regular NumPy arrays
if np.ma.isMaskedArray(time):
    time = time.filled(np.nan)

if np.ma.isMaskedArray(flux):
    flux = flux.filled(np.nan)

# Keep only valid measurements
valid = np.isfinite(time) & np.isfinite(flux)
time = time[valid]
flux = flux[valid]

# Save normalized observations
data = np.column_stack((time, flux))

np.savetxt(
    "data/TIC_149603524_sector1_normalized.csv",
    data,
    delimiter=",",
    header="time_btjd,normalized_flux",
    comments=""
)

print("Normalized data saved successfully!")
print("Total saved rows:", len(data))

# STEP 8: Lomb-Scargle period analysis



# Search for periodic signals between 0.5 and 15 days
min_period = 0.5
max_period = 15.0

min_frequency = 1 / max_period
max_frequency = 1 / min_period

# Calculate the periodogram
frequency, power = LombScargle(
    time,
    flux
).autopower(
    minimum_frequency=min_frequency,
    maximum_frequency=max_frequency,
    samples_per_peak=10
)

# Find the strongest periodic signal
best_index = np.argmax(power)
best_frequency = frequency[best_index]
photometric_period = 1 / best_frequency

# Test twice the photometric period as an orbital candidate
orbital_period_candidate = 2 * photometric_period

print("\n--- Period Analysis ---")
print(f"Photometric period: {photometric_period:.5f} days")
print(f"Candidate orbital period: {orbital_period_candidate:.5f} days")

# Plot the periodogram
plt.figure(figsize=(10, 5))
plt.plot(1 / frequency, power)

plt.axvline(
    photometric_period,
    color="red",
    linestyle="--",
    label=f"Strongest period: {photometric_period:.3f} days"
)

plt.xlabel("Period (days)")
plt.ylabel("Lomb-Scargle Power")
plt.title(f"Lomb-Scargle Periodogram: {tic_id}")
plt.legend()
plt.tight_layout()

plt.savefig("plots/periodogram.png", dpi=300)
plt.show()

# STEP 9: Phase folding

# Fold using the photometric period
folded_phot = normalized_lc.fold(period=photometric_period)

plt.figure(figsize=(10, 5))
plt.scatter(
    folded_phot.phase.value,
    folded_phot.flux.value,
    s=2
)
plt.xlabel("Phase")
plt.ylabel("Normalized Flux")
plt.title(f"Phase-Folded Light Curve (Pphot = {photometric_period:.5f} d)")
plt.tight_layout()
plt.savefig("plots/folded_photometric_period.png", dpi=300)
plt.show()

# Fold using twice the photometric period
folded_orb = normalized_lc.fold(period=orbital_period_candidate)

plt.figure(figsize=(10, 5))
plt.scatter(
    folded_orb.phase.value,
    folded_orb.flux.value,
    s=2
)
plt.xlabel("Phase")
plt.ylabel("Normalized Flux")
plt.title(f"Phase-Folded Light Curve (2 × Pphot = {orbital_period_candidate:.5f} d)")
plt.tight_layout()
plt.savefig("plots/folded_orbital_candidate.png", dpi=300)
plt.show()

# STEP 10: Improved phase-folded comparison

periods = [
    ("Photometric", photometric_period),
    ("Double-period", orbital_period_candidate)
]

for name, period in periods:

    folded = normalized_lc.fold(
        period=period,
        normalize_phase=True
    )

    binned = folded.bin(bins=100)

    plt.figure(figsize=(10, 5))

    plt.scatter(
        folded.phase.value % 1,
        folded.flux.value,
        s=1,
        alpha=0.15,
        label="Individual measurements"
    )

    plt.scatter(
        binned.phase.value % 1,
        binned.flux.value,
        s=15,
        color="red",
        label="Binned measurements"
    )

    plt.xlabel("Orbital phase (0 to 1)")
    plt.ylabel("Normalized Flux")
    plt.title(f"{name} Fold: {period:.5f} days")
    plt.legend()
    plt.tight_layout()

    filename = name.lower().replace("-", "_")
    plt.savefig(f"plots/{filename}_binned.png", dpi=300)
    plt.show()
    
# STEP 11: Inspect the deepest flux measurements

# Find the 20 lowest-flux observations
deepest_indices = np.argsort(flux)[:20]

print("\n--- Deepest Flux Measurements ---")

for index in deepest_indices:
    print(
        f"Time: {time[index]:.5f} BTJD | "
        f"Flux: {flux[index]:.6f}"
    )
# STEP 12: Identify separate eclipse events

# Preliminary threshold for unusually deep dips
threshold = 0.992

# Find observations below the threshold
eclipse_times = time[flux < threshold]

# Group observations separated by more than 0.5 days
groups = np.split(
    eclipse_times,
    np.where(np.diff(eclipse_times) > 0.5)[0] + 1
)

# Estimate the midpoint of each group
event_times = np.array([
    np.median(group)
    for group in groups
    if len(group) >= 5
])

print("\n--- Estimated Eclipse Events ---")

for i, event_time in enumerate(event_times, start=1):
    print(f"Eclipse {i}: {event_time:.5f} BTJD")

# Calculate time differences
intervals = np.diff(event_times)

print("\n--- Intervals Between Eclipse Events ---")

for interval in intervals:
    print(f"{interval:.5f} days")
    
# STEP 13: Refine the eclipse recurrence period

# Cycle numbers, accounting for one missing eclipse
cycle_numbers = np.array([0, 1, 2, 4, 5, 6])

# Fit a linear relationship between cycle and eclipse time
period_fit, reference_time = np.polyfit(
    cycle_numbers,
    event_times,
    1
)

# Calculate predicted eclipse times
predicted_times = reference_time + period_fit * cycle_numbers

# Calculate observed-minus-calculated residuals
residuals = event_times - predicted_times

print("\n--- Refined Period Estimate ---")
print(f"Eclipse recurrence period: {period_fit:.6f} days")
print(f"Reference eclipse time: {reference_time:.6f} BTJD")

print("\n--- Eclipse Timing Residuals ---")
for cycle, residual in zip(cycle_numbers, residuals):
    print(f"Cycle {cycle}: {residual:.6f} days")

# STEP 14: Export eclipse timing measurements

eclipse_data = np.column_stack((
    cycle_numbers,
    event_times,
    predicted_times,
    residuals
))

np.savetxt(
    "data/TIC_149603524_eclipse_timings.csv",
    eclipse_data,
    delimiter=",",
    header="cycle,observed_btjd,predicted_btjd,residual_days",
    comments="",
    fmt=["%d", "%.8f", "%.8f", "%.8f"]
)

print("\nEclipse timing data saved successfully!")


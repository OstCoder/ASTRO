# TJSEF Preliminary Photometric Dataset Report

Generated (UTC): 2026-11-08 04:53 UTC

## Scope

- Distinct TIC systems: 5
- TESS sector records: 15
- Input: `features/binary_features.csv` (not modified)
- Outputs: `system_summary.csv`, `sector_features_copy.csv`, and four graphs in `plots/`

## Processing methodology

The previously generated sector records used TESS-SPOC light curves, removal of missing values, per-sector median normalization, a Lomb–Scargle photometric period search (0.2–3 days), a doubled-period candidate, phase folding using catalog orbital period and reference epoch, an unweighted least-squares fit with three Fourier harmonics, and calculation of H₁, H₂, H₃, H₂/H₁, RMSE, and R². The present script aggregates these already-computed features; it does not reprocess light curves.

System-level means are arithmetic means of sector values. The reported standard deviations use sample SD (ddof=1), and CV is 100 × SD / |mean|. These reflect *between-sector descriptive variation*, not measurement error bars or formal confidence intervals. The error bars on mean-feature plots are between-sector SDs.

The mean of the sector-by-sector H₂/H₁ ratios is not generally equal to the ratio of mean H₂ to mean H₁. This report uses the former.

## Preliminary screening flags

- None under these preliminary screening rules

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

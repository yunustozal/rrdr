# Recurring Repairs to Durable Renewal (rrdr)

Open, reproducible code for the paper:

> Tozal, Y. *From Recurring Repairs to Durable Renewal: Using Open Service-Request Data to Identify Chronically Failing Streets and Target Resurfacing.* Submitted to the ASCE *Journal of Infrastructure Systems*. Preprint: [link to be added].

Cities patch the same streets year after year. This workflow uses public pothole service requests (311) to:

1. **find chronic segments**: street segments that generate pothole requests in almost every year of a multi-year period, validated on a later, independent period;
2. **screen correlates of persistence**: utility openings in the public way, transit routes, LiDAR terrain and drainage indicators, soils;
3. **test whether renewal ends the pattern**: an event study and difference-in-differences models comparing renewed segments with segments renewed later;
4. **rank unrenewed chronic segments for renewal**: the cost per pothole above which resurfacing pays for itself on agency costs alone.

The Chicago case study (2011–2025) reproduces every table and figure in the paper.

*This is independent research conducted on personal time with public data. It was not commissioned or endorsed by the author's employer.*

## Quick start (Chicago)

```bash
git clone https://github.com/yunustozal/rrdr.git
cd rrdr
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .

rrdr download --config configs/chicago.yaml            # about 2 GB of public data
rrdr run      --config configs/chicago.yaml            # about 15-30 minutes on a laptop
```

Results are written to `outputs/chicago/`:

| File | Paper |
| --- | --- |
| `concentration_curve.csv`, `figures/Fig1.*` | Fig. 1 |
| `table_validation.csv`, `figures/Fig2.*` | Fig. 2, persistence by street class and threshold |
| `table2_correlates.csv` | Table 2 |
| `fig3_event_study.csv`, `figures/Fig3.*` | Fig. 3 |
| `table3_robustness.csv`, `results_summary.json` (`renewal`) | Table 3 |
| `table4_breakeven.csv`, `breakeven_targets.csv`, `figures/Fig4.*` | Table 4, Fig. 4 |
| `results_summary.json` | every number quoted in the text |

The LiDAR/soil screen is optional and the slowest step; skip it with `--skip-terrain`.

## Using it for another city

Copy `configs/chicago.yaml`, point it at your own files and edit the column names. The core method needs:

1. pothole complaints or work orders with date and coordinates (ideally 8+ years, split into two periods);
2. street centerlines with a functional class and address ranges;
3. resurfacing or reconstruction records with dates and street address ranges (for the renewal analysis);
4. a local resurfacing cost per block.

Opening permits, transit routes, a bare-earth DEM and soils are optional. See [docs/adapting.md](docs/adapting.md).

## Data sources (Chicago)

All inputs are public: City of Chicago Data Portal datasets 7as2-ds3y, v6vf-nfxy, pr57-gg9e, ndbz-vy4e, pubx-yq2d and 6uva-a5ei; Illinois State Geological Survey Cook County DTM 2022; USDA NRCS SSURGO through Soil Data Access. The data are not redistributed here; `rrdr download` retrieves them from the publishers.

## Citation

If you use this code, please cite the paper and the archived software release (see `CITATION.cff`; DOI: [Zenodo DOI to be added]).

## License

Code: MIT License (see `LICENSE`). Data remain subject to the terms of their publishers.

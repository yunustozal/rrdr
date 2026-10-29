# Five-city study: Chicago, New York, Boston, Minneapolis, Pittsburgh

Code for the paper:

> Tozal, Y. E. *Do Chronically Failing Streets Transfer Across Cities? Repair-History Evidence from Five U.S. Cities.* Manuscript under review.

It applies the rrdr method, with the same rules in every city, to test whether chronic pothole failure (requests in at least 80% of the years of an early period) persists in a later period, whether it survives a change of data source, how it relates to pavement condition scores, and whether resurfacing ends it.

## Run

```bash
# 1. Chicago inputs from the main pipeline (from the repository root)
rrdr run --config configs/chicago.yaml --skip-terrain

# 2. Five-city study (from this folder)
cd studies/five_cities
./run_all.sh            # downloads several GB of public data on the first run
```

Set `RRDR_CHICAGO_OUT` if the Chicago outputs are not in `../../outputs/chicago`.

## Scripts

| Step | Script | What it does |
| --- | --- | --- |
| 1 | `01_download_nyc.py` | NYC DOT pothole work orders (x9wy-ing4), DOT resurfacing projects (ffaf-8mrv), street centerline (inkn-q76z) |
| 2 | `02_download_nyc_311.py` | NYC 311 pothole complaints, 2010–2025 (76ig-c548, erm2-nwe9) |
| 3 | `03_download_boston_minneapolis.py` | Boston 311 and street segments; Minneapolis 311, pavement management (PCI) and centerline |
| 4 | `04_download_pittsburgh.py` | Pittsburgh 311, paving schedule and centerlines (WPRDC) |
| 5–7 | `05_nyc_build.py`, `06_nyc_persistence.py`, `07_nyc_match_311.py` | NYC blocks, work-order panel, 311 matching |
| 8–10 | `08_boston.py`, `09_minneapolis.py`, `10_pittsburgh.py` | City panels and first results |
| 11–12 | `11_nyc_cross_source.py`, `12_nyc_311_outcome.py` | Reporting-bias tests; renewal effect with 311 complaints as outcome |
| 13 | `13_harmonized_results.py` | Harmonized persistence, event studies and difference-in-differences for all cities (Tables 2 and 4) |
| 14 | `14_minneapolis_pci.py` | Condition-score comparison (Figure 3) |
| 15 | `15_figures.py` | Figures 1–3 |

Outputs: `out/harmonized.json`, `out/nyc_cross.json`, `out/mpls_pci.json`, `out/figs/`.

## Notes

- New York road class is a proxy based on snow plowing priority, because the citywide centerline has no functional class.
- Boston 311 files for 2011 and 2014 were not available through the portal's data interface and are not used.
- Minneapolis PCI values come from 2010–2014 inspections.
- Pittsburgh's paving feed stopped updating in 2021.
- Data are not redistributed; the download scripts retrieve them from the publishers.

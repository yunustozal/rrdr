# Adapting the workflow to another city

1. **Create a config.** Copy `configs/chicago.yaml` to `configs/<city>.yaml`. Set `city`, `crs` (a projected CRS in feet; if yours is in metres, convert the `*_ft` settings), `data_dir` and `output_dir`.

2. **Requests.** Split your pothole records into two periods. Period 1 (for example 8 years) defines chronic segments; period 2 validates them and supports the renewal analysis. For each period give the file name, the year range and the column names for date, latitude, longitude and street name (or an address column from which the street name is parsed). Optional filters: request type, status, duplicate flag. If period 1 records how many potholes were filled per request, map it to `filled`; the break-even step needs it.

3. **Centerlines.** Map the street name, direction prefix, functional class, length in feet and the address-range fields. List which class codes are roads (`classes_all_roads`) and which enter the analysis (`classes_analysis`).

4. **Renewals.** Any table of resurfacing or reconstruction with a date, street name, direction prefix and an address range works (moratoria, paving programme lists, bid documents). Remove the `renewals` section if you have none; persistence and correlates still run.

5. **Optional layers.** `openings`, `transit_routes`, `terrain` and `soils` can be removed or set to `enabled: false`.

6. **Costs.** Set `resurfacing_cost_per_block`, `block_length_m` and the scenarios you want. The output reports the break-even cost per pothole, so you do not need a patch cost to run it; compare the result with your own cost per pothole.

7. **Run** `rrdr run --config configs/<city>.yaml`.

Checks worth doing for a new city: the share of requests matched to segments (printed by the matching step; above 90% is typical when street names are clean), and whether renewal records cover the period 2 years.

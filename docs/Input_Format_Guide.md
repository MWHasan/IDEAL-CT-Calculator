# Input Format Guide

The calculator reads CSV files in two forms: a generic custom format and compatible equipment/export files.

## Custom CSV format

The custom format is the recommended format for new users because it does not depend on a particular instrument's column names or export layout.

A typical file is structured as follows:

```text
Parameter,Value,Unit
Specimen ID,Example-01,
Asphalt Mixture Type,Example Mix,
Specimen Type,LMLC,
Diameter,150,mm
Thickness,62,mm
NMAS,12.5,mm
Air Voids,7.0,%
Test Temperature,25,deg C
Aging Condition,Short-term aged,

Time (sec),Load (kN),Displacement (mm)
0.000,0.000,0.000
...
```

### Calculation inputs

The data table must contain numeric values for:

- time, in seconds;
- load, in kN; and
- load-line displacement (LLD), in mm.

The specimen diameter and thickness are used directly in Gf and CTIndex.

### Recommended metadata

The following fields correspond to information needed for ASTM-oriented reporting and QC:

- Specimen ID
- Asphalt Mixture Type
- Specimen Type
- Diameter
- Thickness
- NMAS
- Air Voids
- Test Temperature
- Aging Condition

The data reader also recognizes `Sample ID`, `Specimen`, `Mixture Type`, `Temperature`, `Average Diameter`, and `Average Height` where applicable.

### Column aliases

The reader recognizes common alternatives for the three data columns. Examples include:

| Quantity | Recognized examples |
|---|---|
| Time | `Time`, `Time (sec)`, `Time (s)` |
| Load | `Load`, `Force`, `Load Cell`, `Load (kN)`, `Force (kN)` |
| LLD | `Displacement`, `LVDT`, `Frame LVDT`, `LLD`, `Load Line Displacement` |

Column names are normalized for case and spacing before alias matching.

## Equipment/export files

The calculator first locates the row containing time, load, and displacement/LLD headings. This allows metadata or other equipment information to appear above the data table.

The reader does not remove the first numerical data row. Earlier versions of the calculator had a blanket first-row deletion; that behavior is intentionally not used here because the first recorded point may be legitimate test data.

## Baseline correction

By default, the calculator subtracts the first recorded load and displacement values before the CTIndex calculations. This behavior is retained for compatibility with the existing project implementation.

A non-zero initial load produces a QC warning because baseline subtraction is an analysis choice rather than a statement that the initial seating or preload is irrelevant. Users should inspect the test record before treating the result as an ASTM-based test result.

Baseline correction can be disabled when calling `analyze_ct_file()`:

```python
results, data, input_format = analyze_ct_file(
    "test.csv",
    baseline_correction=False,
)
```

## Terminal load and record length

D8225-26 specifies that testing stops when the measured load drops below 100 N (0.1 kN). When enabled, the calculator cuts the analysis record at the first post-peak measured-load point below 0.1 kN. This check uses the raw load value even when baseline normalization is applied to the calculation data.

If the supplied file never reaches below 0.1 kN, the calculator retains the available record and reports a QC warning. It does not label the record as a complete ASTM test.

## Sampling rate

D8225-26 requires at least 40 data points per second for time, load, and LLD. The calculator estimates the rate from the median positive time increment.

## Displacement-rate diagnostic

D8225-26 specifies an LLD rate of 50 ± 2 mm/min. The calculator reports a simple full-record displacement-rate estimate as a diagnostic. Because the measured displacement can include seating and post-failure behavior, this estimate is not a substitute for review of the actual machine control interval.

## Post-peak slope fallback flag

The preferred calculation uses linear regression with all post-peak data points between P85 and P65. If there are too few points in that interval for regression, the calculator retains the project fallback calculation based on the P85 and P65 values. The exported summary reports `Post-Peak Slope Fallback Used` as `True` when this fallback is used.

## Common mistakes to avoid

- Do not place explanatory text inside the numerical data rows.
- Do not mix units within one file.
- Do not replace missing numeric values with zeros unless zero is the measured value.
- Keep the complete recorded time, load, and LLD series in the input file.
- For the custom format, leave the metadata section above the data-table header.

## Example files

- `examples/IDEAL_CT_Custom_Template.csv` — blank custom structure.
- `examples/IDEAL_CT_Custom_Example.csv` — populated custom example.
- `examples/Original_Equipment_Format_Example.csv` — equipment/export structure used to demonstrate column recognition.

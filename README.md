# IDEAL-CT Calculator

Python software for calculating IDEAL-CT parameters from load, load-line displacement (LLD), and time data.

The calculation workflow implements selected calculations and data-quality checks described in **ASTM D8225-26, Standard Test Method for Determination of Cracking Tolerance Index of Asphalt Mixture Using the Indirect Tensile Cracking Test at Intermediate Temperature**. The software is not an ASTM certification tool and does not determine whether a laboratory has met every requirement of the test method.

## ASTM D8225-26 calculations

For each specimen, the calculator reports the following D8225-26 calculation outputs:

- Maximum load, Pmax
- Work of failure, Wf
- Failure energy, Gf
- P85, P75, and P65
- l85, l75, and l65
- Post-peak slope, |m75|
- CTIndex

Indirect tensile strength (St) and selected data-quality diagnostics are also reported because they support the additional research output and QC review.

### Additional research parameters

- Fracture Strain Tolerance (FST), reported separately from the ASTM D8225-26 results

The program keeps full numerical precision during calculation. The ASTM reporting precision is applied to the exported summary presentation.

### Fracture Strain Tolerance (FST)

The calculator also reports **Fracture Strain Tolerance (FST)** as an additional research parameter. FST is not a required result in ASTM D8225-26 and is not used in the CTIndex calculation.

The FST implementation follows the formulation reported by the Virginia Transportation Research Council (VTRC) in its IDT-CT interlaboratory studies. VTRC FHWA/VTRC 23-R3 defines FST from failure energy and indirect tensile strength as:

```text
FST = (Gf / St) × 10^6
```

where VTRC expresses `Gf` in kN/mm and `St` in kPa. In this calculator, `Gf` is stored as J/m², so the numerically equivalent implementation is `FST = Gf / St`, with FST reported in mm. The VTRC studies treated FST as an IDT-CT performance index alongside CT index, strength, and CRI. [VTRC FHWA/VTRC 23-R3](https://vtrc.virginia.gov/media/vtrc/vtrc-pdf/vtrc-pdf/23-R3.pdf).

FST is presented separately from the ASTM D8225-26 results. It is not used in the CTIndex calculation and should not be interpreted as an ASTM D8225-26 reporting requirement.

## Input formats

Two CSV formats are supported.

### 1. Custom CSV — recommended

Use the template in `examples/IDEAL_CT_Custom_Template.csv`. The file contains a metadata section followed by the test data table.

Required data columns:

```text
Time (sec),Load (kN),Displacement (mm)
```

The displacement column represents load-line displacement (LLD). For ASTM-oriented reporting, provide the specimen diameter, thickness, mixture type, specimen type, NMAS, air voids, test temperature, and aging condition when available.

### 2. Equipment/export CSV

Existing compatible equipment exports can be processed without manual conversion when the file contains recognizable time, load, and displacement/LLD column names. Common aliases include `Load`, `Force`, `Load Cell`, `LVDT`, `LLD`, and `Load Line Displacement`.

`examples/Original_Equipment_Format_Example.csv` is included to show the type of legacy equipment structure the reader can accept. Its equipment metadata should not be interpreted as an ASTM IDEAL-CT test record on its own.

## Installation

Python 3.10 or newer is recommended.

Install the runtime dependencies with:

```bash
pip install -r requirements.txt
```

## Data normalization

The test is normally performed after the specimen is seated in the fixture, so the recorded load may begin with a non-zero seating load and the displacement transducer may not start at zero. To place the analysis on a common zero reference, the calculator subtracts the first recorded load and first recorded LLD value by default.

This normalization is applied after the input reader converts both supported CSV formats to the same internal `Time`, `Load Cell`, and `Frame LVDT` columns. Therefore, equipment/export files and custom CSV files receive the same zero-reference treatment. The original first recorded data point is retained; it is not discarded.

You can disable this normalization explicitly when using `analyze_ct_file()`:

```python
results, data, input_format = analyze_ct_file(
    "test.csv",
    baseline_correction=False,
)
```

## Run a batch analysis

Place the CSV files to be analyzed in one directory and run:

```bash
python CT_Index_calculator.py
```

The program looks for CSV files in the current working directory and writes results to `Results/`.

Each specimen produces an Excel workbook containing:

- `Normalized Data` — processed time, load, displacement, stress, and energy data
- `Summary Results` — calculation results, metadata, and QC warnings

The batch workbook `Summary_Results_CT.xlsx` contains summary statistics and an average load-displacement curve.

## Run one specimen from Python

```python
from CT_Index_calculator import analyze_ct_file

results, data, input_format = analyze_ct_file(
    "examples/IDEAL_CT_Custom_Example.csv"
)

print(results["CTIndex"])
print(results["QC Warnings"])
```

## ASTM D8225-26 calculation basis

The implementation follows the supplied D8225-26 definitions and equations for the core numerical results:

- **Wf:** area under the load-LLD curve using the quadrangle rule. For sequential data points, the implemented expression is the equivalent trapezoidal summation.
- **Gf:** `Wf / (D × t) × 10^6`, giving J/m² when Wf is in J and D and t are in mm.
- **l75:** post-peak displacement at 75% of the peak load.
- **|m75|:** linear-regression slope using all post-peak data points between P85 and P65. The calculation is performed in kN/mm; the reported ASTM unit is MN/m, with the same numerical value. If regression cannot be performed, the existing project fallback is used and flagged in the results as `Post-Peak Slope Fallback Used`.
- **CTIndex:** `(t / 62) × (l75 / D) × (Gf / |m75|)`.

See `docs/ASTM_D8225_26_Methodology.md` for the calculation details and QC scope.

## Quality-control diagnostics

The program reports warnings for selected requirements that can be evaluated from the supplied file, including:

- whether the post-peak measured load reached below 0.1 kN;
- estimated sampling frequency below 40 samples/s;
- a full-record displacement-rate estimate outside 50 ± 2 mm/min;
- specimen-dimension issues that can be classified from the supplied specimen type and NMAS;
- missing reporting metadata; and
- fewer than five specimens in a batch.

These checks are diagnostics. They cannot verify equipment calibration, conditioning history, specimen preparation, operator practice, or other laboratory requirements that are not contained in the CSV data.

## Specimen dimensions used for QC

D8225-26 specifies a nominal 150 ± 2 mm diameter.

For laboratory-compacted specimens:

- NMAS ≤ 20 mm: 62 ± 1 mm thickness
- NMAS > 20 mm: 95 ± 1 mm thickness

Roadway cores may be used when the pavement layer is more than 38 mm thick; the core specimen should be prepared as thick as possible and must not be less than 38 mm thick.

The calculator therefore does not assume that every valid laboratory specimen is 150 × 62 mm. Thickness is also retained in the CTIndex correction.




# ASTM D8225-26 Methodology and Quality-Control Scope

This document describes the part of ASTM D8225-26 implemented in the calculator. It does not reproduce the standard. Users should consult the official ASTM document for the complete test procedure and requirements.

## Method basis

The software is based on **ASTM D8225-26**, *Standard Test Method for Determination of Cracking Tolerance Index of Asphalt Mixture Using the Indirect Tensile Cracking Test at Intermediate Temperature* (DOI: 10.1520/D8225-26).

The standard defines the CTIndex from failure energy, post-peak slope, post-peak displacement at 75% of peak load, specimen diameter, and specimen thickness.

## Calculated parameters

### Work of failure, Wf

Wf is the area under the load versus LLD curve. D8225-26 specifies the quadrangle rule. For adjacent recorded points, the expression used in the program is the equivalent trapezoidal summation:

```text
Wf = sum( (P_i + P_i+1) / 2 × (l_i+1 - l_i) )
```

When load is in kN and displacement is in mm, the product is numerically in J because 1 kN·mm = 1 J.

### Failure energy, Gf

The program calculates:

```text
Gf = Wf / (D × t) × 10^6
```

where D and t are in mm. The result is J/m².

### Post-peak load levels

The program defines:

```text
P85 = 0.85 × Pmax
P75 = 0.75 × Pmax
P65 = 0.65 × Pmax
```

The post-peak displacements l85, l75, and l65 are obtained by linear interpolation between recorded points surrounding the respective load level.

### Post-peak slope, |m75|

The program performs linear regression using all post-peak data points between P85 and P65. The regression is performed using displacement in mm and load in kN, so the numerical slope is in kN/mm. This numerical value is the same as the ASTM reporting value in MN/m.

### CTIndex

The implemented equation is:

```text
CTIndex = (t / 62) × (l75 / D) × (Gf / |m75|)
```

The thickness term is retained because D8225-26 applies a correction for specimen thickness relative to 62 mm.

## Data termination

D8225-26 specifies stopping the test when the load drops below 100 N (0.1 kN). The calculator checks the post-peak data for the first point below 0.1 kN and, by default, ends the numerical analysis at that point.

A file that ends before this condition is reached is not presented as a complete ASTM test record. The calculator reports a QC warning and continues using the data supplied so that exploratory analysis is still possible.

## Sampling frequency

The standard requires a minimum of 40 data points per second for time, load, and LLD. The calculator estimates sampling frequency from the median positive time increment:

```text
sampling rate = 1 / median(dt)
```

A value below 40 Hz generates a warning. The check is based only on the supplied time series and cannot confirm the performance of the data-acquisition system itself.

## LLD rate

D8225-26 specifies an LLD control rate of 50 ± 2 mm/min. The calculator reports a full-record displacement-rate estimate for diagnostic purposes.

This estimate is deliberately not treated as a full procedural compliance test because the complete recorded displacement history can include initial seating and post-failure behavior.

## Specimen dimensions

For laboratory-compacted specimens, D8225-26 specifies:

- 150 ± 2 mm diameter and 62 ± 1 mm thickness for NMAS ≤ 20 mm;
- 150 ± 2 mm diameter and 95 ± 1 mm thickness for NMAS > 20 mm.

Roadway cores are also permitted. They are prepared as thick as possible and must not be less than 38 mm thick; D8225-26 still applies the thickness correction in CTIndex.

The calculator therefore does not assume that every valid specimen has a 62 mm thickness.

## Specimen count

D8225-26 specifies a minimum of five specimens for laboratory mixtures and roadway cores. The batch program issues a warning when fewer than five records are successfully analyzed. It does not block calculation of smaller exploratory datasets.

## Reporting fields

The calculator supports the principal specimen-level fields identified for reporting by D8225-26, including mixture type, test temperature, preparation/aging information, air voids, thickness, diameter, l75, |m75|, Gf, and CTIndex.

The exported summary uses the reporting precision specified by the standard while retaining full precision internally.

## Additional research parameter: Fracture Strain Tolerance (FST)

FST is retained in this calculator as an **additional research parameter**. It is not a parameter specified in ASTM D8225-26 and it does not enter the ASTM CTIndex equation. It is therefore reported separately from the ASTM results.

The FST calculation follows the formulation used in the Virginia Transportation Research Council (VTRC) IDT-CT interlaboratory studies. FHWA/VTRC 23-R3 defines the FST index as:

```text
FST = (Gf / St) × 10^6
```

In that formulation, `Gf` is the total area under the load-displacement curve divided by specimen thickness and diameter, expressed in kN/mm, and `St` is indirect tensile strength in kPa. The same equations are presented in VTRC 21-R16. 

This calculator stores `Gf` as J/m². Because 1 kN/mm = 10^6 J/m², the VTRC equation can be evaluated numerically as:

```text
FST [mm] = Gf [J/m²] / St [kPa]
```

The tensile strength used here is the indirect tensile strength calculated from the peak load and specimen dimensions. FST is not used to calculate CTIndex.

VTRC treated FST as one of several performance indices evaluated from IDT-CT data and developed precision estimates for it in its interlaboratory studies. This research use should not be interpreted as an ASTM D8225-26 requirement.

**References**

- Habbouche, J., Boz, I., and Diefenderfer, B. (2022). *Interlaboratory Study for the Indirect Tensile Cracking Test at Intermediate Temperature: Phase II*. FHWA/VTRC 23-R3. Virginia Transportation Research Council. https://vtrc.virginia.gov/media/vtrc/vtrc-pdf/vtrc-pdf/23-R3.pdf
- Habbouche, J., Boz, I., and Diefenderfer, B. (2021). *Laboratory and Field Performance Evaluation of Pavement Sections With High Polymer-Modified Asphalt Overlays*. FHWA/VTRC 21-R16. Virginia Transportation Research Council. https://vtrc.virginia.gov/media/vtrc/vtrc-pdf/vtrc-pdf/21-R16.pdf

## What this software does not determine

The calculator cannot independently establish:

- equipment calibration or load-cell capacity;
- displacement-device resolution or system-compliance correction;
- specimen conditioning duration or actual specimen temperature;
- specimen fabrication or preparation history;
- operator practice;
- whether the physical test fixture meets every requirement of the standard; or
- any other procedural condition that is not represented in the input data.

For these reasons, a numerical result from this program should not be described as an ASTM certification or as proof of full procedural compliance.

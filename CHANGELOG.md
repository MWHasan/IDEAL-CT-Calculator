# Changelog

## [0.1.3] - Development version

### Changed
- The ASTM 0.1 kN termination check now uses the raw measured load, while baseline-normalized load remains the basis for the calculation workflow.
- The post-peak slope calculation retains the existing P85-P65 fallback when linear regression cannot be performed, and the result now includes an explicit `Post-Peak Slope Fallback Used` flag.
- Updated the software version to 0.1.3.


## [0.1.2] - Development version

### Changed
- Clarified the distinction between ASTM D8225-26 calculation outputs and additional research parameters.
- Clarified the default zero-reference normalization applied to both supported input formats.
- Renamed the displacement-rate diagnostic output to `Full-Record Displacement Rate Estimate [mm/min]`.
- Renamed the internal peak-load time variable for clarity.

## [0.1.1] - Development version

### Added
- Fracture Strain Tolerance (FST) as an additional research parameter, following the formulation reported by the Virginia Transportation Research Council (VTRC) for IDT-CT data.

### Changed
- FST is reported separately from the ASTM D8225-26 results and is not used in CTIndex.
- The FST documentation now identifies VTRC FHWA/VTRC 23-R3 and FHWA/VTRC 21-R16 as the research sources for the formulation.
- The result field for indirect tensile strength is labelled `Tensile Strength (St) [kPa]`.

## [0.1.0] - Development version

### Added
- Custom equipment-independent CSV input format.
- Backward-compatible recognition of supported equipment-export columns.
- ASTM D8225-26 calculations for Wf, Gf, l85/l75/l65, |m75|, and CTIndex.
- Checks for the D8225-26 0.1 kN test endpoint, 40 Hz sampling requirement, specimen dimensions, reporting metadata, and five-specimen batch minimum.
- ASTM-oriented formatting for exported summary results.

### Changed
- Kept full numerical precision during calculation and applied reporting precision only to the exported summary presentation.
- Removed the blanket first-data-row deletion from the input reader.
- Improved dimensional QC so roadway cores are not treated as invalid 62 mm laboratory specimens.

See `docs/ASTM_D8225_26_Methodology.md` for the calculation details and QC scope.

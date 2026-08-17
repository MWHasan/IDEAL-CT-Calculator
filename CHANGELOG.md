# Changelog

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
